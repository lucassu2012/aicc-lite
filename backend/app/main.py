"""AICC-Lite FastAPI 主应用"""
import json
import logging
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import init_db, get_db, AsyncSessionLocal
from .seed import seed_data
from .services import ConversationService, MessageService, InvalidTransitionError, ConcurrentUpdateError
from .models import (
    ConversationSchema, MessageSchema, ContactSchema,
    MessageCreateRequest, ConversationCreateRequest,
    HandoffRequest, StatusChangeRequest, TranslationRequest,
)
from . import mocks
from .flows import executor
from .llm import client as llm_client
from .websocket_manager import manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"DeepSeek LLM enabled: {settings.USE_LLM}")
    await init_db()
    async with AsyncSessionLocal() as s:
        seeded = await seed_data(s)
        if seeded:
            logger.info("Seed data loaded")
        else:
            logger.info("Seed data already exists, skipped")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="智能联络中心轻量级实现 - 4 大场景演示新代际 AI 联络中心能力",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ 健康检查 ============

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "llm_enabled": settings.USE_LLM,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============ 会话 API ============

@app.get("/api/v1/conversations")
async def list_conversations(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    convs = await ConversationService.list_conversations(db, status=status)
    return {
        "data": [
            {
                "id": c.id,
                "status": c.status,
                "assignee_id": c.assignee_id,
                "scenario_id": c.scenario_id,
                "contact": {"id": c.contact.id, "name": c.contact.name, "phone": c.contact.phone} if c.contact else None,
                "messages_count": len(c.messages),
                "last_message": c.messages[-1].content if c.messages else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in convs
        ],
        "total": len(convs),
    }


@app.post("/api/v1/conversations")
async def create_conversation(
    req: ConversationCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    conv = await ConversationService.create_conversation(
        db,
        contact_id=req.contact_id,
        inbox_id=req.inbox_id,
        scenario_id=req.scenario_id,
    )
    await manager.broadcast_all("conversation.created", {
        "id": conv.id,
        "scenario_id": conv.scenario_id,
        "status": conv.status,
    })
    return {"id": conv.id, "status": conv.status, "scenario_id": conv.scenario_id}


@app.get("/api/v1/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    conv = await ConversationService.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(404, f"Conversation {conversation_id} not found")
    return {
        "id": conv.id,
        "status": conv.status,
        "assignee_id": conv.assignee_id,
        "scenario_id": conv.scenario_id,
        "contact": {
            "id": conv.contact.id,
            "name": conv.contact.name,
            "phone": conv.contact.phone,
            "custom_attributes": conv.contact.custom_attributes,
        } if conv.contact else None,
        "messages": [
            {
                "id": m.id,
                "content": m.content,
                "sender_type": m.sender_type,
                "message_type": m.message_type,
                "content_attributes": m.content_attributes,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in conv.messages
        ],
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
    }


@app.post("/api/v1/conversations/{conversation_id}/messages")
async def post_message(
    conversation_id: int,
    req: MessageCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    msg = await MessageService.add_message(
        db, conversation_id,
        content=req.content,
        sender_type=req.sender_type,
        sender_id=req.sender_id,
        content_attributes=req.content_attributes,
    )
    payload = {
        "id": msg.id,
        "conversation_id": conversation_id,
        "content": msg.content,
        "sender_type": msg.sender_type,
        "message_type": msg.message_type,
        "content_attributes": msg.content_attributes,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }
    await manager.broadcast_all("message.created", payload)
    return payload


@app.post("/api/v1/conversations/{conversation_id}/handoff")
async def handoff_conversation(
    conversation_id: int,
    req: HandoffRequest,
    db: AsyncSession = Depends(get_db),
):
    """Bot 主动转人工"""
    try:
        conv = await ConversationService.transition_status(db, conversation_id, "open", actor="bot_handoff")
    except InvalidTransitionError as e:
        raise HTTPException(400, str(e))

    # 添加 AI summary 作为活动消息
    summary_content = f"🤖 AI 转人工分析:\n原因: {req.reason}\n情绪评分: {req.sentiment_score}/10\n摘要: {req.ai_summary or '无'}"
    await MessageService.add_message(
        db, conversation_id,
        content=summary_content,
        sender_type="Captain",
        sender_id=0,
        content_attributes={"type": "ai_handoff_summary", "data": req.dict()},
    )

    await manager.broadcast_all("conversation.handoff", {
        "conversation_id": conversation_id,
        "reason": req.reason,
        "sentiment_score": req.sentiment_score,
        "ai_summary": req.ai_summary,
    })
    return {"id": conv.id, "status": conv.status, "handoff": req.dict()}


@app.post("/api/v1/conversations/{conversation_id}/resolve")
async def resolve_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        conv = await ConversationService.transition_status(db, conversation_id, "resolved", actor="agent")
    except InvalidTransitionError as e:
        raise HTTPException(400, str(e))
    await manager.broadcast_all("conversation.resolved", {"conversation_id": conversation_id})
    return {"id": conv.id, "status": conv.status}


@app.post("/api/v1/conversations/{conversation_id}/assign")
async def assign_conversation(
    conversation_id: int,
    assignee_id: int = 2,
    db: AsyncSession = Depends(get_db),
):
    conv = await ConversationService.assign_conversation(db, conversation_id, assignee_id)
    await manager.broadcast_all("conversation.assigned", {
        "conversation_id": conversation_id,
        "assignee_id": assignee_id,
    })
    return {"id": conv.id, "status": conv.status, "assignee_id": conv.assignee_id}


# ============ Mock APIs ============

@app.get("/mock/profile/lookup")
async def mock_profile_lookup(phone: str):
    contact = mocks.get_contact_by_phone(phone)
    if not contact:
        raise HTTPException(404, "Contact not found")
    return contact


@app.get("/mock/network/diagnose")
async def mock_network_diagnose(phone: str, scenario: str = "s1"):
    return mocks.network_diagnose(phone, scenario)


@app.get("/mock/profile/usage")
async def mock_profile_usage(phone: str):
    return mocks.get_usage(phone)


@app.get("/mock/plan/list")
async def mock_plan_list():
    return mocks.list_plans()


@app.post("/mock/plan/calculate")
async def mock_plan_calculate(plan: str, monthly_data_gb: float, monthly_voice_min: int):
    return mocks.calculate_actual_cost(plan, monthly_data_gb, monthly_voice_min)


@app.get("/mock/offers")
async def mock_offers(phone: str):
    return mocks.get_offers(phone)


@app.post("/mock/offer/apply")
async def mock_offer_apply(phone: str, offer_id: str):
    return mocks.apply_offer(phone, offer_id)


@app.post("/mock/ticket/create")
async def mock_ticket_create(phone: str, issue_type: str, priority: str = "normal", description: str = ""):
    return mocks.create_ticket(phone, issue_type, priority, description)


@app.post("/mock/voucher/grant")
async def mock_voucher_grant(phone: str, data_mb: int, reason: str = "compensation"):
    return mocks.grant_voucher(phone, data_mb, reason)


# ============ 场景触发 ============

@app.post("/api/v1/scenarios/{scenario_id}/trigger")
async def trigger_scenario(
    scenario_id: str,
    phone: str = "13812345678",
    db: AsyncSession = Depends(get_db),
):
    """触发场景:创建 conversation,执行预测分析,返回 AI 第一句话和上下文"""
    if scenario_id not in ("s1", "s2", "s3", "s4"):
        raise HTTPException(400, f"Unknown scenario: {scenario_id}")

    # 创建 conversation
    conv = await ConversationService.create_conversation(
        db, contact_id=1, inbox_id=1, scenario_id=scenario_id,
    )

    # 执行场景前置分析
    scenario_data = None
    if scenario_id == "s1":
        scenario_data = await executor.trigger_s1(phone)
    elif scenario_id == "s2":
        scenario_data = await executor.trigger_s2(phone)
    elif scenario_id == "s3":
        scenario_data = await executor.trigger_s3(phone)
    elif scenario_id == "s4":
        scenario_data = await executor.trigger_s4(phone)

    # 添加初始系统消息(activity)
    activity_msg_content = f"📞 来电接通 - 场景: {scenario_id.upper()} - 客户: {scenario_data['contact']['name']} ({phone})"
    await MessageService.add_message(
        db, conv.id,
        content=activity_msg_content,
        sender_type="User",
        sender_id=1,
        content_attributes={"activity": "call_started", "scenario": scenario_id},
    )

    await manager.broadcast_all("scenario.triggered", {
        "conversation_id": conv.id,
        "scenario_id": scenario_id,
        "data": scenario_data,
    })

    return {
        "conversation_id": conv.id,
        "scenario_id": scenario_id,
        "data": scenario_data,
    }


# ============ AI Chat ============

@app.post("/api/v1/conversations/{conversation_id}/ai_reply")
async def ai_reply(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """触发 AI 生成下一条回复(基于历史 + 场景上下文)"""
    conv = await ConversationService.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(404, "Not found")

    # 构建场景上下文
    contact_data = mocks.get_contact_by_phone(conv.contact.phone) if conv.contact else mocks.MOCK_CONTACT
    scenario_id = conv.scenario_id or "s1"

    if scenario_id == "s1":
        diagnosis = mocks.network_diagnose(contact_data["phone"])
        system_prompt = f"""{conv.contact.name if conv.contact else '客户'},您好。
你是中国移动智能客服。当前场景:网络诊断。
诊断结果: 基站{diagnosis['base_station']} 负载{diagnosis['load_percent']}%, 影响{diagnosis['neighboring_users_affected']}名用户。
回答要简洁专业,告知客户已识别问题并提供补偿方案(10G免费流量+30分钟内修复)。"""
    elif scenario_id == "s2":
        usage = mocks.get_usage(contact_data["phone"])
        system_prompt = f"""你是中国移动智能客服。客户想降套餐。
客户实际使用:流量{usage['monthly_data_gb']}G,通话{usage['monthly_voice_minutes']}分钟。
如降到199基础套餐,实际花费会到¥340(超出+114流量超额+27通话超额)。
建议保留399套餐,提供老客户9折优惠359元/月,赠送家庭宽带提速500M。
要用准确数字算账,然后基于忠诚度提供挽留方案。"""
    elif scenario_id == "s3":
        complaint = mocks.get_complaint_context(contact_data["phone"])
        system_prompt = f"""你是中国移动智能客服。检测到客户投诉。
历史: {complaint['previous_complaints']}
任务: 表达歉意,告知客户即将转接人工坐席,然后立即转人工。
回答要简洁,不要尝试自己解决投诉。最后说: '我马上为您转接专属客服,请稍候'"""
    else:
        system_prompt = "你是中国移动智能客服小智,温和专业地服务客户。"

    # 拼接历史消息
    messages = [{"role": "system", "content": system_prompt}]
    for m in conv.messages[-10:]:  # 最近 10 条
        if m.message_type == 2:  # 跳过 activity
            continue
        role = "user" if m.sender_type == "Contact" else "assistant"
        messages.append({"role": role, "content": m.content})

    # 调用 LLM
    response = await llm_client.chat(messages, temperature=0.7, timeout=10.0)
    reply_content = response.get("content") or "您好,请问有什么可以帮您?"

    # 写入 message
    msg = await MessageService.add_message(
        db, conversation_id,
        content=reply_content,
        sender_type="AgentBot",
        sender_id=1,
        content_attributes={"source": "ai", "model": settings.DEEPSEEK_MODEL if settings.USE_LLM else "fallback"},
    )

    await manager.broadcast_all("message.created", {
        "id": msg.id,
        "conversation_id": conversation_id,
        "content": reply_content,
        "sender_type": "AgentBot",
        "message_type": 1,
        "content_attributes": msg.content_attributes,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    })

    return {
        "message_id": msg.id,
        "content": reply_content,
        "tool_calls": response.get("tool_calls", []),
    }


# ============ S4 翻译 ============

@app.post("/api/v1/translate")
async def translate(req: TranslationRequest):
    result = await executor.translate(req.text, req.source_lang, req.target_lang)
    return result


# ============ Captain Lite (AI 坐席助手建议) ============

@app.post("/api/v1/conversations/{conversation_id}/suggest")
async def captain_suggest(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """为坐席生成 AI 建议话术"""
    conv = await ConversationService.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(404, "Not found")

    scenario_id = conv.scenario_id or "s1"

    suggestions = {
        "s1": [
            "您好张先生,我已经为您处理了基站优化工单",
            "工单号 WO-20260605-001,预计30分钟内恢复",
            "为补偿您,我们额外赠送 10G 免费流量包",
        ],
        "s2": [
            "考虑您的实际使用,降套餐反而会多花钱",
            "作为3年老客户,可享专属9折优惠 359元/月",
            "同时赠送家庭宽带提速 500M,持续6个月",
        ],
        "s3": [
            "非常抱歉给您带来困扰,我会优先处理",
            "我先共情客户情绪,然后确认问题细节",
            "提供升级方案+补偿,确保客户满意",
        ],
        "s4": [
            "翻译质量稳定,延迟<800ms",
            "保留商务对话礼貌语气",
            "已记录关键决策点供后续跟进",
        ],
    }

    return {
        "conversation_id": conversation_id,
        "scenario_id": scenario_id,
        "suggestions": suggestions.get(scenario_id, []),
        "captain_summary": f"AI 已识别{scenario_id.upper()}场景,建议话术已准备就绪",
    }


# ============ 重置 ============

@app.post("/api/v1/demo/reset")
async def reset_demo(db: AsyncSession = Depends(get_db)):
    """清空所有 conversation/message,保留基础数据"""
    from sqlalchemy import delete
    from .models import Conversation, Message

    await db.execute(delete(Message))
    await db.execute(delete(Conversation))
    await db.commit()
    await manager.broadcast_all("demo.reset", {})
    return {"status": "reset"}


# ============ WebSocket ============

@app.websocket("/ws/agent")
async def ws_agent(websocket: WebSocket, token: str = Query("agent-demo-token")):
    """坐席工作台 WebSocket"""
    await manager.connect(websocket, "agent")
    try:
        await manager.send_to(websocket, "ws.connected", {"role": "agent"})
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                # echo back for now
                await manager.send_to(websocket, "ws.ack", {"received": msg})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, "agent")
    except Exception as e:
        logger.error(f"WS error: {e}")
        manager.disconnect(websocket, "agent")


@app.websocket("/ws/customer")
async def ws_customer(websocket: WebSocket):
    """客户端 WebSocket(模拟通话)"""
    await manager.connect(websocket, "customer")
    try:
        await manager.send_to(websocket, "ws.connected", {"role": "customer"})
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, "customer")
    except Exception as e:
        logger.error(f"WS customer error: {e}")
        manager.disconnect(websocket, "customer")


# ============ 静态文件(开发用) ============

import os
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))


@app.get("/")
async def root():
    """前端首页"""
    frontend_index = os.path.join(frontend_dir, "index.html")
    if os.path.exists(frontend_index):
        with open(frontend_index, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return {"message": "AICC-Lite Backend Running", "docs": "/docs"}


@app.get("/styles.css")
async def serve_css():
    fp = os.path.join(frontend_dir, "styles.css")
    if os.path.exists(fp):
        with open(fp, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), media_type="text/css")
    raise HTTPException(404)


@app.get("/app.js")
async def serve_app_js():
    fp = os.path.join(frontend_dir, "app.js")
    if os.path.exists(fp):
        with open(fp, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), media_type="application/javascript")
    raise HTTPException(404)


@app.get("/mock-backend.js")
async def serve_mock_js():
    fp = os.path.join(frontend_dir, "mock-backend.js")
    if os.path.exists(fp):
        with open(fp, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), media_type="application/javascript")
    raise HTTPException(404)


# Mount static for any other assets
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
