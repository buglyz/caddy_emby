> Modified by 爪爪测试推送。

# Caddy Emby Manager

Language:

- English: `README.md`
- 中文: [README.zh-CN.md](README.zh-CN.md)

A Debian and Ubuntu focused management tool for running Emby behind Caddy.

This repository currently includes two entry points:

1. Main WebUI workflow: `webui/app.py`
2. Legacy Bash menu script: `install_caddy_emby.sh`

The recommended path is the WebUI. It is better suited for managing multiple sites, certificate policies, and generated Caddy configuration over time. The legacy Bash script is still kept for SSH-only or temporary usage.

## Features

- Manage multiple Emby reverse proxy sites
- Support local upstreams such as `127.0.0.1:8096`
- Support remote HTTPS upstreams such as `https://remote.example.com:443`
- Support 3 certificate modes
- `auto`: automatic Let's Encrypt certificates through Caddy
- `internal`: Caddy internal certificates
- `custom`: user-provided certificate and key files
- Automatically generate `/etc/caddy/Caddyfile`
- Run `caddy validate` before applying changes
- Reload `caddy` automatically after valid changes
- Persist site data in `/etc/caddy-emby-ui/sites.json`
- Optional Basic Auth protection for the WebUI

## Requirements

- Debian or Ubuntu
- `root` access for installation and service management
- systemd
- For automatic certificates, the domain must already resolve to this server
- For automatic certificates, ports 80 and 443 must be available to Caddy

## Quick Start

From the repository root on a Debian or Ubuntu server:

```bash
chmod +x install_webui.sh
./install_webui.sh
```

The installer will:

- install `caddy` and `python3`
- deploy the WebUI to `/opt/caddy-emby-ui/app.py`
- create `/etc/caddy-emby-ui`
- create `/etc/caddy-emby-ui/webui.env`
- create and start the `caddy-emby-ui` systemd service

After installation, edit the environment file immediately:

```bash
nano /etc/caddy-emby-ui/webui.env
```

At minimum, set credentials for the UI:

```env
CADDY_EMBY_UI_USERNAME=admin
CADDY_EMBY_UI_PASSWORD=change-this-password
```

Then restart the service:

```bash
systemctl restart caddy-emby-ui
```

Open the UI in a browser:

```text
http://SERVER_IP:9780/
```

## Environment Variables

Environment file path:

```text
/etc/caddy-emby-ui/webui.env
```

Supported variables:

`CADDY_EMBY_UI_HOST`

- Default: `0.0.0.0`
- Purpose: bind address for the WebUI
- Change it when: you want to listen on localhost or a private interface only

`CADDY_EMBY_UI_PORT`

- Default: `9780`
- Purpose: bind port for the WebUI
- Change it when: the port is already in use or you want another management port

`CADDY_EMBY_UI_DATA_DIR`

- Default: `/etc/caddy-emby-ui`
- Purpose: location for `sites.json`
- Change it when: you want the management data stored elsewhere

`CADDY_EMBY_UI_CADDYFILE`

- Default: `/etc/caddy/Caddyfile`
- Purpose: generated Caddy configuration target
- Change it when: you want to write to another Caddy config path

`CADDY_EMBY_UI_USERNAME`

- Default: empty
- Purpose: Basic Auth username
- Change it when: you want to protect the WebUI

`CADDY_EMBY_UI_PASSWORD`

- Default: empty
- Purpose: Basic Auth password
- Change it when: you want to protect the WebUI

`CADDY_EMBY_UI_ACME_EMAIL`

- Default: empty
- Purpose: default ACME email for automatic certificate mode
- Change it when: you want a shared default email for managed sites

`CADDY_EMBY_UI_BASE_PATH`

- Default: empty
- Purpose: mount the UI under a subpath such as `/emby-ui`
- Change it when: you are serving the WebUI behind another reverse proxy path

## Using the WebUI

When adding or editing a site, fill in these fields:

`Domain`

- Example: `emby.example.com`
- Used as the Caddy site label

`Upstream`

- Local example: `127.0.0.1:8096`
- Remote HTTPS example: `https://remote.example.com:443`

`Certificate mode`

- `auto`: automatic Let's Encrypt through Caddy
- `internal`: Caddy internal certificates
- `custom`: provide certificate and key file paths manually

`ACME email`

- Optional
- Recommended for automatic certificate mode

`Custom certificate path` / `Custom key path`

- Required only in `custom` mode
- Example:

```text
/etc/ssl/emby/fullchain.pem
/etc/ssl/emby/privkey.pem
```

`Skip TLS verification`

- Only relevant for HTTPS upstreams
- Use this when the upstream uses a self-signed or otherwise untrusted certificate

## Certificate Modes

### Automatic certificates

Use this when:

- you have a public domain
- DNS already points to this server
- Caddy can listen on ports 80 and 443

Notes:

- issuance will fail if another service is already using ports 80 or 443
- issuance will fail if DNS has not propagated yet

### Internal certificates

Use this when:

- the site is only used internally
- you are testing
- you do not need a publicly trusted certificate

Notes:

- browsers will not trust it by default

### Custom certificates

Use this when:

- you already have certificate files
- you want to control certificate sourcing or renewal yourself

Notes:

- the WebUI does not upload certificates
- the certificate and key files must already exist on the server

## Files and Layout

Important paths:

- application: `/opt/caddy-emby-ui/app.py`
- environment file: `/etc/caddy-emby-ui/webui.env`
- site data: `/etc/caddy-emby-ui/sites.json`
- generated config: `/etc/caddy/Caddyfile`
- systemd service: `/etc/systemd/system/caddy-emby-ui.service`

Design note:

- `sites.json` is the source of truth for managed data
- `Caddyfile` is generated output, not the primary data source
- manual edits to `/etc/caddy/Caddyfile` will be overwritten the next time you save a site in the WebUI

## Common Operations

Check WebUI status:

```bash
systemctl status caddy-emby-ui -l
```

Follow WebUI logs:

```bash
journalctl -u caddy-emby-ui -f
```

Restart the WebUI:

```bash
systemctl restart caddy-emby-ui
```

Check Caddy status:

```bash
systemctl status caddy -l
```

Follow Caddy logs:

```bash
journalctl -u caddy -f
```

Validate the generated config manually:

```bash
caddy validate --config /etc/caddy/Caddyfile
```

## Troubleshooting

### The WebUI does not open

Check:

- whether `caddy-emby-ui` is running
- whether the bind address and port are correct
- whether the firewall allows port `9780`

Useful commands:

```bash
systemctl status caddy-emby-ui -l
journalctl -u caddy-emby-ui -f
ss -lntp | grep 9780
```

### Automatic certificate issuance fails

Common reasons:

- the domain does not resolve to this server
- another service is using ports 80 or 443
- the server is not reachable from the public internet

Useful commands:

```bash
ss -lntp | grep -E ':80|:443'
systemctl status caddy -l
journalctl -u caddy -f
```

### HTTPS upstream access fails

Common reasons:

- the upstream URL is wrong
- the remote Emby certificate is not trusted

What to do:

- make sure the upstream starts with `https://`
- enable `Skip TLS verification` if the upstream certificate is self-signed

### Saving succeeds but Emby still does not work

Check:

- whether the upstream is actually reachable
- whether Emby is listening correctly
- whether a firewall blocks access to the upstream
- whether the domain resolves to the correct server

### Manual changes to `Caddyfile` disappear

This is expected with the current design:

- the WebUI manages `sites.json`
- saving a site regenerates `Caddyfile`

If you want to hand-maintain Caddy configuration long term, do not use this WebUI as the primary config manager.

## Security Notes

- Strongly recommend setting `CADDY_EMBY_UI_USERNAME` and `CADDY_EMBY_UI_PASSWORD`
- Do not expose the WebUI directly to the public internet without authentication
- Restrict the management port with firewall rules whenever possible
- If public access is required, place the UI behind another access control layer

## Legacy Bash Script

The old script is still available at:

```bash
install_caddy_emby.sh
```

Use it when:

- you only want to work over SSH
- you need a quick temporary setup
- you do not need a browser UI

Run it with:

```bash
bash install_caddy_emby.sh
```

For long-term multi-site management, the WebUI remains the recommended path.
