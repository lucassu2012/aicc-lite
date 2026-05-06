"""Mock API - 4 大场景的确定性数据"""
from typing import Optional


# ========== 张先生 138xxxxxxxx 完整画像 ==========
MOCK_CONTACT = {
    "id": 1,
    "name": "张先生",
    "phone": "13812345678",
    "email": "zhang@example.com",
    "tier": "loyal_3yr",
    "current_plan": "399_premium",
    "registration_date": "2023-03-15",
    "language": "zh",
    "tags": ["VIP客户", "3年老客户", "高活跃"],
}


# ========== S1: 网速诊断场景 ==========
S1_DIAGNOSIS = {
    "phone": "13812345678",
    "base_station": "BS-008-朝阳区",
    "load_percent": 87,
    "signal_strength_dbm": -98,
    "issue_type": "cell_congestion",
    "fix_eta_minutes": 30,
    "neighboring_users_affected": 234,
    "diagnosis_time": "2026-05-06T10:00:00Z",
    "compensation": {
        "data_voucher_mb": 10240,
        "voucher_id": "VCH-S1-DEMO-001",
    },
    "recommended_action": "create_ticket_and_grant_voucher",
    "ai_proactive_message": "我注意到您所在区域基站当前负载偏高,您是不是觉得网速有点慢?",
}


# ========== S2: 套餐挽留场景 ==========
S2_USAGE = {
    "phone": "13812345678",
    "monthly_data_gb": 68,
    "monthly_voice_minutes": 480,
    "device_count": 4,
    "top_apps": ["腾讯会议", "微信视频", "B站", "网易云"],
    "peak_hours": ["09:00-12:00", "20:00-23:00"],
    "average_session_min": 35,
    "data_growth_yoy": "+25%",
}

PLANS = {
    "199_basic": {
        "id": "199_basic",
        "name": "199 基础版",
        "base": 199,
        "data_quota_gb": 30,
        "data_overage_per_gb": 3,
        "voice_quota_min": 300,
        "voice_overage_per_min": 0.15,
    },
    "299_standard": {
        "id": "299_standard",
        "name": "299 标准版",
        "base": 299,
        "data_quota_gb": 60,
        "data_overage_per_gb": 2,
        "voice_quota_min": 600,
        "voice_overage_per_min": 0.1,
    },
    "399_premium": {
        "id": "399_premium",
        "name": "399 尊享版(当前)",
        "base": 399,
        "data_quota_gb": 100,
        "data_overage_per_gb": 0,
        "voice_quota_min": 1000,
        "voice_overage_per_min": 0,
    },
}

S2_OFFERS = [
    {
        "id": "loyal_3yr_v1",
        "name": "老客户专属优惠",
        "discount": 0.9,
        "new_monthly_cost": 359,
        "savings_per_month": 40,
        "bonus": "家庭宽带提速 500M / 持续 6 个月",
        "valid_for_months": 12,
        "eligibility": "3年以上忠诚客户",
    },
    {
        "id": "data_pack_addon",
        "name": "流量加油包",
        "discount": 1.0,
        "new_monthly_cost": 399,
        "savings_per_month": 0,
        "bonus": "额外赠送 50G 国内流量 / 月",
        "valid_for_months": 6,
        "eligibility": "所有用户",
    },
]


# ========== S3: 投诉转人工场景 ==========
S3_COMPLAINT = {
    "phone": "13812345678",
    "previous_complaints": [
        {
            "ticket_id": "WO-20260601-077",
            "issue": "网速持续慢,影响家人在线学习",
            "status": "supposedly_resolved",
            "actual_resolved": False,
            "created_at": "2026-04-25",
        },
    ],
    "ai_handoff_summary": "客户因之前 WO-20260601-077 工单未解决而投诉,情绪激动,建议优先处理并提供升级方案",
    "suggested_agent_response_template": [
        "1. 先共情:'非常抱歉给您带来困扰'",
        "2. 致歉:'之前的处理没有彻底解决问题'",
        "3. 确认:'让我详细了解一下当前情况'",
        "4. 提供方案:'我会为您升级处理,优先调度技术团队'",
    ],
    "sentiment_score": 2,
    "urgency_level": "high",
    "recommended_actions": [
        "create_priority_ticket",
        "escalate_to_supervisor",
        "offer_compensation",
    ],
}


# ========== S4: 双向翻译场景 ==========
S4_TRANSLATION = {
    "phone": "13812345678",
    "callee": {
        "name": "Ahmed Al-Rashid",
        "phone": "+966-50-1234567",
        "language": "en",
        "company": "Saudi Logistics Co.",
        "country": "Saudi Arabia",
    },
    "context": "上次合同付款条款讨论",
    "preset_dialog": [
        {"speaker": "user_zh", "zh": "你好 Ahmed,关于上次合同的付款条款,我们这边的财务说需要分两期支付。",
         "en": "Hi Ahmed, regarding the payment terms from last contract, our finance department says we need to pay in two installments."},
        {"speaker": "ahmed_en", "en": "Hi, that's fine. The first installment can be made next Monday, and the second installment within 30 days.",
         "zh": "你好,这个安排可以。第一期款项可以下周一支付,第二期款项 30 天内完成。"},
        {"speaker": "user_zh", "zh": "好的,谢谢 Ahmed,稍后给您发邮件确认细节。",
         "en": "Great, thank you Ahmed. I'll send you an email shortly to confirm the details."},
        {"speaker": "ahmed_en", "en": "You're welcome, looking forward to it.",
         "zh": "不客气,期待您的邮件。"},
    ],
}


# ========== Mock API 函数 ==========

def get_contact_by_phone(phone: str) -> Optional[dict]:
    """根据电话号码查询客户画像"""
    if phone == "13812345678":
        return MOCK_CONTACT
    return None


def network_diagnose(phone: str, scenario: str = "s1") -> dict:
    """S1: 网络诊断"""
    if phone == "13812345678":
        return S1_DIAGNOSIS
    return {
        "phone": phone,
        "base_station": "BS-N/A",
        "load_percent": 0,
        "issue_type": "no_issue",
    }


def get_usage(phone: str) -> dict:
    """S2: 用户使用量"""
    if phone == "13812345678":
        return S2_USAGE
    return {"phone": phone, "monthly_data_gb": 0, "monthly_voice_minutes": 0}


def list_plans() -> list:
    """套餐列表"""
    return list(PLANS.values())


def calculate_actual_cost(plan: str, monthly_data_gb: float, monthly_voice_min: int) -> dict:
    """S2 核心 Tool: 计算实际花费(LLM 不能算错)"""
    rate = PLANS.get(plan)
    if not rate:
        return {"error": f"Unknown plan: {plan}"}

    data_overage = max(0, monthly_data_gb - rate["data_quota_gb"])
    data_overage_cost = data_overage * rate["data_overage_per_gb"]

    voice_overage = max(0, monthly_voice_min - rate["voice_quota_min"])
    voice_overage_cost = voice_overage * rate["voice_overage_per_min"]

    total = rate["base"] + data_overage_cost + voice_overage_cost

    current_total = 399  # 当前套餐
    delta_vs_current = total - current_total

    return {
        "plan": plan,
        "plan_name": rate["name"],
        "base_cost": rate["base"],
        "data_quota_gb": rate["data_quota_gb"],
        "data_used_gb": monthly_data_gb,
        "data_overage_gb": round(data_overage, 1),
        "data_overage_per_gb": rate["data_overage_per_gb"],
        "data_overage_cost": round(data_overage_cost, 2),
        "voice_quota_min": rate["voice_quota_min"],
        "voice_used_min": monthly_voice_min,
        "voice_overage_min": voice_overage,
        "voice_overage_per_min": rate["voice_overage_per_min"],
        "voice_overage_cost": round(voice_overage_cost, 2),
        "total": round(total, 2),
        "vs_current": round(delta_vs_current, 2),
        "savings": round(-delta_vs_current, 2) if delta_vs_current < 0 else 0,
        "recommendation": "save" if delta_vs_current < 0 else "more_expensive",
    }


def get_offers(phone: str) -> list:
    """S2: 获取可用的挽留优惠"""
    return S2_OFFERS


def apply_offer(phone: str, offer_id: str) -> dict:
    """S2: 激活优惠"""
    offer = next((o for o in S2_OFFERS if o["id"] == offer_id), None)
    if not offer:
        return {"success": False, "error": f"Offer not found: {offer_id}"}

    return {
        "success": True,
        "offer_id": offer_id,
        "offer_name": offer["name"],
        "phone": phone,
        "activation_id": f"ACT-{offer_id.upper()}-{phone[-4:]}",
        "effective_date": "下个账单周期",
        "message": f"已为您激活{offer['name']},新月费 ¥{offer['new_monthly_cost']}",
    }


def create_ticket(phone: str, issue_type: str, priority: str = "normal", description: str = "") -> dict:
    """创建工单"""
    return {
        "success": True,
        "ticket_id": f"WO-20260605-{hash(phone + issue_type) % 1000:03d}",
        "phone": phone,
        "issue_type": issue_type,
        "priority": priority,
        "description": description,
        "status": "created",
        "estimated_resolution_minutes": 30 if priority == "high" else 120,
        "assigned_team": "网络优化组" if issue_type == "slow_network" else "技术支持组",
    }


def grant_voucher(phone: str, data_mb: int, reason: str = "compensation") -> dict:
    """发放流量包"""
    return {
        "success": True,
        "voucher_id": f"VCH-{hash(phone) % 10000:04d}",
        "phone": phone,
        "data_mb": data_mb,
        "data_gb": round(data_mb / 1024, 2),
        "reason": reason,
        "valid_days": 30,
        "message": f"已为您发放 {data_mb / 1024:.0f}G 免费流量包,有效期 30 天",
    }


def get_complaint_context(phone: str) -> dict:
    """S3: 投诉相关上下文"""
    return S3_COMPLAINT


def get_translation_context(phone: str) -> dict:
    """S4: 翻译会话上下文"""
    return S4_TRANSLATION


def fallback_translate(text: str, source_lang: str, target_lang: str) -> str:
    """简易翻译 fallback (不使用 LLM 时)"""
    # 查找预设对话
    for entry in S4_TRANSLATION["preset_dialog"]:
        if source_lang == "zh" and entry.get("zh", "").strip() == text.strip():
            return entry.get("en", text)
        if source_lang == "en" and entry.get("en", "").strip() == text.strip():
            return entry.get("zh", text)
    return f"[{source_lang}->{target_lang}] {text}"
