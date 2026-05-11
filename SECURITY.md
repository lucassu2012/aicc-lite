# 安全策略与审计报告

## 报告漏洞

如果您在 AICC-Lite 中发现安全漏洞,请通过 GitHub Issue 或邮件联系仓库所有者。**请勿公开披露未经修复的漏洞。**

---

## 初始安全审计结论(2026-05-07)

仓库初始版本经过完整安全审计,**未发现严重或高风险问题**。

### 审计范围

- 全部 31 个源代码文件(后端 Python ~1700 行 + 前端 HTML/CSS/JS ~1400 行)
- 全部 11 个依赖包(`backend/requirements.txt`)
- GitHub Actions 工作流配置
- Docker 镜像配置

### 审计结论

| 风险类别 | 数量 |
|---|---|
| 🔴 严重 (Critical) | 0 |
| 🟠 高 (High) | 0 |
| 🟡 中 (Medium, demo 简化) | 4 |
| 🔵 低 (最佳实践建议) | 9 |

### 核心安全保证

- ✅ 无硬编码 API Key / 密钥(全部 `sk-xxxxx` 为文档占位符)
- ✅ 无危险调用(`eval / exec / subprocess / pickle / os.system` 等)
- ✅ 无未知域名的网络请求
- ✅ 无数据外泄逻辑(无 webhook 上报、无 telemetry)
- ✅ 无 SQL 注入(全部走 SQLAlchemy ORM 参数化)
- ✅ 无混淆代码或隐藏 URL
- ✅ 依赖供应链干净(全部为 PyPI 主流官方包)

### 出站网络请求清单(完整透明)

| 用途 | URL | 触发条件 |
|---|---|---|
| LLM 对话 | `https://api.deepseek.com/v1/chat/completions` | 仅当配置 `DEEPSEEK_API_KEY` 才发起 |
| 前端框架 | `https://unpkg.com/vue@3.4.21/dist/vue.global.prod.js` | 浏览器加载页面 |
| 后端 API(localhost) | `http://127.0.0.1:8000/*` | 同源调用 |
| WebSocket(localhost) | `ws://127.0.0.1:8000/ws/agent` | 同源调用 |

---

## 生产化加固清单

本仓库设计为**演示用途**,如要部署到生产环境,**必须**完成以下加固:

### 1. 认证与授权

- [ ] 为所有 `/api/v1/*` 端点添加 `Depends(get_current_user)` 校验
- [ ] WebSocket 连接校验真实 JWT(移除默认 `agent-demo-token`)
- [ ] 移除或限制 `/api/v1/demo/reset` 端点(应仅 admin 可调用)

### 2. CORS 与传输安全

- [ ] `CORS_ORIGINS` 改为具体生产域名,禁用 `*`
- [ ] 全站强制 HTTPS / WSS
- [ ] 添加 Rate Limit(尤其 `/translate` 和 `/ai_reply`,会消耗 DeepSeek token)

### 3. 密钥管理

- [ ] `SECRET_KEY` 强制从环境变量读取,启动时如检测到默认值则 fail-fast
- [ ] 所有密钥使用 Secret Manager(如 AWS Secrets Manager、HashiCorp Vault)

### 4. 容器加固

- [ ] Dockerfile 添加非 root 用户:
  ```dockerfile
  RUN useradd -m -u 1000 app
  USER app
  ```
- [ ] 镜像使用 `python:3.11-slim`(已是) + scan 镜像漏洞

### 5. 数据库

- [ ] 用 Alembic 替换 `Base.metadata.create_all`
- [ ] 切换到 PostgreSQL(已支持,见 `.env.example`)
- [ ] 启用连接 SSL/TLS

### 6. 前端

- [ ] Vue CDN 添加 SRI(Subresource Integrity)hash:
  ```html
  <script src="..." integrity="sha384-..." crossorigin="anonymous"></script>
  ```
  或自托管 Vue 静态资源

### 7. 依赖清理

- [ ] 从 `requirements.txt` 移除未使用的 `python-jose` 和 `passlib`,或在使用时升级到最新版本

### 8. 日志与 PII

- [ ] 手机号、姓名等 PII 在日志中做掩码处理(如 `138****5678`)
- [ ] 关闭 `DEBUG=True` 默认值
- [ ] 集中化日志收集(ELK / Loki / Datadog)

### 9. 监控与告警

- [ ] 接入 OpenTelemetry / Jaeger(代码已预留 `JAEGER_ENDPOINT` env)
- [ ] 对 LLM 调用失败率、延迟、token 消耗做监控

---

## 已知限制

- 当前实现为 v3 设计文档的 **MVP 子集**,不包含 SIP/PJSIP 实际语音通话功能
- WebSocket 鉴权使用固定 demo token,**不适合生产**
- SQLite 单文件数据库,不支持高并发

完整设计参见 [`docs/AICC-Lite-v3-Dev-Design.md`](docs/AICC-Lite-v3-Dev-Design.md)。
