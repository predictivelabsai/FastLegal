import os, uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, Text, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID

DATABASE_URL = os.getenv("DB_URL", "postgresql://localhost/openharvey")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def utcnow(): return datetime.now(timezone.utc)
def genuuid(): return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=False), primary_key=True, default=genuuid)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    display_name = Column(String)
    organisation = Column(String)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    profile = relationship("UserProfile", uselist=False, back_populates="user", cascade="all, delete-orphan")

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(UUID(as_uuid=False), primary_key=True, default=genuuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    tier = Column(String, default="Free")
    preferred_model = Column(String, default="gpt-4o-mini")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    user = relationship("User", back_populates="profile")

class Project(Base):
    __tablename__ = "projects"
    id = Column(UUID(as_uuid=False), primary_key=True, default=genuuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    shared_with = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="project", cascade="all, delete-orphan")
    user = relationship("User")

class Document(Base):
    __tablename__ = "documents"
    id = Column(UUID(as_uuid=False), primary_key=True, default=genuuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    file_type = Column(String)
    file_path = Column(String)
    size_bytes = Column(Integer, default=0)
    page_count = Column(Integer)
    status = Column(String, default="ready")
    folder_id = Column(UUID(as_uuid=False), ForeignKey("project_subfolders.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    project = relationship("Project", back_populates="documents")

class Chat(Base):
    __tablename__ = "chats"
    id = Column(UUID(as_uuid=False), primary_key=True, default=genuuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan", order_by="ChatMessage.created_at")
    project = relationship("Project", back_populates="chats")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(UUID(as_uuid=False), primary_key=True, default=genuuid)
    chat_id = Column(UUID(as_uuid=False), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    chat = relationship("Chat", back_populates="messages")

class Workflow(Base):
    __tablename__ = "workflows"
    id = Column(UUID(as_uuid=False), primary_key=True, default=genuuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    title = Column(String, nullable=False)
    type = Column(String, default="chat")
    prompt_md = Column(Text)
    columns_config = Column(JSON)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

class TabularReview(Base):
    __tablename__ = "tabular_reviews"
    id = Column(UUID(as_uuid=False), primary_key=True, default=genuuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String)
    columns_config = Column(JSON)
    workflow_id = Column(UUID(as_uuid=False), ForeignKey("workflows.id", ondelete="SET NULL"))
    shared_with = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    cells = relationship("TabularCell", back_populates="review", cascade="all, delete-orphan")

class TabularCell(Base):
    __tablename__ = "tabular_cells"
    id = Column(UUID(as_uuid=False), primary_key=True, default=genuuid)
    review_id = Column(UUID(as_uuid=False), ForeignKey("tabular_reviews.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=False), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    column_index = Column(Integer, nullable=False)
    content = Column(Text)
    status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    review = relationship("TabularReview", back_populates="cells")

class ProjectSubfolder(Base):
    __tablename__ = "project_subfolders"
    id = Column(UUID(as_uuid=False), primary_key=True, default=genuuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    parent_folder_id = Column(UUID(as_uuid=False), ForeignKey("project_subfolders.id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), default=utcnow)

def init_db():
    Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
