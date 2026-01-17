from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./linkedin_scheduler.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    stripe_customer_id = Column(String, nullable=True)
    subscription_status = Column(String, default="free")  # free, trial, paid
    linkedin_access_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    name = Column(String)
    search_query = Column(String)  # "recruiter python Nigeria"
    message_template = Column(String)
    daily_limit = Column(Integer, default=20)
    status = Column(String, default="active")  # active, paused, completed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ConnectionLog(Base):
    __tablename__ = "connection_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, index=True)
    profile_url = Column(String)
    message_sent = Column(String)
    status = Column(String)  # pending, sent, accepted, rejected
    sent_at = Column(DateTime, nullable=True)

# Create tables
Base.metadata.create_all(bind=engine)