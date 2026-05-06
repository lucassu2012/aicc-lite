"""数据模型 - SQLAlchemy ORM 与 Pydantic"""
from datetime import datetime
from typing import Optional, Any
from enum import Enum

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean, Text, BigInteger
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, Field

Base = declarative_base()


# ============ Enums ============

class ConversationStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
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


# ============ ORM Models ============

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(100))
    role = Column(String(20), default="agent")
    pubsub_token = Column(String(64), unique=True)
    password_hash = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())


class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    name = Column(String(100))
    phone = Column(String(20), index=True)
    email = Column(String(255))
    custom_attributes = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())

    conversations = relationship("Conversation", back_populates="contact")


class Inbox(Base):
    __tablename__ = "inboxes"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    name = Column(String(100), nullable=False)
    channel_type = Column(String(50), nullable=False)
    channel_id = Column(Integer, nullable=False)
    enable_auto_assignment = Column(Boolean, default=True)


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    inbox_id = Column(Integer, ForeignKey("inboxes.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    version = Column(BigInteger, default=1, nullable=False)
    scenario_id = Column(String(20), nullable=True)
    additional_attributes = Column(JSON, default=dict)
    custom_attributes = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    contact = relationship("Contact", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation",
                            order_by="Message.created_at", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    inbox_id = Column(Integer, ForeignKey("inboxes.id"), nullable=False)
    content = Column(Text)
    message_type = Column(Integer, default=0)  # 0=incoming, 1=outgoing, 2=activity
    sender_type = Column(String(20), nullable=False)
    sender_id = Column(Integer, nullable=False)
    content_attributes = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")


class MockScenarioState(Base):
    __tablename__ = "mock_scenario_states"
    id = Column(Integer, primary_key=True)
    phone = Column(String(20), nullable=False)
    scenario_id = Column(String(20), nullable=False)
    state = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())


# ============ Pydantic Schemas ============

class ContactSchema(BaseModel):
    id: int
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    custom_attributes: dict = {}

    class Config:
        from_attributes = True


class MessageSchema(BaseModel):
    id: int
    conversation_id: int
    content: str
    message_type: int
    sender_type: str
    sender_id: int
    content_attributes: dict = {}
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationSchema(BaseModel):
    id: int
    account_id: int
    inbox_id: int
    contact_id: int
    assignee_id: Optional[int] = None
    status: str
    scenario_id: Optional[str] = None
    additional_attributes: dict = {}
    created_at: datetime
    updated_at: datetime
    contact: Optional[ContactSchema] = None
    messages: list[MessageSchema] = []

    class Config:
        from_attributes = True


class MessageCreateRequest(BaseModel):
    content: str
    sender_type: str = "Contact"
    sender_id: int = 1
    content_attributes: dict = {}


class ConversationCreateRequest(BaseModel):
    contact_id: int = 1
    inbox_id: int = 1
    scenario_id: Optional[str] = None


class HandoffRequest(BaseModel):
    reason: str = "complaint"
    sentiment_score: int = 5
    ai_summary: Optional[str] = None


class StatusChangeRequest(BaseModel):
    status: str


class TranslationRequest(BaseModel):
    text: str
    source_lang: str = "zh"
    target_lang: str = "en"
