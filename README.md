# Enntity Graft

Graft installs software that needs a repair before it can run on the target machine. A project ships its source, build command and executable acceptance checks in a small manifest. The installer tries the shipped build first. If it fails, Graft gives the selected model the target's hardware and tool inventory, the declared source files and the failure. It rebuilds from the proposed edits and selects the executable once the publisher's checks pass.

The included C program was written for Windows and names a compiler that doesn't exist on either test target. Cloud DeepSeek repaired and installed it on Apple Silicon macOS and in an ARM64 Linux container. The recorded runs include the replacements, binary hashes and independent checks. [macOS evidence](docs/evidence/macos.json) · [Linux evidence](docs/evidence/linux.json)

## Try the broken package

Use Python 3.9 or later. Native macOS builds need the Command Line Tools or Xcode. For a Linux target, install Docker and choose a Linux image that already contains your project's build tools.

```sh
git clone https://github.com/Enntity/graft.git
cd graft
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .

# Set GRAFT_API_KEY in your environment using your usual secret manager.
export GRAFT_ENDPOINT=https://openrouter.ai/api/v1/chat/completions
export GRAFT_MODEL=deepseek/deepseek-v4.1-flash-1017

# Native macOS
enntity-graft install examples/hoststamp --prefix "$PWD/.demo-mac"
./.demo-mac/current/hoststamp --arch

# Linux target, using a C compiler supplied by the image
docker pull node:22
enntity-graft install examples/hoststamp --image node:22 --prefix "$PWD/.demo-linux"
docker run --rm --network none -v "$PWD/.demo-linux:/install:ro" node:22 /install/current/hoststamp --arch
```

Use a distinct prefix for each application and target. The CLI prints the installed entry point and its receipt. A fresh clone works without a registry release. The distribution and command are named `enntity-graft` because other projects already ship a `graft` command.

## Include Graft in your project

Add `graft.json` at the project root, include Graft as an installation dependency and call `enntity-graft install .` from your existing installer. Any language can use the command. Python callers can embed the same controller directly.

```python
import os
from enntity_graft import DockerTarget, Model, install

receipt = install(
    project=".",
    prefix="./installed",
    target=DockerTarget("node:22"),
    model=Model("openai", os.environ["GRAFT_ENDPOINT"],
                os.environ["GRAFT_MODEL"], os.getenv("GRAFT_API_KEY")),
)
```

The manifest names the files the model may read, the subset it may replace, the build argument array, the outputs to install and the executable entry point. Each check invokes that entry point with specified arguments and requires exit zero and exact stdout. A check may use `@machine@` or `@os@` in expected output. Run the check against the delivered behavior a user needs. The source copy, candidate build, and installed payload live in different directories. [Complete manifest](examples/hoststamp/graft.json)

## Choose a model

Set the full request URL, model ID and optional key in the owner environment. `--protocol`, `--endpoint` and `--model` override the corresponding `GRAFT_*` settings. The project manifest cannot choose where to send a credential.

| Service | GRAFT_PROTOCOL | GRAFT_ENDPOINT |
| --- | --- | --- |
| OpenAI | openai | `https://api.openai.com/v1/chat/completions` |
| DeepSeek direct | openai | `https://api.deepseek.com/chat/completions` |
| OpenRouter | openai | `https://openrouter.ai/api/v1/chat/completions` |
| Z.AI standard API | openai | `https://api.z.ai/api/paas/v4/chat/completions` |
| Anthropic Claude | messages | `https://api.anthropic.com/v1/messages` |
| Google Gemini | gemini | `https://generativelanguage.googleapis.com/v1beta/models/MODEL:generateContent` |
| Local server | any implemented protocol | The server's complete request URL, e.g. `http://127.0.0.1:8000/v1/chat/completions` |

Replace `MODEL` in the Gemini URL with the value of `GRAFT_MODEL`. The default protocol is `openai`. All three formats have transport contract tests. The recorded cloud test uses DeepSeek via OpenRouter. A healthy package installs without a model. Setting `--repairs 0` disables model calls even when credentials are present.

## What the agent can change

The owner selects a trusted package, installation prefix and toolchain. The provider receives all declared source files, the manifest, hardware facts and bounded command diagnostics. Keep secrets out of those inputs. Build children receive their own environment. The model can replace declared UTF-8 sources, including build scripts. Each proposal consumes a repair attempt. The default budget is three.

The macOS executor uses the system Seatbelt launcher with writes confined to the build tree and restricted toolchain reads. The Linux executor runs each command in a fresh Docker container, with networking disabled and only the candidate directory mounted. Checks get read-only access. These are build-time controls. The installed executable runs with its caller's permissions when launched normally. Review the local repair before running software in a sensitive environment.

Each release keeps an output hash, receipt and the accepted source replacements in `releases/<id>/`. An atomic symlink selects the release. A failed build retains the previously selected executable. Use `enntity-graft rollback --prefix PATH` to select its predecessor. Use an owner-controlled prefix on a local POSIX filesystem. Old releases and scratch left by an interrupted process can consume disk space.

Version 0.1 supports small, relocatable user-space packages. Source input is capped at 64 files, 64 KiB per file and 256 KiB total. Declared outputs may include binaries and data, up to 64 MiB total. Projects needing new system packages, drivers, privileged services or Windows installation need additional executors. The model can select among tools and dependencies already available on the target.

## Reproduce the checks

```sh
python -m unittest discover -s tests -v
GRAFT_TEST_TARGET=macos python -m unittest discover -s tests -v
GRAFT_TEST_TARGET=node:22 python -m unittest discover -s tests -v

# With model access configured as above, each command runs a fresh cloud repair.
python scripts/verify_demo.py
python scripts/verify_demo.py --image node:22
```

The live script uses the installed command, checks the selected binary on fresh inputs, and emits the result as JSON. The standard test suite uses deterministic repairs and requires no model account. [Architecture and next milestones](docs/design.md) · [MIT license](LICENSE)
