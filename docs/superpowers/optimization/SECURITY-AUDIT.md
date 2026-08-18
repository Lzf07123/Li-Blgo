# Li&Blog 安全审计记录

> 日期：2026-08-19 ｜ 依据：单元测试 + 代码走查 + nginx 配置实测

## 已验证项

| 领域 | 措施 | 证据 |
| --- | --- | --- |
| 密码 | PBKDF2-HMAC-SHA256 600k 迭代，随机盐 | test_security |
| 会话 | SQLite 服务端会话，Cookie 仅随机 id（HttpOnly/SameSite=Lax） | test_session |
| CSRF | 全部 POST 校验，含 JSON 上传 | test_admin_routes |
| 登录限速 | 账号+IP 5 次/60 秒；全局 IP 30 次/60 秒；假哈希防枚举 | test_security + test_account |
| OIDC | PKCE/state/nonce、id_token 验签、at_hash、userinfo sub 一致、回程登出 jti 防重放 | test_oidc |
| 路径安全 | slug 白名单、上传/导入/恢复路径防穿越、ZIP 大小限制 | test_content/test_restore/test_uploads |
| 媒体 | 白名单扩展名、单文件 ≤5MB、1600px 内缩放、删除后清理引用 | test_media |
| 响应头 | nosniff、X-Frame-Options、Referrer-Policy、Permissions-Policy、CSP（nginx）、HSTS（HTTPS 模板） | nginx -t + 中间件 |
| 审计 | 登录/内容操作审计日志（SQLite） | test_account（/logs） |
| 秘密 | OIDC secret/会话密钥仅环境变量或 0600 secret 文件，不入 git | .env.example + config.py |
| 备案 | 备案号非空才展示，无假占位；页脚链接官方域名 | footer.html + brand.yaml |
| 隐私 | beacon 仅记录时间+路径，无 IP/UA/Cookie；公开站零交互表单 | nginx log_format + 模板走查 |

## 结论

后台满足“秘密路径、密码哈希、限速、IP 白名单、非 root、无 Docker socket”红线；公开站不收集访客个人信息。
