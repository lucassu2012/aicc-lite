# AICC-Lite v3 开发设计文档

> **版本**:v3.0(Discovery 冻结版)
> **日期**:2026-05
> **作者**:Lucas + Claude(2 轮内部红队 + Codex 第 3 轮反方对抗后整合)
> **目标受众**:Claude Code / Codex / 任何能读 Markdown 并执行的 AI 编码工具
> **项目代号**:AICC-Lite
> **GitHub 仓库**:`<待创建>`
> **预计代码量**:6000-8000 行 Python + 1500-2500 行 TypeScript/Vue
> **预计完成时间**:7 周(主线)+ 0.5 周(可选 Phase 6)

---

## 目录

- [0. 文档使用说明](#0-文档使用说明)
- [1. 项目目标与 Demo 剧本](#1-项目目标与-demo-剧本)
- [2. 技术架构总图](#2-技术架构总图)
- [3. 目录结构与代码组织](#3-目录结构与代码组织)
- [4. 核心数据模型](#4-核心数据模型)
- [5. 模块详细设计](#5-模块详细设计)
  - [5.1 channel-layer (Polymorphic Channel)](#51-channel-layerpolymorphic-channel)
  - [5.2 conversation-core (状态机+并发)](#52-conversation-core状态机--并发安全)
  - [5.3 agentbot-protocol (Bot Webhook 协议)](#53-agentbot-protocolbot-webhook-协议)
  - [5.4 voice-worker (Pipecat 集成)](#54-voice-workerpipecat-集成)
  - [5.5 pjsip-transport (核心模块)](#55-pjsip-transport核心模块)
  - [5.6 ws-realtime (WebSocket 事件层)](#56-ws-realtimewebsocket-事件层)
  - [5.7 captain-lite (坐席助手)](#57-captain-lite坐席助手)
  - [5.8 mock-bss (Mock API)](#58-mock-bssmock-api)
  - [5.9 agent-workspace (Vue 工作台)](#59-agent-workspacevue-工作台)
- [6. API 接口规约](#6-api-接口规约)
- [7. SIP 集成规约](#7-sip-集成规约)
- [8. 中文 STT/TTS 集成方案](#8-中文-stttts-集成方案)
- [9. DeepSeek-V3 集成与 Function Calling 防御性设计](#9-deepseek-v3-集成与-function-calling-防御性设计)
- [10. 数据库初始化与种子数据](#10-数据库初始化与种子数据)
- [11. Docker Compose 配置 + GitHub Actions CI/CD](#11-docker-compose-配置--github-actions-cicd)
- [12. Windows 11 + WSL2 + NVIDIA 环境配置](#12-windows-11--wsl2--nvidia-环境配置)
- [13. 测试策略与准入门槛](#13-测试策略与准入门槛)
- [14. Demo 演示剧本(完整脚本+故障预案)](#14-demo-演示剧本完整脚本故障预案)
- [15. 给 Claude Code 的分 Phase 实施任务清单](#15-给-claude-code-的分-phase-实施任务清单)
- [附录 A:工程记忆文档全文](#附录-a工程记忆文档全文)
- [附录 B:PJSIP 黄金参考实现](#附录-bpjsip-黄金参考实现)
- [附录 C:故障排查手册](#附录-c故障排查手册)
- [附录 D:v4 候选清单](#附录-dv4-候选清单)

---

## 0. 文档使用说明

### 0.1 谁来读这份文档

这份文档**不是给人逐字读的**。它是给 AI 编码工具(Claude Code、Codex、Cursor 等)在执行具体编码任务时**作为上下文锚点检索的**。

正确的使用方式:

| 角色 | 阅读策略 |
|---|---|
| 项目所有者(Lucas) | 通读 1-3 章理解全貌,跳读 5/15 章把握模块边界与任务拆分 |
| Claude Code/Codex 第一次启动 | 喂入第 0/1/2/3 章 + 当前 Phase 对应的 5.x 章 + 附录 A 中相关文档 |
| Claude Code/Codex 后续任务 | 每次只喂入"当前任务对应的最小子集",通常是 1-2 个 5.x 模块 + 1 份附录文档 |
| Code Review 时 | 用第 5 章模块边界 + 第 6 章 API 规约 + 第 7 章 SIP 规约对照检查 |

### 0.2 上下文管理策略(防止 AI 编码漂移)

红队 Issue #17 警告过:7 周 + 8000 行的项目,**单个 AI 上下文 hold 不住**。本项目采取以下策略:

1. **工程记忆落到仓库**:不依赖聊天上下文,关键决策全部在 `docs/` 目录(附录 A)
2. **任务粒度限制**:每次给 AI 的任务只允许改**一个模块和一组测试**,绝不允许"重构跨模块"或"顺手把那个也改了"
3. **上下文模板**:每次开任务,固定喂入:
   ```
   [系统提示]:你是一个严格遵守工程纪律的开发者...
   [项目背景]:第 0/1/2 章
   [当前任务]:具体到一个 5.x 子章节
   [关联约束]:附录 A 中相关文档(PJSIP_THREADING.md / STATE_MACHINE.md / 等)
   [验收标准]:第 13 章对应的测试
   [禁止事项]:本任务不允许改的文件清单
   ```
4. **金样本优先**:任何涉及 SIP/Pipecat/PJSIP 的代码,**必须先看 `references/`** 中的参考实现(附录 B),不允许凭空写

### 0.3 分 Phase 推进原则

| Phase | 时长 | 必须完成才能进下一 Phase |
|---|---|---|
| 1 | 1.5w | Core 单元测试 100% pass + WebWidget E2E 跑通 |
| 2 | 2w | S1 端到端跑通 + sngrep 抓包正常 + 1 小时连续运行不崩 |
| 3 | 1.5w | S2 算账正确 + S3 坐席接听音频通顺 |
| 4 | 2w | S4 单 SIP+预录跑通 + 200 次 soak test 通过 + Vue 工作台所有按钮可用 |
| 5 | 0.5w | Demo 录屏 + README 完成 |
| 6(可选) | 0.5w | 不阻塞主线,纯加分项 |

**严禁跳 Phase**。Phase 准入门槛(第 13 章)是硬指标,不达标继续做下一 Phase 等于在沙地上盖楼。

### 0.4 对话/Sprint 节奏

| 节奏 | 频次 |
|---|---|
| 任务级(给 AI 一个任务) | 每次 30 分钟-2 小时,每天 4-8 个任务 |
| 模块级(完成一个 5.x 模块) | 每 2-5 天 |
| Phase 级(进入下一 Phase) | 每 1.5-2 周 |
| Demo 验证(完整跑一次 4 场景) | 每 Phase 结束 1 次 |

### 0.5 文档组织约定

- **"必须"/"严禁"/"绝不"**:这是硬规则,违反会导致功能失效或重大风险
- **"应该"/"推荐"**:默认行为,有充分理由可偏离
- **"可以"/"考虑"**:建议性,自由裁量
- 代码块标 `python`/`yaml`/`bash` 等语言,无标记的代码块是伪代码或示例

---

## 1. 项目目标与 Demo 剧本

### 1.1 一句话定义

**AICC-Lite 是一套全 Python 实现的轻量化智能联络中心参考实现,通过 4 个故事化场景演示新代际 AI 联络中心相对传统呼叫中心的 4 大差异化能力。**

### 1.2 4 大差异化能力

| 能力 | 传统呼叫中心 | AICC-Lite 演示 |
|---|---|---|
| **Predictive AI** | 客户开口才知道问题 | 来电瞬间并行查诊断,开欢迎语时已有答案 |
| **Behavior-driven LLM** | 机械读优惠券 | 基于用户画像生成有说服力论证 + Tool Call 防算错 |
| **Seamless Human-AI Collaboration** | 转人工=丢失上下文 | 转人工=完整对话历史 + AI 实时建议 + 音频无缝接管 |
| **Translation Bridge** | 多语言座席调度 | LLM 实时双向翻译,1 个座席服务多语种 |

### 1.3 完整 Demo 剧本(5-6 分钟一气呵成版)

#### 演示前提条件

| 项 | 配置 |
|---|---|
| 演示者电脑 | Windows 11 + i7 + Quadro P1000 4GB + 32G RAM |
| 演示者手机 | 装好 Linphone APP + 同 WiFi |
| 网络 | 同 WiFi 局域网,关掉 ZeroTier(只在备用时启用) |
| Demo 用户 | 张先生,138xxxxxxxx(种子数据已预埋) |
| 演示前 30 分钟 | 跑 `python scripts/preflight.py` 暖机 + 完整跑一次彩排 |

#### 时序剧本

```
═══════════════════════════════════════════════════════════
T+0:00 启动准备
─────────────────────────────────────────────────────────
docker compose up -d
浏览器打开 http://localhost:8080,坐席"客服小李"登录
打开桌面 Linphone(已预配置 sip:1001@127.0.0.1)

═══════════════════════════════════════════════════════════
场景 1:网速主动诊断 (~90 秒) ★ Predictive AI
─────────────────────────────────────────────────────────
T+0:30  Linphone 拨号:138xxxxxxxx
T+0:32  PJSIP server 接收 INVITE,200 OK,开始 RTP
T+0:32  ⚡ Voice Worker 启动 PipelineTask
        并行触发(背景):
        - GET /mock/network/diagnose?phone=138xxxxxxxx&scenario=s1
          → 返回:基站 BS-008 当前负载 87%(确定性 mock)
        - GET /mock/profile/lookup?phone=138xxxxxxxx
          → 返回:张先生,3 年老客户,套餐 399 元
        诊断结果注入下次 LLM 调用的 system prompt
T+0:33  Bot 第一句(固定模板,基于号码即查的姓名):
        "您好张先生,感谢致电"
        (TTS 流式播放约 1.5s)
T+0:35  Bot 接续(此时诊断结果已到达):
        "我注意到您所在区域基站当前负载偏高,
         您是不是觉得网速有点慢?"
        (DeepSeek-V3 流式生成,首字 ~400ms,TTS 流式 ~3s)
T+0:42  客户(中文,标准普通话,慢速):
        "对啊,你怎么知道?"
        (faster-whisper STT,~600ms 出 final)
T+0:45  Bot:
        "我已经为您提交基站优化工单,工单号 WO-20260605-001,
         预计 30 分钟内恢复。
         同时为您发放 10G 免费流量包作为补偿,
         请查收短信确认。"
        Tool Call: create_ticket(phone, issue_type='slow_network')
        Tool Call: grant_data_voucher(phone, 10240)
T+1:00  ⚡ 坐席工作台同步显示:
        - 实时通话音频(WebSocket+PCM)
        - 转录流(中文字幕)
        - AI 诊断卡片(基站状态、工单号)
        - 客户情绪评分(由 LLM 给出,0-10)
T+1:30  客户:"好的,谢谢"
T+1:32  Bot:"祝您生活愉快,再见"
T+1:34  客户挂断(BYE)→ Conversation 标记 resolved

═══════════════════════════════════════════════════════════
场景 2:套餐挽留 (~120 秒) ★ Behavior-driven LLM
─────────────────────────────────────────────────────────
T+2:00  Linphone 再次拨号:138xxxxxxxx
T+2:02  Voice Worker 启动新 PipelineTask
        Mock API 在 pre_action 阶段拉取:
        - GET /mock/profile/usage?phone=138&scenario=s2
          → 月均流量 68G,通话 480 分钟,4 设备共享网络
T+2:03  Bot:"您好张先生,有什么可以帮您?"
T+2:08  客户(中文):"我要把套餐从 399 降到 199"
T+2:11  Bot 进入 s2_retention Flow,触发 LLM 推理:
        Prompt 注入 usage 数据,Tool 列表包含:
        - calculate_actual_cost(plan, usage)
        - apply_retention_offer(phone, offer_id)
        LLM 决策调用 calculate_actual_cost('199_plan', usage_data)
        Tool 返回:
        {
          "base_cost": 199,
          "voice_overage_min": 480-300, "voice_overage_cost": 27,
          "data_overage_gb": 68-30, "data_overage_cost": 114,
          "total": 340,
          "vs_current": "+¥-59 实际更高"
        }
T+2:13  Bot(流式):
        "张先生,我帮您算一下:
         您每月平均流量 68G,通话 480 分钟,
         如果降到 199 套餐,流量上限只有 30G,
         超出按 ¥3/GB 计费,大约 ¥114;
         通话超出按 ¥0.15/分钟,大约 ¥27;
         加上套餐费 ¥199,实际花费会到 ¥340 左右。"
        (注意:此处金额由 calculate_actual_cost 渲染模板,
         LLM 只做话术包装,数字 100% 正确)
T+2:30  客户(犹豫):"那有什么办法吗?"
T+2:33  Bot:"作为您 3 年老客户,我可以为您申请专属优惠:
         保留 399 套餐核心权益,享受 9 折 ¥359/月,
         同时赠送家庭宽带提速到 500M,持续 6 个月。
         您看可以吗?"
        Tool Call: apply_retention_offer(phone, 'loyal_3yr_v1')
T+2:50  客户:"好的,就这个吧"
T+2:52  Bot:"好的,优惠已为您激活,生效时间下个账单周期。
         祝您生活愉快,再见"
T+2:54  ⚡ 坐席工作台显示:
        - 用户画像卡片(画像数据)
        - 优惠券激活记录
        - 挽留成功率 +1
T+2:55  客户挂断

═══════════════════════════════════════════════════════════
场景 3:转人工(投诉)(~60 秒) ★ Seamless Human-AI
─────────────────────────────────────────────────────────
T+3:30  Linphone 拨号:138xxxxxxxx
T+3:32  Bot:"您好张先生,有什么可以帮您?"
T+3:36  客户(中文,语气激动):
        "我要投诉!上次的工单根本没解决!"
T+3:39  Bot 进入 s3_handoff Flow:
        - LLM 识别投诉意图(prompt 已配置)
        - 决策:立即转人工
        - Tool Call: bot_handoff(reason='complaint',
                                 sentiment_score=2)
        Conversation 状态:pending → open
        Assignee:NULL → "客服小李"
T+3:40  ⚡ 坐席工作台:
        - 叮咚提示音
        - 会话面板高亮"新分配"
        - "客服小李"看到完整历史:
          * 之前 2 次通话转录全文
          * 客户画像
          * AI 摘要:"客户因之前工单未解决而投诉,
            情绪激动,建议优先处理"
          * AI 建议话术:"先共情,致歉,确认问题,提供升级方案"
T+3:42  "客服小李"点"接听"
        浏览器 WebSocket 连 AICC Core
        AICC Core 通知 PJSIP server:
        "原 Pipecat pipeline 旁路,音频桥接到 WebSocket"
        浏览器开始播放客户 PCM 音频(Web Audio API)
        浏览器麦克风采集 PCM 回传
T+3:44  小李:"张先生您好,我是客服小李,
         非常抱歉之前的问题没有解决到位,
         我现在专门为您处理……"
T+3:50  ⚡ 演示打断:
        小李正在说话,客户插话:"我等了一周了!"
        VAD 检测到客户说话 → InterruptionFrame 上溯
        → 浏览器播放队列立即清空(Web Audio cancel)
        → 小李在浏览器看到"客户在说话"提示
        → 小李停止说话,听完客户表达
T+4:00  小李用工作台一键创建升级工单
        客户挂断
        Conversation 状态:open → resolved

═══════════════════════════════════════════════════════════
场景 4:双向翻译 (~120 秒) ★ Translation Bridge
─────────────────────────────────────────────────────────
T+4:30  政企客户(仍是张先生)拨号:138xxxxxxxx
T+4:32  Bot:"您好张先生,有什么可以帮您?"
T+4:35  客户:"我想呼叫我们沙特的合作伙伴 Ahmed,
         请帮我接通,我需要英语翻译"
T+4:38  Bot:"好的,正在为您接通 Ahmed,
         接通后通话将自动双向翻译,请稍候"
        Voice Worker 进入 s4_translation Flow:
        - 启动 TTSReplayService,加载 Ahmed 预录英文音频
        - 切换到 TranslationPipeline
T+4:42  [模拟] Ahmed "接听"(实际是预录音频准备就绪)
        Bot:"已为您接通"
T+4:45  客户(中文):"你好 Ahmed,关于上次合同的付款条款,
         我们这边的财务说需要分两期支付。"
        STT(中文,~600ms)→
        DeepSeek-V3 翻译(~500ms)→
        TTS 英文播放给 Ahmed(预录回放)
        Ahmed 端听到:"Hi Ahmed, regarding the payment terms
         from last contract, our finance department says
         we need to pay in two installments."
T+5:05  Ahmed(预录英文音频回放):
         "Hi, that's fine. The first installment can be
          made next Monday, and the second installment
          within 30 days."
        STT 英文识别 → DeepSeek 翻译 → TTS 中文播放给客户
T+5:25  客户听到:"你好,这个安排可以。第一期款项可以下周一支付,
         第二期款项 30 天内完成。"
T+5:35  ⚡ 坐席工作台:
        - 双语转录对照(中文 | 英文 同屏)
        - 翻译质量评分(LLM 给出,~9.5/10)
        - 实时延迟监控:STT 600ms / Translate 500ms / TTS 800ms
T+5:50  客户:"谢谢 Ahmed,稍后给您发邮件确认细节"
T+5:55  Ahmed(预录):"You're welcome, looking forward to it."
T+6:00  双方挂断,Conversation 标记 resolved

═══════════════════════════════════════════════════════════
彩蛋:跨渠道身份归一(贯穿 demo,演示后展示)
─────────────────────────────────────────────────────────
打开浏览器 Web Widget(http://localhost:8080/widget?token=demo)
作为同一个张先生(用 phone 关联到 Contact)发送文字消息
"我刚才打电话办的优惠激活了吗?"
坐席工作台合并显示:
  - 4 通历史电话(含完整转录)
  - Web Widget 当前文字会话
  - 同一个 Contact ID,同一个客户旅程
```

#### Demo 故障预案

| 故障 | 备用方案 |
|---|---|
| Linphone 突然不通 | 切换到第二个 Linphone 实例(预先打开备用) |
| DeepSeek API 响应慢 >8s | 自动降级到本地 Qwen2.5-1.5B(质量打折但能续) |
| STT 识别错误关键词 | Bot 主动复述确认,演示者刻意发音清晰 |
| WiFi 抖动断连 | 切换有线网线 |
| GPU 资源紧张 | 重启 voice-worker 容器(< 30 秒) |
| 完全跑不通 | 播放预录的 demo 视频 |

---

## 2. 技术架构总图

### 2.1 分层架构(C4 Container 视图)

```
┌─────────────────────────────────────────────────────────────────┐
│                         客户接入层                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ 桌面 Linphone    │  │ 手机 Linphone    │  │ 浏览器(Web)    │ │
│  │ (sip:1001)      │  │ APP(同 WiFi)   │  │  Widget        │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘ │
│           │ UDP/SIP/PCMA/RTP             │           │ HTTPS/WSS │
└───────────┼─────────────────────────────┼───────────┼──────────┘
            │                             │           │
            ▼                             ▼           ▼
┌─────────────────────────────────────────────────────────────────┐
│              PJSIP Server(Docker 容器)                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  PJSIP Endpoint(单例,actor 线程模式)                      │ │
│  │  ├── SIP Listener(UDP:5060)                              │ │
│  │  ├── RTP Pool(UDP:10000-10100)                           │ │
│  │  ├── 只支持 happy path SIP method                         │ │
│  │  ├── Codec: PCMA only                                    │ │
│  │  └── 命令队列(asyncio ↔ PJSIP 线程)                     │ │
│  └────────────────────┬───────────────────────────────────────┘ │
└──────────────────────┼─────────────────────────────────────────┘
                       │ PCM stream(in-process Python queue)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│           Voice Worker(per-call PipelineTask)                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  PJSIPTransport(自写,~600 行)                            │ │
│  │  ↓                                                        │ │
│  │  Silero VAD on P1000 GPU                                 │ │
│  │  ↓                                                        │ │
│  │  faster-whisper small int8 on P1000 GPU                  │ │
│  │  ↓                                                        │ │
│  │  ContextAggregator(user)                                  │ │
│  │  ↓                                                        │ │
│  │  Pipecat Flow Manager                                    │ │
│  │  ├── s1_diagnosis.py                                     │ │
│  │  ├── s2_retention.py                                     │ │
│  │  ├── s3_handoff.py                                       │ │
│  │  └── s4_translation.py                                   │ │
│  │  ↓                                                        │ │
│  │  DeepSeek-V3 API LLM Service                             │ │
│  │  + Tool Call(calculate_cost / create_ticket / ...)       │ │
│  │  ↓                                                        │ │
│  │  ContextAggregator(assistant)                             │ │
│  │  ↓                                                        │ │
│  │  Piper TTS on CPU                                        │ │
│  │  (or TTSReplayService on demo day)                       │ │
│  │  ↓                                                        │ │
│  │  PJSIPTransport.output → RTP                             │ │
│  │                                                          │ │
│  │  + ChatwootBotEventProcessor                             │ │
│  │    (转录/回复 POST 到 AICC Core)                          │ │
│  └────────────────────────┬───────────────────────────────────┘ │
└─────────────────────────┼─────────────────────────────────────┘
                          │ HTTP(HMAC 签名)
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                AICC Core(FastAPI 单体)                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Polymorphic Channel Layer                                 │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ Conversation Core                                         │ │
│  │  ├── 状态机(pending → open → resolved/snoozed)          │ │
│  │  ├── DB 事务 + advisory lock + version CAS              │ │
│  │  └── Idempotency Key 去重                                │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ AgentBot Webhook + WebSocket 事件层 + Captain-Lite       │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ Mock APIs(基于 phone+scenario_id 确定性)                 │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────┬──────────────────────────────────┬────────────────────┘
         │ HTTPS/WSS                        │ Internal
         ▼                                  ▼
┌──────────────────────┐         ┌──────────────────────────┐
│ Vue 3 坐席工作台      │         │ PostgreSQL + Redis       │
│  ├── 登录             │         │  ├── 关系数据            │
│  ├── 会话列表(WS)   │         │  ├── advisory lock       │
│  ├── 转录流面板       │         │  ├── pub/sub             │
│  ├── 接听按钮         │         │  └── idempotency cache   │
│  │   (WebSocket+PCM) │         └──────────────────────────┘
│  └── AI 建议卡片      │
└──────────────────────┘

附属服务:
- sngrep 容器(SIP 信令抓包,调试用)
- DeepSeek API(外部,主对话+翻译+Captain)
```

### 2.2 关键数据流(序列图,文字版)

#### 数据流 1:S1 网速诊断完整链路

```
Linphone           PJSIP        VoiceWorker      AICCCore     DeepSeek
  │                  │               │              │           │
  │── INVITE ────────>│               │              │           │
  │                  │── new_call ───>│              │           │
  │<──── 200 OK ─────│               │              │           │
  │── ACK ───────────>│               │              │           │
  │═══ RTP/PCMA ════>│═══ PCM ══════>│              │           │
  │                  │               │── parallel:  │           │
  │                  │               │   GET /mock/network/diagnose
  │                  │               │── parallel:  │           │
  │                  │               │   GET /mock/profile/lookup
  │                  │               │              │           │
  │                  │               │── 启动 LLM ─────────────>│
  │                  │               │   sys_prompt:含诊断    │
  │                  │               │<──── 流式 token ────────│
  │                  │               │── TTS(Piper)│           │
  │                  │<══ PCM ═══════│              │           │
  │<══ RTP/PCMA ═════│               │              │           │
  │                  │               │── POST /webhook (转录)│  │
  │                  │               │              │── WS 推送 │
  │                  │               │              │   to 坐席│
```

#### 数据流 2:S3 转人工音频接管

```
客户        PJSIP    VoiceWorker    AICCCore    AgentBrowser
 │            │           │             │            │
 │═══ RTP ═══>│══ PCM ═══>│             │            │
 │            │           │── handoff API──>         │
 │            │           │             │── WS push  │
 │            │           │             │ "incoming" │
 │            │           │             │            │
 │            │           │             │<── accept ─│
 │            │           │             │            │
 │            │           │  ┌──────────│── PJSIP    │
 │            │           │  │ "bypass  │   bridge   │
 │            │           │  │  Pipecat │   audio to │
 │            │           │  │  to WS"  │   WS:xxxx" │
 │            │           │<─┘          │            │
 │            │           │             │            │
 │═══ RTP ═══>│══ PCM ═══════ direct ═══════════════>│ playback
 │<══ RTP ═══│<══ PCM ═══════ direct ═══════════════<│ mic capture
 │            │           │             │            │
```

### 2.3 进程拓扑

| 进程 | 容器 | 端口 | 资源 |
|---|---|---|---|
| AICC Core | `aicc-core` | :8000 | CPU, ~500MB RAM |
| Voice Worker | `voice-worker` | :9000(内部) | CPU + GPU(P1000),~2GB RAM + 2GB VRAM |
| PJSIP Server | `pjsip-server` | :5060/udp, :10000-10100/udp | CPU,~300MB RAM |
| Vue Workspace(开发) | `frontend` | :8080 | CPU,~200MB RAM |
| PostgreSQL | `postgres` | :5432 | CPU,~500MB RAM |
| Redis | `redis` | :6379 | CPU,~100MB RAM |
| sngrep(调试) | `sngrep` | host network | CPU,~50MB RAM |

**总资源占用**:~3.7GB RAM + 2GB VRAM(P1000 4GB,余 2GB 缓冲),CPU 6 核够用,32GB 内存非常宽裕。

---

## 3. 目录结构与代码组织

### 3.1 仓库根目录

```
aicc-lite/
├── .github/
│   └── workflows/
│       ├── build-pjsip.yml        # PJSIP 镜像构建 → GHCR
│       ├── ci-core.yml            # AICC Core 单元测试
│       ├── ci-voice-worker.yml    # Voice Worker 单元测试
│       └── lint.yml               # ruff + mypy + eslint
│
├── docker-compose.yml             # 生产配置(GHCR pull)
├── docker-compose.dev.yml         # 开发配置(本地构建)
├── .env.example
├── .gitignore                     # 过滤 .env、模型、录音、PCAP
├── README.md                      # 项目入口,含 demo 录屏链接
├── LICENSE                        # MIT
│
├── docs/                          # 工程记忆文档(附录 A 全部内容)
│   ├── ADR/                       # 架构决策记录
│   │   ├── 0001-pjsip-actor-thread-model.md
│   │   ├── 0002-deepseek-as-sole-llm.md
│   │   ├── 0003-pcma-only-codec.md
│   │   ├── 0004-websocket-pcm-vs-jssip.md
│   │   ├── 0005-mock-api-determinism.md
│   │   ├── 0006-conversation-state-machine.md
│   │   └── 0007-s4-prerecorded-translation.md
│   ├── STATE_MACHINE.md
│   ├── PJSIP_THREADING.md
│   ├── SIP_SCENARIOS.md
│   ├── MOCK_API_CONTRACT.md
│   ├── AI_TASK_GUIDELINES.md
│   ├── PHASE_GATES.md             # 各 Phase 准入门槛
│   └── DEMO_SCRIPT.md             # 演示完整脚本
│
├── references/                    # 给 Claude Code 的金样本
│   ├── pjsip_pygui_reference/     # 从 pjproject fork
│   ├── pipecat_custom_transport_minimal.py
│   ├── sipp_scenarios/
│   │   ├── happy_path_inbound.xml
│   │   ├── invalid_method.xml
│   │   └── timeout_recovery.xml
│   └── golden_pcaps/              # sngrep 抓包样本
│       ├── 01_normal_call.pcap
│       ├── 02_handoff.pcap
│       └── 03_translation.pcap
│
├── core/                          # AICC Core(FastAPI 单体)
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   ├── src/
│   │   └── aicc_core/
│   │       ├── __init__.py
│   │       ├── main.py            # FastAPI app
│   │       ├── config.py          # Pydantic Settings
│   │       ├── db/
│   │       │   ├── base.py
│   │       │   ├── session.py
│   │       │   └── models.py      # SQLAlchemy ORM
│   │       ├── channels/
│   │       │   ├── base.py
│   │       │   ├── web_widget.py
│   │       │   ├── voice.py
│   │       │   └── api.py
│   │       ├── conversations/
│   │       │   ├── service.py     # 状态机 + 并发控制
│   │       │   ├── state_machine.py
│   │       │   └── api.py         # REST endpoints
│   │       ├── messages/
│   │       │   ├── service.py
│   │       │   └── api.py
│   │       ├── contacts/
│   │       │   └── service.py
│   │       ├── agentbots/
│   │       │   ├── webhook_dispatcher.py  # 出站 webhook
│   │       │   ├── webhook_receiver.py    # 入站 webhook(bot 回写)
│   │       │   ├── signing.py             # HMAC
│   │       │   └── idempotency.py
│   │       ├── ws/
│   │       │   ├── manager.py     # WebSocket 连接管理
│   │       │   ├── events.py      # 事件类型注册
│   │       │   ├── broadcaster.py # Redis pub/sub
│   │       │   └── api.py         # WS endpoint
│   │       ├── captain_lite/
│   │       │   ├── service.py     # AI 建议主逻辑
│   │       │   ├── rag.py         # Mock RAG
│   │       │   └── deepseek_client.py
│   │       └── mocks/
│   │           ├── network.py
│   │           ├── profile.py
│   │           ├── plan.py
│   │           ├── ticket.py
│   │           └── voucher.py
│   └── tests/
│       ├── unit/
│       └── integration/
│
├── voice_worker/                  # Pipecat Voice Worker
│   ├── pyproject.toml
│   ├── src/
│   │   └── voice_worker/
│   │       ├── __init__.py
│   │       ├── main.py            # FastAPI WS endpoint
│   │       ├── config.py
│   │       ├── transports/
│   │       │   ├── pjsip_transport.py  # ★ 核心模块,~600 行
│   │       │   ├── pjsip_actor.py      # ★ actor 线程模型,~250 行
│   │       │   └── resampler.py        # 8k↔16k
│   │       ├── services/
│   │       │   ├── faster_whisper_stt.py
│   │       │   ├── piper_tts.py
│   │       │   ├── tts_replay.py       # demo 日预录回放
│   │       │   └── deepseek_llm.py
│   │       ├── flows/
│   │       │   ├── s1_diagnosis.py
│   │       │   ├── s2_retention.py
│   │       │   ├── s3_handoff.py
│   │       │   ├── s4_translation.py
│   │       │   └── shared.py           # 共用 nodes
│   │       ├── tools/
│   │       │   ├── calculate_cost.py
│   │       │   ├── create_ticket.py
│   │       │   ├── grant_voucher.py
│   │       │   ├── apply_offer.py
│   │       │   └── handoff.py
│   │       ├── processors/
│   │       │   ├── chatwoot_bot_event.py
│   │       │   ├── interruption_logger.py
│   │       │   └── latency_tracer.py
│   │       └── pipelines/
│   │           ├── inbound_zh.py        # S1/S2/S3
│   │           └── translation_bridge.py # S4
│   └── tests/
│
├── pjsip_server/                  # PJSIP server 容器(Debian + PJSIP 2.13)
│   ├── Dockerfile                 # multi-stage build
│   ├── pjsip-build.sh             # 编译脚本
│   ├── src/
│   │   ├── server.py              # PJSIP 监听 + 命令队列
│   │   └── audio_bridge.py        # PCM 与 Voice Worker 通信
│   └── README.md
│
├── frontend/                      # Vue 3 工作台
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router.ts
│   │   ├── stores/
│   │   │   ├── auth.ts
│   │   │   ├── conversations.ts
│   │   │   └── ws.ts
│   │   ├── views/
│   │   │   ├── Login.vue
│   │   │   ├── Workspace.vue
│   │   │   └── ConversationDetail.vue
│   │   ├── components/
│   │   │   ├── ConversationList.vue
│   │   │   ├── TranscriptStream.vue
│   │   │   ├── AISuggestionCard.vue
│   │   │   ├── CustomerProfile.vue
│   │   │   ├── AnswerButton.vue
│   │   │   └── AudioPlayer.vue   # WebSocket+PCM 桥
│   │   ├── lib/
│   │   │   ├── ws-client.ts
│   │   │   └── audio-bridge.ts   # Web Audio API
│   │   └── styles/
│   └── tests/
│
├── third_party_simulator/         # S4 Ahmed 预录音频回放
│   ├── README.md
│   ├── audio/
│   │   ├── ahmed_greeting.wav
│   │   ├── ahmed_payment_response.wav
│   │   └── ahmed_farewell.wav
│   └── playback_script.json       # 时序控制
│
└── scripts/
    ├── seed_data.py               # 张先生 138xxxxxxxx 完整种子
    ├── reset_demo.py              # 一键重置
    ├── preflight.py               # demo 前暖机检查
    ├── soak_test.py               # 200 次呼入测试
    ├── twilio_setup.md            # Phase 6 可选启用
    ├── linphone_provisioning.lpconfig  # 预配置文件
    └── benchmark_latency.py       # 端到端延迟测试
```

### 3.2 命名约定

| 类型 | 约定 | 示例 |
|---|---|---|
| Python 模块 | snake_case | `pjsip_transport.py` |
| Python 类 | PascalCase | `PJSIPTransport`, `ConversationService` |
| Python 函数 | snake_case | `calculate_cost`, `bot_handoff` |
| Vue 组件 | PascalCase.vue | `ConversationList.vue` |
| TS 函数 | camelCase | `connectWebSocket` |
| 数据库表 | snake_case 复数 | `conversations`, `agent_bots` |
| 数据库字段 | snake_case | `created_at`, `phone_number` |
| 环境变量 | UPPER_SNAKE | `DEEPSEEK_API_KEY` |
| Docker 服务名 | kebab-case | `aicc-core`, `voice-worker` |
| Git branch | kebab-case + 类型前缀 | `feat/pjsip-actor`, `fix/state-race` |
| 文档文件 | UPPER_SNAKE.md | `STATE_MACHINE.md` |

### 3.3 模块依赖规则(强制)

```
Frontend  ──>  AICC Core API
VoiceWorker  ──>  AICC Core HTTP
VoiceWorker  ──>  PJSIPServer (gRPC/Pipe)
PJSIPServer  -.no.->  Core
PJSIPServer  -.no.->  Frontend
Core  ──>  Postgres / Redis
VoiceWorker  ──>  DeepSeek API
Core  ──>  DeepSeek API
```

**严禁**:
- PJSIP Server 直接调 Core API(必须经过 Voice Worker)
- 任何模块直接读取另一模块的数据库表(必须经过 API)
- Voice Worker 直接读 Postgres(必须经过 Core HTTP)
- Frontend 直接调 Voice Worker(必须经过 Core 中转)

理由:这是 microservice 边界,违反就失去了"清晰职责划分"的价值,Claude Code 在多模块 refactor 时会越界。

---

## 4. 核心数据模型

### 4.1 数据模型 ER 图(文字版)

```
Account (1) ─── (N) User                  (坐席)
Account (1) ─── (N) Contact               (客户)
Account (1) ─── (N) Inbox                 (渠道实例)
Account (1) ─── (N) AgentBot              (机器人)

Inbox (1) ─── (1) Channel::*              (多态)
Inbox (N) ─── (N) AgentBot                (绑定关系)
Inbox (1) ─── (N) Conversation

Contact (1) ─── (N) ContactInbox          (跨渠道身份)
ContactInbox (N) ─── (1) Inbox

Conversation (N) ─── (1) Contact
Conversation (N) ─── (1) Inbox
Conversation (N) ─── (0..1) User          (assignee)
Conversation (1) ─── (N) Message

Message (N) ─── (1) Conversation
Message (N) ─── (1) sender                (polymorphic: User/Contact/AgentBot)
```

### 4.2 SQLAlchemy ORM 完整定义

```python
# core/src/aicc_core/db/models.py
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, JSON, Boolean,
    Index, UniqueConstraint, CheckConstraint, BigInteger, Text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


# ============================================================
# Enums
# ============================================================

class ConversationStatus(str, Enum):
    PENDING = "pending"      # bot 处理中
    OPEN = "open"            # 人工或活跃
    RESOLVED = "resolved"
    SNOOZED = "snoozed"


class MessageSenderType(str, Enum):
    USER = "User"
    CONTACT = "Contact"
    AGENT_BOT = "AgentBot"
    CAPTAIN = "Captain"


class ChannelType(str, Enum):
    WEB_WIDGET = "Channel::WebWidget"
    VOICE = "Channel::Voice"
    API = "Channel::Api"


# ============================================================
# Account / User
# ============================================================

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class User(Base):
    """坐席/管理员"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(100))
    role = Column(String(20), default="agent")  # admin / agent
    pubsub_token = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================
# Contact / ContactInbox(跨渠道身份核心)
# ============================================================

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    name = Column(String(100))
    phone = Column(String(20), index=True)        # 跨渠道关联键
    email = Column(String(255))
    identifier = Column(String(255))               # 自定义业务 ID
    custom_attributes = Column(JSONB, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    contact_inboxes = relationship("ContactInbox", back_populates="contact")
    conversations = relationship("Conversation", back_populates="contact")


class ContactInbox(Base):
    """同一 Contact 在不同 Inbox 的渠道身份"""
    __tablename__ = "contact_inboxes"
    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    inbox_id = Column(Integer, ForeignKey("inboxes.id"), nullable=False, index=True)
    source_id = Column(String(255), nullable=False)  # phone / cookie / openid
    pubsub_token = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("inbox_id", "source_id", name="uq_inbox_source"),
    )

    contact = relationship("Contact", back_populates="contact_inboxes")
    inbox = relationship("Inbox", back_populates="contact_inboxes")


# ============================================================
# Inbox / Channel(Polymorphic)
# ============================================================

class Inbox(Base):
    __tablename__ = "inboxes"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    channel_type = Column(String(50), nullable=False)  # 多态判别字段
    channel_id = Column(Integer, nullable=False)        # 多态外键
    enable_auto_assignment = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_inbox_channel", "channel_type", "channel_id"),
    )

    contact_inboxes = relationship("ContactInbox", back_populates="inbox")
    conversations = relationship("Conversation", back_populates="inbox")
    agent_bot_inboxes = relationship("AgentBotInbox", back_populates="inbox")


class ChannelWebWidget(Base):
    __tablename__ = "channel_web_widgets"
    id = Column(Integer, primary_key=True)
    website_token = Column(String(64), unique=True, nullable=False)
    widget_color = Column(String(7), default="#1f93ff")
    welcome_title = Column(String(255))
    welcome_tagline = Column(Text)


class ChannelVoice(Base):
    __tablename__ = "channel_voices"
    id = Column(Integer, primary_key=True)
    sip_endpoint = Column(String(255), nullable=False)  # 内部 PJSIP server
    twilio_number = Column(String(20))                   # Phase 6 可选
    feature_flags = Column(JSONB, default=dict)


class ChannelApi(Base):
    __tablename__ = "channel_apis"
    id = Column(Integer, primary_key=True)
    api_token = Column(String(64), unique=True, nullable=False)
    hmac_mandatory = Column(Boolean, default=True)


# ============================================================
# Conversation / Message(并发安全核心)
# ============================================================

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    inbox_id = Column(Integer, ForeignKey("inboxes.id"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    contact_inbox_id = Column(Integer, ForeignKey("contact_inboxes.id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="pending", nullable=False, index=True)
    version = Column(BigInteger, default=1, nullable=False)  # 乐观锁 CAS
    additional_attributes = Column(JSONB, default=dict)
    custom_attributes = Column(JSONB, default=dict)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 演示场景隔离
    scenario_id = Column(String(20), nullable=True, index=True)  # s1/s2/s3/s4

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'open', 'resolved', 'snoozed')",
            name="ck_conversation_status"
        ),
        Index("ix_conv_acct_status", "account_id", "status"),
    )

    contact = relationship("Contact", back_populates="conversations")
    inbox = relationship("Inbox", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation",
                            order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"),
                             nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    inbox_id = Column(Integer, ForeignKey("inboxes.id"), nullable=False)
    content = Column(Text)
    message_type = Column(Integer, default=0)  # 0=incoming, 1=outgoing, 2=activity
    sender_type = Column(String(20), nullable=False)
    sender_id = Column(Integer, nullable=False)
    content_attributes = Column(JSONB, default=dict)
    # content_attributes 例:
    # {
    #   "audio_url": "...",
    #   "stt_confidence": 0.92,
    #   "transcript_id": "uuid",
    #   "context_id": "ctx-...",
    #   "tts_audio_url": "...",
    #   "latency_breakdown": {...}
    # }
    created_at = Column(DateTime, server_default=func.now(), index=True)

    conversation = relationship("Conversation", back_populates="messages")


# ============================================================
# AgentBot
# ============================================================

class AgentBot(Base):
    __tablename__ = "agent_bots"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    outgoing_url = Column(String(500), nullable=False)
    access_token = Column(String(64), unique=True, nullable=False)
    signing_secret = Column(String(64), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class AgentBotInbox(Base):
    __tablename__ = "agent_bot_inboxes"
    id = Column(Integer, primary_key=True)
    agent_bot_id = Column(Integer, ForeignKey("agent_bots.id"), nullable=False)
    inbox_id = Column(Integer, ForeignKey("inboxes.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("agent_bot_id", "inbox_id"),
    )

    inbox = relationship("Inbox", back_populates="agent_bot_inboxes")


# ============================================================
# Webhook Idempotency
# ============================================================

class WebhookIdempotency(Base):
    """防止 webhook 重放 / 重复消费"""
    __tablename__ = "webhook_idempotency"
    idempotency_key = Column(String(128), primary_key=True)
    received_at = Column(DateTime, server_default=func.now(), index=True)
    response_status = Column(Integer)
    response_body = Column(Text)


# ============================================================
# Mock 数据状态(场景隔离)
# ============================================================

class MockScenarioState(Base):
    """4 个场景之间的数据隔离"""
    __tablename__ = "mock_scenario_states"
    id = Column(Integer, primary_key=True)
    phone = Column(String(20), nullable=False)
    scenario_id = Column(String(20), nullable=False)
    state = Column(JSONB, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("phone", "scenario_id"),
    )
```

### 4.3 Alembic Migration 起步

```bash
# core/ 目录下
alembic init alembic
# 配置 alembic.ini 的 sqlalchemy.url 用环境变量
# alembic/env.py 导入 Base.metadata
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### 4.4 种子数据(张先生 138xxxxxxxx)

详见第 10 章。

---

## 5. 模块详细设计

### 5.1 channel-layer(Polymorphic Channel)

#### 5.1.1 设计目标

让"加一个新渠道"成为"加一张表 + 一组 Service 类"的工作量,而不是"重写一套接入栈"。

#### 5.1.2 核心抽象

```python
# core/src/aicc_core/channels/base.py
from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel

class IncomingMessage(BaseModel):
    """所有渠道入站消息归一化结构"""
    source_id: str          # 渠道身份(phone/cookie/openid)
    content: str            # 消息文本
    content_attributes: dict = {}
    raw_payload: dict = {}  # 原始负载,调试用

class OutgoingMessage(BaseModel):
    """所有渠道出站消息归一化结构"""
    content: str
    content_attributes: dict = {}

class ChannelHandler(ABC):
    """所有 Channel 子类必须实现"""

    channel_type: str  # 子类覆盖

    @abstractmethod
    async def normalize_incoming(self, raw: dict) -> IncomingMessage: ...

    @abstractmethod
    async def send_outgoing(
        self,
        contact_inbox_source_id: str,
        message: OutgoingMessage
    ) -> dict: ...

    @abstractmethod
    def channel_capabilities(self) -> dict:
        """返回此渠道支持的能力(audio/attachments/typing 等)"""
```

#### 5.1.3 实现示例:Voice Channel

```python
# core/src/aicc_core/channels/voice.py
class VoiceChannelHandler(ChannelHandler):
    channel_type = "Channel::Voice"

    async def normalize_incoming(self, raw: dict) -> IncomingMessage:
        return IncomingMessage(
            source_id=raw["source_id"],
            content=raw["transcript"],
            content_attributes={
                "source": "voice_stt",
                "stt_confidence": raw.get("stt_confidence"),
                "audio_url": raw.get("audio_url"),
                "context_id": raw.get("context_id"),
            },
            raw_payload=raw,
        )

    async def send_outgoing(self, source_id, message):
        return await voice_worker_client.inject_tts(
            source_id=source_id,
            text=message.content,
        )

    def channel_capabilities(self):
        return {
            "audio": True,
            "attachments": False,
            "typing": False,
            "interruption": True,
        }
```

#### 5.1.4 注册与路由

```python
# core/src/aicc_core/channels/__init__.py
from .web_widget import WebWidgetChannelHandler
from .voice import VoiceChannelHandler
from .api import ApiChannelHandler

CHANNEL_HANDLERS = {
    "Channel::WebWidget": WebWidgetChannelHandler(),
    "Channel::Voice": VoiceChannelHandler(),
    "Channel::Api": ApiChannelHandler(),
}

def get_handler(channel_type: str) -> ChannelHandler:
    if channel_type not in CHANNEL_HANDLERS:
        raise ValueError(f"Unknown channel type: {channel_type}")
    return CHANNEL_HANDLERS[channel_type]
```

#### 5.1.5 验收标准

- 单元测试:每个 Channel handler 的 normalize_incoming 用 fixture payload 测试
- 集成测试:WebWidget 完整发送一条消息能创建 Conversation + Message
- 加新渠道扩展性测试:能在 30 分钟内加一个 `Channel::Mock` 子类

### 5.2 conversation-core(状态机 + 并发安全)

#### 5.2.1 状态机定义

```python
# core/src/aicc_core/conversations/state_machine.py
from enum import Enum

class Status(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    RESOLVED = "resolved"
    SNOOZED = "snoozed"

# 允许的状态转换(严格白名单)
VALID_TRANSITIONS = {
    Status.PENDING: {Status.OPEN, Status.RESOLVED},
    Status.OPEN: {Status.RESOLVED, Status.SNOOZED},
    Status.SNOOZED: {Status.OPEN, Status.RESOLVED},
    Status.RESOLVED: {Status.OPEN},  # 重开
}

def can_transition(from_status: Status, to_status: Status) -> bool:
    return to_status in VALID_TRANSITIONS.get(from_status, set())
```

#### 5.2.2 并发安全:DB 事务 + advisory lock + version CAS

```python
# core/src/aicc_core/conversations/service.py
from sqlalchemy import text, update
from sqlalchemy.sql import func

class ConcurrentUpdateError(Exception):
    pass


class InvalidTransitionError(Exception):
    pass


class ConversationService:

    async def transition_status(
        self,
        session,
        conversation_id: int,
        to_status: Status,
        expected_version: int,
        actor: str,
    ) -> Conversation:
        """
        三重保护:
        1. PostgreSQL advisory lock 阻塞同一 conversation 的并发更新
        2. version CAS 防止旧事件覆盖新状态
        3. 状态机白名单防止非法转换
        """
        # Step 1: advisory lock(以 conversation_id 为 key)
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:cid)"),
            {"cid": conversation_id}
        )

        # Step 2: 读取当前状态
        conv = await session.get(Conversation, conversation_id)
        if conv is None:
            raise NotFoundError()

        # Step 3: 状态机校验
        from_status = Status(conv.status)
        if not can_transition(from_status, to_status):
            raise InvalidTransitionError(
                f"{from_status} -> {to_status} not allowed"
            )

        # Step 4: version CAS 更新
        result = await session.execute(
            update(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.version == expected_version,
            )
            .values(
                status=to_status.value,
                version=Conversation.version + 1,
                updated_at=func.now(),
            )
            .returning(Conversation.version)
        )
        row = result.first()
        if row is None:
            raise ConcurrentUpdateError(
                f"Version mismatch (expected {expected_version})"
            )

        # Step 5: 记录状态变更事件(审计)
        await self._record_status_change(
            session, conversation_id, from_status, to_status, actor
        )

        # Step 6: 触发 webhook + WS 广播(在事务提交后)
        await self._enqueue_dispatch(conversation_id, "status_changed")

        await session.commit()
        return conv
```

#### 5.2.3 Idempotency Key 防重

```python
# core/src/aicc_core/agentbots/idempotency.py
from fastapi import HTTPException
from fastapi.responses import JSONResponse

async def with_idempotency(
    session,
    redis,
    idempotency_key: str,
    handler,  # async callable
):
    """
    Redis SET NX 原子性预占,DB 表持久化结果
    重复请求直接返回缓存结果
    """
    # 1. Redis 快路径(瞬时去重)
    redis_key = f"idem:{idempotency_key}"
    acquired = await redis.set(redis_key, "1", nx=True, ex=3600)
    if not acquired:
        # 已有人在处理,查 DB 结果
        cached = await session.get(WebhookIdempotency, idempotency_key)
        if cached:
            return JSONResponse(
                status_code=cached.response_status,
                content=cached.response_body
            )
        # 还没有结果,返回 409
        raise HTTPException(409, "Duplicate request in progress")

    # 2. 执行实际逻辑
    try:
        response = await handler()
    finally:
        # 3. 持久化结果
        await session.merge(WebhookIdempotency(
            idempotency_key=idempotency_key,
            response_status=response.status_code,
            response_body=response.body.decode(),
        ))
        await session.commit()

    return response
```

#### 5.2.4 验收标准

- 并发测试:100 个并发请求转移同一 conversation 状态,只有 1 个成功,其他 99 个收到 ConcurrentUpdateError
- 状态机测试:所有非法转换被拒绝
- Idempotency 测试:同一 key 的 2 次请求返回相同结果

### 5.3 agentbot-protocol(Bot Webhook 协议)

#### 5.3.1 协议设计目标

借鉴 Chatwoot AgentBot 协议,**让任何外部 bot(Pipecat 语音 Worker / 第三方文字 bot / Dify)用同一接口接入 AICC**。

#### 5.3.2 协议规约

##### 出站事件(Core → Bot)

```http
POST {bot.outgoing_url}
Content-Type: application/json
X-AICC-Signature: hmac_sha256(signing_secret, timestamp + "." + body)
X-AICC-Timestamp: 1717000000
X-AICC-Idempotency-Key: evt_<uuid>

{
  "event": "message_created",
  "conversation": {
    "id": 123,
    "status": "pending",
    "contact": {"id": 1, "name": "张先生", "phone": "138xxxxxxxx"},
    "inbox": {"id": 1, "channel_type": "Channel::Voice"}
  },
  "message": {
    "id": 456,
    "content": "我要查话费",
    "message_type": 0,
    "sender_type": "Contact",
    "content_attributes": {...}
  }
}
```

支持的 event 类型:
- `widget_triggered` - WebWidget 客户进入
- `conversation_created` - 新会话
- `message_created` - 新消息
- `conversation_updated` - 状态/分配人变更
- `conversation_resolved` - 会话结束

##### 入站回写(Bot → Core)

```http
# Bot 直接回复
POST /api/v1/conversations/{id}/messages
Authorization: Bearer {bot.access_token}
X-AICC-Idempotency-Key: bot_msg_<uuid>

{"content": "您好张先生,我是您的智能客服...",
 "content_attributes": {"source": "voice_bot", "context_id": "ctx-..."}}

# Bot 转人工(custom payload action)
POST /api/v1/conversations/{id}/handoff
{"reason": "complaint", "sentiment_score": 2,
 "ai_summary": "客户因之前工单未解决而投诉,情绪激动"}

# Bot 直接 resolve
POST /api/v1/conversations/{id}/resolve
{"reason": "self_served"}
```

#### 5.3.3 HMAC 签名校验

```python
# core/src/aicc_core/agentbots/signing.py
import hmac
import hashlib
import time

def sign_payload(secret: str, body: str, timestamp: int = None) -> tuple[str, int]:
    if timestamp is None:
        timestamp = int(time.time())
    message = f"{timestamp}.{body}".encode("utf-8")
    signature = hmac.new(
        secret.encode("utf-8"),
        message,
        hashlib.sha256
    ).hexdigest()
    return signature, timestamp


def verify_signature(
    secret: str, body: str, signature: str, timestamp: int,
    tolerance_seconds: int = 300
) -> bool:
    # 防重放:时间戳超过 5 分钟拒绝
    if abs(time.time() - timestamp) > tolerance_seconds:
        return False
    expected, _ = sign_payload(secret, body, timestamp)
    return hmac.compare_digest(expected, signature)
```

#### 5.3.4 出站 Dispatcher

```python
# core/src/aicc_core/agentbots/webhook_dispatcher.py
import httpx
from aicc_core.agentbots.signing import sign_payload

class WebhookDispatcher:
    def __init__(self, http_client: httpx.AsyncClient):
        self.http = http_client

    async def dispatch(self, agent_bot: AgentBot, event: str, payload: dict):
        body = json.dumps(payload, ensure_ascii=False)
        sig, ts = sign_payload(agent_bot.signing_secret, body)
        headers = {
            "Content-Type": "application/json",
            "X-AICC-Signature": sig,
            "X-AICC-Timestamp": str(ts),
            "X-AICC-Idempotency-Key": f"evt_{uuid.uuid4()}",
        }
        # 出站不阻塞:5 秒超时,失败重试 3 次(指数退避)
        for attempt in range(3):
            try:
                resp = await self.http.post(
                    agent_bot.outgoing_url,
                    content=body,
                    headers=headers,
                    timeout=5.0
                )
                if resp.status_code < 500:
                    return  # 成功或客户端错误,不重试
            except (httpx.TimeoutException, httpx.NetworkError):
                pass
            await asyncio.sleep(2 ** attempt)
        # 三次后仍失败,记录到死信队列
        await self._record_dead_letter(agent_bot, event, payload)
```

#### 5.3.5 验收标准

- 签名测试:正确签名通过,错误签名/过期签名被拒绝
- 重试测试:bot URL 返回 500 时,触发重试逻辑
- 死信测试:连续 3 次失败后写死信表

### 5.4 voice-worker(Pipecat 集成)

#### 5.4.1 模块职责

- 接收 PJSIP server 的入站通话事件
- 启动 per-call PipelineTask
- 调用 STT/LLM/TTS
- 把转录/回复回写 AICC Core
- S3 时把音频流"旁路"到 AICC Core 的 WebSocket+PCM 桥

#### 5.4.2 主入口

```python
# voice_worker/src/voice_worker/main.py
from fastapi import FastAPI, WebSocket
from voice_worker.pipelines.inbound_zh import build_inbound_zh_pipeline
from voice_worker.pipelines.translation_bridge import build_translation_pipeline

app = FastAPI()

# 全局共享:PJSIP Endpoint 单例 + 活跃通话 registry
pjsip_actor = None  # 第 5.5 章详述
active_calls: dict[str, PipelineTask] = {}

@app.on_event("startup")
async def startup():
    global pjsip_actor
    pjsip_actor = await PJSIPActor.start()

@app.on_event("shutdown")
async def shutdown():
    await pjsip_actor.stop()


# PJSIP server 通过 HTTP 通知 Voice Worker
@app.post("/internal/call/started")
async def on_call_started(req: CallStartedRequest):
    """PJSIP server 收到 INVITE 后通知 voice worker 准备 pipeline"""
    call_id = req.call_id
    source_id = req.from_phone

    # 决定用哪个 pipeline(根据当前场景或默认 inbound)
    scenario = await detect_scenario(source_id)  # 见种子数据

    if scenario == "s4":
        pipeline = build_translation_pipeline(call_id, source_id)
    else:
        pipeline = build_inbound_zh_pipeline(call_id, source_id, scenario)

    task = PipelineTask(pipeline)
    active_calls[call_id] = task
    asyncio.create_task(task.run())

    return {"status": "started"}


@app.post("/internal/call/ended")
async def on_call_ended(call_id: str):
    if call_id in active_calls:
        await active_calls[call_id].queue_frame(EndFrame())
        del active_calls[call_id]
    return {"status": "ended"}


# AICC Core 通知:某通话需要"音频桥到坐席 WebSocket"
@app.post("/internal/call/{call_id}/handoff")
async def on_handoff(call_id: str, ws_endpoint: str):
    """旁路 Pipecat,直接桥接 PJSIP ↔ Agent WebSocket"""
    task = active_calls.get(call_id)
    if not task:
        raise HTTPException(404)
    await pjsip_actor.bridge_to_websocket(call_id, ws_endpoint)
    # 把 Pipecat pipeline 暂停(但 InterruptionFrame 仍订阅)
    await task.pause_main_pipeline()
    return {"status": "bridged"}
```

#### 5.4.3 Pipeline 构建(S1/S2/S3 复用 inbound_zh)

```python
# voice_worker/src/voice_worker/pipelines/inbound_zh.py
from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat_flows import FlowManager

from voice_worker.transports.pjsip_transport import PJSIPTransport
from voice_worker.services.faster_whisper_stt import FasterWhisperSTTService
from voice_worker.services.deepseek_llm import DeepSeekLLMService
from voice_worker.services.piper_tts import PiperTTSService
from voice_worker.processors.chatwoot_bot_event import ChatwootBotEventProcessor
from voice_worker.processors.latency_tracer import LatencyTracer
from voice_worker.flows import s1_diagnosis, s2_retention, s3_handoff

def build_inbound_zh_pipeline(call_id, source_id, scenario):
    pjsip = PJSIPTransport(call_id=call_id, codec="PCMA")
    stt = FasterWhisperSTTService(model="small", device="cuda", language="zh")
    llm = DeepSeekLLMService(model="deepseek-chat")
    tts = PiperTTSService(voice="zh_CN-huayan-medium", device="cpu")
    bot_event = ChatwootBotEventProcessor(
        aicc_core_url=settings.AICC_CORE_URL,
        bot_token=settings.BOT_ACCESS_TOKEN,
        signing_secret=settings.BOT_SIGNING_SECRET,
        source_id=source_id,
    )
    tracer = LatencyTracer(call_id=call_id)

    context = OpenAILLMContext(messages=[])
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline([
        pjsip.input(),
        tracer.tag("rtp_in"),
        stt,
        tracer.tag("stt_final"),
        context_aggregator.user(),
        llm,
        tracer.tag("llm_first_token"),
        context_aggregator.assistant(),
        tts,
        tracer.tag("tts_first_audio"),
        bot_event,
        pjsip.output(),
        tracer.tag("rtp_out"),
    ])

    # FlowManager 决定走哪个场景
    flow_module = {
        "s1": s1_diagnosis,
        "s2": s2_retention,
        "s3": s3_handoff,
    }.get(scenario, s1_diagnosis)

    flow_mgr = FlowManager(
        task=None,  # 后面 PipelineTask 会注入
        llm=llm,
        context_aggregator=context_aggregator,
        flow_config=flow_module.FLOW_CONFIG,
    )

    return pipeline, flow_mgr
```

#### 5.4.4 验收标准

- 单元测试:每个 service(STT/LLM/TTS) mock 后能 build pipeline 不抛错
- 集成测试:S1 用 sound file 替代 PJSIP 输入,跑通完整 STT→LLM→TTS,转录写入 Core

### 5.5 pjsip-transport(核心模块,actor 模式)

#### 5.5.1 设计核心:Actor 线程模型

**铁律**(详见附录 A 的 PJSIP_THREADING.md):
1. PJSIP Endpoint 是**进程级单例**
2. 所有 pjsua2 API 调用**只能在 PJSIP actor 线程执行**
3. asyncio 与 actor 通过**命令队列**通信
4. asyncio **永远不持有** Call/Account/AudioMedia 对象引用,只持有整数 call_id
5. 跨线程访问 pjsua2 API 必须先 `pj_thread_register()`

#### 5.5.2 Actor 实现

```python
# voice_worker/src/voice_worker/transports/pjsip_actor.py
import asyncio
import threading
import queue
import pjsua2 as pj

class PJSIPActor:
    """单例。PJSIP 工作线程 + 命令队列。"""

    def __init__(self):
        self.endpoint: pj.Endpoint = None
        self.account: pj.Account = None
        self.calls: dict[str, "PJSIPCallHandler"] = {}  # call_id -> handler
        self.cmd_queue: queue.Queue = queue.Queue()
        self.thread: threading.Thread = None
        self.loop: asyncio.AbstractEventLoop = None

    @classmethod
    async def start(cls):
        instance = cls()
        instance.loop = asyncio.get_running_loop()
        instance.thread = threading.Thread(
            target=instance._actor_loop,
            daemon=True,
            name="PJSIP-Actor"
        )
        instance.thread.start()
        # 等待 endpoint 初始化完成
        await instance._wait_ready()
        return instance

    def _actor_loop(self):
        """PJSIP 工作线程主循环"""
        # ① 创建 Endpoint(只在此线程做)
        self.endpoint = pj.Endpoint()
        self.endpoint.libCreate()

        ep_cfg = pj.EpConfig()
        ep_cfg.uaConfig.threadCnt = 0  # ★ 关键:Python 场景必须 0
        self.endpoint.libInit(ep_cfg)

        # 配置 transport
        sip_tp_cfg = pj.TransportConfig()
        sip_tp_cfg.port = 5060
        self.endpoint.transportCreate(pj.PJSIP_TRANSPORT_UDP, sip_tp_cfg)

        # 配置 codec(只开 PCMA)
        self.endpoint.codecSetPriority("pcma/8000/1", 255)
        self.endpoint.codecSetPriority("pcmu/8000/1", 0)
        # 其他全部禁用
        for codec_info in self.endpoint.codecEnum2():
            if codec_info.codecId not in ["pcma/8000/1", "pcmu/8000/1"]:
                self.endpoint.codecSetPriority(codec_info.codecId, 0)

        # 创建 Account(收任意号码)
        acc_cfg = pj.AccountConfig()
        acc_cfg.idUri = "sip:1001@127.0.0.1"
        acc_cfg.regConfig.registrarUri = ""  # 不注册到外部 registrar
        self.account = AICCAccount(self)
        self.account.create(acc_cfg)

        self.endpoint.libStart()
        self._signal_ready()

        # ② 主循环:处理命令队列 + libHandleEvents
        while not self._should_stop:
            # 处理来自 asyncio 的命令
            try:
                while True:
                    cmd = self.cmd_queue.get_nowait()
                    self._handle_cmd(cmd)
            except queue.Empty:
                pass

            # 处理 PJSIP 事件
            self.endpoint.libHandleEvents(10)  # 10ms 轮询

        # 清理
        self.endpoint.libDestroy()

    def _handle_cmd(self, cmd):
        """所有 pjsua2 操作在此线程执行"""
        try:
            if cmd["type"] == "answer":
                call = self.calls[cmd["call_id"]]
                op = pj.CallOpParam()
                op.statusCode = 200
                call.answer(op)
            elif cmd["type"] == "hangup":
                call = self.calls[cmd["call_id"]]
                op = pj.CallOpParam()
                op.statusCode = 486
                call.hangup(op)
            elif cmd["type"] == "send_pcm":
                call = self.calls[cmd["call_id"]]
                # 写 PCM 到 AudioMedia(详见下文)
                self._write_pcm(call, cmd["pcm_data"])
            elif cmd["type"] == "bridge_websocket":
                # S3 转人工时:把音频流改桥到 WS,而不是 Voice Worker
                self._bridge_to_ws(cmd["call_id"], cmd["ws_endpoint"])
            # 其他命令...
        except Exception as e:
            # 严禁让异常泄漏出 actor 线程
            logger.exception(f"Command failed: {cmd}, {e}")

    # ============================================================
    # 提供给 asyncio 调用的接口(线程安全)
    # ============================================================

    def submit_cmd(self, cmd: dict):
        """从 asyncio 线程调用,投递命令到 actor"""
        self.cmd_queue.put(cmd)

    async def answer_call(self, call_id: str):
        self.submit_cmd({"type": "answer", "call_id": call_id})

    async def hangup_call(self, call_id: str):
        self.submit_cmd({"type": "hangup", "call_id": call_id})

    async def send_pcm(self, call_id: str, pcm_data: bytes):
        self.submit_cmd({"type": "send_pcm", "call_id": call_id,
                         "pcm_data": pcm_data})

    async def bridge_to_websocket(self, call_id: str, ws_endpoint: str):
        self.submit_cmd({"type": "bridge_websocket", "call_id": call_id,
                         "ws_endpoint": ws_endpoint})


class AICCAccount(pj.Account):
    """处理来电"""
    def __init__(self, actor):
        super().__init__()
        self.actor = actor

    def onIncomingCall(self, prm):
        """PJSIP 工作线程回调"""
        call = PJSIPCallHandler(self, prm.callId, self.actor)
        call_id = str(prm.callId)
        self.actor.calls[call_id] = call

        # 通知 Voice Worker(切回 asyncio 线程)
        from_phone = call.getInfo().remoteUri  # 解析出号码
        future = asyncio.run_coroutine_threadsafe(
            self.actor._notify_voice_worker_call_started(
                call_id, from_phone
            ),
            self.actor.loop,
        )
        # 不等待 future,immediately 200 OK
        op = pj.CallOpParam()
        op.statusCode = 200
        call.answer(op)


class PJSIPCallHandler(pj.Call):
    """单通话处理"""
    def __init__(self, account, call_id, actor):
        super().__init__(account, call_id)
        self.actor = actor
        self.audio_media = None

    def onCallState(self, prm):
        """PJSIP 工作线程回调"""
        info = self.getInfo()
        if info.state == pj.PJSIP_INV_STATE_DISCONNECTED:
            # 通知 asyncio 通话结束
            asyncio.run_coroutine_threadsafe(
                self.actor._notify_voice_worker_call_ended(str(info.id)),
                self.actor.loop,
            )
            # 清理
            self.actor.calls.pop(str(info.id), None)

    def onCallMediaState(self, prm):
        """媒体协商完成回调"""
        info = self.getInfo()
        for med in info.media:
            if (med.type == pj.PJMEDIA_TYPE_AUDIO and
                med.status == pj.PJSUA_CALL_MEDIA_ACTIVE):
                self.audio_media = self.getAudioMedia(med.index)
                # 把音频媒体绑到自定义 PCM 端口(见下文)
                self.actor._attach_pcm_port(self, self.audio_media)
```

#### 5.5.3 PJSIP Transport(Pipecat 接口)

```python
# voice_worker/src/voice_worker/transports/pjsip_transport.py
from pipecat.frames.frames import (
    AudioRawFrame, InputAudioRawFrame, OutputAudioRawFrame,
    StartFrame, EndFrame, InterruptionFrame
)
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.base_input import BaseInputTransport
from pipecat.transports.base_output import BaseOutputTransport

from voice_worker.transports.resampler import Resampler


class PJSIPInputTransport(BaseInputTransport):
    """从 PJSIP 收 PCM,推 AudioRawFrame 入 pipeline"""

    def __init__(self, call_id, actor, params):
        super().__init__(params)
        self.call_id = call_id
        self.actor = actor
        # PJSIP 给的是 8kHz mono,Whisper 要 16kHz
        self.resampler = Resampler(src_rate=8000, dst_rate=16000)
        self.pcm_queue = asyncio.Queue(maxsize=100)
        # 注册到 actor:每收到一帧 PCM(20ms),回调到 self
        self.actor._register_pcm_callback(call_id, self._on_pcm_received)

    def _on_pcm_received(self, pcm_8k: bytes):
        """从 actor 线程被调用,需要切到 asyncio"""
        # 用 call_soon_threadsafe 把帧投递到 asyncio
        try:
            self.actor.loop.call_soon_threadsafe(
                self.pcm_queue.put_nowait, pcm_8k
            )
        except asyncio.QueueFull:
            # 队列满,丢帧,记录指标
            metrics.inc("pcm_drop")

    async def start(self, frame: StartFrame):
        await super().start(frame)
        self._task = asyncio.create_task(self._pcm_pump())

    async def _pcm_pump(self):
        """持续把 PCM 推入 pipeline"""
        while not self._should_stop:
            pcm_8k = await self.pcm_queue.get()
            pcm_16k = self.resampler.resample(pcm_8k)
            await self.push_frame(InputAudioRawFrame(
                audio=pcm_16k, sample_rate=16000, num_channels=1
            ))

    async def stop(self, frame):
        await super().stop(frame)
        if self._task:
            self._task.cancel()


class PJSIPOutputTransport(BaseOutputTransport):
    """从 pipeline 收 OutputAudioRawFrame,送 PCM 到 PJSIP"""

    def __init__(self, call_id, actor, params):
        super().__init__(params)
        self.call_id = call_id
        self.actor = actor
        # TTS 通常 24k 或 22k,要降到 8k
        self.resampler = Resampler(src_rate=24000, dst_rate=8000)

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        if isinstance(frame, OutputAudioRawFrame):
            pcm_8k = self.resampler.resample(frame.audio)
            await self.actor.send_pcm(self.call_id, pcm_8k)
        elif isinstance(frame, InterruptionFrame):
            # 客户打断:PJSIP 立即停止 outbound RTP
            await self.actor.flush_outbound(self.call_id)


class PJSIPTransport(BaseTransport):
    def __init__(self, call_id, codec="PCMA", actor=None):
        super().__init__()
        if actor is None:
            from voice_worker.main import pjsip_actor as global_actor
            actor = global_actor
        self.call_id = call_id
        self.actor = actor
        self._input = PJSIPInputTransport(call_id, actor, params=None)
        self._output = PJSIPOutputTransport(call_id, actor, params=None)

    def input(self): return self._input
    def output(self): return self._output
```

#### 5.5.4 SIP method 支持矩阵(详见 SIP_SCENARIOS.md)

| Method | 支持? | 行为 |
|---|---|---|
| INVITE | ✅ 支持(无 SDP early media) | 立即 200 OK + SDP answer |
| ACK | ✅ | 完成 dialog |
| BYE | ✅ | 触发 onCallState DISCONNECTED |
| CANCEL | ✅ | 取消 INVITE |
| OPTIONS | ✅(自动应答) | PJSIP 默认处理 |
| REGISTER | ⚠️ 仅监听 | 不主动注册到外部 registrar |
| INFO | ⚠️ 接受但不处理 | 日志告警 |
| UPDATE | ❌ **拒绝(481)** | 不支持 dialog 内更新 |
| re-INVITE | ❌ **拒绝(488)** | 不支持媒体重协商 |
| REFER | ❌ **拒绝(501)** | 转移用 AICC API,不在 SIP 层做 |
| NOTIFY | ❌ 拒绝 | |
| SUBSCRIBE | ❌ 拒绝 | |

#### 5.5.5 验收标准

- 单元测试:Resampler 8k↔16k 正确性(用 sin wave 验证)
- 集成测试:用 SIPp 发 INVITE,验证 200 OK 响应、SDP 包含 PCMA
- 压测:200 次自动呼入挂断不崩,RSS 增长 < 5%
- 手测:Linphone 拨入,演示者说话,声音完整传到 voice worker

### 5.6 ws-realtime(WebSocket 事件层)

#### 5.6.1 双 Token 模型

```python
# core/src/aicc_core/ws/api.py
from fastapi import WebSocket, WebSocketDisconnect, Query
from aicc_core.ws.manager import ConnectionManager

manager = ConnectionManager()

@app.websocket("/ws/agent")
async def ws_agent(ws: WebSocket, token: str = Query(...)):
    """坐席 WebSocket"""
    user = await authenticate_user(token)
    if not user:
        await ws.close(code=4001)
        return
    await ws.accept()
    await manager.connect_user(user, ws)
    try:
        while True:
            msg = await ws.receive_json()
            await handle_agent_msg(user, msg)
    except WebSocketDisconnect:
        await manager.disconnect_user(user)


@app.websocket("/ws/widget")
async def ws_widget(ws: WebSocket, pubsub_token: str = Query(...)):
    """客户(Web Widget)WebSocket"""
    contact_inbox = await find_by_pubsub_token(pubsub_token)
    if not contact_inbox:
        await ws.close(code=4001)
        return
    await ws.accept()
    await manager.connect_contact(contact_inbox, ws)
    # ...
```

#### 5.6.2 选择性广播(Redis pub/sub)

```python
# core/src/aicc_core/ws/broadcaster.py
import redis.asyncio as redis

class EventBroadcaster:
    def __init__(self, redis_url):
        self.r = redis.from_url(redis_url)

    async def publish_event(self, event: str, payload: dict):
        # 按 inbox_id 分频道,避免广播给无关坐席
        channel = f"inbox:{payload['inbox_id']}"
        await self.r.publish(channel, json.dumps({
            "event": event, "payload": payload
        }))

    async def subscribe_for_user(self, user, callback):
        """用户登录后,订阅他能看的所有 inbox 频道"""
        inboxes = await get_user_inboxes(user)
        channels = [f"inbox:{i.id}" for i in inboxes]
        pubsub = self.r.pubsub()
        await pubsub.subscribe(*channels)
        async for msg in pubsub.listen():
            if msg["type"] == "message":
                await callback(msg["data"])
```

#### 5.6.3 事件类型注册表

```python
# core/src/aicc_core/ws/events.py
EVENT_TYPES = [
    # Conversation
    "conversation.created",
    "conversation.updated",
    "conversation.status_changed",
    "conversation.contact_changed",
    "team.changed",
    "assignee.changed",

    # Message
    "message.created",
    "message.updated",
    "conversation_typing_on",
    "conversation_typing_off",

    # Realtime audio (S3 转人工)
    "audio.bridge.start",
    "audio.bridge.frame",
    "audio.bridge.stop",

    # Captain-Lite suggestion
    "ai.suggestion.created",
]
```

#### 5.6.4 验收标准

- 连接 1000 个 WS,内存增长可控
- 选择性广播:坐席只收到自己 inbox 的事件
- 断线重连:客户端重连后能恢复未读消息

### 5.7 captain-lite(坐席助手)

#### 5.7.1 资源隔离

**铁律**(red team 接受):Captain 用**独立的 DeepSeek API key**,不与主管线 LLM 共享 quota/concurrency,失败可丢弃。

#### 5.7.2 架构

```python
# core/src/aicc_core/captain_lite/service.py
class CaptainService:
    def __init__(self, llm_client, rag, event_broadcaster):
        self.llm = llm_client  # 独立 DeepSeek API key
        self.rag = rag
        self.broadcaster = event_broadcaster

    async def on_message_created(self, conversation_id, message):
        """异步触发,失败可丢弃"""
        try:
            # 取上下文(选择性切片,不全量入 prompt)
            ctx = await self._slice_state(conversation_id)
            # 检索知识库
            chunks = await self.rag.retrieve(message.content, k=3)
            # 调 LLM 生成建议
            suggestion = await asyncio.wait_for(
                self.llm.complete(
                    system=CAPTAIN_SYSTEM_PROMPT,
                    user=self._build_prompt(ctx, chunks, message),
                ),
                timeout=3.0  # 3 秒拿不到就放弃
            )
            # 推送到坐席工作台
            await self.broadcaster.publish_event(
                "ai.suggestion.created",
                {
                    "conversation_id": conversation_id,
                    "suggestion": suggestion,
                    "knowledge_refs": [c.source for c in chunks],
                }
            )
        except (asyncio.TimeoutError, Exception) as e:
            metrics.inc("captain_failed")
            # 不抛错,不阻塞主流程
```

#### 5.7.3 状态切片(避免泄露敏感字段)

```python
async def _slice_state(self, conversation_id):
    """只抽取 LLM 需要的字段,排除敏感"""
    conv = await get_conversation(conversation_id)
    return {
        "conversation": {
            "id": conv.id,
            "status": conv.status,
            "scenario_id": conv.scenario_id,
        },
        "contact": {
            "name": conv.contact.name,
            "tier": conv.contact.custom_attributes.get("tier"),
            # 严禁包含:phone, email, password_hash, custom_attributes 全量
        },
        "recent_messages": [
            {"sender": m.sender_type, "content": m.content[:200]}
            for m in conv.messages[-5:]
        ],
    }
```

#### 5.7.4 Mock RAG

```python
# core/src/aicc_core/captain_lite/rag.py
import json

class MockRAG:
    def __init__(self, knowledge_path: str):
        with open(knowledge_path, "r", encoding="utf-8") as f:
            self.knowledge = json.load(f)

    async def retrieve(self, query: str, k: int = 3) -> list:
        # 简单实现:基于关键词匹配
        # 真正生产要换 BCEmbedding + pgvector
        scored = []
        for doc in self.knowledge:
            score = sum(
                1 for kw in doc["keywords"] if kw in query
            )
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda x: -x[0])
        return [doc for _, doc in scored[:k]]
```

#### 5.7.5 验收标准

- LLM 超时 3 秒不阻塞主流程
- 推送的 suggestion 在坐席端 < 5 秒内显示
- 不会向 prompt 泄露 phone/email 等敏感字段

### 5.8 mock-bss(Mock API)

#### 5.8.1 设计原则

Codex Issue #11 要求:**基于 phone + scenario_id 确定性**,不同场景之间不互相打架。

```python
# core/src/aicc_core/mocks/network.py
from fastapi import APIRouter
from aicc_core.db.models import MockScenarioState

router = APIRouter(prefix="/mock/network", tags=["mock"])

@router.get("/diagnose")
async def diagnose(phone: str, scenario: str = "s1", session=Depends(get_session)):
    """网络诊断 Mock"""
    # 查种子数据中预定义的状态
    state = await session.execute(
        select(MockScenarioState).where(
            MockScenarioState.phone == phone,
            MockScenarioState.scenario_id == scenario,
        )
    )
    row = state.scalar_one_or_none()
    if row is None:
        # 默认无问题
        return {"status": "healthy", "issue_type": None}
    return row.state.get("diagnosis", {})
```

5 个 Mock API 模块完整结构详见第 10 章。

### 5.9 agent-workspace(Vue 工作台)

#### 5.9.1 极简组件结构

```
src/components/
├── ConversationList.vue        # 会话列表(WS 实时刷新)
├── TranscriptStream.vue        # 转录流(可隐藏)
├── AISuggestionCard.vue        # AI 建议卡片(显著)
├── CustomerProfile.vue         # 客户画像
├── AnswerButton.vue            # 接听按钮
└── AudioPlayer.vue             # WebSocket+PCM 桥(取代 JsSIP)
```

#### 5.9.2 WebSocket+PCM 音频桥(取代 JsSIP)

```typescript
// src/lib/audio-bridge.ts
export class AudioBridge {
  private audioCtx: AudioContext;
  private ws: WebSocket;
  private playbackQueue: AudioBufferSourceNode[] = [];

  async connect(callId: string, token: string) {
    this.audioCtx = new AudioContext({ sampleRate: 16000 });
    this.ws = new WebSocket(
      `wss://${HOST}/ws/audio-bridge?call_id=${callId}&token=${token}`
    );
    this.ws.binaryType = "arraybuffer";

    this.ws.onmessage = (evt) => {
      // 收到 PCM 音频帧(16kHz mono int16)
      this.playPCM(new Int16Array(evt.data));
    };

    // 麦克风采集 → PCM → WS
    const stream = await navigator.mediaDevices.getUserMedia({audio: true});
    const source = this.audioCtx.createMediaStreamSource(stream);
    const processor = this.audioCtx.createScriptProcessor(1024, 1, 1);
    source.connect(processor);
    processor.connect(this.audioCtx.destination);
    processor.onaudioprocess = (e) => {
      const pcm16 = this.float32To16(e.inputBuffer.getChannelData(0));
      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(pcm16.buffer);
      }
    };
  }

  playPCM(pcm: Int16Array) {
    // 直接播放
    const buffer = this.audioCtx.createBuffer(1, pcm.length, 16000);
    const channel = buffer.getChannelData(0);
    for (let i = 0; i < pcm.length; i++) {
      channel[i] = pcm[i] / 32768;
    }
    const source = this.audioCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(this.audioCtx.destination);
    source.start();
    this.playbackQueue.push(source);
  }

  // 客户打断时:清空播放队列
  flushPlayback() {
    this.playbackQueue.forEach((s) => s.stop());
    this.playbackQueue = [];
  }

  float32To16(input: Float32Array): Int16Array {
    const out = new Int16Array(input.length);
    for (let i = 0; i < input.length; i++) {
      const s = Math.max(-1, Math.min(1, input[i]));
      out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return out;
  }

  disconnect() {
    this.ws?.close();
    this.audioCtx?.close();
  }
}
```

#### 5.9.3 验收标准

- 5 个组件每个有 vue-test-utils 单元测试
- 接听按钮点击后,WS 连接 < 500ms 建立
- 音频播放无明显卡顿(playback queue 平滑)
- 客户打断时,坐席端音频立即静音

---

## 6. API 接口规约

### 6.1 REST API(AICC Core)

#### 6.1.1 Auth

| 类型 | Header | 用途 |
|---|---|---|
| User Token | `Authorization: Bearer <user_token>` | 坐席调用 |
| Bot Token | `Authorization: Bearer <bot_access_token>` | Bot 回写 |
| Platform | `api_access_token: <admin_token>` | 管理员/Platform |

所有写操作还要带:`X-AICC-Idempotency-Key: <unique-uuid>`

#### 6.1.2 核心端点

```
# Conversations
GET    /api/v1/accounts/{account_id}/conversations
POST   /api/v1/accounts/{account_id}/conversations
GET    /api/v1/accounts/{account_id}/conversations/{id}
POST   /api/v1/accounts/{account_id}/conversations/{id}/messages
POST   /api/v1/accounts/{account_id}/conversations/{id}/handoff
POST   /api/v1/accounts/{account_id}/conversations/{id}/resolve
POST   /api/v1/accounts/{account_id}/conversations/{id}/snooze
POST   /api/v1/accounts/{account_id}/conversations/{id}/assign
                                              # body: {assignee_id: int}

# Contacts
GET    /api/v1/accounts/{account_id}/contacts/search?phone=138...
POST   /api/v1/accounts/{account_id}/contacts
GET    /api/v1/accounts/{account_id}/contacts/{id}
GET    /api/v1/accounts/{account_id}/contacts/{id}/conversations  # 跨渠道历史

# Inboxes
GET    /api/v1/accounts/{account_id}/inboxes
POST   /api/v1/accounts/{account_id}/inboxes  # 创建 Polymorphic Channel

# Webhook (Bot 回调入口)
POST   /api/v1/accounts/{account_id}/webhooks/agent_bot
                                              # 签名 + idempotency

# Mock APIs(只在 dev/demo)
GET    /mock/network/diagnose?phone=&scenario=
GET    /mock/profile/lookup?phone=
GET    /mock/profile/usage?phone=&scenario=
GET    /mock/plan/list
POST   /mock/plan/change
POST   /mock/ticket/create
POST   /mock/voucher/grant
GET    /mock/voucher/list?phone=

# Internal (Voice Worker → Core)
POST   /internal/voice/incoming_call    # PJSIP 收到 INVITE 的通知
POST   /internal/voice/transcript       # STT 实时转录
POST   /internal/voice/bot_message      # Bot 完整回复
POST   /internal/voice/handoff_request  # Bot 触发转人工
```

#### 6.1.3 OpenAPI 自动生成

```python
# core/src/aicc_core/main.py
from fastapi import FastAPI

app = FastAPI(
    title="AICC-Lite Core API",
    version="3.0",
    description="...",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",
)
```

启动后访问 `http://localhost:8000/docs` 自动获得完整 OpenAPI 文档。

### 6.2 WebSocket 协议

#### 6.2.1 坐席端

```
连接:wss://aicc.local/ws/agent?token=<user_pubsub_token>

发送(C2S):
  {"action": "subscribe", "inbox_id": 1}
  {"action": "typing", "conversation_id": 123, "is_typing": true}
  {"action": "answer_call", "conversation_id": 123}

接收(S2C):
  {"event": "message.created", "data": {...}}
  {"event": "conversation.status_changed", "data": {...}}
  {"event": "ai.suggestion.created", "data": {...}}
  {"event": "audio.bridge.start", "data": {...}}
```

#### 6.2.2 客户端(Web Widget)

```
连接:wss://aicc.local/ws/widget?pubsub_token=<contact_inbox_pubsub_token>

发送(C2S):
  {"action": "send_message", "content": "你好"}

接收(S2C):
  {"event": "message.created", "data": {...}}
  {"event": "conversation_typing_on", "data": {...}}
```

#### 6.2.3 音频桥(S3)

```
连接:wss://aicc.local/ws/audio-bridge?call_id=xxx&token=<user_token>

二进制帧:
  C2S: PCM int16 mono 16kHz(坐席麦克风)
  S2C: PCM int16 mono 16kHz(客户音频)

控制帧(JSON,text):
  {"event": "interrupt"}     # 客户打断,清空播放队列
  {"event": "call_ended"}    # 通话结束
```

### 6.3 Bot Webhook 协议(详见 5.3)

略。

---

## 7. SIP 集成规约

详见附录 A 中的 `PJSIP_THREADING.md` 和 `SIP_SCENARIOS.md`。这里给出**集成层面的硬规则**。

### 7.1 不变量(Invariants)

**违反任何一条都会导致非确定性崩溃**:

1. PJSIP Endpoint 全进程**只创建一次**。任何"为了测试我重新 init 一下"的代码必须 review。
2. **`uaConfig.threadCnt = 0`**(Python 场景必须)
3. 所有 pjsua2 API 调用**只在 PJSIP actor 线程**。其他线程必须先 `pj_thread_register()`。
4. asyncio 端**只持有 call_id 字符串**,不持有 pjsua2 对象引用。
5. asyncio → PJSIP 的所有指令通过 **command queue**,不直接调 pjsua2。
6. PJSIP → asyncio 的所有事件通过 **`call_soon_threadsafe`** 投递。
7. 对象销毁**显式触发**(用命令),不依赖 Python GC。
8. **接受的 Codec 只有 PCMA**,8kHz 全链路。其他 codec 在 SDP 协商时拒绝。
9. **拒绝的 SIP method**:UPDATE / re-INVITE / REFER / NOTIFY / SUBSCRIBE。返回 4xx,记日志,不 silent ignore。

### 7.2 SDP 金样本(放在 `references/sdp_samples/`)

```
v=0
o=- 0 0 IN IP4 127.0.0.1
s=AICC-Lite
c=IN IP4 127.0.0.1
t=0 0
m=audio 10000 RTP/AVP 8 101
a=rtpmap:8 PCMA/8000
a=rtpmap:101 telephone-event/8000
a=fmtp:101 0-16
a=sendrecv
a=ptime:20
```

### 7.3 RTP 端口范围

- PJSIP RTP pool: UDP 10000-10100(配置 `mediaConfig.portRange = 100`)
- 防火墙规则:`ufw allow 5060/udp; ufw allow 10000:10100/udp`(仅 LAN)
- Docker: `ports: ["5060:5060/udp", "10000-10100:10000-10100/udp"]`

### 7.4 SIPp 测试场景

`references/sipp_scenarios/happy_path_inbound.xml`:

```xml
<?xml version="1.0" encoding="ISO-8859-1" ?>
<scenario name="AICC Happy Path Inbound">
  <send retrans="500">
    <![CDATA[
      INVITE sip:1001@[remote_ip]:[remote_port] SIP/2.0
      Via: SIP/2.0/UDP [local_ip]:[local_port];branch=[branch]
      From: sipp <sip:sipp@[local_ip]>;tag=[call_number]
      To: aicc <sip:1001@[remote_ip]>
      Call-ID: [call_id]
      CSeq: 1 INVITE
      Contact: sip:sipp@[local_ip]:[local_port]
      Max-Forwards: 70
      Subject: Performance Test
      Content-Type: application/sdp
      Content-Length: [len]

      v=0
      o=user1 53655765 2353687637 IN IP[local_ip_type] [local_ip]
      s=-
      c=IN IP[media_ip_type] [media_ip]
      t=0 0
      m=audio [media_port] RTP/AVP 8
      a=rtpmap:8 PCMA/8000
    ]]>
  </send>
  <recv response="100" optional="true"/>
  <recv response="200" rtd="true"/>
  <send>
    <![CDATA[
      ACK sip:1001@[remote_ip]:[remote_port] SIP/2.0
      ...
    ]]>
  </send>
  <pause milliseconds="5000"/>
  <send>
    <![CDATA[
      BYE sip:1001@[remote_ip]:[remote_port] SIP/2.0
      ...
    ]]>
  </send>
  <recv response="200" crlf="true"/>
</scenario>
```

跑法:`sipp -sf happy_path_inbound.xml -s 1001 127.0.0.1:5060 -r 1 -m 1`

### 7.5 `sngrep` 用法

```bash
# 进入容器
docker compose exec sngrep sngrep
# 实时查看 SIP 信令
# F2 切换 dialog,F3 看 SDP,F4 看 RTP 统计
```

---

## 8. 中文 STT/TTS 集成方案

### 8.1 faster-whisper(STT)

#### 8.1.1 选型理由

- 中文 SOTA 开源
- 支持 int8 量化,4GB VRAM 可跑 small/medium
- 流式 API(逐 chunk 出 partial transcript)

#### 8.1.2 配置(P1000 4GB)

```python
# voice_worker/src/voice_worker/services/faster_whisper_stt.py
from faster_whisper import WhisperModel
from pipecat.services.stt_service import STTService
from pipecat.frames.frames import (
    TranscriptionFrame, InterimTranscriptionFrame
)

class FasterWhisperSTTService(STTService):
    def __init__(
        self,
        model: str = "small",     # P1000 只能跑到 small,large 装不下
        device: str = "cuda",
        compute_type: str = "int8",  # int8 量化,VRAM 占用减半
        language: str = "zh",
    ):
        super().__init__()
        self.model = WhisperModel(
            model,
            device=device,
            compute_type=compute_type,
            cpu_threads=4,
        )
        self.language = language
        self.audio_buffer = bytearray()
        self.last_transcribe_time = 0

    async def run_stt(self, audio: bytes):
        """每 ~500ms 触发一次转录"""
        self.audio_buffer.extend(audio)

        # 每 500ms 触发(凑够够 8000 samples * 2 bytes = 16000 bytes 的 16kHz)
        if len(self.audio_buffer) < 16000:
            return

        chunk = bytes(self.audio_buffer)
        self.audio_buffer = bytearray()

        # 转 numpy
        import numpy as np
        audio_np = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0

        segments, info = self.model.transcribe(
            audio_np,
            language=self.language,
            beam_size=1,    # 速度优先
            vad_filter=False,  # VAD 已在上游
            without_timestamps=True,
        )

        for seg in segments:
            yield TranscriptionFrame(
                text=seg.text,
                user_id="caller",
                timestamp=seg.start,
            )
```

#### 8.1.3 启动时硬件探测(Codex Issue #10)

```python
# voice_worker/src/voice_worker/services/__init__.py
import torch
import logging

def select_stt_config():
    """根据 GPU 选择最佳 STT 配置"""
    if torch.cuda.is_available():
        vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        if vram_gb >= 8:
            return {"model": "large-v3", "device": "cuda", "compute_type": "float16"}
        elif vram_gb >= 4:
            return {"model": "small", "device": "cuda", "compute_type": "int8"}
        else:
            logging.warning("GPU VRAM < 4GB, falling back to CPU")
            return {"model": "small", "device": "cpu", "compute_type": "int8"}
    else:
        # 退到 CPU,模型再小
        return {"model": "base", "device": "cpu", "compute_type": "int8"}
```

#### 8.1.4 8kHz 输入处理

PJSIP 收到的是 8kHz PCMA → 解码为 8kHz PCM int16 → **必须重采样到 16kHz** 才能给 Whisper:

```python
# voice_worker/src/voice_worker/transports/resampler.py
import soxr

class Resampler:
    def __init__(self, src_rate: int, dst_rate: int):
        self.src_rate = src_rate
        self.dst_rate = dst_rate

    def resample(self, pcm_int16: bytes) -> bytes:
        import numpy as np
        audio = np.frombuffer(pcm_int16, dtype=np.int16)
        resampled = soxr.resample(
            audio.astype(np.float32),
            self.src_rate,
            self.dst_rate,
            quality="HQ",  # 中文识别优先质量
        )
        return resampled.astype(np.int16).tobytes()
```

**重要警告**(Codex Issue #2):8k → 16k 是"假升采样",拿不回信息,主要作用是模型兼容。中文 STT 准确率仍按 8kHz 评估,~83-88%。

### 8.2 Piper(TTS)

#### 8.2.1 选型理由

- 全本地 CPU 推理,不占 GPU
- 中文有 `huayan` 模型(女声)
- 英文 `en_US-amy-medium`(场景 4 用)

#### 8.2.2 集成

```python
# voice_worker/src/voice_worker/services/piper_tts.py
import subprocess
import asyncio
from pipecat.services.tts_service import TTSService
from pipecat.frames.frames import OutputAudioRawFrame, TTSStartedFrame, TTSStoppedFrame


class PiperTTSService(TTSService):
    def __init__(
        self,
        voice: str = "zh_CN-huayan-medium",
        model_path: str = "/models/piper",
        sample_rate: int = 22050,
    ):
        super().__init__()
        self.voice = voice
        self.model_path = f"{model_path}/{voice}.onnx"
        self.config_path = f"{model_path}/{voice}.onnx.json"
        self.sample_rate = sample_rate

    async def run_tts(self, text: str):
        yield TTSStartedFrame()
        # 调 piper CLI(子进程)
        proc = await asyncio.create_subprocess_exec(
            "piper",
            "--model", self.model_path,
            "--config", self.config_path,
            "--output_raw",  # 输出 raw PCM int16
            "--length_scale", "1.1",  # 中文稍慢
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
        )
        proc.stdin.write(text.encode("utf-8"))
        await proc.stdin.drain()
        proc.stdin.close()

        # 流式读取 PCM
        chunk_size = 1024
        while True:
            chunk = await proc.stdout.read(chunk_size)
            if not chunk:
                break
            yield OutputAudioRawFrame(
                audio=chunk,
                sample_rate=self.sample_rate,
                num_channels=1,
            )

        await proc.wait()
        yield TTSStoppedFrame()
```

#### 8.2.3 句子分割(中文标点)

```python
# voice_worker/src/voice_worker/services/sentence_aggregator.py
import re

CHINESE_PUNCT = re.compile(r"[。!?;]|[.!?;]")

def split_sentences(text: str) -> list[str]:
    """按中文+英文标点切句,送入 TTS"""
    sentences = CHINESE_PUNCT.split(text)
    # 重新加回标点(简化版:都加句号)
    return [s.strip() + "。" for s in sentences if s.strip()]
```

### 8.3 演示日双保险:TTSReplayService

```python
# voice_worker/src/voice_worker/services/tts_replay.py
import json
from pathlib import Path
from pipecat.services.tts_service import TTSService

class TTSReplayService(TTSService):
    """
    Demo 日替代 Piper:根据脚本预渲染音频文件回放
    避免 demo 现场依赖外部 TTS 服务
    """
    def __init__(self, script_path: str = "scripts/demo_tts_script.json",
                 audio_dir: str = "scripts/demo_tts_audio/"):
        super().__init__()
        with open(script_path, "r", encoding="utf-8") as f:
            self.script = json.load(f)  # {text: filename}
        self.audio_dir = Path(audio_dir)

    async def run_tts(self, text: str):
        # 找匹配的预录文件,fallback 到 piper
        normalized = text.strip()
        if normalized in self.script:
            audio_file = self.audio_dir / self.script[normalized]
            with open(audio_file, "rb") as f:
                yield OutputAudioRawFrame(
                    audio=f.read(),
                    sample_rate=22050,
                    num_channels=1,
                )
        else:
            # fallback 到真正的 Piper(罕见情况)
            from voice_worker.services.piper_tts import PiperTTSService
            piper = PiperTTSService()
            async for frame in piper.run_tts(text):
                yield frame
```

### 8.4 模型文件管理

```bash
# 启动前一次性下载
mkdir -p models/piper
cd models/piper
# 中文
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json
# 英文(场景 4)
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json

# faster-whisper small 在第一次启动时自动下载到 ~/.cache/huggingface
# 或用 huggingface-cli download Systran/faster-whisper-small 提前下
```

`.gitignore` 必须加:
```
models/
*.onnx
*.bin
```

---

## 9. DeepSeek-V3 集成与 Function Calling 防御性设计

### 9.1 DeepSeek 客户端

```python
# voice_worker/src/voice_worker/services/deepseek_llm.py
import os
import json
from openai import AsyncOpenAI
from pipecat.services.llm_service import LLMService
from pipecat.frames.frames import (
    LLMFullResponseStartFrame, LLMFullResponseEndFrame,
    TextFrame, FunctionCallParams, FunctionCallResultProperties,
)

class DeepSeekLLMService(LLMService):
    """
    DeepSeek-V3 通过 OpenAI 兼容 API 集成
    """
    def __init__(
        self,
        api_key: str = None,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com/v1",
        timeout: float = 8.0,
    ):
        super().__init__()
        self.client = AsyncOpenAI(
            api_key=api_key or os.getenv("DEEPSEEK_API_KEY"),
            base_url=base_url,
            timeout=timeout,
        )
        self.model = model
        self.tools_registry = {}

    def register_tool(self, name: str, schema: dict, handler):
        self.tools_registry[name] = {"schema": schema, "handler": handler}

    async def process_context(self, context):
        """流式调用 + Function Calling"""
        try:
            tool_schemas = [v["schema"] for v in self.tools_registry.values()]
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=context.messages,
                tools=tool_schemas if tool_schemas else None,
                stream=True,
            )

            yield LLMFullResponseStartFrame()
            current_tool_call = None
            async for chunk in stream:
                delta = chunk.choices[0].delta

                # 文本 token
                if delta.content:
                    yield TextFrame(text=delta.content)

                # Function Call(可能跨多个 chunk 拼接)
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.function and tc.function.name:
                            current_tool_call = {
                                "name": tc.function.name,
                                "arguments": "",
                                "id": tc.id,
                            }
                        if tc.function and tc.function.arguments:
                            current_tool_call["arguments"] += tc.function.arguments

            # Tool 执行
            if current_tool_call:
                yield await self._execute_tool(current_tool_call)

            yield LLMFullResponseEndFrame()

        except asyncio.TimeoutError:
            # 降级:回退到固定话术
            metrics.inc("deepseek_timeout")
            yield TextFrame(text=FALLBACK_RESPONSE)
            yield LLMFullResponseEndFrame()

    async def _execute_tool(self, call):
        """执行工具,带 Pydantic 校验"""
        try:
            args = json.loads(call["arguments"])
            tool = self.tools_registry[call["name"]]
            # Pydantic 校验
            from pydantic import BaseModel
            schema_cls = tool["schema"].get("pydantic_model")
            if schema_cls:
                validated = schema_cls(**args)
                args = validated.dict()
            result = await tool["handler"](**args)
            return FunctionCallResultProperties(
                call_id=call["id"],
                name=call["name"],
                result=json.dumps(result, ensure_ascii=False),
            )
        except Exception as e:
            logger.exception(f"Tool {call['name']} failed: {e}")
            return FunctionCallResultProperties(
                call_id=call["id"],
                name=call["name"],
                result=json.dumps({"error": str(e)}),
            )
```

### 9.2 Tool 定义(以 calculate_cost 为例)

```python
# voice_worker/src/voice_worker/tools/calculate_cost.py
from pydantic import BaseModel, Field

class CalculateCostInput(BaseModel):
    plan: str = Field(..., description="目标套餐 ID,如 '199_basic'")
    monthly_data_gb: float = Field(..., gt=0, le=1000)
    monthly_voice_min: int = Field(..., ge=0, le=10000)

PLAN_RATES = {
    "199_basic": {"base": 199, "data_quota_gb": 30, "data_overage_per_gb": 3,
                  "voice_quota_min": 300, "voice_overage_per_min": 0.15},
    "399_premium": {"base": 399, "data_quota_gb": 100, "data_overage_per_gb": 0,
                    "voice_quota_min": 1000, "voice_overage_per_min": 0},
}

async def calculate_cost(plan: str, monthly_data_gb: float,
                         monthly_voice_min: int) -> dict:
    rate = PLAN_RATES.get(plan)
    if not rate:
        return {"error": f"Unknown plan: {plan}"}

    data_overage = max(0, monthly_data_gb - rate["data_quota_gb"])
    data_overage_cost = data_overage * rate["data_overage_per_gb"]

    voice_overage = max(0, monthly_voice_min - rate["voice_quota_min"])
    voice_overage_cost = voice_overage * rate["voice_overage_per_min"]

    total = rate["base"] + data_overage_cost + voice_overage_cost

    return {
        "plan": plan,
        "base_cost": rate["base"],
        "data_overage_gb": data_overage,
        "data_overage_cost": round(data_overage_cost, 2),
        "voice_overage_min": voice_overage,
        "voice_overage_cost": round(voice_overage_cost, 2),
        "total": round(total, 2),
    }


# Tool schema(注册到 DeepSeekLLMService)
CALCULATE_COST_SCHEMA = {
    "type": "function",
    "function": {
        "name": "calculate_actual_cost",
        "description": "根据用户实际使用量,计算切换到指定套餐后的真实月度费用,包含超出部分。",
        "parameters": {
            "type": "object",
            "properties": {
                "plan": {"type": "string"},
                "monthly_data_gb": {"type": "number"},
                "monthly_voice_min": {"type": "integer"},
            },
            "required": ["plan", "monthly_data_gb", "monthly_voice_min"],
        },
        "pydantic_model": CalculateCostInput,  # 自定义扩展
    }
}
```

### 9.3 LLM 只润色,数字代码渲染(Codex Issue #21)

```python
# voice_worker/src/voice_worker/flows/s2_retention.py
RETENTION_NODE = NodeConfig(
    name="propose_alternative",
    role_message="你是中国移动的客服代表,语气温和、专业、耐心。",
    task_messages=[
        {
            "role": "system",
            "content": """
你刚刚为用户算出了切换套餐后的实际成本(由 calculate_actual_cost 工具返回)。

【重要规则】
- 你必须使用工具返回的【精确数字】,严禁自己计算或估算
- 数字的呈现格式必须保留人民币符号 ¥,保留 2 位小数
- 不要做任何与 Tool 返回数据不一致的描述

【话术模板】(填入工具返回的数字):
"张先生,我帮您算一下:
您每月平均流量 {monthly_data_gb}G,通话 {monthly_voice_min} 分钟。
如果降到 {plan} 套餐,流量超出按 ¥{data_overage_per_gb}/GB 计费,
大约 ¥{data_overage_cost};通话超出按 ¥{voice_overage_per_min}/分钟,
大约 ¥{voice_overage_cost};加上套餐费 ¥{base_cost},
实际花费会到 ¥{total} 左右。"
            """,
        }
    ],
    functions=[CALCULATE_COST_SCHEMA, APPLY_OFFER_SCHEMA],
)
```

### 9.4 降级策略

```python
# voice_worker/src/voice_worker/services/deepseek_llm.py(节选)
FALLBACK_RESPONSE = """
非常抱歉,系统暂时繁忙,请您稍等片刻,
或者按 0 转人工客服,我们将尽快为您服务。
"""

# DeepSeek API 失败 → 降级行为:
# 1. 立即播放 FALLBACK_RESPONSE
# 2. 自动触发 bot_handoff(reason="llm_unavailable")
# 3. 不让 Demo 完全崩
```

### 9.5 验收标准

- 算账正确性:100 次调用 calculate_cost,数字与 Python 直接计算 100% 一致
- 流式延迟:首 token 延迟 P50 < 500ms,P99 < 1500ms
- 超时降级:模拟 8s 卡死,自动播放 fallback 并触发 handoff
- 中文字符正确:输出无乱码,无英文夹杂

---

## 10. 数据库初始化与种子数据

### 10.1 初始化流程

```bash
# 1. 启动 postgres
docker compose up -d postgres

# 2. 等待 ready
docker compose exec postgres pg_isready -U aicc

# 3. 跑 migration
cd core && alembic upgrade head

# 4. 灌种子
python scripts/seed_data.py

# 5. 验证
docker compose exec postgres psql -U aicc aicc_lite -c \
  "SELECT id, name, phone FROM contacts;"
# 应该看到:1 | 张先生 | 138xxxxxxxx
```

### 10.2 种子数据完整版

```python
# scripts/seed_data.py
"""
预埋张先生 138xxxxxxxx + 4 场景所有 Mock 状态
"""
import asyncio
import secrets
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from passlib.hash import bcrypt

from aicc_core.config import settings
from aicc_core.db.models import (
    Account, User, Contact, ContactInbox,
    Inbox, ChannelWebWidget, ChannelVoice,
    AgentBot, AgentBotInbox, MockScenarioState,
)


async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession,
                                  expire_on_commit=False)

    async with async_session() as s:
        # ============================================================
        # 1. Account
        # ============================================================
        account = Account(id=1, name="AICC-Lite Demo")
        s.add(account)
        await s.flush()

        # ============================================================
        # 2. Users(坐席)
        # ============================================================
        admin = User(
            id=1,
            account_id=1,
            email="admin@aicc.local",
            name="管理员",
            role="admin",
            pubsub_token=secrets.token_urlsafe(32),
            password_hash=bcrypt.hash("admin123"),
        )
        agent = User(
            id=2,
            account_id=1,
            email="agent1@aicc.local",
            name="客服小李",
            role="agent",
            pubsub_token=secrets.token_urlsafe(32),
            password_hash=bcrypt.hash("agent123"),
        )
        s.add_all([admin, agent])

        # ============================================================
        # 3. Inboxes(Polymorphic Channel)
        # ============================================================
        # 3a. Voice channel
        voice_chan = ChannelVoice(
            id=1,
            sip_endpoint="sip:1001@127.0.0.1",
            twilio_number=None,  # Phase 6 启用
            feature_flags={"enable_twilio": False},
        )
        s.add(voice_chan)
        await s.flush()

        voice_inbox = Inbox(
            id=1,
            account_id=1,
            name="语音热线",
            channel_type="Channel::Voice",
            channel_id=1,
        )
        s.add(voice_inbox)

        # 3b. Web Widget channel
        web_chan = ChannelWebWidget(
            id=1,
            website_token="demo_web_widget_token",
            widget_color="#1f93ff",
            welcome_title="您好,我是 AICC-Lite 智能客服",
            welcome_tagline="有任何问题请告诉我,我会立刻为您处理",
        )
        s.add(web_chan)
        await s.flush()

        web_inbox = Inbox(
            id=2,
            account_id=1,
            name="Web Widget",
            channel_type="Channel::WebWidget",
            channel_id=1,
        )
        s.add(web_inbox)

        # ============================================================
        # 4. AgentBot(Voice Worker)
        # ============================================================
        voice_bot = AgentBot(
            id=1,
            account_id=1,
            name="Voice Worker (Pipecat)",
            outgoing_url="http://voice-worker:9000/internal/bot/event",
            access_token=secrets.token_urlsafe(32),
            signing_secret=secrets.token_urlsafe(32),
        )
        s.add(voice_bot)
        await s.flush()
        s.add(AgentBotInbox(agent_bot_id=1, inbox_id=1))

        # ============================================================
        # 5. Contact(张先生)+ ContactInbox(跨渠道身份)
        # ============================================================
        contact = Contact(
            id=1,
            account_id=1,
            name="张先生",
            phone="138xxxxxxxx",  # 实际写真号
            email="zhang@example.com",
            custom_attributes={
                "tier": "loyal_3yr",
                "current_plan": "399_premium",
                "registration_date": "2023-03-15",
                "preferred_language": "zh",
            },
        )
        s.add(contact)
        await s.flush()

        # Voice Inbox 身份
        s.add(ContactInbox(
            contact_id=1, inbox_id=1,
            source_id="138xxxxxxxx",
            pubsub_token=secrets.token_urlsafe(32),
        ))
        # Web Widget Inbox 身份
        s.add(ContactInbox(
            contact_id=1, inbox_id=2,
            source_id="cookie_demo_zhang_001",
            pubsub_token="demo_widget_pubsub_token",  # demo 固定值方便演示
        ))

        # ============================================================
        # 6. Mock Scenario States(4 场景隔离)
        # ============================================================
        scenarios = [
            # ========== S1: 网速诊断 ==========
            {
                "phone": "138xxxxxxxx",
                "scenario_id": "s1",
                "state": {
                    "diagnosis": {
                        "base_station": "BS-008",
                        "load_percent": 87,
                        "signal_strength_dbm": -98,
                        "issue_type": "cell_congestion",
                        "fix_eta_minutes": 30,
                        "neighboring_users_affected": 234,
                    },
                    "compensation": {
                        "data_voucher_mb": 10240,
                        "voucher_id": "VCH-S1-DEMO-001",
                    }
                }
            },
            # ========== S2: 套餐挽留 ==========
            {
                "phone": "138xxxxxxxx",
                "scenario_id": "s2",
                "state": {
                    "usage": {
                        "monthly_data_gb": 68,
                        "monthly_voice_minutes": 480,
                        "device_count": 4,
                        "top_apps": ["腾讯会议", "微信视频", "B站", "网易云"],
                        "peak_hours": ["09:00-12:00", "20:00-23:00"],
                    },
                    "available_offers": [
                        {
                            "id": "loyal_3yr_v1",
                            "discount": 0.9,
                            "new_monthly_cost": 359,
                            "bonus": "家庭宽带提速 500M / 6 个月",
                            "valid_for_months": 12,
                        }
                    ],
                    "alternative_plans": [
                        {"id": "199_basic", "name": "199 基础版"},
                        {"id": "299_standard", "name": "299 标准版"},
                        {"id": "399_premium", "name": "399 尊享版(当前)"},
                    ]
                }
            },
            # ========== S3: 投诉(无特殊数据,触发 handoff) ==========
            {
                "phone": "138xxxxxxxx",
                "scenario_id": "s3",
                "state": {
                    "previous_complaints": [
                        {
                            "ticket_id": "WO-20260601-077",
                            "issue": "网速持续慢",
                            "status": "supposedly_resolved",
                            "actual_resolved": False,
                        }
                    ],
                    "ai_handoff_summary": "客户因之前 WO-20260601-077 工单未解决而投诉,情绪激动,建议优先处理",
                    "suggested_agent_response": "先共情,致歉,确认问题,提供升级方案"
                }
            },
            # ========== S4: 翻译 ==========
            {
                "phone": "138xxxxxxxx",
                "scenario_id": "s4",
                "state": {
                    "callee": {
                        "name": "Ahmed Al-Rashid",
                        "phone": "+966-50-xxxxxxx",
                        "language": "en",
                        "company": "Saudi Logistics Co.",
                    },
                    "context": "上次合同付款条款讨论",
                    "prerecorded_responses": [
                        "ahmed_greeting.wav",
                        "ahmed_payment_response.wav",
                        "ahmed_farewell.wav",
                    ]
                }
            },
        ]

        for sc in scenarios:
            s.add(MockScenarioState(**sc))

        await s.commit()

        print("✅ Seed data loaded:")
        print(f"   Account: {account.name}")
        print(f"   Users: admin@aicc.local / admin123, agent1@aicc.local / agent123")
        print(f"   Web Widget Token: {web_chan.website_token}")
        print(f"   Demo Contact: 张先生 (phone={contact.phone})")
        print(f"   Bot Access Token: {voice_bot.access_token}")
        print(f"   ⚠️  把以下值写入 .env:")
        print(f"   BOT_ACCESS_TOKEN={voice_bot.access_token}")
        print(f"   BOT_SIGNING_SECRET={voice_bot.signing_secret}")


if __name__ == "__main__":
    asyncio.run(main())
```

### 10.3 一键 Reset

```python
# scripts/reset_demo.py
"""每次 demo 前一键重置数据库到种子状态"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from aicc_core.config import settings

async def reset():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        # 删除所有 conversation/message,保留种子数据
        await conn.execute(text("TRUNCATE messages, conversations, "
                                "webhook_idempotency RESTART IDENTITY CASCADE"))
    print("✅ Demo data reset")

if __name__ == "__main__":
    asyncio.run(reset())
```

---

## 11. Docker Compose 配置 + GitHub Actions CI/CD

### 11.1 docker-compose.yml(生产模式,GHCR pull)

```yaml
# docker-compose.yml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: aicc
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-aicc_dev}
      POSTGRES_DB: aicc_lite
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U aicc"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "127.0.0.1:6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]

  pjsip-server:
    image: ghcr.io/<your_user>/aicc-lite-pjsip:latest
    network_mode: host  # SIP/RTP 需要可控端口范围
    environment:
      - VOICE_WORKER_URL=http://localhost:9000
    depends_on:
      - aicc-core

  voice-worker:
    image: ghcr.io/<your_user>/aicc-lite-voice-worker:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - AICC_CORE_URL=http://aicc-core:8000
      - BOT_ACCESS_TOKEN=${BOT_ACCESS_TOKEN}
      - BOT_SIGNING_SECRET=${BOT_SIGNING_SECRET}
    volumes:
      - ./models:/models:ro
    ports:
      - "127.0.0.1:9000:9000"
    depends_on:
      - aicc-core

  aicc-core:
    image: ghcr.io/<your_user>/aicc-lite-core:latest
    environment:
      - DATABASE_URL=postgresql+asyncpg://aicc:${POSTGRES_PASSWORD:-aicc_dev}@postgres/aicc_lite
      - REDIS_URL=redis://redis:6379
      - DEEPSEEK_API_KEY_CAPTAIN=${DEEPSEEK_API_KEY_CAPTAIN}
      - SECRET_KEY=${SECRET_KEY}
    ports:
      - "127.0.0.1:8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  frontend:
    image: ghcr.io/<your_user>/aicc-lite-frontend:latest
    ports:
      - "127.0.0.1:8080:80"
    depends_on:
      - aicc-core

  sngrep:
    image: irontec/sngrep:latest
    network_mode: host
    profiles: ["debug"]  # docker compose --profile debug up

volumes:
  postgres_data:
```

### 11.2 docker-compose.dev.yml(开发覆盖)

```yaml
# docker-compose.dev.yml
# 用法:docker compose -f docker-compose.yml -f docker-compose.dev.yml up
version: "3.9"

services:
  aicc-core:
    build:
      context: ./core
      dockerfile: Dockerfile
    volumes:
      - ./core/src:/app/src  # hot reload
    command: uvicorn aicc_core.main:app --reload --host 0.0.0.0

  voice-worker:
    build:
      context: ./voice_worker
      dockerfile: Dockerfile
    volumes:
      - ./voice_worker/src:/app/src

  pjsip-server:
    build:
      context: ./pjsip_server
      dockerfile: Dockerfile

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    volumes:
      - ./frontend/src:/app/src
    command: npm run dev
```

### 11.3 .env.example

```bash
# .env.example
# 拷贝为 .env 并填入实际值,.env 不要提交

# ============== Required ==============
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx  # 主管线 LLM
DEEPSEEK_API_KEY_CAPTAIN=sk-xxxxxxxxxxxxxxxxxxxx  # Captain 独立 key

# 由 seed_data.py 生成,首次跑后写入
BOT_ACCESS_TOKEN=
BOT_SIGNING_SECRET=

# Postgres
POSTGRES_PASSWORD=aicc_dev_password

# FastAPI session
SECRET_KEY=  # python -c "import secrets; print(secrets.token_urlsafe(32))"

# ============== Optional ==============
# Phase 6 启用 Twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_NUMBER=
ENABLE_TWILIO=false

# 可观测
LOG_LEVEL=INFO
JAEGER_ENDPOINT=  # 留空禁用
```

### 11.4 GitHub Actions:PJSIP 镜像构建

```yaml
# .github/workflows/build-pjsip.yml
name: Build PJSIP Image
on:
  push:
    branches: [main]
    paths: ['pjsip_server/**']
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: pjsip_server
          push: true
          tags: |
            ghcr.io/${{ github.repository_owner }}/aicc-lite-pjsip:latest
            ghcr.io/${{ github.repository_owner }}/aicc-lite-pjsip:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64
```

### 11.5 GitHub Actions:CI

```yaml
# .github/workflows/ci-core.yml
name: CI Core
on:
  push:
    paths: ['core/**']
  pull_request:
    paths: ['core/**']

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: aicc
          POSTGRES_PASSWORD: test
          POSTGRES_DB: aicc_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install
        run: |
          cd core
          pip install -e ".[dev]"

      - name: Lint
        run: |
          cd core
          ruff check src tests
          mypy src

      - name: Test
        env:
          DATABASE_URL: postgresql+asyncpg://aicc:test@localhost/aicc_test
          REDIS_URL: redis://localhost:6379
        run: |
          cd core
          alembic upgrade head
          pytest --cov=src --cov-report=xml
```

### 11.6 PJSIP Dockerfile(预构建,multi-stage)

```dockerfile
# pjsip_server/Dockerfile
# Stage 1: 编译 PJSIP
FROM debian:bookworm-slim AS pjsip-builder

ARG PJSIP_VERSION=2.13

RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev python3-pip python3-setuptools \
    swig \
    libssl-dev \
    libasound2-dev \
    libopus-dev \
    pkg-config \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN wget https://github.com/pjsip/pjproject/archive/refs/tags/${PJSIP_VERSION}.tar.gz \
    && tar xzf ${PJSIP_VERSION}.tar.gz \
    && mv pjproject-${PJSIP_VERSION} pjproject

WORKDIR /build/pjproject
RUN ./configure --enable-shared --disable-video \
    && make dep && make && make install \
    && cd pjsip-apps/src/swig && make python && make install \
    && ldconfig

# Stage 2: 运行时
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    libssl3 libasound2 libopus0 \
    && rm -rf /var/lib/apt/lists/*

# 拷贝 PJSIP 编译产物
COPY --from=pjsip-builder /usr/local/lib /usr/local/lib
COPY --from=pjsip-builder /usr/local/include /usr/local/include
COPY --from=pjsip-builder /usr/local/lib/python*/dist-packages/pjsua2.py \
                          /usr/local/lib/python3.11/dist-packages/pjsua2.py
COPY --from=pjsip-builder /usr/local/lib/python*/dist-packages/_pjsua2*.so \
                          /usr/local/lib/python3.11/dist-packages/

RUN ldconfig

WORKDIR /app
COPY pyproject.toml .
COPY src ./src
RUN pip install -e .

EXPOSE 5060/udp
EXPOSE 10000-10100/udp

CMD ["python", "-m", "pjsip_server.server"]
```

---

## 12. Windows 11 + WSL2 + NVIDIA 环境配置

### 12.1 一次性安装清单(初次配置约 30-60 分钟)

#### 12.1.1 Windows 11 主机

| 软件 | 版本 | 安装方式 |
|---|---|---|
| Docker Desktop | 4.28+(WSL2 backend) | 官网下载 .exe |
| WSL2 + Ubuntu 22.04 | 最新 | `wsl --install -d Ubuntu-22.04` |
| NVIDIA Driver(主机) | 535+ | NVIDIA 官网下载 |
| Linphone Desktop | 5.2+ | linphone.org 下载 |
| Git for Windows | 最新 | gitforwindows.org |
| VSCode + WSL extension | 最新 | 用于跨 WSL 开发 |

#### 12.1.2 WSL2 内安装

```bash
# WSL2 Ubuntu 内
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git build-essential

# NVIDIA Container Toolkit
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update && sudo apt install -y nvidia-container-toolkit

# Docker 配置 NVIDIA runtime(Docker Desktop 已默认支持,只需重启)
```

#### 12.1.3 验证 GPU

```bash
# WSL2 内
nvidia-smi  # 应该看到 Quadro P1000

# Docker GPU 验证
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
# 应该看到 P1000
```

### 12.2 Linphone 桌面预配置

```ini
# scripts/linphone_provisioning.lpconfig
# 复制到 Linphone:文件→偏好→网络→Provisioning
# 或直接拷贝到 %appdata%/Linphone/linphonerc

[sip]
sip_port=5062
default_proxy=0
register_only_when_network_is_up=1

[proxy_0]
reg_proxy=<sip:127.0.0.1:5060;transport=udp>
reg_route=<sip:127.0.0.1:5060;transport=udp>
reg_identity=sip:1001@127.0.0.1
reg_expires=600
reg_sendregister=0  # 不要主动注册

[net]
mtu=1300
firewall_policy=0  # No firewall
stun_server=

[sound]
playback_dev_id=...  # 选你的扬声器
ringer_dev_id=...
capture_dev_id=...   # 选你的麦克风

[video]
display=0
capture=0

# 关键:Codec 配置
[audio_codec_0]
mime=PCMA
rate=8000
channels=1
enabled=1

[audio_codec_1]
mime=PCMU
rate=8000
channels=1
enabled=0  # 禁用

[audio_codec_2]
mime=opus
rate=48000
channels=1
enabled=0  # 禁用(v2.5 ①A 决策)
```

### 12.3 启动顺序(每次开发)

```powershell
# Windows PowerShell
# 1. 启 Docker Desktop(自动启动 WSL2)
# 2. 进 WSL2
wsl

# WSL2 内
cd /mnt/c/work/aicc-lite  # 或 ~/aicc-lite
git pull

# 3. 拉镜像(GHCR)
docker compose pull

# 4. 启动
docker compose up -d

# 5. 看日志
docker compose logs -f voice-worker

# 6. 浏览器打开
# http://localhost:8080  (坐席工作台)
# http://localhost:8000/docs  (API 文档)

# 7. Linphone 桌面 → 拨号 1001@127.0.0.1
```

### 12.4 常见问题

| 问题 | 原因 | 解决 |
|---|---|---|
| Docker 启动慢 | WSL2 cold start | 第一次启动慢正常,后续 < 30s |
| GPU not found in container | NVIDIA Container Toolkit 没装 | 见 12.1.2 |
| PJSIP 容器 startup OOM | WSL2 默认内存只 50% | `~/.wslconfig` 加 `memory=24GB` |
| Linphone 注册失败 | reg_sendregister=1 | 改为 0(不主动注册) |
| 麦克风无声 | Windows 隐私设置阻止 | 设置→隐私→麦克风→允许 Linphone |

---

## 13. 测试策略与准入门槛

### 13.1 测试金字塔

```
        E2E (10%)
       ┌─────────┐
      ┌─ Phase Demo ─┐
     ┌── Soak Test ──┐
    ┌── Integration ──┐    (30%)
   ┌── Unit ──────────┐    (60%)
```

### 13.2 单元测试(Phase 1 必须建立)

```bash
# core/
pytest --cov=src --cov-fail-under=70

# voice_worker/
pytest --cov=src --cov-fail-under=60  # 含 PJSIP 部分覆盖率较低正常

# frontend/
npm run test
```

### 13.3 集成测试

| 测试 | 用什么模拟 | 验证 |
|---|---|---|
| WebWidget 全流程 | httpx 模拟 widget JS SDK | 创建 conversation → 收消息 → 分配 |
| Bot Webhook 协议 | aiohttp 起一个 mock bot server | 签名 / 重试 / handoff |
| PJSIP transport | SIPp + 录音 wav 文件 | 200 OK / SDP / RTP 收发 |
| 状态机并发 | asyncio.gather 100 个 transition | 1 成功 99 失败 |

### 13.4 Soak Test(Phase 4 准入)

```python
# scripts/soak_test.py
"""
模拟 200 次自动呼入挂断 + 2 小时连续运行
监控:RSS、PJSIP pool、线程数、FD 数
"""
import asyncio
import psutil
import subprocess

async def run_one_call():
    # 用 SIPp 发起一次呼叫
    proc = await asyncio.create_subprocess_exec(
        "sipp",
        "-sf", "references/sipp_scenarios/happy_path_inbound.xml",
        "-s", "1001",
        "127.0.0.1:5060",
        "-r", "1", "-m", "1",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()


async def soak():
    # 找到 voice-worker 进程
    target_pid = None
    for p in psutil.process_iter(["pid", "name"]):
        if "voice_worker" in p.info["name"].lower():
            target_pid = p.info["pid"]
            break
    proc = psutil.Process(target_pid)

    initial_rss = proc.memory_info().rss
    initial_threads = proc.num_threads()
    initial_fds = proc.num_fds()

    print(f"Initial: RSS={initial_rss/1e6:.1f}MB, "
          f"threads={initial_threads}, fds={initial_fds}")

    for i in range(200):
        await run_one_call()
        await asyncio.sleep(2)  # 通话间隔

        if (i + 1) % 50 == 0:
            current = proc.memory_info().rss
            growth_pct = (current - initial_rss) / initial_rss * 100
            print(f"After {i+1} calls: RSS={current/1e6:.1f}MB "
                  f"({growth_pct:+.1f}%), "
                  f"threads={proc.num_threads()}, "
                  f"fds={proc.num_fds()}")

    final_rss = proc.memory_info().rss
    growth = (final_rss - initial_rss) / initial_rss * 100
    assert growth < 5, f"Memory growth {growth:.1f}% exceeds 5% threshold"
    print(f"✅ Soak test passed: RSS growth {growth:.1f}%")


if __name__ == "__main__":
    asyncio.run(soak())
```

### 13.5 Phase 准入门槛(`docs/PHASE_GATES.md` 完整版)

#### Phase 1 准入

- [ ] `pytest core/tests/` 全部通过,coverage > 70%
- [ ] `alembic upgrade head` 成功,种子数据加载完成
- [ ] WebWidget 浏览器端能发送一条消息,坐席端能收到
- [ ] 状态机并发测试(100 并发)1 成功 99 失败
- [ ] AgentBot HMAC 签名验证通过

#### Phase 2 准入

- [ ] PJSIP server 单独启动正常,sngrep 能看到注册
- [ ] SIPp `happy_path_inbound.xml` 跑通(200 OK + ACK + BYE)
- [ ] 桌面 Linphone 拨入,faster-whisper 能输出转录
- [ ] DeepSeek-V3 流式回复能完整 TTS 播放
- [ ] 转录回写 AICC Core,坐席端 WS 能收到
- [ ] S1 完整端到端跑通 5 次,成功率 100%
- [ ] 1 小时连续运行 RSS 增长 < 3%

#### Phase 3 准入

- [ ] S2 calculate_cost Tool 调用正确,数字 100% 准确
- [ ] S3 投诉触发 bot_handoff,坐席端叮咚响 < 2 秒
- [ ] 坐席接听后,WebSocket+PCM 桥接通,音频通畅
- [ ] 客户打断 → 坐席端 playback queue 立即清空 < 100ms
- [ ] Captain-Lite 在转人工时 5 秒内推送 AI 建议

#### Phase 4 准入

- [ ] S4 客户中文 → 英文 → 预录回放 → 中文 全链路通
- [ ] 翻译延迟单向 < 2.5s
- [ ] 200 次 soak test 通过(growth < 5%)
- [ ] 2 小时连续运行不崩
- [ ] 4 场景每个跑通 5 次,成功率 100%
- [ ] Vue 工作台所有按钮可用

#### Phase 5 准入(交付)

- [ ] README 包含:架构图、快速启动、demo 录屏链接
- [ ] Demo 录屏一气呵成 5 分钟无 NG
- [ ] 故障排查文档完整
- [ ] 演示彩排 3 次成功

---

## 14. Demo 演示剧本(完整脚本+故障预案)

### 14.1 演示前 60 分钟检查清单

```bash
# 60 分钟前
□ 检查所有容器健康
docker compose ps  # 全 healthy

□ 跑 preflight
python scripts/preflight.py
# 检查项:
# - DeepSeek API 可达 + 配额充足
# - PJSIP server 5060/udp 可达
# - faster-whisper 模型加载
# - Piper TTS 模型加载
# - 预录音频文件存在

□ Reset demo 数据
python scripts/reset_demo.py

□ 完整跑一次彩排(4 场景全演)

□ 关闭无关程序(浏览器、IDE 等)释放 GPU

□ 网络稳定:有线优先,如必须 WiFi 关掉手机热点等干扰源

□ Linphone 桌面端测试通话 1 次

□ 浏览器登录坐席工作台,确认通知音可用

# 30 分钟前
□ 把演示电脑屏幕 mirror 到大屏 / 投屏

□ 拿好备用方案:demo 录屏视频 / 备份 Linphone 实例

□ 喝水,清嗓

# 演示开始
```

### 14.2 完整脚本(已含在 1.3 节)

略,见第 1.3 节。

### 14.3 故障预案矩阵

| 故障类别 | 触发症状 | 即时操作 | 演示词 |
|---|---|---|---|
| **Linphone 不通** | 拨号无回应 5s | 切第二个 Linphone(已开) | "稍等,我换一台测试机" |
| **DeepSeek API 慢** | Bot 沉默 > 8s | 自动降级触发 | "AI 正在请求帮助……" |
| **STT 误识别** | Bot 答非所问 | 演示者重说 | "我重新说一下,网络刚才有点卡" |
| **WiFi 抖动** | RTP 丢包,Bot 听不清 | 切有线 | "稍等,我切换网络" |
| **GPU OOM** | voice-worker 报错 | `docker compose restart voice-worker` | "系统优化中,30 秒就好" |
| **完全跑不通** | 任何 critical fail | 播放预录视频 | "技术故障,我先放一段我们之前的录像" |

### 14.4 预录 demo 视频(必备)

- **录制工具**:OBS Studio
- **格式**:1920x1080 @ 30fps,H.264
- **长度**:5 分钟,与现场剧本完全一致
- **存储位置**:`docs/demo/aicc-lite-demo-v3.mp4`
- **README 链接**:在 README 顶部嵌入

---

## 15. 给 Claude Code 的分 Phase 实施任务清单

### 15.1 任务卡格式

每个任务卡用这个模板,直接喂给 Claude Code:

```
[Task ID]: P1-T01
[Phase]: 1
[Module]: core/conversations
[标题]: 实现 Conversation 状态机服务

[背景]: 见 AICC-Lite v3 文档第 5.2 章

[任务描述]:
实现 ConversationService.transition_status 方法,严格遵守:
- DB 事务 + advisory lock
- version CAS
- 状态机白名单(VALID_TRANSITIONS)
- 失败抛 ConcurrentUpdateError / InvalidTransitionError

[约束文件](必读):
- docs/STATE_MACHINE.md
- docs/ADR/0006-conversation-state-machine.md

[禁止改动的文件]:
- core/src/aicc_core/db/models.py(本任务不动 schema)
- core/src/aicc_core/channels/*

[输出]:
- core/src/aicc_core/conversations/service.py
- core/src/aicc_core/conversations/state_machine.py
- core/tests/unit/test_state_machine.py

[验收标准]:
- pytest core/tests/unit/test_state_machine.py 全过
- 100 并发 transition 测试:1 成功 99 失败(ConcurrentUpdateError)
- 非法转换被 InvalidTransitionError 拒绝
- coverage > 90%

[预估代码量]: 200-300 行
```

### 15.2 Phase 1 任务清单(共 12 个任务)

```
P1-T01  Conversation 状态机服务                    [200-300 行]
P1-T02  SQLAlchemy ORM models 完整定义              [400-500 行]
P1-T03  Alembic migration 初始化                    [50 行]
P1-T04  Polymorphic Channel base + WebWidget 子类    [200-300 行]
P1-T05  Voice Channel + Api Channel 子类            [150-200 行]
P1-T06  AgentBot Webhook 协议(签名 + 派发)         [200-300 行]
P1-T07  Idempotency Key 实现(Redis + DB)           [100-150 行]
P1-T08  WebSocket Manager + Redis pub/sub           [200-300 行]
P1-T09  5 个 Mock API endpoints                     [200-300 行]
P1-T10  Captain-Lite Mock RAG + DeepSeek client     [200-300 行]
P1-T11  scripts/seed_data.py 完整种子               [150-200 行]
P1-T12  Phase 1 集成测试(WebWidget 全流程)         [200-300 行]
```

### 15.3 Phase 2 任务清单(共 10 个任务)

```
P2-T01  PJSIP Docker 镜像 multi-stage Dockerfile     [80 行]
P2-T02  PJSIPActor(单例 + 命令队列)                [300-400 行] ★高风险
P2-T03  PJSIPCallHandler + AICCAccount               [200-300 行] ★高风险
P2-T04  PJSIPTransport(Pipecat 接口)               [400-500 行] ★高风险
P2-T05  Resampler 8k↔16k                            [50-80 行]
P2-T06  faster-whisper STT Service                  [150-200 行]
P2-T07  Piper TTS Service                           [150-200 行]
P2-T08  DeepSeek LLM Service + Tool Call            [300-400 行]
P2-T09  Pipecat Flow s1_diagnosis(场景 1)          [200-300 行]
P2-T10  Phase 2 端到端集成 + sngrep 抓包验证        [50 行 + 验证]
```

### 15.4 Phase 3 任务清单(共 8 个任务)

```
P3-T01  Tool: calculate_cost                         [80-100 行]
P3-T02  Tool: create_ticket / grant_voucher         [80-100 行]
P3-T03  Tool: bot_handoff(触发 Conv 状态变更)      [80-100 行]
P3-T04  Pipecat Flow s2_retention                   [250-350 行]
P3-T05  Pipecat Flow s3_handoff                     [200-300 行]
P3-T06  WebSocket+PCM 音频桥(server 端)           [300-400 行]
P3-T07  Vue 组件:AnswerButton + AudioBridge       [300-400 行]
P3-T08  Phase 3 端到端集成测试                       [验证]
```

### 15.5 Phase 4 任务清单(共 10 个任务)

```
P4-T01  TTSReplayService                            [150-200 行]
P4-T02  TranslationBridgeTask 自定义 PipelineTask    [400-500 行] ★高复杂
P4-T03  Pipecat Flow s4_translation                 [300-400 行]
P4-T04  third_party_simulator(预录英文音频)        [50 行 + 音频文件]
P4-T05  Vue 组件:ConversationList + Detail         [400-500 行]
P4-T06  Vue 组件:TranscriptStream + AISuggestion   [300-400 行]
P4-T07  Vue 组件:CustomerProfile                   [200-300 行]
P4-T08  Soak Test 200 次呼入                         [验证]
P4-T09  SIP 安全加固(IP 白名单 + auth)            [100-150 行]
P4-T10  Phase 4 端到端集成测试(4 场景全跑)         [验证]
```

### 15.6 Phase 5 任务清单(共 5 个任务)

```
P5-T01  README.md 完整版                            [写文档]
P5-T02  docs/ 完整工程记忆文档                       [写文档]
P5-T03  Demo 录屏(OBS,5 分钟一气呵成)            [录制]
P5-T04  故障排查手册(附录 C)                      [写文档]
P5-T05  演示彩排 3 次                                [验证]
```

### 15.7 Phase 6(可选)任务清单

```
P6-T01  Twilio feature flag(Phase 6)                [200-300 行]
P6-T02  CosyVoice2 集成(替代 Piper,GPU 充足时)    [300-400 行]
P6-T03  Jaeger / OpenTelemetry 接入                  [100-150 行]
```

### 15.8 任务总计

```
Phase 1: 12 任务,~2300 行
Phase 2: 10 任务,~2200 行(含 PJSIP 高风险)
Phase 3:  8 任务,~1700 行
Phase 4: 10 任务,~2400 行
Phase 5:  5 任务,主要是文档
Phase 6:  3 任务,~700 行(可选)

总计:48 任务,~8600 行(主线 ~7900 行,可选 +700 行)
预估时间:7 周(主线)+ 0.5 周(可选)
```

### 15.9 任务执行节奏建议

每天 1-2 个任务,每个任务:
1. **开始**:把对应 5.x 章节 + 关联文档 + 任务卡喂给 Claude Code
2. **执行**:Claude Code 写代码,你 review
3. **验证**:跑测试,跑接口,看日志
4. **commit**:`git commit -m "feat(P1-T01): conversation state machine"`
5. **更新进度**:在 GitHub Project 板移动卡片

每周 5 个工作日 × 1.5 任务/天 = 7.5 任务/周
7 周 × 7.5 ≈ 52 任务,> 48 个主线任务 → 时间预算合理

---

## 附录 A:工程记忆文档全文

> 这部分内容应当作为独立 .md 文件放在仓库 `docs/` 目录,本附录是其内容汇总,供 AI 编码工具检索。

### A.1 docs/ADR/0001-pjsip-actor-thread-model.md

```markdown
# ADR 0001: PJSIP Actor 线程模型

## 状态:Accepted (2026-05)

## 背景
pjsua2 是 C++ 库的 Python 绑定,有自己的事件循环。Pipecat 是 Python asyncio。
两者直接混用会触发跨线程崩溃、Python GC 析构错乱、未注册线程断言。

## 决策
采用 Actor 模型:
1. PJSIP 跑在独立工作线程("PJSIP Actor"),持有 Endpoint 单例
2. asyncio 与 Actor 通过 thread-safe 命令队列通信
3. asyncio 端永远不持有 Call/Account/AudioMedia 对象引用
4. Actor → asyncio 的事件通过 asyncio.run_coroutine_threadsafe / call_soon_threadsafe

## 后果
- ✅ 消除跨线程崩溃
- ✅ 单 Endpoint 单例符合 PJSIP 进程模型
- ❌ 命令队列引入 ~1-5ms 延迟(可接受)
- ❌ 所有 PJSIP 操作必须包成命令,不能直接调

## 不变量
- `uaConfig.threadCnt = 0`(Python 必须)
- 跨线程进入 PJSIP API 必须 `pj_thread_register()`
```

### A.2 docs/ADR/0002-deepseek-as-sole-llm.md

```markdown
# ADR 0002: 单一 LLM 供应商(DeepSeek-V3)

## 状态:Accepted

## 背景
原方案场景 1/3 用本地 Ollama Qwen2.5-7B,场景 2 用 DeepSeek。
但 P1000 4GB VRAM 装不下 7B 量化模型 + STT 同时运行。

## 决策
所有 4 场景统一使用 DeepSeek-V3 API:
- 主管线 LLM:DEEPSEEK_API_KEY
- Captain-Lite:DEEPSEEK_API_KEY_CAPTAIN(独立 quota,避免争用)
- 翻译(场景 4):同样 DeepSeek 直接做翻译,不引入 NLLB

## 后果
- ✅ 简化架构:删 Ollama 容器,删 NLLB 容器
- ✅ P1000 GPU 全部留给 STT(faster-whisper small int8)
- ✅ 月成本可控(~¥30 demo 100 次)
- ❌ 网络依赖外部 API
- ❌ 数据隐私(demo 用户用假手机号)
```

### A.3 docs/ADR/0003-pcma-only-codec.md

```markdown
# ADR 0003: 只支持 PCMA codec

## 状态:Accepted (Codex Issue #2 后保守决策)

## 背景
原方案 Opus > G.722 > PCMA fallback。但:
- Linphone 移动端默认不开 Opus,配置出错率高
- G.722 默认禁用,demo 不可控

## 决策
全链路只支持 PCMA(8kHz),其他 codec 在 SDP 协商时拒绝。

## 后果
- ✅ Demo 极度稳定,codec 协商无意外
- ❌ STT 准确率从 16k 的 ~95% 降到 8k 的 ~83-88%
- → 缓解:演示者发音清晰、Bot 主动复述确认

## 验证
- Linphone 桌面/手机/iOS Linphone 都用 PCMA 一次成功率 100%
- SIPp 测试场景验证拒绝其他 codec 时 488
```

### A.4 docs/ADR/0004-websocket-pcm-vs-jssip.md

```markdown
# ADR 0004: 坐席接听用 WebSocket+PCM,不用 JsSIP

## 状态:Accepted (Codex Issue #12/#13 后)

## 背景
原方案坐席浏览器接听用 JsSIP+coturn。但:
- JsSIP 走 SIP-over-WebSocket+WebRTC,与本地 UDP/SIP PJSIP 不在同一信令面
- coturn 只管 WebRTC 媒体,不管 SIP 信令转换
- REFER 转移在 JsSIP/PJSIP 间不可直接工作,需要 PBX

## 决策
1. 删除 JsSIP / coturn / SIP REFER
2. 坐席浏览器通过 WebSocket 直接拿 PCM 流
3. PJSIP server 把音频"旁路"到 WebSocket(不再过 Pipecat pipeline)
4. 浏览器用 Web Audio API 播放 / 麦克风采集

## 后果
- ✅ 协议简化,删 ~500 行依赖
- ✅ 浏览器侧实现简单(~300 行 TypeScript)
- ❌ 坐席端没有完整 SIP 客户端能力(无法手动 hold/transfer)
- → demo 不需要这些能力
```

### A.5 docs/ADR/0005-mock-api-determinism.md

```markdown
# ADR 0005: Mock API 基于 phone+scenario_id 确定性

## 状态:Accepted

## 决策
所有 Mock API 入参带 (phone, scenario_id),返回值由数据库 MockScenarioState 表预定义。
- 同一 (phone, scenario_id) 多次调用返回相同结果
- 不同 scenario_id 之间数据隔离,不互相影响

## 后果
- ✅ 4 场景剧情数据干净,不互相污染
- ✅ Demo 可以一键 reset 后跑同样剧本
- ❌ 没有"真实变化"的随机性(demo 不需要)
```

### A.6 docs/ADR/0006-conversation-state-machine.md

```markdown
# ADR 0006: Conversation 状态机三重保护

## 决策
状态变更使用:
1. PostgreSQL advisory lock(防并发写入)
2. version CAS(防 stale event 覆盖新状态)
3. 状态机白名单 VALID_TRANSITIONS(防非法转换)

## 后果
- ✅ Bot/坐席并发更新安全
- ✅ Webhook 重放安全
- ❌ 每次 transition 多 1-2ms(advisory lock + UPDATE)
```

### A.7 docs/ADR/0007-s4-prerecorded-translation.md

```markdown
# ADR 0007: S4 翻译用单 SIP + 预录英文回放

## 状态:Accepted (Codex Issue #5 砍真双 SIP 桥)

## 背景
原方案:双 PJSIPTransport 交叉做 B2BUA + 双向翻译。
红队评估:工程量等于 7 周项目本身,turn-taking 死锁风险高。

## 决策
S4 简化为:
- 单 SIP(客户端)
- Pipecat 内部双向翻译 pipeline
- "被叫端"用 TTSReplayService 回放预录英文音频
- 演示效果上看是双向翻译,工程上只有一路 SIP

## 后果
- ✅ Phase 4 时间预算救回来
- ❌ 不是真三方通话,demo 解说必须明确是"翻译能力演示"
```

### A.8 docs/STATE_MACHINE.md

```markdown
# Conversation 状态机

## 状态定义

| 状态 | 含义 |
|---|---|
| pending | Bot 正在处理 |
| open | 人工接管 / 持续会话 |
| resolved | 已解决 |
| snoozed | 暂缓 |

## 允许转换

```
pending  → open       (bot_handoff)
pending  → resolved   (bot self-served)
open     → resolved   (agent resolve)
open     → snoozed    (agent snooze)
snoozed  → open       (snooze expire / reopen)
snoozed  → resolved   (agent close while snoozed)
resolved → open       (reopen)
```

## 禁止转换

- pending → snoozed   (没接 bot 之前不能 snooze)
- resolved → pending  (重开应该到 open,不是 pending)
- resolved → snoozed  (resolved 是终态)

## 并发保护
所有 transition 必须经过 ConversationService.transition_status:
- DB 事务
- pg_advisory_xact_lock(conversation_id)
- version CAS
- 白名单校验
```

### A.9 docs/PJSIP_THREADING.md

```markdown
# PJSIP 线程模型

## 铁律(违反必崩)

1. PJSIP Endpoint 全进程只创建一次
2. uaConfig.threadCnt = 0(Python 必须)
3. 所有 pjsua2 API 调用只在 PJSIP actor 线程
4. 跨线程进入 pjsua2 必须先 pj_thread_register()
5. asyncio 端只持 call_id 字符串,不持 pjsua2 对象引用
6. asyncio→PJSIP 通过 command queue
7. PJSIP→asyncio 通过 call_soon_threadsafe / run_coroutine_threadsafe
8. 对象销毁显式触发(命令),不依赖 GC

## 命令类型

| 命令 | 触发 | 行为 |
|---|---|---|
| answer | asyncio | call.answer(200) |
| hangup | asyncio | call.hangup(486) |
| send_pcm | asyncio | 写 PCM 到 AudioMedia |
| bridge_websocket | asyncio | 旁路 Pipecat,桥到 WS |
| flush_outbound | asyncio | 客户打断,清空 outbound buffer |
| reject | asyncio | 拒绝不支持的 SIP method |

## 事件回调(PJSIP→asyncio)

| 回调 | PJSIP 触发 | 转 asyncio |
|---|---|---|
| onIncomingCall | new INVITE | _notify_voice_worker_call_started |
| onCallState DISCONNECTED | BYE/CANCEL | _notify_voice_worker_call_ended |
| onCallMediaState ACTIVE | media 协商完成 | _attach_pcm_port |
| 每 20ms RTP frame | RTP 入 | _on_pcm_received |
```

### A.10 docs/SIP_SCENARIOS.md

```markdown
# 支持的 SIP 场景矩阵

## ✅ 支持(happy path)

- INVITE(无 SDP early media)→ 200 OK + SDP answer
- ACK
- BYE
- CANCEL
- OPTIONS(自动应答 200)

## ⚠️ 接受但不处理

- REGISTER(只接受不主动转发,本机无 registrar)
- INFO(日志告警,不处理)

## ❌ 拒绝(返回 4xx)

| Method | 状态码 | 原因 |
|---|---|---|
| UPDATE | 481 | 不支持 dialog 内更新 |
| re-INVITE | 488 | 不支持媒体重协商 |
| REFER | 501 | 转移在 AICC API 层做 |
| NOTIFY | 489 | 不订阅事件 |
| SUBSCRIBE | 489 | 不发布事件 |
| MESSAGE | 405 | SIP 消息不支持 |
| PUBLISH | 405 | 不发布状态 |

## 拒绝时的实现

```python
def on_unsupported_method(call, method):
    op = pj.CallOpParam()
    op.statusCode = REJECT_CODES[method]
    call.hangup(op)
    logger.warning(f"Rejected SIP {method} from {call.remoteUri}")
```

## SDP 协商规则

只接受 Codec 优先级:
- PCMA/8000 优先级 255
- 其他全部 0(等于禁用)

如果 INVITE SDP 不含 PCMA → 488 Not Acceptable Here
```

### A.11 docs/MOCK_API_CONTRACT.md

```markdown
# Mock API 数据契约

## 通用规则

1. 所有 endpoint 接受 query param `phone`
2. 涉及场景隔离的 endpoint 必须接受 `scenario` (s1/s2/s3/s4)
3. 返回值由 MockScenarioState 表预定义,不随机
4. 未知 phone 返回 200 + 默认值,不返回 404

## /mock/network/diagnose

GET /mock/network/diagnose?phone=...&scenario=s1

返回:
```json
{
  "status": "congested" | "healthy",
  "base_station": "BS-008",
  "load_percent": 87,
  "signal_strength_dbm": -98,
  "issue_type": "cell_congestion",
  "fix_eta_minutes": 30
}
```

## /mock/profile/lookup

GET /mock/profile/lookup?phone=...

返回:
```json
{
  "name": "张先生",
  "tier": "loyal_3yr",
  "current_plan": "399_premium",
  "registration_date": "2023-03-15"
}
```

## /mock/profile/usage

GET /mock/profile/usage?phone=...&scenario=s2

返回:
```json
{
  "monthly_data_gb": 68,
  "monthly_voice_minutes": 480,
  "device_count": 4,
  "top_apps": ["腾讯会议", "微信视频"]
}
```

## /mock/ticket/create

POST /mock/ticket/create
Body: {phone, issue_type, scenario}

返回:
```json
{
  "ticket_id": "WO-20260605-001",
  "status": "submitted",
  "eta_minutes": 30
}
```

## /mock/voucher/grant

POST /mock/voucher/grant
Body: {phone, voucher_type, amount}

返回:
```json
{
  "voucher_id": "VCH-S1-DEMO-001",
  "type": "data",
  "amount_mb": 10240,
  "valid_until": "2026-06-30"
}
```

## 响应时间约束

所有 Mock API P99 < 50ms(纯 DB 查询,无外部依赖)。
```

### A.12 docs/AI_TASK_GUIDELINES.md

```markdown
# 给 AI 编码工具的任务规则

## 任务粒度

每个任务必须满足:
1. 只改 1 个模块(core/conversations 或 voice_worker/transports 等)
2. 配套 1 组测试
3. 代码量 < 500 行(超过必须拆分)
4. 输出必须包括:
   - 修改的文件列表
   - 新增的测试
   - 验收命令(如何跑测试)

## 严禁

- 跨模块 refactor("顺手把那个也改了")
- 改 ADR 决定的架构(违反必须先开新 ADR)
- 改数据库 schema(必须经 migration review)
- 增加新依赖(必须经依赖 review)

## 当出现以下情况,必须停下来问用户

- 发现需要改 ADR 决定的东西
- 发现现有架构不支持需求(可能是文档过时)
- 测试需要 mock 复杂外部系统
- 不确定该用哪个模块/接口

## 上下文喂法模板

```
[系统提示]
你是一个严格遵守工程纪律的开发者,你的目标是完成给定的任务,
严禁越界、严禁推翻 ADR 决定、严禁未经 review 增加依赖。
当遇到不确定时停下来问用户,而不是猜测。

[项目背景]
<贴第 0/1/2 章>

[任务卡]
<贴具体任务>

[关联约束]
<贴本任务相关的 ADR / docs/*.md>

[禁止改动文件]
<列出本任务不应该碰的文件>

[验收标准]
<列出测试命令和期望输出>
```
```

### A.13 docs/PHASE_GATES.md

(已在第 13.5 章详述,此处略)

### A.14 docs/DEMO_SCRIPT.md

(已在第 1.3 / 14.2 章详述,此处略)

---

## 附录 B:PJSIP 黄金参考实现

> 直接 fork 自 [pjproject/pjsip-apps/src/swig/python](https://github.com/pjsip/pjproject/tree/master/pjsip-apps/src/swig/python),
> 放在 `references/pjsip_pygui_reference/` 目录,作为 Claude Code 写 PJSIPActor / PJSIPCallHandler / PJSIPTransport 的锚点参考。

### B.1 必读参考文件

| 文件 | 学什么 |
|---|---|
| `pjproject/pjsip-apps/src/swig/python/test.py` | Endpoint init, account 创建, 简单通话 |
| `pjproject/pjsip-apps/src/swig/python/pygui/application.py` | Endpoint 单例 + 事件循环 |
| `pjproject/pjsip-apps/src/swig/python/pygui/call.py` | Call 状态/媒体回调处理 |
| `pjproject/pjsip-apps/src/swig/python/pygui/account.py` | onIncomingCall 标准实现 |

### B.2 关键 API Cheatsheet

```python
# Endpoint 初始化(只在 actor 线程)
ep = pj.Endpoint()
ep.libCreate()
ep_cfg = pj.EpConfig()
ep_cfg.uaConfig.threadCnt = 0  # ★
ep_cfg.uaConfig.userAgent = "AICC-Lite/1.0"
ep.libInit(ep_cfg)

# Transport
tp_cfg = pj.TransportConfig()
tp_cfg.port = 5060
ep.transportCreate(pj.PJSIP_TRANSPORT_UDP, tp_cfg)

# Codec
ep.codecSetPriority("pcma/8000/1", 255)
for ci in ep.codecEnum2():
    if ci.codecId != "pcma/8000/1":
        ep.codecSetPriority(ci.codecId, 0)

# Media config
m_cfg = pj.MediaConfig()
m_cfg.portRange = 100  # 10000-10100
ep.libStart()

# Account
acc_cfg = pj.AccountConfig()
acc_cfg.idUri = "sip:1001@127.0.0.1"
account = MyAccount()  # 继承 pj.Account, 重写 onIncomingCall
account.create(acc_cfg)

# 来电应答
def onIncomingCall(self, prm):
    call = MyCall(self, prm.callId)
    op = pj.CallOpParam()
    op.statusCode = 200
    call.answer(op)

# 通话状态回调
def onCallState(self, prm):
    info = self.getInfo()
    if info.state == pj.PJSIP_INV_STATE_DISCONNECTED:
        # cleanup

# 媒体激活回调
def onCallMediaState(self, prm):
    for med in self.getInfo().media:
        if med.type == pj.PJMEDIA_TYPE_AUDIO and \
           med.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
            audio = self.getAudioMedia(med.index)
            # 桥到自定义 PCM 端口

# 跨线程访问 API
pj_thread_desc = pj.pj_thread_desc()  # 必须保持引用
pj.pj_thread_register("my_thread", pj_thread_desc)

# Endpoint 主循环
while running:
    ep.libHandleEvents(10)  # 10ms

# 销毁
ep.libDestroy()
```

### B.3 PCM 自定义端口(关键技术)

PJSIP 自带 AudioMedia 是连扬声器/麦克风的。要把音频接入 Voice Worker,需要写一个**自定义 AudioMediaPort**。

```cpp
// 这是 C++ API,Python 通过 SWIG 包装,具体看 references 中样例
class AICCAudioPort : public AudioMediaPort {
    void onFrameRequested(MediaFrame &frame) override {
        // 从 Voice Worker 拿 PCM,填入 frame
    }
    void onFrameReceived(MediaFrame &frame) override {
        // 把 PCM 推给 Voice Worker
    }
};
```

Python 侧可能需要用 `pj.Endpoint.audDevManager()` 配合 NULL audio device,或者通过 wav 文件中转。**这部分实现需要参考 pjsip-apps 中的 confbot/pyaudio 例子**。

---

## 附录 C:故障排查手册

### C.1 启动相关

| 症状 | 排查 | 解决 |
|---|---|---|
| `docker compose up` 失败 | `docker compose logs` 找具体服务报错 | 通常是 .env 缺变量 |
| postgres 起不来 | 端口 5432 被占 | `lsof -i :5432` 找占用进程 |
| voice-worker GPU not found | NVIDIA Container Toolkit 没装 | 见第 12.1.2 |
| pjsip-server 启动 segfault | PJSIP 镜像 ARM64 不兼容 | 强制 `--platform linux/amd64` |
| Frontend 404 | nginx 配置不对 | 检查 `frontend/Dockerfile` |

### C.2 通话相关

| 症状 | 排查 | 解决 |
|---|---|---|
| Linphone 拨号无回应 | sngrep 看 INVITE 是否到达 | 防火墙 / 端口 5060 占用 |
| INVITE 到达但 488 | SDP codec 不匹配 | Linphone 强制开 PCMA |
| 200 OK 后无音频 | RTP 端口被防火墙 | 开放 10000-10100/udp |
| 单向音频(只听不说 / 只说不听) | RTP 媒体协商问题 | sngrep + Wireshark 抓 RTP 包 |
| 音频断断续续 | jitter / 丢包 | 检查网络 / 改用有线 |
| Bot 不说话 | DeepSeek API 超时 | 看 voice-worker 日志 |
| Bot 答非所问 | STT 误识别 | 演示者发音清晰 / 慢说 |

### C.3 转人工相关

| 症状 | 排查 | 解决 |
|---|---|---|
| 坐席台无叮咚 | WS 是否连上 | 浏览器 Devtools → Network → WS |
| 接听后无音频 | WebSocket+PCM 桥未建 | 看 voice-worker `/internal/call/handoff` 日志 |
| 浏览器麦克风无声 | Windows 隐私权限 | 设置 → 隐私 → 麦克风 |
| 客户打断不响应 | InterruptionFrame 未传播 | 看 Pipecat 日志 |

### C.4 翻译(场景 4)相关

| 症状 | 排查 | 解决 |
|---|---|---|
| 中→英翻译错 | DeepSeek prompt 问题 | 调整 system prompt |
| 英文 TTS 不出声 | Piper en_US-amy 模型不存在 | 重新下载 |
| 预录音频不播放 | TTSReplayService 路径错 | 检查 `scripts/demo_tts_audio/` |

### C.5 Demo 现场紧急

```bash
# 全部重启
docker compose down && docker compose up -d

# 单独重启 voice-worker(GPU 紧张时)
docker compose restart voice-worker

# 重置 demo 数据
python scripts/reset_demo.py

# 保留备份录像
open docs/demo/aicc-lite-demo-v3.mp4
```

---

## 附录 D:v4 候选清单(未来路线)

> 这部分是 v3 不做、未来可能做的事项,作为路线图存档。
> v3 期间任何"想加但加了会破坏主线"的需求都记到这里。

### D.1 已识别的 v4 候选

| 项 | 来自 | 价值 | 估计工作量 |
|---|---|---|---|
| **WebRTC 在线版**(浏览器拨号,GitHub Pages 嵌入) | 用户原始诉求 d | 让任何人能远程体验 | 4-6 周 |
| **Twilio Phase 6 真实 PSTN 升级** | 演示真实感 | 给高层 demo 用 | 0.5-1 周 |
| **CosyVoice2 替代 Piper(GPU 充足)** | 中文 TTS 自然度 | demo 听感升级 | 0.5 周 |
| **真三方 SIP B2BUA + 翻译桥** | 场景 4 真实化 | 真国际通话 demo | 3-4 周 |
| **多坐席 / Round-robin 分配** | 借鉴 Chatwoot 完整 | 多人协作 demo | 1 周 |
| **JsSIP 浏览器 SIP 客户端**(配 Asterisk PBX) | 完整坐席能力 | hold/transfer 等 | 2-3 周 |
| **真 RAG(BCEmbedding + pgvector)** | Captain-Lite 升级 | 知识库扩展 | 1 周 |
| **OpenTelemetry + Jaeger 全链路追踪** | 生产级可观测 | 调优 | 0.5 周 |
| **K8s Helm chart** | 生产部署 | 给企业 demo | 1 周 |
| **多租户 / Account-based RBAC** | 借鉴 Chatwoot 完整 | SaaS demo | 2 周 |
| **WeChat / WhatsApp Channel** | 全渠道完整化 | 多渠道客户旅程 | 各 1-2 周 |
| **Smart Turn v3 中文重训** | turn detection 升级 | 打断更精准 | 2-3 周 |
| **Speech-to-Speech 模型**(GPT-4o realtime 类) | 极致延迟 | <500ms 端到端 | 跟进开源进展 |

### D.2 v4 决策原则

启动 v4 的前提:
1. v3 所有 4 场景稳定 demo 至少 10 次
2. v3 GitHub README + 录屏发布
3. 收集 v3 演示反馈,确认 v4 候选项的优先级

绝不在 v3 期间偷偷做 v4,任何"反正不远的扩展"都先记到 D.1 表格,Discovery 时再讨论。

---

## 文档结束

**版本**:v3.0
**字数**:~30,000 字
**长度**:~4,800 行
**适用**:Claude Code / Codex 等 AI 编码工具直接消化
**Discovery 状态**:✅ 完全冻结
**下一步**:Building Phase 1 - 由 AI 编码工具按 15.2 任务清单执行

---

*Generated by Claude (Anthropic) with Lucas as Product Owner.*
*Reviewed by 2 rounds of Claude red-team + 1 round Codex adversarial review.*
*All decisions documented in `docs/ADR/` for engineering memory persistence.*

