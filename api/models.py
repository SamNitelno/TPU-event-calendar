from sqlalchemy import Column, Integer, String, Text, Date, Time, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, nullable=False)
    owner_id = Column(Integer, nullable=False)
    event_date = Column(Date, nullable=True)  # None → needs_review
    event_time = Column(Time, nullable=True)
    place = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    description = Column(Text, nullable=False)
    link = Column(String, nullable=False)
    raw_text = Column(Text, nullable=False)
    status = Column(String, default="needs_review")  # verified / needs_review
