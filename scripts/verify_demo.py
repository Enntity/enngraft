"""Run the installed CLI on hoststamp, retain the receipt, and check unseen inputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from enntity_graft import DockerTarget, MacTarget


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1] / "examples/hoststamp"
    target = DockerTarget(args.image) if args.image else MacTarget()
    cmd = ["enntity-graft", "install", str(project)]
    if args.image:
        cmd += ["--image", args.image]
    with tempfile.TemporaryDirectory(prefix="graft-demo-") as tmp:
        prefix = Path(tmp).resolve()
        process = subprocess.run(cmd + ["--prefix", str(prefix)], stdout=subprocess.PIPE, text=True, check=True)
        receipt = json.loads(process.stdout)
        del receipt["executable"]
        if not receipt["repairs"]:
            raise RuntimeError("The broken example unexpectedly installed without a repair")
        app = (prefix / "current").resolve()
        repair = json.loads((app.parent / "repair.json").read_text())
        cases = [(["--bytes", "Café 🧬"], 0, "10\n"), (["--arch"], 0, receipt["target"]["machine"] + "\n"),
                 (["--invalid"], 2, "")]
        checks = []
        for argv, code, stdout in cases:
            result = target.run(["./hoststamp", *argv], app, writable=False)
            if (result.code, result.stdout) != (code, stdout):
                raise RuntimeError(f"Held-out check failed: {argv!r}, {result!r}")
            checks.append({"argv": argv, "exit": result.code, "stdout": result.stdout, "stderr": result.stderr})
        report = {"endpoint": os.environ["GRAFT_ENDPOINT"], "receipt": receipt, "replacements": repair,
                  "independent_checks": checks,
                  "input_sha256": {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(project.iterdir())}}
        data = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.evidence:
            args.evidence.write_text(data, encoding="utf-8")
        else:
            print(data, end="")


if __name__ == "__main__":
    main()
