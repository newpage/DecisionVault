from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base
from app.models import KnowledgeCard, Permission, Role, Tenant
from app.seed import seed


def seeded_session(monkeypatch, *, include_demo: bool) -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(settings, "dv_seed_demo_data", include_demo)
    db = Session(engine)
    seed(db)
    return db


def test_core_seed_creates_required_access_data_without_demo_cards(monkeypatch):
    with seeded_session(monkeypatch, include_demo=False) as db:
        assert db.scalar(select(func.count()).select_from(Tenant)) == 1
        assert db.scalar(select(func.count()).select_from(Role)) == 1
        assert db.scalar(select(func.count()).select_from(Permission)) > 0
        assert db.scalar(select(func.count()).select_from(KnowledgeCard)) == 0


def test_demo_seed_is_opt_in_and_idempotent(monkeypatch):
    with seeded_session(monkeypatch, include_demo=True) as db:
        titles = set(db.scalars(select(KnowledgeCard.title)))
        assert "Electronic Manufacturer Quality Certification" in titles
        assert "Electronics Manufacturing Capability Review" in titles

        seed(db)

        assert db.scalar(select(func.count()).select_from(KnowledgeCard)) == 4
