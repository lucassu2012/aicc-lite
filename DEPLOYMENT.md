# 部署指南

本文档介绍 AICC-Lite 的多种部署方式。

## 🌐 部署选项概览

| 方式 | 用途 | 需要后端 | 真实 LLM | 难度 |
|---|---|---|---|---|
| **GitHub Pages** | 公开演示 | ❌ | ❌ | ⭐ |
| **Vercel/Netlify** | 公开演示 | ❌ | ❌ | ⭐ |
| **本地 Python** | 开发 | ✅ | 可选 | ⭐ |
| **Docker** | 自托管 | ✅ | 可选 | ⭐⭐ |
| **Railway/Render** | 公开 + 真 LLM | ✅ | ✅ | ⭐⭐ |
| **自有服务器** | 生产 | ✅ | ✅ | ⭐⭐⭐ |

---

## 1️⃣ GitHub Pages (推荐用于纯演示)

### 自动化部署 (使用本仓库的 Actions)

1. **Fork 本仓库** 到自己的 GitHub 账号

2. **启用 GitHub Pages**:
   - Settings → Pages
   - Source: `GitHub Actions`

3. **触发部署**:
   - 推送代码到 `main` 分支会自动触发 `.github/workflows/deploy-pages.yml`
   - 或在 Actions 页面手动 `workflow_dispatch`

4. **访问 demo**:
   ```
   https://<your-username>.github.io/aicc-lite/
   ```

### 手动部署 (无 Actions)

如果不想用 Actions:
- Settings → Pages → Source: `Deploy from a branch`
- Branch: `main`, Folder: `/demo`
- 几分钟后访问 `https://<your-username>.github.io/aicc-lite/`

> **限制**: GitHub Pages 部署的版本是 standalone 模式
> - 数据存浏览器 LocalStorage(每用户独立)
> - AI 回复使用 fallback (基于关键字匹配)
> - 翻译使用预设对话表
> - 4 大场景全部可玩

---

## 2️⃣ Vercel (一键部署)

```bash
# 全局安装 vercel CLI
npm i -g vercel

# 在仓库根目录
vercel
```

或点击此处直接部署:
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone)

`vercel.json` 配置 (项目根创建):
```json
{
  "buildCommand": "echo no build needed",
  "outputDirectory": "demo",
  "framework": null
}
```

---

## 3️⃣ 本地开发 (含真实 LLM)

```bash
# 1. 克隆
git clone https://github.com/<your-username>/aicc-lite.git
cd aicc-lite

# 2. 安装后端依赖
cd backend
pip install -r requirements.txt

# 3. (可选) 配置 DeepSeek
cp ../.env.example ../.env
# 编辑 .env 填入 DEEPSEEK_API_KEY

# 4. 启动
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 5. 浏览器访问
open http://127.0.0.1:8000
```

第一次启动会自动:
- 创建 SQLite (`aicc_lite.db`)
- 灌入种子数据 (张先生 + 4 场景)
- 启动 WebSocket 服务

---

## 4️⃣ Docker

```bash
# 单容器
cd backend
docker build -t aicc-lite .
docker run -p 8000:8000 -e DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY aicc-lite

# 或用 docker compose (含数据卷持久化)
docker compose up -d
```

---

## 5️⃣ Railway (一键部署 + 真 LLM)

1. 访问 [railway.app](https://railway.app)
2. New Project → Deploy from GitHub repo → 选择本仓库
3. 配置:
   - Root Directory: `backend`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. 添加环境变量:
   - `DEEPSEEK_API_KEY=sk-xxx`
5. Generate Domain → 访问

---

## 6️⃣ Render

1. New Web Service → 选 GitHub repo
2. Build Command: `cd backend && pip install -r requirements.txt`
3. Start Command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Environment: Add `DEEPSEEK_API_KEY`

---

## 7️⃣ 自有服务器 (Linux + systemd)

```bash
# 1. 部署
cd /opt
git clone https://github.com/<your-username>/aicc-lite.git
cd aicc-lite/backend
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. systemd service
sudo tee /etc/systemd/system/aicc-lite.service <<EOF
[Unit]
Description=AICC-Lite Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/aicc-lite/backend
Environment="DEEPSEEK_API_KEY=sk-xxx"
ExecStart=/opt/aicc-lite/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable aicc-lite
sudo systemctl start aicc-lite

# 3. Nginx 反向代理
sudo tee /etc/nginx/sites-available/aicc-lite <<EOF
server {
    listen 80;
    server_name aicc.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF
sudo ln -s /etc/nginx/sites-available/aicc-lite /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 4. HTTPS (Let's Encrypt)
sudo certbot --nginx -d aicc.yourdomain.com
```

---

## 🔧 故障排查

### CORS 错误

确保 `.env` 中:
```bash
CORS_ORIGINS=https://your-frontend-domain.com,http://localhost:8080
```

### LLM 不工作

```bash
# 检查 API Key
curl http://localhost:8000/api/health
# 应返回 "llm_enabled": true

# 测试 DeepSeek 连接
curl https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"hi"}]}'
```

### 数据库异常

```bash
# 重置数据库
rm backend/aicc_lite.db
python scripts/seed_demo.py

# 或调用 API 清空 conversation
curl -X POST http://localhost:8000/api/v1/demo/reset
```

### WebSocket 连接失败

- 确认前端 `app.js` 中 `API_BASE` 配置正确
- 确认反向代理 (Nginx/Caddy) 已配置 WebSocket 升级
- 检查浏览器控制台

---

## 🎯 推荐部署架构

| 用途 | 推荐方案 |
|---|---|
| 仅展示 demo | GitHub Pages (`/demo` 目录) |
| 需要真实 AI 体验 | Railway / Render (一键) |
| 演示给客户 | 自有 VPS + Nginx + HTTPS |
| 内部使用 | Docker Compose 私网部署 |
