from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

load_dotenv()

DATABASE_URL_P = os.getenv("DATABASE_URL_P")

engine = create_engine(DATABASE_URL_P, echo=False)

SessionLocal = sessionmaker(
    bind = engine,
    autoflush=False,
    expire_on_commit=False
)

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    except:
        db.close()
