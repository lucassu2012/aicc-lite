"""核心业务服务 - 会话管理、状态机、消息"""
import logging
from typing import Optional
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    Conversation, Message, Contact, Inbox, User,
    ConversationStatus, MessageSenderType,
)

logger = logging.getLogger(__name__)


VALID_TRANSITIONS = {
    "pending": {"open", "resolved"},
    "open": {"resolved", "snoozed"},
    "snoozed": {"open", "resolved"},
    "resolved": {"open"},
}


class ConcurrentUpdateError(Exception):
    pass


class InvalidTransitionError(Exception):
    pass


class ConversationService:

    @staticmethod
    async def list_conversations(
        session: AsyncSession,
        account_id: int = 1,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> list[Conversation]:
        query = (
            select(Conversation)
            .where(Conversation.account_id == account_id)
            .options(selectinload(Conversation.contact), selectinload(Conversation.messages))
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        if status:
            query = query.where(Conversation.status == status)
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_conversation(
        session: AsyncSession,
        conversation_id: int,
    ) -> Optional[Conversation]:
        query = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.contact), selectinload(Conversation.messages))
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_conversation(
        session: AsyncSession,
        contact_id: int = 1,
        inbox_id: int = 1,
        scenario_id: Optional[str] = None,
        account_id: int = 1,
    ) -> Conversation:
        conv = Conversation(
            account_id=account_id,
            inbox_id=inbox_id,
            contact_id=contact_id,
            scenario_id=scenario_id,
            status="pending",
            additional_attributes={"channel": "voice"},
        )
        session.add(conv)
        await session.commit()
        await session.refresh(conv)
        return conv

    @staticmethod
    async def transition_status(
        session: AsyncSession,
        conversation_id: int,
        to_status: str,
        actor: str = "system",
    ) -> Conversation:
        conv = await session.get(Conversation, conversation_id)
        if conv is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        from_status = conv.status
        if to_status not in VALID_TRANSITIONS.get(from_status, set()):
            raise InvalidTransitionError(
                f"Invalid transition: {from_status} -> {to_status}"
            )

        # version CAS
        result = await session.execute(
            update(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.version == conv.version,
            )
            .values(
                status=to_status,
                version=Conversation.version + 1,
            )
            .returning(Conversation.version)
        )
        if result.scalar_one_or_none() is None:
            raise ConcurrentUpdateError(
                f"Version mismatch on conv {conversation_id}"
            )

        # 添加状态变更活动消息
        activity_msg = Message(
            conversation_id=conversation_id,
            account_id=conv.account_id,
            inbox_id=conv.inbox_id,
            content=f"状态变更: {from_status} → {to_status} (by {actor})",
            message_type=2,
            sender_type=MessageSenderType.USER.value,
            sender_id=1,
            content_attributes={"activity": "status_change", "from": from_status, "to": to_status},
        )
        session.add(activity_msg)
        await session.commit()
        await session.refresh(conv)
        return conv

    @staticmethod
    async def assign_conversation(
        session: AsyncSession,
        conversation_id: int,
        assignee_id: int,
    ) -> Conversation:
        conv = await session.get(Conversation, conversation_id)
        if conv is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        conv.assignee_id = assignee_id
        # 自动转 open
        if conv.status == "pending":
            conv.status = "open"
            conv.version += 1
        await session.commit()
        await session.refresh(conv)
        return conv


class MessageService:

    @staticmethod
    async def add_message(
        session: AsyncSession,
        conversation_id: int,
        content: str,
        sender_type: str = "Contact",
        sender_id: int = 1,
        content_attributes: dict = None,
    ) -> Message:
        conv = await session.get(Conversation, conversation_id)
        if conv is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        msg_type = 0 if sender_type == "Contact" else 1
        msg = Message(
            conversation_id=conversation_id,
            account_id=conv.account_id,
            inbox_id=conv.inbox_id,
            content=content,
            message_type=msg_type,
            sender_type=sender_type,
            sender_id=sender_id,
            content_attributes=content_attributes or {},
        )
        session.add(msg)

        # 更新 conv.updated_at
        conv.version = (conv.version or 0) + 1

        await session.commit()
        await session.refresh(msg)
        return msg

    @staticmethod
    async def list_messages(
        session: AsyncSession,
        conversation_id: int,
    ) -> list[Message]:
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        return list(result.scalars().all())
