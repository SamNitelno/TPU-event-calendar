from fastapi import FastAPI, HTTPException, Query, Depends
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from datetime import date
from typing import List, Optional

from config import DB_URL, PAGE_SIZE
from models import Base, Event, Category
from schemas import EventOut, EventsPageOut, EventDetailOut, CategoryOut

app = FastAPI(title="Календарь мероприятий ВУЗа (API только из БД)")

engine = create_engine(DB_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

@app.get("/categories", response_model=List[CategoryOut])
def get_categories(db: Session = Depends(get_db)):
    cats = db.query(Category).all()
    return [{"id": c.id, "name": c.name} for c in cats]

@app.get("/events", response_model=EventsPageOut)
def get_events(
    category: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    query = db.query(Event)

    if category:
        query = query.filter(Event.category.has(name=category))
    if date_from:
        query = query.filter(Event.event_date >= date_from)
    if date_to:
        query = query.filter(Event.event_date <= date_to)
    if q:
        query = query.filter(Event.description.ilike(f"%{q}%"))

    total = query.count()
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    items = query.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()

    result_items = []
    for e in items:
        result_items.append(EventOut(
            id=e.id,
            date=e.event_date.isoformat() if e.event_date else None,
            time=e.event_time.strftime("%H:%M") if e.event_time else None,
            place=e.place,
            category=e.category.name if e.category else None,
            description=e.description,
            link=e.link,
            source_community_id=e.owner_id,
            status=e.status,
        ))

    return EventsPageOut(page=page, total_pages=total_pages, total_items=total, items=result_items)

@app.get("/events/{event_id}", response_model=EventDetailOut)
def get_event(event_id: int, db: Session = Depends(get_db)):
    e = db.query(Event).filter(Event.id == event_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")
    return EventDetailOut(
        id=e.id,
        date=e.event_date.isoformat() if e.event_date else None,
        time=e.event_time.strftime("%H:%M") if e.event_time else None,
        place=e.place,
        category=e.category.name if e.category else None,
        description=e.description,
        link=e.link,
        source_community_id=e.owner_id,
        status=e.status,
        raw_text=e.raw_text,
    )
