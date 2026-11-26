"""Build an installation contract from conventional project files."""
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

SOURCE_TYPES = {".c", ".cc", ".cpp", ".h", ".hpp", ".py", ".js", ".cjs", ".mjs",
                ".sh", ".go", ".rs", ".ts"}
BUILD_FILES = {"Makefile", "GNUmakefile", "CMakeLists.txt", "Cargo.toml", "go.mod",
               "package.json", "pyproject.toml", "README.md", "README", "setup.cfg"}
SOURCE_DIRS = {"src", "lib", "bin", "include", "app", "cmd"}
SKIP_DIRS = {"node_modules", "vendor", "build", "dist", "target", "__pycache__", "venv"}


def project_name(root):
    return re.sub("[^a-z0-9]+", "-", root.name.lower()).strip("-")[:64] or "project"


def inventory(root):
    files = []
    for directory, dirs, entries in os.walk(root):
        base = Path(directory)
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS
                         and not d.endswith(".egg-info") and not (base / d).is_symlink()
                         and (base != root or d in SOURCE_DIRS or (base / d / "__init__.py").is_file()))
        for name in sorted(entries):
            path = base / name
            if name.startswith(".") or path.is_symlink() or not path.is_file():
                continue
            if name not in BUILD_FILES and path.suffix.lower() not in SOURCE_TYPES:
                continue
            if re.search(r"(secret|credential|password|private[-_]?key)", name, re.I):
                continue
            rel = path.relative_to(root).as_posix()
            if not re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9_./+-]{0,239}", rel):
                continue
            files.append(rel)
    if (root / ".git").exists() and files:
        result = subprocess.run(["git", "check-ignore", "-z", "--stdin"], cwd=root,
                                input="\0".join(files).encode() + b"\0", capture_output=True)
        if result.returncode not in (0, 1):
            raise ValueError("Could not determine which project files Git ignores")
        ignored = set(result.stdout.decode().split("\0"))
        files = [f for f in files if f not in ignored]
    if not files:
        raise ValueError("No supported project source or build metadata found here")
    if len(files) > 64:
        raise ValueError("Discovery exceeds 64 files. Run inside the application directory or provide graft.json.")
    return sorted(files)


def python_cli(files):
    try:
        import tomllib
    except ImportError:
        return None
    project = tomllib.loads(files["pyproject.toml"]).get("project", {})
    scripts = project.get("scripts") if isinstance(project, dict) else None
    if not isinstance(scripts, dict) or len(scripts) != 1:
        return None
    name, hook = next(iter(scripts.items()))
    if not re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9_.-]*", name) or not isinstance(hook, str):
        return None
    match = re.fullmatch(r"([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*):([a-zA-Z_]\w*)", hook)
    if not match:
        return None
    module, function = match.groups()
    path = module.replace(".", "/")
    for base in ("", "src/"):
        if base + path + ".py" in files or base + path + "/__init__.py" in files:
            break
    else:
        return None
    entry = "bin/" + name
    launcher = ("#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\n"
                f"sys.path.insert(0, str(Path(__file__).resolve().parents[1] / {base!r}))\n"
                f"from {module} import {function}\nsys.exit({function}())\n")
    build = ["python3", "-c",
             "import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.parent.mkdir(exist_ok=True); "
             "p.write_text(sys.argv[2]); p.chmod(0o755)", entry, launcher]
    return entry, build, [entry] + [f for f in files if f.startswith(base) and f.endswith(".py")]


def local_recipe(files):
    if "pyproject.toml" in files:
        return python_cli(files)
    if "package.json" in files:
        package = json.loads(files["package.json"])
        bins = package.get("bin") if isinstance(package, dict) else None
        if isinstance(bins, dict) and len(bins) == 1:
            bins = next(iter(bins.values()))
        if isinstance(bins, str):
            entry = bins.removeprefix("./")
            if entry in files and files[entry].startswith("#!"):
                return entry, ["chmod", "+x", entry], [f for f in files if f != "README.md" and f != "README"]
        return None
    code = [name for name in files if Path(name).suffix in SOURCE_TYPES]
    if (len(code) == 1 and code[0] not in {"build.sh", "setup.py", "install.sh"}
            and files[code[0]].startswith("#!") and not set(files) & {"Makefile", "CMakeLists.txt", "GNUmakefile"}):
        return code[0], ["chmod", "+x", code[0]], code
    return None


def documented_checks(readme, entry):
    """Read literal CLI transcripts. Never execute README text as a shell."""
    if not isinstance(entry, str):
        return []
    checks = []
    for block in re.findall(r"^```console[ \t]*\n(.*?)^```[ \t]*$", readme, re.M | re.S):
        for command, output in re.findall(r"^\$ ([^\n]+)\n((?:(?!^\$ ).)*?)(?=^\$ |\Z)", block, re.M | re.S):
            try:
                words = shlex.split(command)
            except ValueError:
                continue
            if words and words[0] in (entry, "./" + entry, Path(entry).name) and output.strip():
                checks.append({"args": words[1:], "stdout": output.rstrip("\n") + "\n"})
    return checks


def split_progress(proposal):
    """Treat model captions as optional display text, never as installer instructions."""
    if not isinstance(proposal, dict) or "progress" not in proposal:
        return proposal, {}
    proposal = proposal.copy()
    messages = proposal.pop("progress")
    if not isinstance(messages, dict):
        return proposal, {}
    return proposal, {key: value.strip() for key, value in messages.items()
                      if key in {"build", "check", "repair"} and isinstance(value, str)
                      and 0 < len(value.strip()) <= 100 and value.isprintable()}


def infer(root, files, model, facts, report):
    readme = files.get("README.md", files.get("README", ""))
    recipe = local_recipe(files)
    editable = [name for name in files if name not in {"README", "README.md"}]
    fixed = {"version": 1, "name": project_name(root), "files": sorted(files), "editable": editable}
    if recipe:
        entry, build, outputs = recipe
        return {**fixed, "entry": entry, "outputs": outputs, "build": build,
                "checks": documented_checks(readme, entry) or [{"args": ["--help"], "nonempty_stdout": True}]}, "metadata", {}
    if model is None:
        raise ValueError("No unambiguous local recipe. Configure a model to infer the build and checks, "
                         "or supply graft.json.")
    if not callable(getattr(model, "plan", None)):
        raise ValueError("This model adapter needs a plan(packet) method for project discovery")
    report("Finding a build that fits this machine…")
    plan = model.plan({"target": facts, "project": fixed["name"], "files": files})
    plan, messages = split_progress(plan)
    if isinstance(plan, dict) and set(plan) == {"stop"}:
        raise ValueError("Planner stopped: " + str(plan["stop"])[:512])
    if not isinstance(plan, dict) or set(plan) != {"entry", "outputs", "build", "checks"}:
        raise ValueError("Expected build, outputs, entry and checks from the planner")
    if isinstance(plan["checks"], list):
        for check in documented_checks(readme, plan["entry"]):
            if check not in plan["checks"]:
                plan["checks"].append(check)
    if not isinstance(plan["checks"], list) or not any(
        isinstance(c, dict) and isinstance(c.get("stdout"), str) and c["stdout"].strip() for c in plan["checks"]
    ):
        raise ValueError("Inferred plan needs a behavioral check with nonempty expected stdout")
    return {**fixed, **plan}, "model", messages
