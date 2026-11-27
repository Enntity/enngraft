# Contributing to Enngraft

Start with a focused change. Documentation fixes, small compatibility fixtures, build and install reliability, and clearer diagnostics are welcome. For a larger feature, open an issue with the use case and proposed scope.

## Run the checks

Use Python 3.9 or newer. GitHub Actions exercises native macOS and a Linux Docker target on Python 3.12.

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
enngraft --help
```

For changes to a runner, test the relevant target with `GRAFT_TEST_TARGET=macos` or `GRAFT_TEST_TARGET=node:22` when that toolchain is available. Pull `node:22` before running Docker integration checks. The test suite uses fixtures and requires no model account.

## Send a pull request

Describe the user-visible change and the checks you ran. For an installation regression, provide a small redistributable source fixture, the target architecture and toolchain, the command, and the expected and actual output. Include a scrubbed receipt when it helps. For provider changes, use a fixture and state which protocol you verified.

Credit imported work with its source and license. Use `Co-authored-by` for actual co-authors. Keep credentials, private source, and provider receipts with sensitive content out of issues and pull requests. Report security issues through [private reporting](SECURITY.md).
