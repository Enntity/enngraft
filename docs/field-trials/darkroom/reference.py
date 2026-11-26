"""Run the lab's original x86 build on the published negative and verify its print."""
import argparse
import gzip
import hashlib
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    destination = parser.parse_args().output.resolve()
    if platform.machine().lower() not in ("amd64", "x86_64"):
        raise SystemExit("Run this reference build on x86-64.")
    here = Path(__file__).resolve().parent
    destination.mkdir(parents=True, exist_ok=True)
    transcript = []

    def run(args, cwd):
        result = subprocess.run(args, cwd=cwd, check=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        transcript.extend(["$ " + shlex.join(args), result.stdout.rstrip()])

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        shutil.copytree(here.parents[2] / "examples/darkroom", root / "source")
        negative = gzip.decompress((here / "negative.ppm.gz").read_bytes())
        (root / "negative.ppm").write_bytes(negative)
        run(["uname", "-sm"], root)
        run(["make"], root / "source")
        run(["./darkroom", "../negative.ppm", "../print.ppm"], root / "source")
        header, pixels = negative.split(b"\n255\n", 1)
        expected = header + b"\n255\n" + bytes(255 - value for value in pixels)
        printed = (root / "print.ppm").read_bytes()
        if printed != expected:
            raise SystemExit("The photo output differs from the independent pixel reference.")
        digest = hashlib.sha256(printed).hexdigest()
        transcript.append(f"Verified print SHA-256: {digest}")
        (destination / "print.ppm.gz").write_bytes(gzip.compress(printed, mtime=0))
    log = "\n".join(transcript) + "\n"
    (destination / "terminal.txt").write_text(log)
    print(log, end="")


if __name__ == "__main__":
    main()
