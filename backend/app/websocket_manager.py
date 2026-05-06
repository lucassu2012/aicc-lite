"""WebSocket 连接管理 - 实时事件推送"""
import json
import logging
from typing import Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """全局 WebSocket 连接池"""

    def __init__(self):
        # role -> [WebSocket]
        self.connections: dict[str, list[WebSocket]] = {
            "agent": [],
            "customer": [],
        }

    async def connect(self, ws: WebSocket, role: str = "agent"):
        await ws.accept()
        self.connections.setdefault(role, []).append(ws)
        logger.info(f"WS connected: role={role}, total={len(self.connections[role])}")

    def disconnect(self, ws: WebSocket, role: str = "agent"):
        if ws in self.connections.get(role, []):
            self.connections[role].remove(ws)

    async def send_to(self, ws: WebSocket, event: str, data: dict):
        try:
            await ws.send_text(json.dumps({"event": event, "data": data}, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"Send to single ws failed: {e}")

    async def broadcast(self, role: str, event: str, data: dict):
        """广播给指定 role 的所有连接"""
        message = json.dumps({"event": event, "data": data}, ensure_ascii=False)
        dead = []
        for ws in self.connections.get(role, []):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, role)

    async def broadcast_all(self, event: str, data: dict):
        for role in self.connections:
            await self.broadcast(role, event, data)


manager = ConnectionManager()
