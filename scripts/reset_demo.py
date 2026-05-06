"""一键重置 demo - 清空所有 conversation/message,保留种子数据"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import delete
from app.database import AsyncSessionLocal, init_db
from app.models import Conversation, Message


async def reset():
    await init_db()
    async with AsyncSessionLocal() as s:
        await s.execute(delete(Message))
        await s.execute(delete(Conversation))
        await s.commit()
    print("✅ Demo 已重置 (会话与消息已清空,种子数据保留)")


if __name__ == "__main__":
    asyncio.run(reset())
