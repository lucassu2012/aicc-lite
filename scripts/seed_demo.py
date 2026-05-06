"""一键灌入种子数据 + 启动 demo 检查"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database import init_db, AsyncSessionLocal
from app.seed import seed_data


async def main():
    print("📦 初始化数据库...")
    await init_db()
    async with AsyncSessionLocal() as s:
        result = await seed_data(s)
        if result:
            print("✅ 种子数据已灌入")
        else:
            print("ℹ️  种子数据已存在,跳过")
    print("\n✨ Demo 准备就绪!")
    print("   启动后端: cd backend && python -m uvicorn app.main:app --reload")
    print("   访问演示: http://localhost:8000")


if __name__ == "__main__":
    asyncio.run(main())
