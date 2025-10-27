from app.models import Base
from sqlalchemy import create_engine
import os

# Use the same database URL as your main app
DATABASE_URL = "sqlite:///./theclamed.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create all tables
Base.metadata.create_all(bind=engine)
print("✅ All database tables created successfully!")