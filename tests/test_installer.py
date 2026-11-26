import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from enngraft import Model, install, rollback
from enngraft.__main__ import main
from enngraft.controller import locked
from enngraft.runners import execute


class FixtureTarget:
    def facts(self, directory):
        return {"machine": "fixture", "os": "test"}

    def run(self, args, directory, writable):
        return execute(args, directory, {"PATH": "/usr/bin:/bin"}, 3)


class Repair:
    model = "test-adapter"

    def __init__(self, answer):
        self.answer = answer
        self.packets = []

    def propose(self, packet):
        self.packets.append(packet)
        return self.answer


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.prefix = self.root / "prefix"
        self.target = FixtureTarget()
        self.manifest = {"version": 1, "name": "test", "files": ["program"], "editable": ["program"],
                         "build": ["cp", "program", "tool"], "outputs": ["tool"], "entry": "tool",
                         "checks": [{"args": [], "stdout": "working\n"}]}
        self.manifest_write()
        self.program = self.root / "program"
        self.good = "#!/bin/sh\necho working\n"
        self.program.write_text(self.good)
        self.program.chmod(0o755)

    def manifest_write(self):
        (self.root / "graft.json").write_text(json.dumps(self.manifest))

    def go(self, agent=None, repairs=3):
        return install(self.root, self.prefix, self.target, agent, repairs)

    def test_healthy_is_offline_and_rollback_selects_previous(self):
        first = self.go()
        self.assertIsNone(first["model"])
        second = self.go(Repair({"stop": "unexpected cloud call"}))
        self.assertEqual(second["previous"], f"releases/{first['release']}/app")
        self.assertEqual(rollback(self.prefix), second["previous"])
        self.assertEqual(subprocess.check_output([self.prefix / "current/tool"]), b"working\n")

    def test_failed_check_then_repair_in_clean_stage(self):
        bad = "#!/bin/sh\necho broken\n"
        self.program.write_text(bad)
        self.manifest["build"] = ["/bin/sh", "-ec", "test ! -e stale && touch stale && cp program tool"]
        self.manifest_write()
        agent = Repair({"edits": {"program": self.good}})
        receipt = self.go(agent)
        self.assertEqual(agent.packets[0]["failure"]["phase"], "check")
        self.assertEqual(receipt["repairs"][0]["changed"], ["program"])
        self.assertEqual(self.program.read_text(), bad)

    def test_tty_gets_steps_and_a_runnable_command_and_json_is_opt_in(self):
        with patch("enngraft.__main__.MacTarget", return_value=self.target), patch.dict(os.environ, {}, clear=True):
            for as_json in (False, True):
                with self.subTest(as_json=as_json), patch("sys.stdout", new_callable=io.StringIO) as out:
                    out.isatty = lambda: True
                    args = [str(self.root), "--prefix", str(self.prefix)]
                    self.assertEqual(main(args + (["--json"] if as_json else [])), 0)
                    if as_json:
                        self.assertEqual(json.loads(out.getvalue())["entry"], "tool")
                    else:
                        self.assertIn("Checking tool", out.getvalue())
                        self.assertIn("Installed tool.", out.getvalue())
                        self.assertIn("Run: enngraft go --prefix ", out.getvalue())

    def test_go_forwards_arguments_streams_and_exit_status(self):
        self.program.write_text("#!/bin/sh\nif [ $# = 0 ]; then echo working; exit; fi\n"
                                "printf '%s\\n' \"$@\"; cat; exit 7\n")
        self.go()
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
        proc = subprocess.run([sys.executable, "-m", "enngraft", "go", "--prefix", str(self.prefix),
                               "--", "--prefix", "two words", "; echo no"],
                              cwd=self.root, env=env, input="stdin\n", capture_output=True, text=True)
        self.assertEqual(proc.returncode, 7, proc.stderr)
        self.assertEqual(proc.stdout, "--prefix\ntwo words\n; echo no\nstdin\n")

    def test_rejects_check_spoof_on_stderr(self):
        self.program.write_text("#!/bin/sh\necho working >&2\n")
        with self.assertRaisesRegex(ValueError, "Installation failed"):
            self.go()

    def test_invalid_edit_keeps_selected_release(self):
        self.go()
        active = os.readlink(self.prefix / "current")
        self.program.write_text("#!/bin/sh\nexit 1\n")
        for answer in ({"edits": {"../outside": "x"}}, {"edits": {"graft.json": "{}"}},
                       {"edits": {"program": self.program.read_text()}}, {"stop": "missing dependency"}):
            with self.subTest(answer=answer), self.assertRaises(ValueError):
                self.go(Repair(answer))
        self.assertEqual(os.readlink(self.prefix / "current"), active)

    def test_budget_and_readonly_contract(self):
        self.manifest["checks"][0]["stdout"] = "impossible\n"
        self.manifest_write()
        agent = Repair({"edits": {"program": self.good + "# retry\n"}})
        with self.assertRaisesRegex(ValueError, "Installation failed"):
            self.go(agent, 1)
        self.assertEqual(len(agent.packets), 1)
        self.assertFalse((self.prefix / "current").exists())

    def test_symlinks_are_rejected_for_input_and_output(self):
        self.program.rename(self.root / "outside")
        self.program.symlink_to(self.root / "outside")
        with self.assertRaisesRegex(ValueError, "regular file"):
            self.go()
        self.program.unlink()
        (self.root / "outside").rename(self.program)
        self.manifest["build"] = ["ln", "-s", str(self.program), "tool"]
        self.manifest_write()
        with self.assertRaisesRegex(ValueError, "collect"):
            self.go()

    def test_concurrent_writer_and_wrong_package(self):
        with locked(self.prefix), self.assertRaisesRegex(ValueError, "Another install"):
            self.go()
        self.go()
        self.manifest["name"] = "other"
        self.manifest_write()
        with self.assertRaisesRegex(ValueError, "another application"):
            self.go()

    def test_timeout_and_output_bound(self):
        self.assertEqual(execute(["/bin/sleep", "1"], self.root, {}, 0.05).code, 124)
        self.assertEqual(execute(["/usr/bin/yes"], self.root, {}, 2).code, 125)
