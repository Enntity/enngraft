import os
from pathlib import Path
import tempfile
import unittest

from enntity_graft import DockerTarget, MacTarget, install

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
            receipt = install(FIXTURE, prefix, self.target, KnownRepair())
            self.assertEqual(len(receipt["repairs"]), 1)
            if isinstance(self.target, DockerTarget):
                self.assertEqual(receipt["target"]["executor_limits"]["memory_bytes"], 512 * 1024**2)
            result = self.target.run(["./hoststamp", "--bytes", "another input"], prefix / "current", False)
            self.assertEqual((result.code, result.stdout), (0, "13\n"))

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
