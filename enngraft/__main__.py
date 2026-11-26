import argparse
import json
import os
from pathlib import Path
import shlex
import sys

from . import DockerTarget, MacTarget, Model, install, rollback
from .controller import contract, default_prefix, relpath, selected
from .discovery import project_name


def go(args):
    root = Path.cwd()
    if args[:1] == ["--prefix"]:
        if len(args) < 2:
            raise ValueError("Supply a directory after --prefix")
        prefix = Path(args[1]).resolve()
        args = args[2:]
    else:
        name = contract(root)["name"] if os.path.lexists(root / "graft.json") else project_name(root)
        prefix = default_prefix(name)
    if args[:1] == ["--"]:
        args = args[1:]
    release = selected(prefix)
    if not release:
        raise ValueError("No installation here. Run enngraft . first.")
    app = prefix / release
    receipt = json.loads((app.parent / "receipt.json").read_text())
    entry = relpath(receipt.get("entry"))
    if receipt.get("image"):
        DockerTarget(receipt["image"]).launch(app, entry, args)
    else:
        # The user explicitly invoked the installed program. Preserve ordinary CLI I/O.
        env = os.environ.copy()
        env.pop("GRAFT_API_KEY", None)
        os.execve(app / entry, [str(app / entry), *args], env)


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["go"]:
        try:
            return go(args[1:])
        except (OSError, ValueError) as exc:
            print(f"enngraft: {exc}", file=sys.stderr)
            return 1

    if args[:1] == ["rollback"]:
        parser = argparse.ArgumentParser(prog="enngraft rollback", description="Select the previous release.")
        parser.add_argument("--prefix", type=Path, required=True)
        options = parser.parse_args(args[1:])
        try:
            print(rollback(options.prefix))
            return 0
        except (OSError, ValueError) as exc:
            print(f"enngraft: {exc}", file=sys.stderr)
            return 1

    explicit = args[:1] == ["install"]
    parser = argparse.ArgumentParser(
        prog="enngraft install" if explicit else "enngraft",
        description="Inspect a project directory and install its application.",
        epilog="Run the installed program with enngraft go [ARGS...]. To select a previous release, run enngraft rollback --prefix PATH.",
    )
    parser.add_argument("project", nargs="?", default=".", help="Project directory (default: current directory).")
    parser.add_argument("--prefix", type=Path)
    parser.add_argument("--json", action="store_true", help="Print the machine-readable receipt (default when piped).")
    parser.add_argument("--image", default=os.getenv("GRAFT_IMAGE"), help="Installed Docker image for a Linux target. Default: native macOS.")
    parser.add_argument("--repairs", type=int, default=3)
    parser.add_argument("--protocol", choices=("openai", "messages", "gemini"),
                        default=os.getenv("GRAFT_PROTOCOL", "openai"))
    parser.add_argument("--endpoint", default=os.getenv("GRAFT_ENDPOINT"))
    parser.add_argument("--model", default=os.getenv("GRAFT_MODEL"))
    options = parser.parse_args(args[1:] if explicit else args)
    try:
        if bool(options.endpoint) != bool(options.model):
            raise ValueError("Supply endpoint and model together")
        model = None
        if options.endpoint:
            model = Model(options.protocol, options.endpoint, options.model, os.getenv("GRAFT_API_KEY"),
                          timeout=int(os.getenv("GRAFT_MODEL_TIMEOUT", "90")))
        target = DockerTarget(options.image) if options.image else MacTarget()
        human = sys.stdout.isatty() and not options.json
        progress = (lambda message: print(message, flush=True)) if human else None
        receipt = install(options.project, options.prefix, target, model, options.repairs, progress=progress)
        prefix = options.prefix or default_prefix(receipt["name"])
        if human:
            command = ["enngraft", "go"]
            if options.prefix or Path(options.project).resolve() != Path.cwd():
                command.extend(["--prefix", str(prefix.resolve())])
            print(f"Installed {receipt['entry']}.")
            print(f"Run: {shlex.join(command)}")
            return 0
        print(json.dumps({"executable": str(prefix.resolve() / "current" / receipt["entry"]),
                          **receipt}, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"enngraft: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
