"""种子数据 - 张先生 138xxxxxxxx + 4 场景预埋"""
import secrets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    Account, User, Contact, Inbox,
    MockScenarioState,
)
from . import mocks


async def seed_data(session: AsyncSession):
    """灌入演示种子数据。已存在则跳过。"""

    # 检查是否已有数据
    result = await session.execute(select(Account).where(Account.id == 1))
    if result.scalar_one_or_none():
        return False  # 已经初始化

    # 1. Account
    account = Account(id=1, name="AICC-Lite Demo")
    session.add(account)

    # 2. Users
    admin = User(
        id=1, account_id=1,
        email="admin@aicc.local", name="管理员",
        role="admin",
        pubsub_token=secrets.token_urlsafe(32),
        password_hash="demo",
    )
    agent = User(
        id=2, account_id=1,
        email="agent1@aicc.local", name="客服小李",
        role="agent",
        pubsub_token="agent-demo-token",
        password_hash="demo",
    )
    session.add_all([admin, agent])

    # 3. Inboxes
    voice_inbox = Inbox(
        id=1, account_id=1,
        name="语音热线",
        channel_type="Channel::Voice",
        channel_id=1,
    )
    web_inbox = Inbox(
        id=2, account_id=1,
        name="Web Widget",
        channel_type="Channel::WebWidget",
        channel_id=1,
    )
    session.add_all([voice_inbox, web_inbox])

    # 4. Contact - 张先生
    contact = Contact(
        id=1, account_id=1,
        name="张先生",
        phone="13812345678",
        email="zhang@example.com",
        custom_attributes={
            "tier": "loyal_3yr",
            "current_plan": "399_premium",
            "registration_date": "2023-03-15",
            "preferred_language": "zh",
            "tags": ["VIP客户", "3年老客户", "高活跃"],
        },
    )
    session.add(contact)

    # 5. Mock 场景数据
    scenarios = [
        MockScenarioState(phone="13812345678", scenario_id="s1", state=mocks.S1_DIAGNOSIS),
        MockScenarioState(phone="13812345678", scenario_id="s2", state={
            "usage": mocks.S2_USAGE,
            "offers": mocks.S2_OFFERS,
        }),
        MockScenarioState(phone="13812345678", scenario_id="s3", state=mocks.S3_COMPLAINT),
        MockScenarioState(phone="13812345678", scenario_id="s4", state=mocks.S4_TRANSLATION),
    ]
    session.add_all(scenarios)

    await session.commit()
    return True
