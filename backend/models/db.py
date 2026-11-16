import os
from sqlalchemy import create_engine, Column, String, Text, Integer, DateTime, JSON, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:CHANGE_ME@localhost:5432/resolveai")

def get_engine():
    try:
        eng = create_engine(DATABASE_URL)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1;"))
        return eng
    except Exception:
        sqlite_url = "sqlite:///./resolveai_local.db"
        eng = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        return eng

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DocumentModel(Base):
    __tablename__ = "documents"
    document_id = Column(String, primary_key=True)
    filename = Column(String, index=True)
    document_type = Column(String, index=True)
    service_name = Column(String, index=True)
    chunk_id = Column(Integer, primary_key=True)
    content = Column(Text)
    embedding = Column(JSON)
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
    ground_truth_docs = Column(JSON)
    expected_tools = Column(JSON)

def init_db():
    if "postgresql" in str(engine.url):
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        except Exception:
            pass
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

if __name__ == "__main__":
    init_db()
