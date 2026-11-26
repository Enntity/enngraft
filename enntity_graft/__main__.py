import argparse
import json
import os
from pathlib import Path
import sys

from . import DockerTarget, MacTarget, Model, install, rollback
from .controller import contract


def main():
    parser = argparse.ArgumentParser(prog="enntity-graft")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("install")
    add.add_argument("project", nargs="?", default=".")
    add.add_argument("--prefix", type=Path)
    add.add_argument("--image", help="Installed Docker image for a Linux target. Default: native macOS.")
    add.add_argument("--repairs", type=int, default=3)
    add.add_argument("--protocol", choices=("openai", "messages", "gemini"),
                     default=os.getenv("GRAFT_PROTOCOL", "openai"))
    add.add_argument("--endpoint", default=os.getenv("GRAFT_ENDPOINT"))
    add.add_argument("--model", default=os.getenv("GRAFT_MODEL"))
    back = commands.add_parser("rollback")
    back.add_argument("--prefix", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "rollback":
            print(rollback(args.prefix))
            return 0
        if bool(args.endpoint) != bool(args.model):
            raise ValueError("Supply endpoint and model together")
        model = Model(args.protocol, args.endpoint, args.model, os.getenv("GRAFT_API_KEY")) if args.endpoint else None
        target = DockerTarget(args.image) if args.image else MacTarget()
        prefix = args.prefix or Path.home() / ".local/share/enntity-graft" / contract(Path(args.project).resolve())["name"]
        receipt = install(args.project, prefix, target, model, args.repairs)
        print(json.dumps({"executable": str(prefix.resolve() / "current" / receipt["entry"]),
                          **receipt}, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"enntity-graft: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
