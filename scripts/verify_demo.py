"""Run a manifest-free demo with the installed command and verify the selected executable."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from enngraft import DockerTarget, MacTarget


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("demo", choices=("hoststamp", "cueclock"))
    parser.add_argument("--image")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1] / "examples" / args.demo
    target = DockerTarget(args.image) if args.image else MacTarget()
    with tempfile.TemporaryDirectory(prefix="enngraft-demo-") as tmp:
        stage = Path(tmp).resolve()
        baseline = stage / "baseline"
        shutil.copytree(project, baseline)
        before = [{"argv": ["sh", "build.sh"]}]
        if args.demo == "cueclock":
            before.append({"argv": ["./cueclock", "00:00:59,900", "250"]})
        for item in before:
            item.update(target.run(item["argv"], baseline, writable=True)._asdict())
        prefix = stage / "install"
        cmd = ["enngraft", ".", "--prefix", str(prefix)]
        if args.image:
            cmd += ["--image", args.image]
        process = subprocess.run(cmd, cwd=project, stdout=subprocess.PIPE, text=True, check=True)
        receipt = json.loads(process.stdout)
        del receipt["executable"]
        if receipt["contract_source"] != "model":
            raise RuntimeError("Expected a model-discovered contract")
        app = (prefix / "current").resolve()
        repair = json.loads((app.parent / "repair.json").read_text())
        if args.demo == "hoststamp":
            cases = [(["--bytes", "Café 🧬"], 0, "10\n"), (["--arch"], 0, receipt["target"]["machine"] + "\n"),
                     (["--invalid"], 2, "")]
        else:
            cases = [(["00:59:59,980", "40"], 0, "01:00:00,020\n"),
                     (["00:00:00,001", "-2"], 0, "00:00:00,000\n"),
                     (["01:00:00,020", "-40"], 0, "00:59:59,980\n")]
        checks = []
        for argv, code, stdout in cases:
            result = target.run(["./" + receipt["entry"], *argv], app, writable=False)
            if (result.code, result.stdout) != (code, stdout):
                raise RuntimeError(f"Independent check failed: {argv!r}, {result!r}")
            checks.append({"argv": argv, "exit": result.code, "stdout": result.stdout, "stderr": result.stderr})
        report = {"endpoint": os.environ["GRAFT_ENDPOINT"], "baseline": before, "receipt": receipt,
                  "inferred_contract": json.loads((app.parent / "contract.json").read_text()),
                  "replacements": repair, "independent_checks": checks,
                  "input_sha256": {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(project.iterdir())}}
        data = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.evidence:
            args.evidence.write_text(data, encoding="utf-8")
        else:
            print(data, end="")


if __name__ == "__main__":
    main()
