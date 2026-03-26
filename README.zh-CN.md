# Caddy Emby Manager

一个面向 Debian 和 Ubuntu 服务器的 Emby + Caddy 管理工具。

当前仓库包含两个入口：

1. WebUI 主方案：`webui/app.py`
2. 旧版 Bash 菜单脚本：`install_caddy_emby.sh`

推荐使用 WebUI。它更适合长期管理多个站点、证书策略，以及统一生成和维护 Caddy 配置。旧版 Bash 脚本仍然保留，适合只通过 SSH 临时操作的场景。

## 功能特性

- 管理多个 Emby 反向代理站点
- 支持本地上游，例如 `127.0.0.1:8096`
- 支持远程 HTTPS 上游，例如 `https://remote.example.com:443`
- 支持 3 种证书模式
- `auto`：由 Caddy 自动申请 Let's Encrypt 证书
- `internal`：使用 Caddy 内部证书
- `custom`：使用你自己提供的证书和私钥文件
- 自动生成 `/etc/caddy/Caddyfile`
- 应用前先执行 `caddy validate`
- 配置有效后自动重载 `caddy`
- 站点数据持久化保存在 `/etc/caddy-emby-ui/sites.json`
- WebUI 可选启用 Basic Auth 保护

## 运行要求

- Debian 或 Ubuntu
- 需要 `root` 权限完成安装和服务管理
- 需要 systemd
- 如果使用自动证书，域名必须已经解析到当前服务器
- 如果使用自动证书，80 和 443 端口必须能被 Caddy 使用

## 快速开始

在 Debian 或 Ubuntu 服务器中，进入仓库根目录后执行：

```bash
chmod +x install_webui.sh
./install_webui.sh
```

安装脚本会：

- 安装 `caddy` 和 `python3`
- 将 WebUI 部署到 `/opt/caddy-emby-ui/app.py`
- 创建 `/etc/caddy-emby-ui`
- 创建 `/etc/caddy-emby-ui/webui.env`
- 创建并启动 `caddy-emby-ui` systemd 服务

安装完成后，建议立刻编辑环境变量文件：

```bash
nano /etc/caddy-emby-ui/webui.env
```

至少设置一组账号密码：

```env
CADDY_EMBY_UI_USERNAME=admin
CADDY_EMBY_UI_PASSWORD=change-this-password
```

然后重启服务：

```bash
systemctl restart caddy-emby-ui
```

浏览器访问：

```text
http://服务器IP:9780/
```

## 环境变量说明

环境文件路径：

```text
/etc/caddy-emby-ui/webui.env
```

支持的变量如下。

`CADDY_EMBY_UI_HOST`

- 默认值：`0.0.0.0`
- 作用：WebUI 监听地址
- 什么时候修改：你只想监听本机或内网地址时

`CADDY_EMBY_UI_PORT`

- 默认值：`9780`
- 作用：WebUI 监听端口
- 什么时候修改：端口冲突，或者你想换一个管理端口时

`CADDY_EMBY_UI_DATA_DIR`

- 默认值：`/etc/caddy-emby-ui`
- 作用：保存 `sites.json`
- 什么时候修改：你想把管理数据放到其他目录时

`CADDY_EMBY_UI_CADDYFILE`

- 默认值：`/etc/caddy/Caddyfile`
- 作用：WebUI 生成并覆盖的 Caddy 配置文件
- 什么时候修改：你想写入其他 Caddy 配置路径时

`CADDY_EMBY_UI_USERNAME`

- 默认值：空
- 作用：Basic Auth 用户名
- 什么时候修改：你希望保护 WebUI 时

`CADDY_EMBY_UI_PASSWORD`

- 默认值：空
- 作用：Basic Auth 密码
- 什么时候修改：你希望保护 WebUI 时

`CADDY_EMBY_UI_ACME_EMAIL`

- 默认值：空
- 作用：自动证书模式下的默认 ACME 邮箱
- 什么时候修改：你希望所有站点都默认带上同一个邮箱时

`CADDY_EMBY_UI_BASE_PATH`

- 默认值：空
- 作用：把 WebUI 挂到某个子路径，例如 `/emby-ui`
- 什么时候修改：你准备把 WebUI 放到另一个反向代理路径后面时

## WebUI 使用说明

新增或编辑站点时，需要填写以下字段。

`Domain`

- 示例：`emby.example.com`
- 用作 Caddy 站点标签

`Upstream`

- 本地示例：`127.0.0.1:8096`
- 远程 HTTPS 示例：`https://remote.example.com:443`

`Certificate mode`

- `auto`：通过 Caddy 自动申请 Let's Encrypt
- `internal`：使用 Caddy 内部证书
- `custom`：手动填写证书文件路径和私钥文件路径

`ACME email`

- 可选
- 自动证书模式推荐填写

`Custom certificate path` / `Custom key path`

- 仅在 `custom` 模式下需要
- 示例：

```text
/etc/ssl/emby/fullchain.pem
/etc/ssl/emby/privkey.pem
```

`Skip TLS verification`

- 只对 HTTPS 上游有意义
- 当上游使用自签名证书或不受信任证书时可启用

## 证书模式说明

### Automatic certificates

适合以下场景：

- 你有公网域名
- DNS 已经解析到当前服务器
- Caddy 能监听 80 和 443 端口

注意：

- 如果 80/443 被其他服务占用，签发会失败
- 如果 DNS 还没有生效，签发也会失败

### Internal certificates

适合以下场景：

- 仅在内网使用
- 测试环境
- 不需要公网信任证书

注意：

- 浏览器默认不会信任它

### Custom certificates

适合以下场景：

- 你已经有现成证书文件
- 你希望自己控制证书来源和续期方式

注意：

- WebUI 不负责上传证书
- 证书和私钥文件必须已经存在于服务器中

## 文件与目录

关键路径如下：

- 应用程序：`/opt/caddy-emby-ui/app.py`
- 环境文件：`/etc/caddy-emby-ui/webui.env`
- 站点数据：`/etc/caddy-emby-ui/sites.json`
- 生成配置：`/etc/caddy/Caddyfile`
- systemd 服务：`/etc/systemd/system/caddy-emby-ui.service`

设计说明：

- `sites.json` 是受管数据的唯一事实来源
- `Caddyfile` 是生成结果，不是主数据源
- 你手工修改 `/etc/caddy/Caddyfile` 的内容，会在下一次通过 WebUI 保存站点时被覆盖

## 常用操作

查看 WebUI 状态：

```bash
systemctl status caddy-emby-ui -l
```

跟踪 WebUI 日志：

```bash
journalctl -u caddy-emby-ui -f
```

重启 WebUI：

```bash
systemctl restart caddy-emby-ui
```

查看 Caddy 状态：

```bash
systemctl status caddy -l
```

跟踪 Caddy 日志：

```bash
journalctl -u caddy -f
```

手动校验生成的配置：

```bash
caddy validate --config /etc/caddy/Caddyfile
```

## 故障排查

### WebUI 打不开

检查：

- `caddy-emby-ui` 是否正在运行
- 监听地址和端口是否正确
- 防火墙是否允许 `9780` 端口

可用命令：

```bash
systemctl status caddy-emby-ui -l
journalctl -u caddy-emby-ui -f
ss -lntp | grep 9780
```

### 自动证书签发失败

常见原因：

- 域名没有解析到当前服务器
- 80 或 443 端口被其他服务占用
- 服务器无法从公网访问

可用命令：

```bash
ss -lntp | grep -E ':80|:443'
systemctl status caddy -l
journalctl -u caddy -f
```

### HTTPS 上游访问失败

常见原因：

- 上游地址填写错误
- 远程 Emby 证书不被信任

处理方式：

- 确认上游地址以 `https://` 开头
- 如果上游使用自签名证书，可以启用 `Skip TLS verification`

### 保存成功但 Emby 仍然无法访问

检查：

- 上游是否真实可达
- Emby 是否正常监听
- 是否有防火墙拦截到上游的访问
- 域名是否解析到了正确服务器

### 手工修改 `Caddyfile` 后内容消失

这是当前设计下的预期行为：

- WebUI 管理的是 `sites.json`
- 每次保存站点都会重新生成 `Caddyfile`

如果你希望长期手工维护 Caddy 配置，不要把这个 WebUI 当作主配置入口。

## 安全建议

- 强烈建议设置 `CADDY_EMBY_UI_USERNAME` 和 `CADDY_EMBY_UI_PASSWORD`
- 不要在没有认证的情况下直接把 WebUI 暴露到公网
- 尽量通过防火墙限制管理端口
- 如果必须公网访问，建议再套一层额外的访问控制

## 旧版 Bash 脚本

旧脚本仍然保留在：

```bash
install_caddy_emby.sh
```

适用场景：

- 只想通过 SSH 操作
- 需要快速临时搭建
- 不需要浏览器界面

运行方式：

```bash
bash install_caddy_emby.sh
```

如果你要长期维护多个站点，仍然推荐使用 WebUI。
