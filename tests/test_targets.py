import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from enngraft import DockerTarget, MacTarget, install

FIXTURE = Path(__file__).resolve().parents[1] / "examples/hoststamp"


class KnownRepair:
    model = "deterministic-test-fixture"

    def propose(self, packet):
        return {"edits": {"build.sh": 'exec cc -std=c11 hoststamp.c -o hoststamp\n',
                          "hoststamp.c": packet["files"]["hoststamp.c"].replace(
                              "#include <windows.h>", "#include <sys/utsname.h>").replace(
                              "SYSTEM_INFO sys;", "struct utsname sys;").replace(
                              "GetNativeSystemInfo(&sys);", "if (uname(&sys)) return 1;").replace(
                              'sys.wProcessorArchitecture == PROCESSOR_ARCHITECTURE_AMD64 ? "x86_64" : "unknown"',
                              "sys.machine")}}


@unittest.skipUnless(os.getenv("GRAFT_TEST_TARGET"), "select a real target for the integration suite")
class RealTarget(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        choice = os.environ["GRAFT_TEST_TARGET"]
        cls.target = MacTarget() if choice == "macos" else DockerTarget(choice)

    def test_build_verify_and_launch(self):
        with tempfile.TemporaryDirectory() as d:
            prefix = Path(d).resolve()
            project = prefix / "source"
            shutil.copytree(FIXTURE, project)
            shutil.copyfile(FIXTURE.parent / "manifests/hoststamp.json", project / "graft.json")
            receipt = install(project, prefix, self.target, KnownRepair())
            self.assertEqual(len(receipt["repairs"]), 1)
            if isinstance(self.target, DockerTarget):
                self.assertEqual(receipt["target"]["executor_limits"]["memory_bytes"], 512 * 1024**2)
            result = self.target.run(["./hoststamp", "--bytes", "another input"], prefix / "current", False)
            self.assertEqual((result.code, result.stdout), (0, "13\n"))

    def test_installed_command_from_project_directory(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d).resolve() / "demo"
            project.mkdir()
            cmd = ["enngraft", "."]
            env = dict(os.environ)
            for key in ("GRAFT_ENDPOINT", "GRAFT_MODEL", "GRAFT_API_KEY"):
                env.pop(key, None)
            if isinstance(self.target, DockerTarget):
                # The Docker client uses HOME to locate the owner's context.
                prefix = project / "installed"
                env["GRAFT_IMAGE"] = self.target.image
                cmd += ["--prefix", str(prefix)]
            else:
                env["HOME"] = str(project)
                prefix = project / ".local/share/enngraft" / project.name
            (project / "hello.sh").write_text("#!/bin/sh\necho ready\n")
            result = subprocess.run(cmd, cwd=project, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(json.loads(result.stdout)["executable"]), prefix / "current/hello.sh")
            self.assertEqual(json.loads(result.stdout)["contract_source"], "metadata")
            check = self.target.run(["./hello.sh"], prefix / "current", False)
            self.assertEqual((check.code, check.stdout), (0, "ready\n"))

    def test_build_isolation_and_readonly_check(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            work = root / "build"
            work.mkdir()
            outside = root / "private-marker"
            outside.write_text("private test data")
            cmd = ["/bin/sh", "-ec", 'test -z "${GRAFT_API_KEY:-}"; ! cat "$1"; touch writable',
                   "build", str(outside)]
            result = self.target.run(cmd, work, True)
            self.assertEqual(result.code, 0, result)
            self.assertNotIn("private test data", result.stdout)
            self.assertTrue((work / "writable").exists())
            self.assertNotEqual(self.target.run(["touch", "forbidden"], work, False).code, 0)
