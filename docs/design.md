# Installer design, version 1

The project ships source, a build recipe and an executable acceptance contract. The owner supplies the model endpoint, model ID, credential, target executor and installation prefix. One CLI invocation owns an installation. There is no resident service.

1. Probe the target through the executor. Record the kernel, machine architecture, available build tools and CPU count. A Linux container on a Mac reports Linux facts.
2. Snapshot the publisher's explicit file list. Start each build in a fresh private directory. First try the shipped recipe so a healthy package installs offline and costs no model tokens.
3. On build or acceptance failure, send the target facts, selected source, build/check contract and bounded diagnostics to the owner's model. The model returns replacement text for declared editable files or a reason to stop. Keep the accepted edits in memory across attempts. Restart from clean inputs each time.
4. The controller runs the publisher's build and acceptance commands. It owns expected outputs and file permissions. The candidate cannot redefine those checks through the model protocol. A matching executable and successful checks are required for selection.
5. Keep verified releases under one owner-controlled prefix and atomically switch its current symlink. Serialize writers. Retain the previous target for rollback. Record the model, target, changed files, attempts and release identity locally. The source checkout is read-only input.

## Components and trust

The manifest and model protocol are JSON. A small standard-library Python controller can be embedded or invoked by another language as a CLI. Transport adapters implement OpenAI Chat Completions, Anthropic Messages and Gemini generateContent. Full request URLs support private gateways and local servers. A provider sees every declared text file and the failed command's diagnostic. The owner chooses the provider and which project is appropriate to send.

The executor owns the build environment. Start with an owner-selected offline Docker toolchain for Linux and a native macOS runner with an OS-enforced file/network policy. Toolchain provisioning happens outside a repair. A publisher describes a relocatable user-space application. Kernel drivers, services, privileged package managers, and dependency downloads need separate host integration. Compiled artifacts must be launched on a compatible target. Acceptance quality is a product decision. A check for startup alone says little about whether the application works.

## First acceptance experiment

Ship a small native executable with a hard-coded compiler path and a Windows-specific hardware probe. Ask cloud DeepSeek to install the pristine package on real targets. Exercise architecture reporting and argument handling on the selected executable, including at least one input outside the manifest. Keep offline regression tests for a bad proposal, an impossible check, repeated installation, prefix state and adapter payloads. Record which provider/target combinations were actually exercised.
