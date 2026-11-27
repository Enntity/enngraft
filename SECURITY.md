# Security policy

Report vulnerabilities privately through [GitHub Security Advisories](https://github.com/Enntity/enngraft/security/advisories/new). Include the Enngraft revision, target OS or Docker image, and a minimal sanitized description. Keep credentials and private project files out of reports.

## Data handling

Enngraft makes model requests when you configure a provider and model-assisted discovery or repair is needed. Requests can include filenames, selected source and build files, README content, target facts, the install contract and failure diagnostics. The chosen provider handles that data under its own terms. Use a trusted local endpoint for source that must stay on your machine, or run with `--repairs 0` to disable model calls. Use a [manifest](docs/integration.md#discovery) to control the selected files. Review build output as well as source for sensitive data.

Set `GRAFT_API_KEY` in the installer’s environment through your secret manager. Build and check subprocesses receive a restricted environment. Keep the local install prefix private if its receipts or source replacements contain sensitive project details.

## Execution boundaries

Use source and toolchain images you trust. Native build and check commands run under macOS Seatbelt. Docker builds and checks run without network access in a restricted container. Passing checks establish only the behavior they cover. Review consequential repairs before using the installed program.

The native program runs with your account’s permissions when you invoke it. The printed Docker run command mounts your working directory read-write and the installed files read-only. Run it from a directory you intend to expose to that program.
