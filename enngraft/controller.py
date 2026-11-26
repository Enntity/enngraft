"""Stage, verify and select a relocatable installation."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import uuid

from .discovery import infer, inventory, project_name, split_progress

MAX_SOURCE = 64 * 1024
MAX_OUTPUT = 64 * 1024 * 1024


def relpath(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_./+-]{0,239}", value):
        raise ValueError("Invalid package path")
    if any(p in ("", ".", "..") for p in value.split("/")):
        raise ValueError("Invalid package path")
    return value


def read_file(root, name, limit):
    # Keep each directory pinned while opening its child. A build cannot swap a
    # checked path to a symlink between validation and the controller's read.
    parts = name.split("/")
    flags = os.O_RDONLY | os.O_NOFOLLOW
    directory = os.open(root, flags | os.O_DIRECTORY)
    try:
        for part in parts[:-1]:
            child = os.open(part, flags | os.O_DIRECTORY, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(parts[-1], flags | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
                raise ValueError(f"Expected a bounded, regular file: {name}")
            contents = stream.read(limit + 1)
            if len(contents) > limit:
                raise ValueError(f"File exceeds size limit: {name}")
            return contents, info.st_mode
    except OSError:
        raise ValueError(f"Expected a bounded, regular file: {name}") from None
    finally:
        os.close(directory)


def names(values, empty=False):
    if not isinstance(values, list) or len(values) > 64 or not (values or empty):
        raise ValueError("Expected a list of package paths")
    paths = [relpath(v) for v in values]
    if len(paths) != len(set(paths)):
        raise ValueError("Duplicate package path")
    return paths


def argv(value, empty=False):
    if (not isinstance(value, list) or not (value or empty) or len(value) > 64 or
            not all(isinstance(a, str) and "\0" not in a and len(a) <= 4096 for a in value)):
        raise ValueError("Expected a bounded argument array")
    return value


def contract(root):
    m = json.loads(read_file(root, "graft.json", MAX_SOURCE)[0].decode("utf-8"))
    return validate_contract(m)


def validate_contract(m, *, discovered=False):
    fields = {"version", "name", "files", "editable", "build", "outputs", "entry", "checks"}
    if not isinstance(m, dict) or set(m) != fields or type(m["version"]) != int or m["version"] != 1:
        raise ValueError("Expected a version 1 graft.json manifest")
    if not isinstance(m["name"], str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", m["name"]):
        raise ValueError("Invalid application name")
    if not set(names(m["editable"], True)) <= set(names(m["files"])):
        raise ValueError("Editable files must be source files")
    if relpath(m["entry"]) not in names(m["outputs"]):
        raise ValueError("Entry must be a declared output")
    argv(m["build"])
    if not isinstance(m["checks"], list) or not 1 <= len(m["checks"]) <= 16:
        raise ValueError("Declare between one and sixteen acceptance checks")
    for check in m["checks"]:
        if discovered and isinstance(check, dict) and set(check) == {"args", "nonempty_stdout"} and check["nonempty_stdout"] is True:
            argv(check["args"], True)
            continue
        if (not isinstance(check, dict) or not {"args", "stdout"} <= set(check)
                or set(check) - {"args", "stdout", "exit", "stderr"} or not isinstance(check["stdout"], str)
                or type(check.get("exit", 0)) is not int or not 0 <= check.get("exit", 0) <= 255
                or ("stderr" in check and not isinstance(check["stderr"], str))):
            raise ValueError("Each check requires args and exact stdout")
        argv(check["args"], True)
    return m


def patched(proposal, current, editable):
    if isinstance(proposal, dict) and set(proposal) == {"stop"}:
        raise ValueError("Agent stopped: " + str(proposal["stop"])[:512])
    if not isinstance(proposal, dict) or set(proposal) != {"edits"}:
        raise ValueError("Expected a repair proposal")
    edits = proposal["edits"]
    if not isinstance(edits, dict) or not edits or not set(edits) <= set(editable):
        raise ValueError("Proposal must edit declared editable paths")
    if any(not isinstance(v, str) or "\0" in v or len(v.encode()) > MAX_SOURCE for v in edits.values()):
        raise ValueError("Invalid replacement contents")
    result = {**current, **edits}
    if result == current or sum(len(v.encode()) for v in result.values()) > 256 * 1024:
        raise ValueError("Repair was unchanged or too large")
    return result


@contextmanager
def locked(prefix):
    prefix.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (prefix / ".graft-lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another install owns this prefix") from None
        yield


def selected(prefix):
    link = prefix / "current"
    if link.is_symlink():
        value = os.readlink(link)
        if not re.fullmatch(r"releases/[a-f0-9]{32}/app", value) or not link.is_dir():
            raise ValueError("Invalid current release pointer")
        return value
    if link.exists():
        raise ValueError("Prefix contains an unmanaged current path")
    return None


def select(prefix, target):
    if not re.fullmatch(r"releases/[a-f0-9]{32}/app", target) or not (prefix / target).is_dir():
        raise ValueError("Release unavailable")
    link = prefix / (".select-" + uuid.uuid4().hex)
    link.symlink_to(target)
    try:
        os.replace(link, prefix / "current")
    finally:
        link.unlink(missing_ok=True)


def rollback(prefix):
    prefix = Path(prefix).resolve()
    with locked(prefix):
        active = selected(prefix)
        if active:
            receipt = json.loads((prefix / active).parent.joinpath("receipt.json").read_text())
            if receipt.get("previous"):
                select(prefix, receipt["previous"])
                return receipt["previous"]
        raise ValueError("No previous release")


def build_and_check(target, work, app, m, sources, modes, facts, report, messages):
    for name, contents in sources.items():
        dest = work / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(contents.encode())
        dest.chmod(modes[name])
    report(messages.get("build", f"Building {m['entry']}…"))
    code, out, err = target.run(m["build"], work, writable=True)
    if code:
        return {"phase": "build", "exit": code, "diagnostic": (out + err)[-4096:]}
    try:
        total = 0
        for name in m["outputs"]:
            data, mode = read_file(work, name, MAX_OUTPUT - total)
            total += len(data)
            if name == m["entry"] and not mode & stat.S_IXUSR:
                raise ValueError("Entry is not executable")
            dst = app / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            dst.chmod(0o755 if mode & 0o111 else 0o644)
    except (FileNotFoundError, ValueError) as exc:
        return {"phase": "collect", "diagnostic": str(exc)}
    report(messages.get("check", f"Checking {m['entry']}…"))
    for check in m["checks"]:
        cmd = ["./" + m["entry"], *check["args"]]
        code, out, err = target.run(cmd, app, writable=False)
        if check.get("nonempty_stdout"):
            if code == 0 and out.strip():
                continue
            return {"phase": "check", "args": check["args"], "exit": code,
                    "expected": "nonempty stdout", "diagnostic": (out + err)[-4096:]}
        expected = check["stdout"].replace("@machine@", facts["machine"]).replace("@os@", facts["os"])
        if code != check.get("exit", 0) or out != expected or ("stderr" in check and err != check["stderr"]):
            return {"phase": "check", "args": check["args"], "exit": code,
                    "expected": check, "diagnostic": (out + err)[-4096:]}
    return None


def default_prefix(name):
    data = Path.home() / ".local/share"
    legacy = data / "enntity-graft" / name
    return legacy if legacy.is_dir() else data / "enngraft" / name


def install(project, prefix, target, model=None, repairs=3, *, progress=None):
    """Install from a project directory. Return the verified release receipt."""
    report = progress if progress is not None else lambda message: None
    if type(repairs) != int or not 0 <= repairs <= 8:
        raise ValueError("Repair budget must be 0 through 8")
    root = Path(project).resolve()
    if not root.is_dir():
        raise ValueError("Project must be a directory")
    report("Reading the project…")
    m = contract(root) if os.path.lexists(root / "graft.json") else None
    app_name = m["name"] if m else project_name(root)
    prefix = Path(prefix).resolve() if prefix is not None else default_prefix(app_name)
    origin = "manifest"
    sources, modes = {}, {}
    for name in (m["files"] if m else inventory(root)):
        data, mode = read_file(root, name, MAX_SOURCE)
        sources[name] = data.decode("utf-8")
        modes[name] = 0o755 if mode & 0o111 else 0o644
    if sum(len(s.encode()) for s in sources.values()) > 256 * 1024:
        raise ValueError("Package source exceeds 256 KiB")
    with locked(prefix):
        previous = selected(prefix)
        if previous:
            old = json.loads((prefix / previous).parent.joinpath("receipt.json").read_text())
            if old["name"] != app_name:
                raise ValueError("Prefix belongs to another application")
        releases = prefix / "releases"
        releases.mkdir(exist_ok=True)
        current = sources
        history = []
        with tempfile.TemporaryDirectory(dir=prefix, prefix=".graft-") as tmp:
            scratch = Path(tmp)
            report("Checking the machine…")
            messages = {}
            facts = target.facts(scratch)
            if m is None:
                m, origin, messages = infer(root, sources, model if repairs else None, facts, report)
                validate_contract(m, discovered=origin == "metadata")
            for attempt in range(repairs + 1):
                with tempfile.TemporaryDirectory(dir=scratch) as stage:
                    work, app = Path(stage) / "source", Path(stage) / "app"
                    work.mkdir()
                    app.mkdir()
                    failure = build_and_check(target, work, app, m, current, modes, facts, report, messages)
                    if failure is None:
                        release = uuid.uuid4().hex
                        path = f"releases/{release}/app"
                        receipt = dict(name=m["name"], release=release, previous=previous, target=facts,
                                       image=getattr(target, "image", None), model=model.model if history or origin == "model" else None,
                                       contract_source=origin, entry=m["entry"], repairs=history, checks=len(m["checks"]),
                                       sha256={n: hashlib.sha256((app / n).read_bytes()).hexdigest()
                                               for n in m["outputs"]})
                        ready = scratch / "verified"
                        ready.mkdir()
                        app.rename(ready / "app")
                        (ready / "contract.json").write_text(json.dumps(m, indent=2) + "\n")
                        (ready / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
                        (ready / "repair.json").write_text(json.dumps(
                            {k: v for k, v in current.items() if v != sources[k]}, indent=2) + "\n")
                        ready.rename(releases / release)
                        select(prefix, path)
                        return receipt
                    failure["diagnostic"] = failure["diagnostic"].replace(str(work), "<build>").replace(str(app), "<app>")
                if model is None or attempt == repairs:
                    raise ValueError(f"Installation failed: {json.dumps(failure)}")
                packet = {"target": facts, "contract": m, "files": current, "failure": failure,
                          "prior_attempts": history, "remaining_repairs": repairs - attempt}
                report(f"The {failure['phase']} step failed. Finding a repair…")
                proposal, captions = split_progress(model.propose(packet))
                revised = patched(proposal, current, m["editable"])
                report(captions.get("repair", "Applying the repair…"))
                history.append({"phase": failure["phase"], "diagnostic": failure["diagnostic"],
                                "changed": sorted(k for k in revised if revised[k] != current[k])})
                current = revised
