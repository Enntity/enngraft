# Enngraft

Give people a way to install your software from source, even when the build needs a repair on their machine.

**In your installer or setup instructions, include these two lines.** Run them from your project directory in an active Python environment (Python 3.9+).

```sh
python -m pip install 'enngraft @ git+https://github.com/Enntity/enngraft.git'
enngraft .
```

Enngraft reads the project's existing source, build files and README. You can ship ordinary source without writing an Enngraft config. Describe one command and its expected output in your README so the installer knows what success looks like.

**To enable model-assisted discovery and repair**, set the model URL, model ID and key in the installing user's environment. The key belongs on their machine.

```sh
export GRAFT_ENDPOINT=https://openrouter.ai/api/v1/chat/completions
export GRAFT_MODEL=deepseek/deepseek-v4.1-flash-1017
# Set GRAFT_API_KEY through your secret manager.
```

OpenAI-compatible endpoints are the default. Set `GRAFT_PROTOCOL=messages` for Claude or `gemini` for Gemini. A local model may omit the key. Native macOS needs Command Line Tools. For a Linux target, set `GRAFT_IMAGE` to a locally installed Docker image containing your build tools.

Enngraft prints the verified executable's path. [Watch Enngraft build QOA on a Mac](docs/enngraft-demos.mp4) · [Reproduce the field trial](docs/field-trials/qoa/README.md) · [Integration details and limits](docs/integration.md)
