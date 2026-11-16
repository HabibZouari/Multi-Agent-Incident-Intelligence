"""SQLAlchemy models and engine setup.

PostgreSQL + pgvector is used when reachable; otherwise the app transparently falls back to a
local SQLite file so the project can be explored without Docker.
"""

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.core.config import settings
from backend.core.logger import logger

SQLITE_URL = "sqlite:///./resolveai_local.db"


def get_engine() -> Engine:
    try:
        url = settings.database_url
        engine = create_engine(url, connect_args={"check_same_thread": False}) if url.startswith("sqlite") else create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        logger.info("Connected to database: %s", engine.url.render_as_string(hide_password=True))
        return engine
    except Exception as exc:  # noqa: BLE001 - any connection failure triggers the fallback
        logger.warning("Primary database unavailable (%s). Falling back to local SQLite.", type(exc).__name__)
        return create_engine(SQLITE_URL, connect_args={"check_same_thread": False})


engine = get_engine()
IS_POSTGRES = engine.dialect.name == "postgresql"
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

if IS_POSTGRES:
    from pgvector.sqlalchemy import Vector

    EmbeddingType = Vector(settings.embedding_dim)
else:
    EmbeddingType = JSON


class DocumentModel(Base):
    __tablename__ = "documents"
    document_id = Column(String, primary_key=True)
    filename = Column(String, index=True)
    document_type = Column(String, index=True)
    service_name = Column(String, index=True)
    chunk_id = Column(Integer, primary_key=True)
    content = Column(Text)
    embedding = Column(EmbeddingType)
    metadata_json = Column(JSON)


class IncidentModel(Base):
    __tablename__ = "incidents"
    incident_id = Column(String, primary_key=True)
    title = Column(String)
    severity = Column(String, index=True)
    service_name = Column(String, index=True)
    status = Column(String)
    category = Column(String, index=True)
    symptoms = Column(Text)
    root_cause = Column(Text)
    resolution = Column(Text)
    created_at = Column(DateTime)
    resolved_at = Column(DateTime)


class ServiceModel(Base):
    __tablename__ = "services"
    service_id = Column(String, primary_key=True)
    name = Column(String, unique=True, index=True)
    tier = Column(String)
    owner = Column(String)
    dependencies = Column(JSON)


class DeploymentModel(Base):
    __tablename__ = "deployments"
    deployment_id = Column(String, primary_key=True)
    service_name = Column(String, index=True)
    service_id = Column(String)
    version = Column(String)
    deployed_at = Column(DateTime)
    author = Column(String)
    status = Column(String)
    changes_summary = Column(Text)


class EvalDatasetModel(Base):
    __tablename__ = "eval_dataset"
    question_id = Column(String, primary_key=True)
    category = Column(String, index=True)
    query = Column(Text)
    expected_answer = Column(Text)
    expected_route = Column(String)
    ground_truth_docs = Column(JSON)
    expected_tools = Column(JSON)


def create_schema() -> None:
    """Create the pgvector extension (PostgreSQL only) and all tables."""
    if IS_POSTGRES:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    Base.metadata.create_all(bind=engine)


def init_db() -> None:
    create_schema()
    logger.info("Database tables created successfully.")


if __name__ == "__main__":
    init_db()
