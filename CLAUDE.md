# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`a9f.zabbix` is an Ansible collection for managing Zabbix monitoring. It contains one role: `a9f.zabbix.agent2`. Requires Ansible >= 2.16.0.

## Common commands

```bash
# Build the collection artifact
ansible-galaxy collection build

# Install the collection locally (from the built artifact)
ansible-galaxy collection install a9f-zabbix-*.tar.gz --force

# Run all Molecule tests (from collection root)
export MOLECULE_GLOB="./extensions/molecule/*/molecule.yml"
molecule test

# Test a single platform
MOLECULE_GLOB="./extensions/molecule/*/molecule.yml" molecule test --platform-name="molecule-debian12"

# Keep containers alive after testing (for debugging)
MOLECULE_GLOB="./extensions/molecule/*/molecule.yml" molecule test --destroy=never

# Shell into a running test instance
MOLECULE_GLOB="./extensions/molecule/*/molecule.yml" molecule login --host molecule-debian12

# Lint (ansible-lint)
ansible-lint

# REUSE compliance check
reuse lint
```

**Note:** Always run `molecule` from the collection root dir with `MOLECULE_GLOB` set, not from the `extensions/` subdirectory. Without it, Molecule won't find the collection roles correctly.

## Architecture

### Platform dispatch pattern

The role uses a consistent pattern for platform-specific task files. In `init.yml`, it builds a list of candidate filenames ordered most-to-least specific (e.g., `debian_12.yml`, `debian.yml`, `debian.yml`, then `default.yml`). Each task group (setup/install, setup/uninstall, config, service) then loops through this list and includes the first matching file.

To add platform-specific behavior, create a file named after the platform in the relevant task subdirectory (e.g., `roles/agent2/tasks/setup/install/debian.yml`). The `default.yml` in each subdirectory serves as the fallback for all unsupported platforms.

The same pattern applies to `vars/`: platform-specific var files (e.g., `vars/debian.yml`) are loaded from least-to-most specific so more specific values win.

### Role variables

- `roles/agent2/defaults/main.yml` — user-facing parameters (`agent2_zabbix_*` prefix): `agent2_zabbix_state`, `agent2_zabbix_autoupgrade`, `agent2_zabbix_service_state`, etc.
- `roles/agent2/vars/main.yml` — internal variables (`__agent2_zabbix_*` prefix, not for users): package lists, supported platforms, used facts
- `roles/agent2/meta/argument_specs.yml` — must be updated when adding new parameters to `defaults/main.yml`

### Molecule testing

Tests live under `extensions/molecule/`. The `default` scenario uses Podman with `quay.io/foundata/*-itt` images that provide full systemd. Test tasks go in:
- `extensions/molecule/resources/tasks/converge/` — role invocations and state assertions via task failures
- `extensions/molecule/resources/tasks/verify/` — `ansible.builtin.assert` tasks for outcome validation

### Changelog

Uses `antsibull-changelog`. Add changelog fragments to `changelogs/fragments/` (see template at `changelogs/fragments/00-fragment-template.txt`).

### Licensing

REUSE-compliant (GPL-3.0-or-later). Licensing metadata is in `REUSE.toml`. Run `reuse spdx` to generate an SBOM.
