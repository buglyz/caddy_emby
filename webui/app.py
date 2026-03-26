#!/usr/bin/env python3
import base64
import html
import json
import os
import secrets
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List
from urllib.parse import parse_qs, urlparse


DATA_DIR = Path(os.environ.get("CADDY_EMBY_UI_DATA_DIR", "/etc/caddy-emby-ui"))
DATA_FILE = DATA_DIR / "sites.json"
CADDYFILE_PATH = Path(os.environ.get("CADDY_EMBY_UI_CADDYFILE", "/etc/caddy/Caddyfile"))
HOST = os.environ.get("CADDY_EMBY_UI_HOST", "0.0.0.0")
PORT = int(os.environ.get("CADDY_EMBY_UI_PORT", "9780"))
DEFAULT_EMAIL = os.environ.get("CADDY_EMBY_UI_ACME_EMAIL", "")
UI_USERNAME = os.environ.get("CADDY_EMBY_UI_USERNAME", "")
UI_PASSWORD = os.environ.get("CADDY_EMBY_UI_PASSWORD", "")
BASE_PATH = os.environ.get("CADDY_EMBY_UI_BASE_PATH", "").strip("/")


STYLE = """
:root {
  color-scheme: light;
  --bg: #f4efe6;
  --panel: rgba(255, 252, 247, 0.92);
  --panel-strong: #fffaf2;
  --line: #d7c9b2;
  --text: #231b12;
  --muted: #6e5a44;
  --brand: #0f766e;
  --brand-strong: #115e59;
  --danger: #b42318;
  --shadow: 0 18px 40px rgba(35, 27, 18, 0.08);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  color: var(--text);
  background:
    radial-gradient(circle at top left, rgba(15, 118, 110, 0.18), transparent 30%),
    radial-gradient(circle at right center, rgba(180, 71, 8, 0.12), transparent 25%),
    linear-gradient(180deg, #f8f3ea 0%, var(--bg) 100%);
}
.shell {
  width: min(1180px, calc(100% - 32px));
  margin: 32px auto;
}
.hero, .card {
  background: var(--panel);
  border: 1px solid rgba(215, 201, 178, 0.9);
  border-radius: 24px;
  box-shadow: var(--shadow);
}
.hero {
  padding: 28px;
}
.hero h1 {
  margin: 0 0 10px;
  font-size: 34px;
}
.hero p {
  margin: 0;
  max-width: 780px;
  color: var(--muted);
  line-height: 1.6;
}
.grid {
  display: grid;
  grid-template-columns: 1.45fr 1fr;
  gap: 20px;
  margin-top: 20px;
}
.card-header {
  padding: 18px 22px;
  border-bottom: 1px solid rgba(215, 201, 178, 0.8);
  background: rgba(255, 250, 242, 0.8);
}
.card-header h2 {
  margin: 0 0 6px;
  font-size: 21px;
}
.card-header p, .hint {
  margin: 0;
  color: var(--muted);
  line-height: 1.5;
}
.card-body {
  padding: 22px;
}
.flash {
  padding: 14px 16px;
  border-radius: 16px;
  margin-bottom: 18px;
  line-height: 1.5;
}
.flash.success { background: rgba(15, 118, 110, 0.12); color: var(--brand-strong); }
.flash.error { background: rgba(180, 35, 24, 0.1); color: var(--danger); }
.status-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 18px;
}
.pill {
  padding: 14px;
  border-radius: 18px;
  background: var(--panel-strong);
  border: 1px solid rgba(215, 201, 178, 0.85);
}
.pill strong {
  display: block;
  font-size: 13px;
  color: var(--muted);
  margin-bottom: 4px;
}
.toolbar, .actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th, td {
  text-align: left;
  padding: 14px 10px;
  border-bottom: 1px solid rgba(215, 201, 178, 0.65);
  vertical-align: top;
}
th {
  color: var(--muted);
  font-size: 13px;
  font-weight: 600;
}
.domain {
  font-weight: 700;
  margin-bottom: 4px;
}
label {
  display: block;
  margin-bottom: 14px;
  font-weight: 600;
}
label span {
  display: block;
  margin-bottom: 8px;
}
input, select, textarea {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 12px 14px;
  font: inherit;
  background: #fffdfa;
  color: var(--text);
}
textarea {
  min-height: 110px;
  resize: vertical;
}
.check {
  display: flex;
  gap: 10px;
  align-items: center;
  font-weight: 500;
}
.check input {
  width: auto;
}
button, .button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 999px;
  padding: 11px 18px;
  text-decoration: none;
  background: var(--brand);
  color: white;
  cursor: pointer;
  font: inherit;
}
.button.secondary, button.secondary {
  background: #efe2cf;
  color: var(--text);
}
.button.danger, button.danger {
  background: var(--danger);
}
.stack {
  display: grid;
  gap: 10px;
}
.empty {
  padding: 18px;
  border-radius: 16px;
  background: rgba(255, 250, 242, 0.85);
  border: 1px dashed var(--line);
  color: var(--muted);
}
.mono {
  font-family: Consolas, "SFMono-Regular", monospace;
  font-size: 13px;
}
@media (max-width: 900px) {
  .grid { grid-template-columns: 1fr; }
  .status-grid { grid-template-columns: 1fr; }
  th:nth-child(3), td:nth-child(3) { display: none; }
}
"""


@dataclass
class SiteConfig:
    domain: str
    upstream: str
    certificate_mode: str = "auto"
    custom_cert_path: str = ""
    custom_key_path: str = ""
    acme_email: str = ""
    skip_tls_verify: bool = False
    notes: str = ""


def normalize_base_path() -> str:
    return f"/{BASE_PATH}" if BASE_PATH else ""


def route(path: str) -> str:
    return f"{normalize_base_path()}{path}"


def ensure_data_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text(json.dumps({"sites": []}, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state() -> Dict[str, List[Dict[str, object]]]:
    ensure_data_file()
    try:
        state = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        state = {"sites": []}
    state.setdefault("sites", [])
    return state


def save_state(state: Dict[str, List[Dict[str, object]]]) -> None:
    ensure_data_file()
    DATA_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_form(body: bytes) -> Dict[str, str]:
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {key: values[0] for key, values in parsed.items()}


def parse_bool(value: str) -> bool:
    return value in {"1", "true", "on", "yes"}


def validate_site(form: Dict[str, str], original_domain: str = "") -> SiteConfig:
    domain = form.get("domain", "").strip()
    upstream = form.get("upstream", "").strip()
    certificate_mode = form.get("certificate_mode", "auto").strip() or "auto"
    custom_cert_path = form.get("custom_cert_path", "").strip()
    custom_key_path = form.get("custom_key_path", "").strip()
    acme_email = form.get("acme_email", "").strip()
    notes = form.get("notes", "").strip()
    skip_tls_verify = parse_bool(form.get("skip_tls_verify", ""))

    if not domain:
        raise ValueError("???????")
    if " " in domain or "/" in domain:
        raise ValueError("????????")
    if not upstream:
        raise ValueError("?????????")
    if certificate_mode not in {"auto", "internal", "custom"}:
        raise ValueError("?????????")
    if certificate_mode == "custom" and (not custom_cert_path or not custom_key_path):
        raise ValueError("?????????????????????")
    if skip_tls_verify and not upstream.startswith("https://"):
        raise ValueError("?? HTTPS ??????? TLS ???")

    state = load_state()
    for site in state["sites"]:
        existing = str(site.get("domain", "")).lower()
        if existing == domain.lower() and existing != original_domain.lower():
            raise ValueError(f"?? {domain} ????")

    return SiteConfig(
        domain=domain,
        upstream=upstream,
        certificate_mode=certificate_mode,
        custom_cert_path=custom_cert_path,
        custom_key_path=custom_key_path,
        acme_email=acme_email,
        skip_tls_verify=skip_tls_verify,
        notes=notes,
    )


def site_to_caddy_block(site: Dict[str, object]) -> str:
    domain = str(site["domain"])
    upstream = str(site["upstream"])
    mode = str(site.get("certificate_mode", "auto"))
    custom_cert = str(site.get("custom_cert_path", ""))
    custom_key = str(site.get("custom_key_path", ""))
    skip_tls_verify = bool(site.get("skip_tls_verify", False))

    lines = [f"{domain} {{", "    encode gzip", "    header Access-Control-Allow-Origin *"]
    if mode == "internal":
        lines.append("    tls internal")
    elif mode == "custom":
        lines.append(f"    tls {custom_cert} {custom_key}")

    lines.append(f"    reverse_proxy {upstream} {{")
    if upstream.startswith("https://"):
        lines.append("        transport http {")
        if skip_tls_verify:
            lines.append("            tls_insecure_skip_verify")
        lines.append("        }")

    lines.extend(
        [
            "        header_up X-Real-IP {remote_host}",
            "        header_up X-Forwarded-For {remote_host}",
            "        header_up X-Forwarded-Proto {scheme}",
            "        header_up Host {upstream_hostport}",
            "    }",
            "}",
        ]
    )
    return "\n".join(lines)


def render_caddyfile(state: Dict[str, List[Dict[str, object]]]) -> str:
    emails = sorted(
        {
            str(site.get("acme_email", "")).strip()
            for site in state["sites"]
            if str(site.get("acme_email", "")).strip()
        }
    )
    blocks: List[str] = []
    if emails:
        blocks.append("{\n    email " + emails[0] + "\n}")
    blocks.extend(site_to_caddy_block(site) for site in sorted(state["sites"], key=lambda item: str(item["domain"]).lower()))
    return ("\n\n".join(blocks).strip() + "\n") if blocks else ""


def run_command(command: List[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def apply_caddy_config(state: Dict[str, List[Dict[str, object]]]) -> str:
    CADDYFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = render_caddyfile(state) or "# managed by caddy-emby-ui\n"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".caddy") as handle:
        handle.write(content)
        temp_path = Path(handle.name)

    try:
        validate = run_command(["caddy", "validate", "--config", str(temp_path)])
        if validate.returncode != 0:
            raise RuntimeError((validate.stderr or validate.stdout).strip() or "Caddy ???????")

        CADDYFILE_PATH.write_text(content, encoding="utf-8")

        reload_result = run_command(["systemctl", "reload", "caddy"])
        if reload_result.returncode != 0:
            restart = run_command(["systemctl", "restart", "caddy"])
            if restart.returncode != 0:
                raise RuntimeError((restart.stderr or restart.stdout).strip() or "Caddy ?????")
        return "Caddy ?????????"
    finally:
        temp_path.unlink(missing_ok=True)


def get_service_status() -> Dict[str, str]:
    active = run_command(["systemctl", "is-active", "caddy"])
    version = run_command(["caddy", "version"])
    return {
        "caddy_status": (active.stdout or active.stderr).strip() or "unknown",
        "caddy_version": (version.stdout or version.stderr).strip() or "unknown",
        "managed_sites": str(len(load_state()["sites"])),
    }


def html_escape(value: object) -> str:
    return html.escape(str(value or ""))


def cert_label(mode: str) -> str:
    return {
        "auto": "???? Let's Encrypt",
        "internal": "????",
        "custom": "?????",
    }.get(mode, mode)


def require_auth(handler: "AppHandler") -> bool:
    if not UI_USERNAME or not UI_PASSWORD:
        return True
    header = handler.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        handler.send_response(HTTPStatus.UNAUTHORIZED)
        handler.send_header("WWW-Authenticate", 'Basic realm="Caddy Emby UI"')
        handler.end_headers()
        return False
    try:
        decoded = base64.b64decode(header.split(" ", 1)[1].strip()).decode("utf-8")
    except Exception:
        handler.send_error(HTTPStatus.UNAUTHORIZED)
        return False
    username, _, password = decoded.partition(":")
    if not (secrets.compare_digest(username, UI_USERNAME) and secrets.compare_digest(password, UI_PASSWORD)):
        handler.send_error(HTTPStatus.UNAUTHORIZED)
        return False
    return True


def layout(title: str, content: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html_escape(title)}</title>
  <style>{STYLE}</style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>Caddy Emby WebUI</h1>
      <p>?????? Emby ?????HTTPS ????? Caddy ???WebUI ? <span class="mono">{html_escape(DATA_FILE)}</span> ????????? <span class="mono">{html_escape(CADDYFILE_PATH)}</span>?</p>
    </section>
    {content}
  </div>
</body>
</html>"""


def render_dashboard(message: str = "", message_type: str = "success", form: Dict[str, str] | None = None, edit_domain: str = "") -> str:
    state = load_state()
    status = get_service_status()
    current = next((site for site in state["sites"] if str(site.get("domain")) == edit_domain), None) if edit_domain else None

    values = {
        "domain": "",
        "upstream": "127.0.0.1:8096",
        "certificate_mode": "auto",
        "custom_cert_path": "",
        "custom_key_path": "",
        "acme_email": DEFAULT_EMAIL,
        "skip_tls_verify": "",
        "notes": "",
    }
    if current:
        values.update({key: str(value) for key, value in current.items() if key in values})
        values["skip_tls_verify"] = "1" if current.get("skip_tls_verify") else ""
    if form:
        values.update(form)

    flash = f'<div class="flash {message_type}">{html_escape(message)}</div>' if message else ""

    rows = []
    for site in sorted(state["sites"], key=lambda item: str(item["domain"]).lower()):
        domain = str(site["domain"])
        rows.append(
            f"""
            <tr>
              <td>
                <div class="domain">{html_escape(domain)}</div>
                <div class="hint">{html_escape(str(site.get("notes", "")) or "???")}</div>
              </td>
              <td class="mono">{html_escape(site.get("upstream", ""))}</td>
              <td>{html_escape(cert_label(str(site.get("certificate_mode", "auto"))))}</td>
              <td>
                <div class="actions">
                  <a class="button secondary" href="{route('/')}?edit={html_escape(domain)}">??</a>
                  <form method="post" action="{route('/delete')}" onsubmit="return confirm('???? {html_escape(domain)} ??');">
                    <input type="hidden" name="domain" value="{html_escape(domain)}">
                    <button class="danger" type="submit">??</button>
                  </form>
                </div>
              </td>
            </tr>
            """
        )

    table = (
        """
        <table>
          <thead>
            <tr>
              <th>??</th>
              <th>????</th>
              <th>????</th>
              <th>??</th>
            </tr>
          </thead>
          <tbody>
        """
        + "".join(rows)
        + "</tbody></table>"
        if rows
        else '<div class="empty">???????????????????? Caddy ????????</div>'
    )

    content = f"""
    <div class="grid">
      <section class="card">
        <div class="card-header">
          <h2>????</h2>
          <p>??????????? Caddy ????????? <span class="mono">127.0.0.1:8096</span>????? <span class="mono">https://remote.example.com:443</span>?</p>
        </div>
        <div class="card-body">
          {flash}
          <div class="status-grid">
            <div class="pill"><strong>Caddy ??</strong>{html_escape(status["caddy_status"])}</div>
            <div class="pill"><strong>Caddy ??</strong>{html_escape(status["caddy_version"])}</div>
            <div class="pill"><strong>????</strong>{html_escape(status["managed_sites"])}</div>
          </div>
          <div class="toolbar">
            <form method="post" action="{route('/reload')}">
              <button type="submit">???? Caddy</button>
            </form>
            <a class="button secondary" href="{route('/config')}">????? Caddyfile</a>
          </div>
          <div style="margin-top:18px">{table}</div>
        </div>
      </section>
      <section class="card">
        <div class="card-header">
          <h2>{'????' if edit_domain else '????'}</h2>
          <p>??????????????????????????????????????????? 80/443 ???? Caddy ???</p>
        </div>
        <div class="card-body">
          <form method="post" action="{route('/save')}" class="stack">
            <input type="hidden" name="original_domain" value="{html_escape(edit_domain)}">
            <label>
              <span>??</span>
              <input name="domain" required value="{html_escape(values['domain'])}" placeholder="emby.example.com">
            </label>
            <label>
              <span>????</span>
              <input name="upstream" required value="{html_escape(values['upstream'])}" placeholder="127.0.0.1:8096 ? https://remote.example.com:443">
            </label>
            <label>
              <span>????</span>
              <select name="certificate_mode">
                <option value="auto" {'selected' if values['certificate_mode'] == 'auto' else ''}>???? Let's Encrypt</option>
                <option value="internal" {'selected' if values['certificate_mode'] == 'internal' else ''}>????</option>
                <option value="custom" {'selected' if values['certificate_mode'] == 'custom' else ''}>???????</option>
              </select>
            </label>
            <label>
              <span>ACME ??</span>
              <input name="acme_email" value="{html_escape(values['acme_email'])}" placeholder="?????????????">
            </label>
            <label>
              <span>???????</span>
              <input name="custom_cert_path" value="{html_escape(values['custom_cert_path'])}" placeholder="/etc/ssl/emby/fullchain.pem">
            </label>
            <label>
              <span>???????</span>
              <input name="custom_key_path" value="{html_escape(values['custom_key_path'])}" placeholder="/etc/ssl/emby/privkey.pem">
            </label>
            <label class="check">
              <input type="checkbox" name="skip_tls_verify" value="1" {'checked' if values['skip_tls_verify'] else ''}>
              <span>??? HTTPS ???????????? TLS ??</span>
            </label>
            <label>
              <span>??</span>
              <textarea name="notes" placeholder="????????? Emby ??">{html_escape(values['notes'])}</textarea>
            </label>
            <div class="actions">
              <button type="submit">{'????' if edit_domain else '????'}</button>
              <a class="button secondary" href="{route('/')}">????</a>
            </div>
          </form>
        </div>
      </section>
    </div>
    """
    return layout("Caddy Emby WebUI", content)


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if not require_auth(self):
            return
        path = self.relative_path()
        if path == "/":
            query = parse_qs(urlparse(self.path).query)
            edit_domain = query.get("edit", [""])[0]
            self.send_html(render_dashboard(edit_domain=edit_domain))
            return
        if path == "/config":
            caddyfile = CADDYFILE_PATH.read_text(encoding="utf-8") if CADDYFILE_PATH.exists() else ""
            body = f"""
            <section class="card" style="margin-top:20px">
              <div class="card-header">
                <h2>??? Caddyfile</h2>
                <p>???? <span class="mono">{html_escape(CADDYFILE_PATH)}</span> ?????????? WebUI ???????</p>
              </div>
              <div class="card-body">
                <div class="actions" style="margin-bottom:18px">
                  <a class="button secondary" href="{route('/')}">????</a>
                </div>
                <pre class="mono" style="white-space:pre-wrap">{html_escape(caddyfile or '# ????????? Caddy ??')}</pre>
              </div>
            </section>
            """
            self.send_html(layout("Caddyfile", body))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if not require_auth(self):
            return
        body = self.rfile.read(int(self.headers.get("Content-Length", "0") or 0))
        form = parse_form(body)
        path = self.relative_path()

        if path == "/save":
            self.handle_save(form)
            return
        if path == "/delete":
            self.handle_delete(form)
            return
        if path == "/reload":
            self.handle_reload()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def handle_save(self, form: Dict[str, str]) -> None:
        original_domain = form.get("original_domain", "").strip()
        try:
            site = validate_site(form, original_domain)
            state = load_state()
            updated = False
            for index, item in enumerate(state["sites"]):
                if str(item.get("domain")) == original_domain:
                    state["sites"][index] = asdict(site)
                    updated = True
                    break
            if not updated:
                state["sites"].append(asdict(site))
            message = apply_caddy_config(state)
            save_state(state)
            self.send_html(render_dashboard(message=message, message_type="success"))
        except Exception as exc:
            self.send_html(
                render_dashboard(message=str(exc), message_type="error", form=form, edit_domain=original_domain),
                status=HTTPStatus.BAD_REQUEST,
            )

    def handle_delete(self, form: Dict[str, str]) -> None:
        domain = form.get("domain", "").strip()
        state = load_state()
        state["sites"] = [site for site in state["sites"] if str(site.get("domain")) != domain]
        try:
            message = apply_caddy_config(state)
            save_state(state)
            self.send_html(render_dashboard(message=f"{domain} ????{message}", message_type="success"))
        except Exception as exc:
            self.send_html(render_dashboard(message=str(exc), message_type="error"), status=HTTPStatus.BAD_REQUEST)

    def handle_reload(self) -> None:
        try:
            self.send_html(render_dashboard(message=apply_caddy_config(load_state()), message_type="success"))
        except Exception as exc:
            self.send_html(render_dashboard(message=str(exc), message_type="error"), status=HTTPStatus.BAD_REQUEST)

    def relative_path(self) -> str:
        path = urlparse(self.path).path
        base = normalize_base_path()
        if base and path.startswith(base):
            return path[len(base):] or "/"
        return path

    def send_html(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {self.address_string()} {fmt % args}")


def main() -> None:
    ensure_data_file()
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"listening on http://{HOST}:{PORT}{normalize_base_path() or '/'}")
    server.serve_forever()


if __name__ == "__main__":
    main()
