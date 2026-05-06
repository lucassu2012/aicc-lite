# AICC-Lite | 新代际智能联络中心

> **轻量级 AI 联络中心参考实现** · 通过 4 大场景演示新代际 AI 联络中心相对传统呼叫中心的差异化能力

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![Vue](https://img.shields.io/badge/Vue-3-brightgreen)](https://vuejs.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

## 🎯 项目概览

**AICC-Lite** 是基于 [AICC-Lite v3 开发设计文档](docs/AICC-Lite-v3-Dev-Design.md) 的轻量化实现，演示 4 大新代际 AI 联络中心能力：

| 能力 | 传统呼叫中心 | AICC-Lite 演示 |
|---|---|---|
| **🔮 Predictive AI** | 客户开口才知道问题 | 来电瞬间并行查诊断,开欢迎语时已有答案 |
| **💰 Behavior-driven LLM** | 机械读优惠券 | 基于用户画像生成有说服力论证 + Tool Call 防算错 |
| **🤝 Seamless Human-AI** | 转人工=丢失上下文 | 转人工=完整对话 + AI 实时建议 + 无缝接管 |
| **🌐 Translation Bridge** | 多语言座席调度 | LLM 实时双向翻译,1 个座席服务多语种 |

## 🚀 在线体验

- **GitHub Pages 在线 Demo**: 部署后访问 `https://<your-username>.github.io/aicc-lite/demo/`
- **本地完整体验**: 见下方 [本地运行](#-本地运行)

## 📸 功能展示

### 4 大场景

```
┌────────────────────────────────────────────────────────────┐
│  📡 场景 1: 主动诊断 (Predictive AI)                       │
│     来电瞬间 → 并行查基站 → AI 主动告知问题 → 自动开工单+补偿 │
├────────────────────────────────────────────────────────────┤
│  💰 场景 2: 套餐挽留 (Behavior-driven LLM)                 │
│     用户要降套餐 → Tool 精确算账 → 推荐忠诚度优惠 → 数字100%准确│
├────────────────────────────────────────────────────────────┤
│  🆘 场景 3: 投诉转人工 (Seamless Human-AI)                  │
│     检测投诉情绪 → 完整摘要+建议话术 → 一键转人工无缝接管    │
├────────────────────────────────────────────────────────────┤
│  🌐 场景 4: 双向翻译 (Translation Bridge)                  │
│     中国客户 ↔ 沙特合作伙伴 → LLM 实时双向翻译 → 商务对话流畅  │
└────────────────────────────────────────────────────────────┘
```

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Vue 3 Frontend                         │
│  • 3-列工作台 (会话列表 / 主对话 / AI 洞察)                  │
│  • CDN 加载,零构建步骤                                      │
│  • 支持 standalone 模式 (LocalStorage,GitHub Pages 部署)   │
└─────────────────┬───────────────────────────────────────────┘
                  │ REST + WebSocket
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                           │
│  • Conversation 状态机 (pending → open → resolved)          │
│  • Polymorphic Channel (Voice / WebWidget / API)            │
│  • AgentBot 协议 (HMAC 签名 + Idempotency)                  │
│  • 4 场景流程 (Flow Manager 路由)                           │
│  • Mock API (确定性数据,演示稳定)                           │
│  • DeepSeek-V3 集成 + Function Calling 防御性设计           │
│  • SQLite (zero config) / PostgreSQL (production-ready)     │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层 | 选型 | 说明 |
|---|---|---|
| 后端 | Python 3.11 + FastAPI 0.115 | 异步 I/O |
| ORM | SQLAlchemy 2.0 + aiosqlite | 异步 ORM |
| LLM | DeepSeek-V3 (可选) + Fallback | 中文 SOTA + 防降级 |
| 前端 | Vue 3 (CDN) + 原生 CSS | 零构建,可静态托管 |
| 实时 | WebSocket | 双向事件推送 |
| 部署 | Docker / Vercel / GitHub Pages | 多种选项 |

> **简化点说明**(相对设计文档): 因 SIP/PJSIP 需要复杂基础设施(GPU、PJSIP 编译、防火墙配置),本实现用浏览器 Web Speech API + 文本输入模拟语音流。完整 SIP 实现请参考 `docs/AICC-Lite-v3-Dev-Design.md` 第 5.5 章。

## 📦 项目结构

```
aicc-lite/
├── backend/                # FastAPI 后端
│   ├── app/
│   │   ├── main.py         # 路由 + 应用入口
│   │   ├── config.py       # 配置管理
│   │   ├── models.py       # ORM + Pydantic 模型
│   │   ├── database.py     # 异步 DB 会话
│   │   ├── services.py     # 业务服务 (会话状态机/消息)
│   │   ├── mocks.py        # 4 场景确定性 Mock 数据
│   │   ├── flows.py        # 场景流程编排
│   │   ├── llm.py          # DeepSeek 集成 + Tool Calling
│   │   ├── seed.py         # 种子数据
│   │   └── websocket_manager.py  # WS 连接池
│   └── requirements.txt
│
├── frontend/               # Vue 3 工作台 (CDN, 零构建)
│   ├── index.html          # 主入口
│   ├── styles.css          # 完整样式
│   ├── app.js              # Vue 应用主逻辑
│   └── mock-backend.js     # 浏览器端 Mock (用于无后端模式)
│
├── demo/                   # GitHub Pages 部署的 standalone 版本
│   └── index.html          # 强制使用 mock-backend
│
├── docs/                   # 设计文档
│   └── AICC-Lite-v3-Dev-Design.md  # 8000+ 行完整设计
│
├── scripts/                # 辅助脚本
├── .github/workflows/      # CI/CD
├── docker-compose.yml      # Docker 编排
├── README.md               # 本文档
└── LICENSE
```

## 🛠️ 本地运行

### 方式 1: 一键启动 (推荐)

```bash
# 1. 安装依赖
cd backend
pip install -r requirements.txt

# 2. 启动后端 (会自动初始化数据库 + 灌种子数据)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 3. 浏览器打开
open http://127.0.0.1:8000
```

第一次启动会:
- 创建 SQLite 数据库 `backend/aicc_lite.db`
- 灌入种子数据(张先生 + 4 场景 Mock 状态)
- 启动后端在 `:8000`,前端通过同端口访问

### 方式 2: 启用 DeepSeek-V3 LLM (真实 AI 对话)

```bash
# 1. 设置 API Key
export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxx"

# 2. 启动
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 验证 LLM 已启用:
curl http://localhost:8000/api/health
# {"llm_enabled": true, ...}
```

启用后:
- AI 回复使用真实 DeepSeek-V3 模型
- 翻译使用 LLM 而非预设
- Tool Calling 真实生效

### 方式 3: 纯前端模式 (无需 Python)

```bash
# 直接用任何静态服务器
cd frontend
python -m http.server 8080
# 或
npx serve .
```

打开 `http://localhost:8080/index.html`,会自动检测后端不可用,启用 LocalStorage Mock 模式。

### 方式 4: Docker

```bash
docker compose up
# 访问 http://localhost:8000
```

## 🌐 在线 Demo (GitHub Pages)

`/demo/` 目录是为 GitHub Pages 准备的纯静态版本,**完全不需要后端**:
- 数据存储在浏览器 LocalStorage
- 4 场景全部可玩(基于预设 Mock 数据)
- 翻译走预设对话表
- AI 回复走 fallback 模式(基于关键字匹配)

启用步骤:
1. Fork 本仓库
2. Settings → Pages → Source: `main` branch, `/` folder
3. 访问 `https://<your-username>.github.io/aicc-lite/demo/`

## 📝 API 文档

启动后访问 `http://localhost:8000/docs` 查看完整 OpenAPI(Swagger UI)文档。

### 核心端点

```
# 场景触发
POST   /api/v1/scenarios/{s1|s2|s3|s4}/trigger?phone=138...

# 会话管理
GET    /api/v1/conversations
POST   /api/v1/conversations
GET    /api/v1/conversations/{id}
POST   /api/v1/conversations/{id}/messages
POST   /api/v1/conversations/{id}/handoff
POST   /api/v1/conversations/{id}/resolve
POST   /api/v1/conversations/{id}/assign
POST   /api/v1/conversations/{id}/ai_reply
POST   /api/v1/conversations/{id}/suggest

# Mock APIs (Demo 数据源)
GET    /mock/profile/lookup?phone=
GET    /mock/network/diagnose?phone=
GET    /mock/profile/usage?phone=
POST   /mock/plan/calculate?plan=&monthly_data_gb=&monthly_voice_min=
GET    /mock/offers?phone=
POST   /mock/offer/apply?phone=&offer_id=
POST   /mock/ticket/create?phone=&issue_type=
POST   /mock/voucher/grant?phone=&data_mb=

# 翻译
POST   /api/v1/translate

# WebSocket
WS     /ws/agent?token=
```

## 🎬 Demo 演示流程

### 场景 1: 主动诊断 (~90 秒)

1. 选择"场景 1: 主动诊断" → 点击"新建呼入"
2. 系统自动:
   - 并行查询基站状态 (BS-008-朝阳区, 负载 87%)
   - 查询客户画像 (张先生, 3年老客户, 399 套餐)
   - 自动开工单 + 发放 10G 流量补偿
3. AI 主动开口:"您好张先生,我注意到您所在区域基站当前负载偏高..."
4. 右侧 AI 助手面板实时展示诊断结果与已执行 Tool

### 场景 2: 套餐挽留 (~120 秒)

1. 选择"场景 2: 套餐挽留" → 新建呼入
2. 输入:"我要把套餐从 399 降到 199"
3. 点击"让 AI 回复"
4. AI 调用 `calculate_actual_cost` Tool,精确计算:
   - 基础套餐 ¥199
   - 流量超额 (68G - 30G) × ¥3 = ¥114
   - 通话超额 (480 - 300) × ¥0.15 = ¥27
   - **实际月费: ¥340**
5. AI 推荐挽留方案: "9 折 359 元 + 家庭宽带提速"

### 场景 3: 投诉转人工 (~60 秒)

1. 选择"场景 3: 投诉转人工" → 新建呼入
2. 输入:"我要投诉!上次的工单根本没解决!"
3. 系统检测投诉关键词,自动转人工:
   - 完整对话历史
   - AI 摘要 (情绪 2/10, 历史工单 WO-20260601-077)
   - AI 建议话术 (4 步标准流程)
4. 点击"接听" → 客服小李无缝接管

### 场景 4: 双向翻译 (~120 秒)

1. 选择"场景 4: 双向翻译" → 新建呼入
2. 点击"播放预设对话(中→英 4 轮)"
3. 系统自动播放完整商务对话:
   - 中文方:"你好 Ahmed,关于上次合同的付款条款..."
   - 英文方 (Ahmed):"Hi, that's fine. The first installment..."
   - 实时双向翻译
4. 也可以手动输入文本测试翻译

## 🔧 开发

### 启动开发模式 (热重载)

```bash
# 后端
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 前端 (无需构建,直接编辑 frontend/*.html|css|js,刷新浏览器)
```

### 重置 Demo 数据

```bash
# 删除 SQLite 数据库
rm backend/aicc_lite.db

# 或调用 API
curl -X POST http://localhost:8000/api/v1/demo/reset
```

### 切换到 PostgreSQL

```bash
# 安装额外依赖
pip install asyncpg

# 设置环境变量
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/aicc_lite"

# 启动
python -m uvicorn app.main:app
```

## 📚 完整设计文档

本仓库 `docs/AICC-Lite-v3-Dev-Design.md` 是完整的 8000+ 行设计文档,包含:

- 完整数据模型 ER 图
- PJSIP Actor 线程模型详细设计
- Pipecat Pipeline 完整集成
- 中文 STT/TTS 选型与参数调优
- DeepSeek-V3 Function Calling 防御性设计
- 7 周分 Phase 实施计划
- Soak Test + Phase 准入门槛
- Demo 完整剧本与故障预案

> **本仓库实现是 v3 文档的 MVP 子集**, 用于快速演示核心理念。完整的 PJSIP/Pipecat/SIP 实现需要专门的环境(GPU、Linux 服务器、防火墙配置),不适合纯 Web 演示。

## 🤝 贡献

欢迎提 Issue 和 PR!

## 📄 License

MIT © 2026 AICC-Lite Contributors

## 🙏 致谢

- 设计参考:[Chatwoot](https://www.chatwoot.com) 的 AgentBot 协议设计
- LLM:[DeepSeek-V3](https://www.deepseek.com)
- 框架:[FastAPI](https://fastapi.tiangolo.com), [Vue.js](https://vuejs.org)
