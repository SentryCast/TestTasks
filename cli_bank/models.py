from sqlalchemy import Column, DateTime, Float, \
    String, Integer, ForeignKey, func
from sqlalchemy.orm import relationship, backref, Session
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    balance = Column(Float)
    
class Ledger(Base):
    __tablename__ = "ledger"
    
    id = Column(Integer, primary_key=True)
    
    recepient_id = Column(Integer, ForeignKey('user.id'))
    operation_date = Column(DateTime, default=func.now())
    description = Column(String(300))
    
    previous_balance = Column(Float, nullable=False)
    current_balance = Column(Float, nullable=False)
    
    recepient = relationship("User", foreign_keys=[recepient_id])
    
from sqlalchemy import create_engine
# 'sqlite://' is sqlite's :memory: equivalent, so db will be stored in RAM
engine = create_engine('sqlite://')

from sqlalchemy.orm import sessionmaker
session = sessionmaker()
session.configure(bind=engine)
Base.metadata.create_all(engine)

