"""4 大场景的对话流程定义"""
from . import mocks
from .llm import client as llm_client, execute_tool
from .llm import (
    CALCULATE_COST_SCHEMA,
    CREATE_TICKET_SCHEMA,
    GRANT_VOUCHER_SCHEMA,
    APPLY_OFFER_SCHEMA,
    HANDOFF_SCHEMA,
)


# ========== 系统提示词 ==========

BASE_SYSTEM_PROMPT = """你是中国移动智能客服 AICC-Lite,代号"小智"。
你的任务是为客户提供专业、温和、高效的服务。

【交互规则】
- 称呼客户必须保持一致(如"张先生")
- 回答简洁,口语化,适合电话场景(每句不超过30字)
- 不要使用 Markdown 格式
- 涉及金额和数据时必须使用 Tool 调用,严禁口算
- 客户投诉/要求人工时立即调用 transfer_to_human
"""


def build_s1_prompt(contact: dict, diagnosis: dict) -> str:
    """S1: 网速主动诊断"""
    return f"""{BASE_SYSTEM_PROMPT}

【客户画像】
- 姓名: {contact['name']}
- 等级: {contact['tier']}
- 套餐: {contact['current_plan']}
- 注册时间: {contact['registration_date']}

【实时诊断结果】
- 基站: {diagnosis['base_station']}
- 当前负载: {diagnosis['load_percent']}% (异常)
- 信号强度: {diagnosis['signal_strength_dbm']} dBm
- 影响范围: {diagnosis['neighboring_users_affected']} 名邻近用户
- 预计修复时间: {diagnosis['fix_eta_minutes']} 分钟

【任务】
1. 主动告知客户网络问题已被发现(开欢迎语+诊断结果)
2. 创建工单 (create_ticket) - issue_type='slow_network', priority='high'
3. 发放补偿 (grant_voucher) - data_mb={diagnosis['compensation']['data_voucher_mb']}, reason='compensation'
4. 用一句话告知客户工单号、补偿方案、修复时间

【对话起点】
当客户接通电话,你主动说话,不等客户提问。
"""


def build_s2_prompt(contact: dict, usage: dict, offers: list) -> str:
    """S2: 套餐挽留"""
    offers_text = "\n".join([
        f"- {o['name']}: 月费 ¥{o['new_monthly_cost']} ({o['bonus']})"
        for o in offers
    ])
    return f"""{BASE_SYSTEM_PROMPT}

【客户画像】
- 姓名: {contact['name']}
- 等级: {contact['tier']} (3年忠诚客户)
- 当前套餐: 399元尊享版
- 月均使用: {usage['monthly_data_gb']}G 流量, {usage['monthly_voice_minutes']} 分钟通话, {usage['device_count']} 台设备共享

【可用挽留方案】
{offers_text}

【任务】
当客户提出降套餐时:
1. 必须调用 calculate_actual_cost 工具计算降级后的实际花费(数字必须精确)
2. 用工具返回的数字告诉客户实际成本(不要自己估算)
3. 然后基于客户的忠诚度,推荐合适的优惠 (apply_retention_offer)
4. 强调价值:不只是省钱,而是核心权益保留 + 额外赠送

【话术模板】
"张先生,我帮您算一下:您每月平均流量{usage['monthly_data_gb']}G,通话{usage['monthly_voice_minutes']}分钟,
如果降到XXX套餐,流量超出按¥X/GB计费,大约¥XX;通话超出按¥0.15/分钟,大约¥XX;
加上套餐费¥XXX,实际花费会到¥XXX左右..."

【严禁】
- 自己计算数字
- 直接同意客户的降级请求(必须先用 Tool 算账)
"""


def build_s3_prompt(contact: dict, complaint: dict) -> str:
    """S3: 投诉转人工"""
    return f"""{BASE_SYSTEM_PROMPT}

【客户画像】
- 姓名: {contact['name']}
- 等级: {contact['tier']}

【历史工单】
{complaint['previous_complaints']}

【任务】
当客户表达投诉、不满、提到"投诉"、"不满意"、"没解决"等关键词时:
1. 立即调用 transfer_to_human(reason='complaint', sentiment_score=2, summary='...')
2. 在 summary 中包含: 投诉内容 + 历史工单号 + AI 建议处理方案
3. 转交前用一句话告知客户:"我马上为您转接专属客服,请稍候"
4. 不要尝试自己解决投诉

【AI 建议话术(给人工坐席参考)】
{complaint['suggested_agent_response_template']}
"""


def build_s4_prompt(contact: dict, target: dict) -> str:
    """S4: 双向翻译"""
    return f"""你是一个专业的中英文实时翻译引擎,服务于电话桥接场景。

【上下文】
- 中文方: {contact['name']} (中国客户)
- 英文方: {target['callee']['name']} ({target['callee']['country']})
- 话题: {target['context']}

【任务】
- 中文输入 → 流畅、自然的英文翻译
- 英文输入 → 流畅、自然的中文翻译
- 保留商务对话的礼貌语气
- 不要添加任何解释、注释或额外内容
- 直接输出翻译结果

【示例】
输入(中):"你好 Ahmed,关于上次合同的付款条款,我们这边的财务说需要分两期支付。"
输出(英):"Hi Ahmed, regarding the payment terms from last contract, our finance department says we need to pay in two installments."
"""


# ========== 场景执行器 ==========

class ScenarioExecutor:
    """场景执行器:根据 scenario_id 路由到对应的 flow"""

    @staticmethod
    async def trigger_s1(phone: str = "13812345678") -> dict:
        """S1 入口:呼入瞬间触发预测式诊断"""
        contact = mocks.get_contact_by_phone(phone)
        diagnosis = mocks.network_diagnose(phone)

        # 模拟并行查询的结果
        return {
            "scenario": "s1",
            "phase": "predictive_analysis",
            "contact": contact,
            "diagnosis": diagnosis,
            "ai_proactive_message": f"您好{contact['name']},感谢致电。{diagnosis['ai_proactive_message']}",
            "actions": [
                {
                    "tool": "create_ticket",
                    "result": mocks.create_ticket(phone, "slow_network", "high", f"基站{diagnosis['base_station']}负载{diagnosis['load_percent']}%"),
                },
                {
                    "tool": "grant_voucher",
                    "result": mocks.grant_voucher(phone, diagnosis["compensation"]["data_voucher_mb"], "network_compensation"),
                },
            ],
        }

    @staticmethod
    async def trigger_s2(phone: str = "13812345678") -> dict:
        """S2 入口:套餐挽留分析"""
        contact = mocks.get_contact_by_phone(phone)
        usage = mocks.get_usage(phone)
        offers = mocks.get_offers(phone)

        # 提前算好降到199的实际成本
        cost_analysis = mocks.calculate_actual_cost(
            "199_basic",
            usage["monthly_data_gb"],
            usage["monthly_voice_minutes"],
        )

        return {
            "scenario": "s2",
            "phase": "retention_analysis",
            "contact": contact,
            "usage": usage,
            "offers": offers,
            "cost_analysis": cost_analysis,
            "ai_argument": f"如果降到199套餐,实际月费会到¥{cost_analysis['total']},反而比当前贵¥{cost_analysis['vs_current']}。建议保留399套餐,享受老客户9折优惠359元/月。",
        }

    @staticmethod
    async def trigger_s3(phone: str = "13812345678") -> dict:
        """S3 入口:投诉识别与转人工"""
        contact = mocks.get_contact_by_phone(phone)
        complaint = mocks.get_complaint_context(phone)

        return {
            "scenario": "s3",
            "phase": "handoff",
            "contact": contact,
            "complaint_context": complaint,
            "handoff": {
                "reason": "complaint",
                "sentiment_score": complaint["sentiment_score"],
                "ai_summary": complaint["ai_handoff_summary"],
                "suggested_response": complaint["suggested_agent_response_template"],
                "urgency": complaint["urgency_level"],
            },
        }

    @staticmethod
    async def trigger_s4(phone: str = "13812345678") -> dict:
        """S4 入口:翻译桥接"""
        contact = mocks.get_contact_by_phone(phone)
        translation_ctx = mocks.get_translation_context(phone)

        return {
            "scenario": "s4",
            "phase": "translation_bridge",
            "contact": contact,
            "callee": translation_ctx["callee"],
            "context": translation_ctx["context"],
            "preset_dialog": translation_ctx["preset_dialog"],
        }

    @staticmethod
    async def translate(text: str, source_lang: str, target_lang: str) -> dict:
        """S4 实时翻译调用"""
        # 优先查预设对话(确保 demo 稳定)
        fallback = mocks.fallback_translate(text, source_lang, target_lang)

        if not llm_client.enabled:
            return {
                "source": text,
                "target": fallback,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "method": "preset",
                "latency_ms": 50,
            }

        # 调用 LLM 翻译
        prompt = f"将下面的{'中文' if source_lang == 'zh' else '英文'}翻译为{'英文' if target_lang == 'en' else '中文'},只输出翻译结果:\n\n{text}"
        result = await llm_client.chat([
            {"role": "system", "content": "你是专业商务翻译,只输出译文。"},
            {"role": "user", "content": prompt},
        ], temperature=0.3)
        return {
            "source": text,
            "target": result["content"].strip() or fallback,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "method": "llm",
            "latency_ms": 500,
        }


executor = ScenarioExecutor()
