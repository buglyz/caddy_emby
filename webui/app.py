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
from urllib.parse import parse_qs, urlencode, urlparse

DATA_DIR = Path(os.environ.get("CADDY_EMBY_UI_DATA_DIR", "/etc/caddy-emby-ui"))
DATA_FILE = DATA_DIR / "sites.json"
CADDYFILE_PATH = Path(os.environ.get("CADDY_EMBY_UI_CADDYFILE", "/etc/caddy/Caddyfile"))
HOST = os.environ.get("CADDY_EMBY_UI_HOST", "0.0.0.0")
PORT = int(os.environ.get("CADDY_EMBY_UI_PORT", "9780"))
DEFAULT_EMAIL = os.environ.get("CADDY_EMBY_UI_ACME_EMAIL", "")
DEFAULT_LANG = os.environ.get("CADDY_EMBY_UI_LANG", "zh-CN")
UI_USERNAME = os.environ.get("CADDY_EMBY_UI_USERNAME", "")
UI_PASSWORD = os.environ.get("CADDY_EMBY_UI_PASSWORD", "")
BASE_PATH = os.environ.get("CADDY_EMBY_UI_BASE_PATH", "").strip("/")

STYLE = """
:root{--bg:#f4efe6;--panel:rgba(255,252,247,.92);--panel2:#fffaf2;--line:#d7c9b2;--text:#231b12;--muted:#6e5a44;--brand:#0f766e;--danger:#b42318;--shadow:0 18px 40px rgba(35,27,18,.08)}*{box-sizing:border-box}body{margin:0;font-family:"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;color:var(--text);background:radial-gradient(circle at top left,rgba(15,118,110,.18),transparent 30%),radial-gradient(circle at right center,rgba(180,71,8,.12),transparent 25%),linear-gradient(180deg,#f8f3ea 0%,var(--bg) 100%)}.shell{width:min(1180px,calc(100% - 32px));margin:32px auto}.hero,.card{background:var(--panel);border:1px solid rgba(215,201,178,.9);border-radius:24px;box-shadow:var(--shadow)}.hero{padding:28px}.hero h1{margin:0 0 10px;font-size:34px}.hero p{margin:0;max-width:780px;color:var(--muted);line-height:1.6}.grid{display:grid;grid-template-columns:1.45fr 1fr;gap:20px;margin-top:20px}.card-header{padding:18px 22px;border-bottom:1px solid rgba(215,201,178,.8);background:rgba(255,250,242,.8)}.card-header h2{margin:0 0 6px;font-size:21px}.card-header p,.hint{margin:0;color:var(--muted);line-height:1.5}.card-body{padding:22px}.flash{padding:14px 16px;border-radius:16px;margin-bottom:18px;line-height:1.5}.flash.success{background:rgba(15,118,110,.12);color:#115e59}.flash.error{background:rgba(180,35,24,.1);color:var(--danger)}.status-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:18px}.pill{padding:14px;border-radius:18px;background:var(--panel2);border:1px solid rgba(215,201,178,.85)}.pill strong{display:block;font-size:13px;color:var(--muted);margin-bottom:4px}.toolbar,.actions,.lang-switch{display:flex;gap:10px;flex-wrap:wrap}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:14px 10px;border-bottom:1px solid rgba(215,201,178,.65);vertical-align:top}th{color:var(--muted);font-size:13px;font-weight:600}.domain{font-weight:700;margin-bottom:4px}label{display:block;margin-bottom:14px;font-weight:600}label span{display:block;margin-bottom:8px}input,select,textarea{width:100%;border:1px solid var(--line);border-radius:14px;padding:12px 14px;font:inherit;background:#fffdfa;color:var(--text)}textarea{min-height:110px;resize:vertical}.check{display:flex;gap:10px;align-items:center;font-weight:500}.check input{width:auto}button,.button{display:inline-flex;align-items:center;justify-content:center;border:none;border-radius:999px;padding:11px 18px;text-decoration:none;background:var(--brand);color:#fff;cursor:pointer;font:inherit}.button.secondary,button.secondary{background:#efe2cf;color:var(--text)}.button.danger,button.danger{background:var(--danger)}.stack{display:grid;gap:10px}.empty{padding:18px;border-radius:16px;background:rgba(255,250,242,.85);border:1px dashed var(--line);color:var(--muted)}.mono{font-family:Consolas,"SFMono-Regular",monospace;font-size:13px}@media (max-width:900px){.grid{grid-template-columns:1fr}.status-grid{grid-template-columns:1fr}th:nth-child(3),td:nth-child(3){display:none}}
"""

I18N = {
    "en": {
        "html_lang":"en","title":"Caddy Emby WebUI","lang_zh":"中文","lang_en":"English",
        "hero":"Manage Emby reverse proxies, HTTPS certificate policies, and generated Caddy configuration from a browser. The WebUI uses {data} as the source of truth and generates {cfg}.",
        "sites":"Sites","sites_desc":"Saving or deleting a site immediately updates the generated Caddy configuration. The upstream can be a local address like {local} or a remote HTTPS origin like {remote}.",
        "status":"Caddy status","version":"Caddy version","managed":"Managed sites","reload":"Reload Caddy","view_cfg":"View generated Caddyfile",
        "edit_site":"Edit site","add_site":"Add site","form_desc":"Automatic certificates require the domain to resolve to this server and Caddy to have access to ports 80 and 443.",
        "domain":"Domain","upstream":"Upstream","cert_mode":"Certificate mode","cert_auto":"Automatic Let's Encrypt","cert_internal":"Internal certificate","cert_custom":"Custom certificate files",
        "acme":"ACME email","acme_ph":"Optional but recommended for automatic certificates","cert_path":"Custom certificate path","key_path":"Custom key path",
        "skip_tls":"Skip TLS verification for HTTPS upstreams with self-signed or untrusted certificates","notes":"Notes","notes_ph":"Optional notes for this site",
        "save":"Save changes","add":"Add site","clear":"Clear form","no_notes":"No notes","empty":"No managed sites yet. Saving the form on the right will generate Caddy configuration and reload the service.",
        "actions":"Actions","edit":"Edit","delete":"Delete","delete_q":"Delete {domain}?","cfg_title":"Generated Caddyfile","cfg_desc":"Manual changes to {cfg} will be overwritten the next time you save a site through the WebUI.",
        "back":"Back to dashboard","no_cfg":"# No Caddy configuration has been generated yet","deleted":"{domain} deleted. {message}",
        "e_domain_req":"Domain is required.","e_domain_fmt":"Domain format is invalid.","e_upstream_req":"Upstream address is required.","e_mode":"Certificate mode is not supported.","e_custom":"Custom certificate mode requires both certificate and key paths.","e_skip":"Skip TLS verification can only be used with an HTTPS upstream.","e_exists":"Domain {domain} already exists.","e_validate":"Caddy configuration validation failed.","e_restart":"Caddy restart failed.","updated":"Caddy configuration updated and reloaded."
    },
    "zh-CN": {
        "html_lang":"zh-CN","title":"Caddy Emby WebUI","lang_zh":"中文","lang_en":"English",
        "hero":"用浏览器维护 Emby 反向代理、HTTPS 证书策略和生成的 Caddy 配置。WebUI 以 {data} 作为管理数据源，并生成 {cfg}。",
        "sites":"站点列表","sites_desc":"保存或删除站点会立即更新生成的 Caddy 配置。上游既可以是本地地址 {local}，也可以是远程 HTTPS 地址 {remote}。",
        "status":"Caddy 状态","version":"Caddy 版本","managed":"受管站点","reload":"重新加载 Caddy","view_cfg":"查看生成的 Caddyfile",
        "edit_site":"编辑站点","add_site":"新增站点","form_desc":"自动证书模式要求域名已经解析到当前服务器，并且 Caddy 可以使用 80 和 443 端口。",
        "domain":"域名","upstream":"上游地址","cert_mode":"证书模式","cert_auto":"自动申请 Let's Encrypt","cert_internal":"内部证书","cert_custom":"自定义证书文件",
        "acme":"ACME 邮箱","acme_ph":"可选，自动证书模式建议填写","cert_path":"自定义证书路径","key_path":"自定义私钥路径",
        "skip_tls":"如果上游是 HTTPS 且使用自签名或不受信任证书，则跳过 TLS 校验","notes":"备注","notes_ph":"可选，便于区分站点",
        "save":"保存修改","add":"新增站点","clear":"清空表单","no_notes":"无备注","empty":"当前还没有受管站点。保存右侧表单后会生成 Caddy 配置并重载服务。",
        "actions":"操作","edit":"编辑","delete":"删除","delete_q":"确认删除 {domain} 吗？","cfg_title":"生成的 Caddyfile","cfg_desc":"手工修改 {cfg} 的内容，会在下次通过 WebUI 保存站点时被覆盖。",
        "back":"返回首页","no_cfg":"# 当前还没有生成任何 Caddy 配置","deleted":"{domain} 已删除。{message}",
        "e_domain_req":"域名不能为空。","e_domain_fmt":"域名格式不正确。","e_upstream_req":"上游地址不能为空。","e_mode":"证书模式不受支持。","e_custom":"自定义证书模式必须填写证书路径和私钥路径。","e_skip":"只有 HTTPS 上游才支持跳过 TLS 校验。","e_exists":"域名 {domain} 已存在。","e_validate":"Caddy 配置校验失败。","e_restart":"Caddy 重启失败。","updated":"Caddy 配置已更新并重载。"
    }
}

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
    base_path: str = ""


def get_lang(requested=""):
    if requested in I18N:
        return requested
    return DEFAULT_LANG if DEFAULT_LANG in I18N else "en"

def tr(lang, key, **kwargs):
    text = I18N[get_lang(lang)][key]
    return text.format(**kwargs) if kwargs else text

def normalize_base_path():
    return f"/{BASE_PATH}" if BASE_PATH else ""

def ensure_data_file():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text(json.dumps({"sites": []}, ensure_ascii=False, indent=2), encoding="utf-8")

def load_state():
    ensure_data_file()
    try:
        state = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        state = {"sites": []}
    state.setdefault("sites", [])
    return state

def save_state(state):
    ensure_data_file()
    DATA_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def parse_form(body):
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {k: v[0] for k, v in parsed.items()}

def parse_bool(value):
    return value in {"1", "true", "on", "yes"}

def html_escape(value):
    return html.escape(str(value or ""))

def run_command(command):
    return subprocess.run(command, capture_output=True, text=True, check=False)

def route(path, lang, extra=None):
    query = {"lang": get_lang(lang)}
    if extra:
        query.update(extra)
    return f"{normalize_base_path()}{path}?{urlencode(query)}"

def validate_site(form, lang, original_domain=""):
    domain = form.get("domain", "").strip()
    upstream = form.get("upstream", "").strip()
    certificate_mode = form.get("certificate_mode", "auto").strip() or "auto"
    custom_cert_path = form.get("custom_cert_path", "").strip()
    custom_key_path = form.get("custom_key_path", "").strip()
    acme_email = form.get("acme_email", "").strip()
    notes = form.get("notes", "").strip()
    base_path = form.get("base_path", "").strip()
    skip_tls_verify = parse_bool(form.get("skip_tls_verify", ""))
    if not domain:
        raise ValueError(tr(lang, "e_domain_req"))
    if " " in domain or "/" in domain:
        raise ValueError(tr(lang, "e_domain_fmt"))
    if not upstream:
        raise ValueError(tr(lang, "e_upstream_req"))
    if certificate_mode not in {"auto", "internal", "custom"}:
        raise ValueError(tr(lang, "e_mode"))
    if certificate_mode == "custom" and (not custom_cert_path or not custom_key_path):
        raise ValueError(tr(lang, "e_custom"))
    if skip_tls_verify and not upstream.startswith("https://"):
        raise ValueError(tr(lang, "e_skip"))
    state = load_state()
    for site in state["sites"]:
        existing = str(site.get("domain", "")).lower()
        if existing == domain.lower() and existing != original_domain.lower():
            raise ValueError(tr(lang, "e_exists", domain=domain))
    return SiteConfig(domain, upstream, certificate_mode, custom_cert_path, custom_key_path, acme_email, skip_tls_verify, notes, base_path)

def site_to_caddy_block(site):
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
    lines.extend([
        "        header_up X-Real-IP {remote_host}",
        "        header_up X-Forwarded-For {remote_host}",
        "        header_up X-Forwarded-Proto {scheme}",
        "        header_up Host {upstream_hostport}",
        "    }",
        "}",
    ])
    return "\n".join(lines)

def render_caddyfile(state):
    emails = sorted({str(site.get("acme_email", "")).strip() for site in state["sites"] if str(site.get("acme_email", "")).strip()})
    blocks = []
    if emails:
        blocks.append("{\n    email " + emails[0] + "\n}")
    blocks.extend(site_to_caddy_block(site) for site in sorted(state["sites"], key=lambda item: str(item["domain"]).lower()))
    return ("\n\n".join(blocks).strip() + "\n") if blocks else ""

def apply_caddy_config(state, lang):
    CADDYFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = render_caddyfile(state) or "# managed by caddy-emby-ui\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".caddy") as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    try:
        validate = run_command(["caddy", "validate", "--config", str(temp_path), "--adapter", "caddyfile"])
        if validate.returncode != 0:
            raise RuntimeError((validate.stderr or validate.stdout).strip() or tr(lang, "e_validate"))
        CADDYFILE_PATH.write_text(content, encoding="utf-8")
        reload_result = run_command(["systemctl", "reload", "caddy"])
        if reload_result.returncode != 0:
            restart = run_command(["systemctl", "restart", "caddy"])
            if restart.returncode != 0:
                raise RuntimeError((restart.stderr or restart.stdout).strip() or tr(lang, "e_restart"))
        return tr(lang, "updated")
    finally:
        temp_path.unlink(missing_ok=True)

def probe_upstream(upstream: str, timeout: float = 3.0) -> str:
    """Best-effort HTTP probe for the configured upstream.

    Notes:
    - This runs on the WebUI host, *not* from Caddy itself.
    - It only does a lightweight request and is safe to ignore if it fails.
    """
    try:
        import urllib.request
        import urllib.error

        # Normalise bare host:port into http://host:port for probing
        url = upstream.strip()
        if not url.startswith(("http://", "https://")):
            url = f"http://{url}"

        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = getattr(resp, "status", getattr(resp, "code", 0))
            return f"OK (HTTP {code})"
    except Exception as exc:  # pragma: no cover - best-effort diagnostics
        return f"unreachable: {exc.__class__.__name__}"


def get_service_status():
    active = run_command(["systemctl", "is-active", "caddy"])
    version = run_command(["caddy", "version"])
    return {
        "caddy_status": (active.stdout or active.stderr).strip() or "unknown",
        "caddy_version": (version.stdout or version.stderr).strip() or "unknown",
        "managed_sites": str(len(load_state()["sites"])),
    }

def cert_label(mode, lang):
    return {"auto": tr(lang, "cert_auto"), "internal": tr(lang, "cert_internal"), "custom": tr(lang, "cert_custom")}.get(mode, mode)

def require_auth(handler):
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
def language_switch(lang):
    return f'<div class="lang-switch"><a class="button secondary" href="{route("/", "zh-CN")}">{html_escape(tr("zh-CN", "lang_zh"))}</a><a class="button secondary" href="{route("/", "en")}">{html_escape(tr("en", "lang_en"))}</a></div>'

def layout(title, content, lang):
    hero = tr(lang, "hero", data=f'<span class="mono">{html_escape(DATA_FILE)}</span>', cfg=f'<span class="mono">{html_escape(CADDYFILE_PATH)}</span>')
    return f'''<!doctype html><html lang="{html_escape(tr(lang, "html_lang"))}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html_escape(title)}</title><style>{STYLE}</style></head><body><div class="shell"><section class="hero"><h1>Caddy Emby WebUI</h1><p>{hero}</p>{language_switch(lang)}</section>{content}</div></body></html>'''

def render_dashboard(message="", message_type="success", form=None, edit_domain="", lang="en"):
    state = load_state(); status = get_service_status(); current = next((site for site in state["sites"] if str(site.get("domain")) == edit_domain), None) if edit_domain else None
    values = {"domain":"","upstream":"127.0.0.1:8096","certificate_mode":"auto","custom_cert_path":"","custom_key_path":"","acme_email":DEFAULT_EMAIL,"skip_tls_verify":"","notes":"","base_path":""}
    if current:
        values.update({k: str(v) for k, v in current.items() if k in values}); values["skip_tls_verify"] = "1" if current.get("skip_tls_verify") else ""; values["base_path"] = str(current.get("base_path", ""))
    if form:
        values.update(form)
    flash = f'<div class="flash {message_type}">{html_escape(message)}</div>' if message else ""
    rows = []
    for site in sorted(state["sites"], key=lambda item: str(item["domain"]).lower()):
        domain = str(site["domain"])
        upstream = str(site.get("upstream", ""))
        health = probe_upstream(upstream) if upstream else "-"
        rows.append(f'''<tr><td><div class="domain">{html_escape(domain)}</div><div class="hint">{html_escape(str(site.get("notes", "")) or tr(lang, "no_notes"))}</div></td><td class="mono">{html_escape(upstream)}<div class="hint">{html_escape(health)}</div></td><td>{html_escape(cert_label(str(site.get("certificate_mode", "auto")), lang))}</td><td><div class="actions"><a class="button secondary" href="{route("/", lang, {"edit": domain})}">{html_escape(tr(lang, "edit"))}</a><form method="post" action="{route("/delete", lang)}" onsubmit="return confirm('{html_escape(tr(lang, "delete_q", domain=domain))}');"><input type="hidden" name="domain" value="{html_escape(domain)}"><button class="danger" type="submit">{html_escape(tr(lang, "delete"))}</button></form></div></td></tr>''')
    if rows:
        table = f'''<table><thead><tr><th>{html_escape(tr(lang, "domain"))}</th><th>{html_escape(tr(lang, "upstream"))}</th><th>{html_escape(tr(lang, "cert_mode"))}</th><th>{html_escape(tr(lang, "actions"))}</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'''
    else:
        table = f'<div class="empty">{html_escape(tr(lang, "empty"))}</div>'
    desc = tr(lang, "sites_desc", local=f'<span class="mono">127.0.0.1:8096</span>', remote=f'<span class="mono">https://remote.example.com:443</span>')
    content = f'''<div class="grid"><section class="card"><div class="card-header"><h2>{html_escape(tr(lang, "sites"))}</h2><p>{desc}</p></div><div class="card-body">{flash}<div class="status-grid"><div class="pill"><strong>{html_escape(tr(lang, "status"))}</strong>{html_escape(status["caddy_status"])}</div><div class="pill"><strong>{html_escape(tr(lang, "version"))}</strong>{html_escape(status["caddy_version"])}</div><div class="pill"><strong>{html_escape(tr(lang, "managed"))}</strong>{html_escape(status["managed_sites"])}</div></div><div class="toolbar"><form method="post" action="{route("/reload", lang)}"><button type="submit">{html_escape(tr(lang, "reload"))}</button></form><a class="button secondary" href="{route("/config", lang)}">{html_escape(tr(lang, "view_cfg"))}</a></div><div style="margin-top:18px">{table}</div></div></section><section class="card"><div class="card-header"><h2>{html_escape(tr(lang, "edit_site") if edit_domain else tr(lang, "add_site"))}</h2><p>{html_escape(tr(lang, "form_desc"))}</p></div><div class="card-body"><form method="post" action="{route("/save", lang)}" class="stack"><input type="hidden" name="original_domain" value="{html_escape(edit_domain)}"><label><span>{html_escape(tr(lang, "domain"))}</span><input name="domain" required value="{html_escape(values['domain'])}" placeholder="emby.example.com"></label><label><span>{html_escape(tr(lang, "upstream"))}</span><input name="upstream" required value="{html_escape(values['upstream'])}" placeholder="127.0.0.1:8096 or https://remote.example.com:443"></label><label><span>子路径 / Base path (可选)</span><input name="base_path" value="{html_escape(values['base_path'])}" placeholder="/emby01"></label><label><span>{html_escape(tr(lang, "cert_mode"))}</span><select name="certificate_mode"><option value="auto" {"selected" if values['certificate_mode']=='auto' else ""}>{html_escape(tr(lang, "cert_auto"))}</option><option value="internal" {"selected" if values['certificate_mode']=='internal' else ""}>{html_escape(tr(lang, "cert_internal"))}</option><option value="custom" {"selected" if values['certificate_mode']=='custom' else ""}>{html_escape(tr(lang, "cert_custom"))}</option></select></label><label><span>{html_escape(tr(lang, "acme"))}</span><input name="acme_email" value="{html_escape(values['acme_email'])}" placeholder="{html_escape(tr(lang, "acme_ph"))}"></label><label><span>{html_escape(tr(lang, "cert_path"))}</span><input name="custom_cert_path" value="{html_escape(values['custom_cert_path'])}" placeholder="/etc/ssl/emby/fullchain.pem"></label><label><span>{html_escape(tr(lang, "key_path"))}</span><input name="custom_key_path" value="{html_escape(values['custom_key_path'])}" placeholder="/etc/ssl/emby/privkey.pem"></label><label class="check"><input type="checkbox" name="skip_tls_verify" value="1" {"checked" if values['skip_tls_verify'] else ""}><span>{html_escape(tr(lang, "skip_tls"))}</span></label><label><span>{html_escape(tr(lang, "notes"))}</span><textarea name="notes" placeholder="{html_escape(tr(lang, "notes_ph"))}">{html_escape(values['notes'])}</textarea></label><div class="actions"><button type="submit">{html_escape(tr(lang, "save") if edit_domain else tr(lang, "add"))}</button><a class="button secondary" href="{route("/", lang)}">{html_escape(tr(lang, "clear"))}</a></div></form></div></section></div>'''
    return layout(tr(lang, "title"), content, lang)

class AppHandler(BaseHTTPRequestHandler):
    def current_lang(self):
        return get_lang(parse_qs(urlparse(self.path).query).get("lang", [""])[0])
    def relative_path(self):
        path = urlparse(self.path).path; base = normalize_base_path();
        return path[len(base):] or "/" if base and path.startswith(base) else path
    def send_html(self, content, status=HTTPStatus.OK):
        payload = content.encode("utf-8"); self.send_response(status); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)
    def do_GET(self):
        if not require_auth(self): return
        lang = self.current_lang(); path = self.relative_path()
        if path == "/":
            edit_domain = parse_qs(urlparse(self.path).query).get("edit", [""])[0]
            self.send_html(render_dashboard(edit_domain=edit_domain, lang=lang)); return
        if path == "/config":
            caddyfile = CADDYFILE_PATH.read_text(encoding="utf-8") if CADDYFILE_PATH.exists() else ""
            body = f'''<section class="card" style="margin-top:20px"><div class="card-header"><h2>{html_escape(tr(lang, "cfg_title"))}</h2><p>{html_escape(tr(lang, "cfg_desc", cfg=str(CADDYFILE_PATH)))}</p></div><div class="card-body"><div class="actions" style="margin-bottom:18px"><a class="button secondary" href="{route("/", lang)}">{html_escape(tr(lang, "back"))}</a></div><pre class="mono" style="white-space:pre-wrap">{html_escape(caddyfile or tr(lang, "no_cfg"))}</pre></div></section>'''
            self.send_html(layout("Caddyfile", body, lang)); return
        self.send_error(HTTPStatus.NOT_FOUND)
    def do_POST(self):
        if not require_auth(self): return
        form = parse_form(self.rfile.read(int(self.headers.get("Content-Length", "0") or 0))); lang = get_lang(form.get("lang", self.current_lang())); path = self.relative_path()
        if path == "/save": return self.handle_save(form, lang)
        if path == "/delete": return self.handle_delete(form, lang)
        if path == "/reload": return self.handle_reload(lang)
        self.send_error(HTTPStatus.NOT_FOUND)
    def handle_save(self, form, lang):
        original_domain = form.get("original_domain", "").strip()
        try:
            site = validate_site(form, lang, original_domain); state = load_state(); updated = False
            for index, item in enumerate(state["sites"]):
                if str(item.get("domain")) == original_domain:
                    state["sites"][index] = asdict(site); updated = True; break
            if not updated: state["sites"].append(asdict(site))
            message = apply_caddy_config(state, lang); save_state(state)
            self.send_html(render_dashboard(message=message, message_type="success", lang=lang))
        except Exception as exc:
            self.send_html(render_dashboard(message=str(exc), message_type="error", form=form, edit_domain=original_domain, lang=lang), status=HTTPStatus.BAD_REQUEST)
    def handle_delete(self, form, lang):
        domain = form.get("domain", "").strip(); state = load_state(); state["sites"] = [site for site in state["sites"] if str(site.get("domain")) != domain]
        try:
            message = apply_caddy_config(state, lang); save_state(state)
            self.send_html(render_dashboard(message=tr(lang, "deleted", domain=domain, message=message), message_type="success", lang=lang))
        except Exception as exc:
            self.send_html(render_dashboard(message=str(exc), message_type="error", lang=lang), status=HTTPStatus.BAD_REQUEST)
    def handle_reload(self, lang):
        try:
            self.send_html(render_dashboard(message=apply_caddy_config(load_state(), lang), message_type="success", lang=lang))
        except Exception as exc:
            self.send_html(render_dashboard(message=str(exc), message_type="error", lang=lang), status=HTTPStatus.BAD_REQUEST)
    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {self.address_string()} {fmt % args}")

def main():
    ensure_data_file(); server = ThreadingHTTPServer((HOST, PORT), AppHandler); print(f"listening on http://{HOST}:{PORT}{normalize_base_path() or '/'}"); server.serve_forever()

if __name__ == "__main__":
    main()
