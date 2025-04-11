from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()
engine = create_engine(os.getenv('DATABASE_URL'))
Session = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    first_name = Column(String)
    last_name = Column(String)
    phone = Column(String)
    wallet_address = Column(String)
    balance = Column(Float, default=0.0)
    spins_left = Column(Integer, default=3)
    referral_code = Column(String)

# Crea le tabelle
Base.metadata.create_all(engine)

def get_db_session():
    return Session()