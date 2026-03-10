from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./scans.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ScanEvent(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    barcode_data = Column(String, index=True, nullable=False)
    count = Column(Integer, default=1, server_default='1')
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

def init_db():
    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE scans ADD COLUMN count INTEGER DEFAULT 1"))
    except Exception:
        pass
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
