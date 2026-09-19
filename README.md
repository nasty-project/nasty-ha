# NASty for Home Assistant

Monitor a [NASty](https://github.com/nasty-project/nasty) storage appliance from
Home Assistant and optionally control its virtual machines and Apps.

This integration is an independent implementation built against NASty's public
REST API. It does not contain or depend on code from an Unraid integration.

## Features

- CPU temperature and load, memory use, uptime, system health, and active alerts
- Filesystem capacity and mount state
- SMART health and temperatures for discovered disks
- UPS battery, runtime, load, input/output voltage, and connectivity from NUT
- App runtime statistics
- Optional start/stop switches for VMs and Apps
- Reauthentication and privacy-redacted diagnostics

NASty is polled locally every 30 seconds for runtime state and every five
minutes for filesystem and SMART data. The integration does not use a cloud
service.

## Requirements

- A NASty appliance with the REST gateway enabled
- A Viewer API token for monitoring
- An Operator or Admin API token only if VM and App controls are enabled
- Network access from Home Assistant to the appliance

Use the least-privileged token that satisfies your configuration. TLS
certificate verification is enabled by default.

## Installation

### HACS

[![Open your Home Assistant instance and add the NASty repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=nasty-project&repository=nasty-ha&category=integration)

Until the repository is included in the HACS default catalog:

1. Open **HACS** in Home Assistant.
2. Open the menu in the top-right corner and select **Custom repositories**.
3. Enter `https://github.com/nasty-project/nasty-ha`, select the
   **Integration** category, and add the repository.
4. Search HACS for **NASty** and install it.
5. Restart Home Assistant.
6. Open **Settings > Devices & services > Add integration**, search for
   **NASty**, and complete the configuration flow.

### Manual

Copy `custom_components/nasty` into Home Assistant's `custom_components`
directory and restart Home Assistant. Add **NASty** from the integrations UI.

## Configuration

Enter the appliance base URL and API token. The URL can include an existing
path prefix, but must not include credentials, query parameters, or fragments.

Leave **Enable VM and App controls** disabled for monitoring-only setups. The
integration never exposes destructive storage, VM creation, or App installation
operations.

If NASty uses a private certificate authority, import that CA into Home
Assistant where possible. Disabling certificate verification should be a last
resort.

## Development

```bash
uv sync --extra dev
uv run ruff check .
uv run pytest
uv run python -m compileall -q custom_components
```

The integration source is GPL-3.0-only. See `LICENSE`.
