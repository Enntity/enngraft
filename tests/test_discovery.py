import json
from pathlib import Path
import tempfile
import unittest

from enngraft import install
from enngraft.discovery import inventory
from test_installer import FixtureTarget


class Planner:
    model = "test-planner"

    def __init__(self, plan):
        self.response = plan
        self.calls = []

    def plan(self, packet):
        self.calls.append(packet)
        return self.response


class DiscoveryTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve() / "example"
        self.root.mkdir()
        self.prefix = self.root.parent / "install"
        self.plan = {"build": ["sh", "build.sh"], "entry": "hello", "outputs": ["hello"],
                     "checks": [{"args": [], "stdout": "hello\n"}]}
        (self.root / "hello.sh").write_text("#!/bin/sh\necho hello\n")
        (self.root / "build.sh").write_text("cp hello.sh hello && chmod +x hello\n")

    def test_model_plans_without_manifest_and_keeps_checkout_clean(self):
        agent = Planner(self.plan)
        (self.root / ".env").write_text("sensitive")
        (self.root / "credentials.py").write_text("sensitive")
        (self.root / "copy.c").symlink_to(self.root / ".env")
        receipt = install(self.root, self.prefix, FixtureTarget(), agent)
        packet, = agent.calls
        self.assertEqual(set(packet["files"]), {"hello.sh", "build.sh"})
        self.assertIn("machine", packet["target"])
        self.assertEqual(receipt["contract_source"], "model")
        self.assertFalse((self.root / "graft.json").exists())
        stored = (self.prefix / "current").resolve().parent / "contract.json"
        self.assertEqual(json.loads(stored.read_text())["checks"], self.plan["checks"])

    def test_plan_messages_follow_execution_and_never_enter_the_contract(self):
        captions = {"build": "Compiling hello", "check": "Checking its greeting"}
        reports = []
        agent = Planner({**self.plan, "progress": captions})
        install(self.root, self.prefix, FixtureTarget(), agent, progress=reports.append)
        self.assertEqual(reports[-2:], list(captions.values()))
        contract = json.loads((self.prefix / "current").resolve().parent.joinpath("contract.json").read_text())
        self.assertNotIn("progress", contract)
        reports.clear()
        agent.response["progress"] = {"build": "bad\x1b[2J", "check": "bad\ncommand"}
        install(self.root, self.prefix, FixtureTarget(), agent, progress=reports.append)
        self.assertEqual(reports[-2:], ["Building hello…", "Checking hello…"])

    def test_ignored_files_and_output_limits(self):
        import subprocess
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / ".gitignore").write_text("local.py\n")
        (self.root / "local.py").write_text("ignore")
        self.assertNotIn("local.py", inventory(self.root))
        for plan in ({**self.plan, "entry": "../out"}, {**self.plan, "checks": []},
                     {**self.plan, "checks": [{"args": [], "stdout": ""}]}):
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                install(self.root, self.prefix, FixtureTarget(), Planner(plan))
        self.assertFalse((self.prefix / "current").exists())

    def test_explicit_manifest_takes_precedence_even_when_invalid(self):
        (self.root / "graft.json").write_text("{}")
        agent = Planner(self.plan)
        with self.assertRaisesRegex(ValueError, "manifest"):
            install(self.root, self.prefix, FixtureTarget(), agent)
        self.assertFalse(agent.calls)

    def test_zero_budget_does_not_call_planner(self):
        agent = Planner(self.plan)
        with self.assertRaisesRegex(ValueError, "No unambiguous local recipe"):
            install(self.root, self.prefix, FixtureTarget(), agent, repairs=0)
        self.assertFalse(agent.calls)

    def test_readme_example_catches_a_model_check_that_misses_a_bug(self):
        (self.root / "README.md").write_text("```console\n$ hello\ncorrect\n```\n")
        class Stop(Planner):
            def propose(self, packet):
                self.failure = packet["failure"]
                return {"stop": "fixture stopping after detection"}
        agent = Stop(self.plan)
        with self.assertRaisesRegex(ValueError, "Agent stopped"):
            install(self.root, self.prefix, FixtureTarget(), agent)
        self.assertEqual(agent.failure["phase"], "check")
        self.assertFalse((self.prefix / "current").exists())

    def test_exit_and_stderr_are_part_of_acceptance(self):
        (self.root / "hello.sh").write_text("#!/bin/sh\necho usage >&2\nexit 2\n")
        contract = {**self.plan, "version": 1, "name": "demo", "files": ["hello.sh", "build.sh"],
                    "editable": [], "checks": [{"args": [], "stdout": "", "stderr": "usage\n", "exit": 2}]}
        (self.root / "graft.json").write_text(json.dumps(contract))
        install(self.root, self.prefix, FixtureTarget())
        (self.root / "hello.sh").write_text("#!/bin/sh\necho usage >&2\nexit 0\n")
        with self.assertRaisesRegex(ValueError, "Installation failed"):
            install(self.root, self.prefix, FixtureTarget())

    def test_node_bin(self):
        (self.root / "package.json").write_text('{"bin":{"hello":"./hello.sh"}}')
        receipt = install(self.root, self.prefix, FixtureTarget())
        self.assertEqual(receipt["contract_source"], "metadata")
