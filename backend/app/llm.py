"""LLM 服务 - DeepSeek-V3 集成 + 防御性 Fallback"""
import json
import logging
from typing import AsyncGenerator, Optional
import httpx

from .config import settings
from . import mocks

logger = logging.getLogger(__name__)


# ============ Function Calling Schemas ============

CALCULATE_COST_SCHEMA = {
    "type": "function",
    "function": {
        "name": "calculate_actual_cost",
        "description": "根据用户实际使用量,计算切换到指定套餐后的真实月度费用。包含基础套餐费、流量超出费、通话超出费。",
        "parameters": {
            "type": "object",
            "properties": {
                "plan": {"type": "string", "description": "套餐ID,如199_basic, 299_standard, 399_premium"},
                "monthly_data_gb": {"type": "number", "description": "月均流量GB"},
                "monthly_voice_min": {"type": "integer", "description": "月均通话分钟数"},
            },
            "required": ["plan", "monthly_data_gb", "monthly_voice_min"],
        },
    },
}

CREATE_TICKET_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_ticket",
        "description": "为客户创建工单,触发后端工作流",
        "parameters": {
            "type": "object",
            "properties": {
                "phone": {"type": "string"},
                "issue_type": {"type": "string", "enum": ["slow_network", "billing", "complaint", "general"]},
                "priority": {"type": "string", "enum": ["normal", "high"]},
                "description": {"type": "string"},
            },
            "required": ["phone", "issue_type"],
        },
    },
}

GRANT_VOUCHER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "grant_voucher",
        "description": "发放流量优惠券作为补偿",
        "parameters": {
            "type": "object",
            "properties": {
                "phone": {"type": "string"},
                "data_mb": {"type": "integer", "description": "流量包大小,单位MB"},
                "reason": {"type": "string"},
            },
            "required": ["phone", "data_mb"],
        },
    },
}

APPLY_OFFER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "apply_retention_offer",
        "description": "为客户激活挽留优惠",
        "parameters": {
            "type": "object",
            "properties": {
                "phone": {"type": "string"},
                "offer_id": {"type": "string", "enum": ["loyal_3yr_v1", "data_pack_addon"]},
            },
            "required": ["phone", "offer_id"],
        },
    },
}

HANDOFF_SCHEMA = {
    "type": "function",
    "function": {
        "name": "transfer_to_human",
        "description": "将会话转给人工坐席处理。当客户投诉、要求人工、超出AI能力时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "enum": ["complaint", "request_human", "out_of_scope", "high_value"]},
                "sentiment_score": {"type": "integer", "description": "客户情绪 0-10"},
                "summary": {"type": "string", "description": "AI 摘要,供人工坐席参考"},
            },
            "required": ["reason", "summary"],
        },
    },
}


# ============ Tool 执行 ============

TOOL_HANDLERS = {
    "calculate_actual_cost": lambda args: mocks.calculate_actual_cost(**args),
    "create_ticket": lambda args: mocks.create_ticket(**args),
    "grant_voucher": lambda args: mocks.grant_voucher(**args),
    "apply_retention_offer": lambda args: mocks.apply_offer(args["phone"], args["offer_id"]),
}


def execute_tool(name: str, arguments: dict) -> dict:
    """执行 Tool 调用"""
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    try:
        return handler(arguments)
    except Exception as e:
        logger.exception(f"Tool {name} failed")
        return {"error": str(e)}


# ============ DeepSeek 调用 ============

class DeepSeekClient:
    """DeepSeek-V3 异步客户端"""

    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = settings.DEEPSEEK_MODEL
        self.enabled = bool(self.api_key)

    async def chat(
        self,
        messages: list,
        tools: Optional[list] = None,
        temperature: float = 0.7,
        timeout: float = 15.0,
    ) -> dict:
        """非流式调用,返回 完整 response"""
        if not self.enabled:
            return self._fallback_response(messages)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": False,
                }
                if tools:
                    payload["tools"] = tools

                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                msg = data["choices"][0]["message"]
                return {
                    "content": msg.get("content", ""),
                    "tool_calls": msg.get("tool_calls", []),
                    "usage": data.get("usage", {}),
                }
        except Exception as e:
            logger.exception(f"DeepSeek call failed: {e}")
            return self._fallback_response(messages)

    async def stream(
        self,
        messages: list,
        tools: Optional[list] = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[dict, None]:
        """流式调用"""
        if not self.enabled:
            text = self._fallback_response(messages)["content"]
            for char in text:
                yield {"type": "delta", "content": char}
            yield {"type": "done"}
            return

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": True,
                }
                if tools:
                    payload["tools"] = tools

                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            yield {"type": "done"}
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            if delta.get("content"):
                                yield {"type": "delta", "content": delta["content"]}
                            if delta.get("tool_calls"):
                                yield {"type": "tool_calls", "tool_calls": delta["tool_calls"]}
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.exception(f"DeepSeek stream failed: {e}")
            yield {"type": "error", "error": str(e)}
            yield {"type": "done"}

    def _fallback_response(self, messages: list) -> dict:
        """无 API key 时返回预设回复"""
        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m.get("content", "")
                break

        # 基于关键字简单匹配 - 这是 Demo 兜底
        responses = {
            "网速": "我注意到您所在区域基站当前负载偏高,您是不是觉得网速有点慢?我已为您提交基站优化工单。",
            "降套餐": "张先生,我帮您算了一下:您每月平均流量68G,通话480分钟,降到199套餐实际花费会到340元左右,反而多花。作为3年老客户,我可以为您申请9折优惠,新月费359元,赠送家庭宽带提速。",
            "投诉": "非常抱歉给您带来困扰,我马上为您升级处理,优先调度技术团队。",
            "翻译": "Hi Ahmed, regarding the payment terms, we need to discuss two installments.",
        }
        for k, v in responses.items():
            if k in last_user_msg:
                return {"content": v, "tool_calls": [], "usage": {}}

        return {
            "content": "您好张先生,有什么可以帮您?",
            "tool_calls": [],
            "usage": {},
        }


client = DeepSeekClient()
