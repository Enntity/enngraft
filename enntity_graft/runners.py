"""Owner-selected execution targets. No provider credential enters a child environment."""
import json
import os
from pathlib import Path
from typing import NamedTuple
import platform
import selectors
import shutil
import signal
import subprocess
import time
import uuid

PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
PROBE = """set -eu
uname -s; uname -m; uname -r
getconf _NPROCESSORS_ONLN || echo unknown
case "$(uname -s)" in
    Darwin) /usr/sbin/sysctl -n hw.memsize || echo unknown ;;
    Linux) awk '/^MemTotal:/ {printf "%.0f\\n", $2*1024}' /proc/meminfo ;;
    *) echo unknown ;;
esac
for t in cc clang gcc make cmake python3 node; do command -v "$t" || :; done
"""


class Result(NamedTuple):
    code: int
    stdout: str
    stderr: str


def execute(argv, cwd, env, timeout):
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, start_new_session=True)
    end = time.monotonic() + timeout
    out, err = bytearray(), bytearray()
    try:
        with selectors.DefaultSelector() as sel:
            sel.register(proc.stdout, selectors.EVENT_READ, out)
            sel.register(proc.stderr, selectors.EVENT_READ, err)
            while sel.get_map():
                remaining = end - time.monotonic()
                if remaining <= 0:
                    return Result(124, "", "command timed out")
                for key, _ in sel.select(remaining):
                    chunk = os.read(key.fd, 8192)
                    if not chunk:
                        sel.unregister(key.fd)
                        continue
                    key.data.extend(chunk)
                    if len(out) + len(err) > 65536:
                        return Result(125, "", "command output exceeded 64 KiB")
            try:
                code = proc.wait(timeout=max(0, end - time.monotonic()))
            except subprocess.TimeoutExpired:
                return Result(124, "", "command timed out")
        return Result(code, out.decode(errors="replace"), err.decode(errors="replace"))
    finally:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        proc.stdout.close()
        proc.stderr.close()


class Target:
    def facts(self, directory):
        code, out, err = self.run(["/bin/sh", "-c", PROBE], directory, writable=False)
        lines = out.splitlines()
        if code or len(lines) < 5:
            raise ValueError("Target probe failed (" + str(code) + "): " + (err or out)[:1000])
        return dict(os=lines[0], machine=lines[1], kernel=lines[2], logical_cpus=lines[3], physical_memory_bytes=lines[4], tools=lines[5:])


class MacTarget(Target):
    def __init__(self):
        if platform.system() != "Darwin" or not Path("/usr/bin/sandbox-exec").exists():
            raise ValueError("Native runner requires macOS sandbox-exec. Select a Docker toolchain.")

    def run(self, argv, directory, writable):
        directory = Path(directory).resolve()
        temp = directory / ".tmp"
        if writable:
            temp.mkdir(exist_ok=True)
        allowed = ["/System/Library", "/usr/bin", "/usr/lib", "/usr/libexec", "/usr/share", "/bin", "/sbin", "/Library/Developer/CommandLineTools",
                   "/Applications/Xcode.app/Contents/Developer", "/private/var/db/xcode_select_link"]
        read = " ".join("(subpath " + json.dumps(p) + ")" for p in allowed + [str(directory)])
        profile = f"""(version 1)(deny default)
(import "dyld-support.sb")
(allow process-fork process-exec sysctl-read)
(allow file-read-metadata)
(allow file-read* file-map-executable {read} (literal "/dev/null") (literal "/dev/urandom") (literal "/dev/random"))
(allow file-write* (literal "/dev/null"))
"""
        if writable:
            profile += "(allow file-write* (subpath " + json.dumps(str(directory)) + "))"
        developer = Path("/Library/Developer/CommandLineTools")
        toolpath = str(developer / "usr/bin") + ":" + PATH if developer.is_dir() else PATH
        env = dict(PATH=toolpath, LC_ALL="C", HOME=str(temp), TMPDIR=str(temp))
        if (developer / "SDKs/MacOSX.sdk").is_dir():
            env["SDKROOT"] = str(developer / "SDKs/MacOSX.sdk")
        return execute(["/usr/bin/sandbox-exec", "-p", profile, *argv], directory, env, 45)


class DockerTarget(Target):
    memory_mib = 512
    cpus = 2

    def facts(self, directory):
        facts = super().facts(directory)
        facts["executor_limits"] = {"cpu_quota": self.cpus, "memory_bytes": self.memory_mib * 1024**2}
        return facts

    def __init__(self, image):
        self.docker = shutil.which("docker")
        if not self.docker or not image or image.startswith("-"):
            raise ValueError("Docker runner requires Docker and an installed toolchain image")
        # Resolve the tag once so probe, build and verification use the same image.
        self.env = {k: os.environ[k] for k in ("PATH", "HOME", "DOCKER_HOST", "DOCKER_CONTEXT",
                                                "DOCKER_CONFIG") if k in os.environ}
        code, out, err = execute([self.docker, "image", "inspect", "--format", "{{.Id}}", image],
                            None, self.env, 15)
        if code or not out.strip().startswith("sha256:"):
            raise ValueError("Docker toolchain unavailable: " + (err or out)[:400])
        self.image = out.strip()

    def run(self, argv, directory, writable):
        name = "enntity-graft-" + uuid.uuid4().hex
        mount = str(Path(directory).resolve())
        if "," in mount:
            raise ValueError("Docker staging paths cannot contain a comma")
        flags = [self.docker, "run", "--rm", "--pull=never", "--name", name, "--network=none",
                 "--label", "io.enntity.owner=enntity-graft", "--label", "io.enntity.job=" + name,
                 "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges",
                 "--pids-limit=64", f"--cpus={self.cpus}", f"--memory={self.memory_mib}m", "--tmpfs", "/tmp:size=128m",
                 "--user", f"{os.getuid()}:{os.getgid()}", "--env", "HOME=/tmp", "--env", "LC_ALL=C",
                 "--mount", "type=bind,src=" + mount + ",dst=/work" + ("" if writable else ",readonly"),
                 "-w", "/work", "--entrypoint", "/usr/bin/env", self.image]
        try:
            return execute(flags + argv, None, self.env, 60)
        finally:
            subprocess.run([self.docker, "rm", "-f", name], env=self.env, timeout=10,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
