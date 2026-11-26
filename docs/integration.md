# Integration

The CLI accepts a project directory. Use `enngraft .` from the unpacked project, or pass its path from a wrapper. `enngraft install .` is the explicit equivalent. The terminal shows each step as it starts. When the configured model plans a build or repair, it can also describe the step. The installer prints `Installed` after the checks pass and the release is active. Use `--json` for the full receipt. Redirected and piped stdout retain the JSON format.

Run `enngraft go [ARGS...]` from the project directory to launch its current release. For a custom destination use `enngraft go --prefix PATH [ARGS...]`. Use `--` to pass a literal leading `--prefix` or `--` to your program. A Docker release runs in its recorded local image, with the current working directory mounted at `/work` and installed files at `/app`. Native releases use the caller’s working directory. Python callers use the same installer and can pass `progress=print` for step messages.

```python
import os
from enngraft import DockerTarget, Model, install

install(".", "./installed", DockerTarget("node:22"),
        Model("openai", os.environ["GRAFT_ENDPOINT"], os.environ["GRAFT_MODEL"],
              os.getenv("GRAFT_API_KEY")))
```

## Discovery

Enngraft recognizes a shebang script with a supported source extension, a single Node package binary, or a conventional Python console script declared in a pyproject (Python 3.11+ for offline TOML parsing). It stages the sources, produces an executable and checks worked examples from the README. Without examples it runs the help invocation and requires successful exit with output. That fallback is a startup check. A project that needs stronger fixed acceptance criteria can ship the optional manifest.

For other layouts, the configured model gets one planning request containing the bounded file inventory, file contents and target facts. It proposes a build command, outputs, entry point and behavioral examples derived from the project. The controller validates the plan, builds it in isolation and freezes the checks before requesting any repair. It also extracts literal example invocations and their stdout from fenced `console` transcripts in the README, like this one:

````markdown
```console
$ cueclock 00:00:59,900 250
00:01:00,150
```
````

Transcript commands are parsed into argument arrays and run against the installed entry point. Fixed checks may additionally specify an expected exit status and exact stderr. Poorly documented or unsupported software can fail discovery. A model-inferred test can miss the same bug its author missed. Review the saved contract and add independent product checks for consequential uses.

Discovery inspects common source/build files at the root, language package directories and conventional source directories. It skips dotfiles, symlinks, Git-ignored files, vendored dependencies and common credential filenames. Any eligible source or README can contain private information and may be sent to the chosen model. For precise file selection, place an explicit [graft.json](../examples/manifests/hoststamp.json) at the project root. Existing manifests take precedence. The installer never needs to write one into the project.

## Settings and results

| Setting | Meaning |
| --- | --- |
| `GRAFT_ENDPOINT` | Full request URL for the owner's provider |
| `GRAFT_MODEL` | Model ID. For Gemini use that same ID in the generateContent URL. |
| `GRAFT_MODEL_TIMEOUT` | Model response timeout in seconds (default 90) |
| `GRAFT_API_KEY` | Optional model credential |
| `GRAFT_PROTOCOL` | `openai`, `messages`, or `gemini` |
| `GRAFT_IMAGE` or `--image` | Locally available Docker toolchain for a Linux target |
| `--prefix PATH` | Destination for this application and target |
| `--repairs N` | Maximum repair requests (default 3). Zero disables all model calls. |

OpenAI, OpenRouter, DeepSeek, Z.AI and compatible local servers use their Chat Completions URLs. For Claude use the Messages URL. For Gemini use a URL ending in `/models/MODEL:generateContent`. Protocol shape is tested for all three. The live examples used cloud DeepSeek through OpenRouter.

Native macOS builds run under Seatbelt. Linux builds run inside an offline Docker container. Running the resulting executable normally gives it the caller's permissions. Dependencies must already be present in the target toolchain or included among the supported source files. This version handles small relocatable CLI projects, with up to 64 files, 64 KiB per source, 256 KiB total source and 64 MiB of installed outputs. Windows, privileged installation and general dependency acquisition are outside this version's support.

New installations default to `~/.local/share/enngraft/<name>`. Existing default prefixes under `enntity-graft` retain their release history. Each release stores its resolved `contract.json`, source replacements, receipt and executable hashes. `current` selects the last verified release. Use `enngraft rollback --prefix PATH` to select its predecessor.

## Reproduce the two demos

After installing the package and configuring the model, run these from this repository. Use a Mac with Command Line Tools for the first and a local `node:22` Docker image for the second.

```sh
python scripts/verify_demo.py hoststamp
docker pull node:22
python scripts/verify_demo.py cueclock --image node:22
```

Each run starts from fresh source, executes the broken baseline, installs through the CLI and invokes the selected binary on additional inputs. [macOS receipt](evidence/hoststamp.json) · [Linux receipt](evidence/cueclock.json)
