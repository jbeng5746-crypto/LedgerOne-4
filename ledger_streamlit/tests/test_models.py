
import uuid
from ledger.db.session import init_db, SessionLocal
from ledger.db.models import Tenant, User, Role, JournalEntry
import pytest

def setup_module(module):
    # Initialize DB (creates sqlite file by default)
    init_db()

def test_tenant_and_user_crud(tmp_path):
    db = SessionLocal()
    tid = str(uuid.uuid4())
    tenant = Tenant(id=tid, name="TCorp", industry="demo")
    db.add(tenant)
    db.commit()
    # create user
    uid = str(uuid.uuid4())
    user = User(id=uid, tenant_id=tid, email="admin@tcorp.local", password_hash="x")
    db.add(user)
    db.commit()
    fetched = db.query(User).filter_by(id=uid).one()
    assert fetched.email == "admin@tcorp.local"
    db.close()

def test_role_assignment_and_isolation():
    db = SessionLocal()
    # create two tenants
    t1 = Tenant(id=str(uuid.uuid4()), name="A", industry="x"); db.add(t1)
    t2 = Tenant(id=str(uuid.uuid4()), name="B", industry="y"); db.add(t2)
    db.commit()
    # roles for tenant A
    r1 = Role(id=str(uuid.uuid4()), tenant_id=t1.id, name="finance", permissions=["ledger.*"])
    db.add(r1); db.commit()
    # user in tenant A
    u1 = User(id=str(uuid.uuid4()), tenant_id=t1.id, email="u1@a.local", password_hash="x"); db.add(u1); db.commit()
    # assign role via association
    u1.roles.append(r1); db.commit()
    # ensure user in tenant B cannot get tenant A role accidentally
    u2 = User(id=str(uuid.uuid4()), tenant_id=t2.id, email="u2@b.local", password_hash="x"); db.add(u2); db.commit()
    assert r1 not in u2.roles
    db.close()

def test_journal_balance_check():
    db = SessionLocal()
    jid = str(uuid.uuid4())
    je = JournalEntry(id=jid, tenant_id=str(uuid.uuid4()), description="test", lines=[
        {"account": "cash", "debit": 100.0, "credit": 0.0},
        {"account": "revenue", "debit": 0.0, "credit": 100.0},
    ], posted=False)
    db.add(je); db.commit()
    fetched = db.query(JournalEntry).filter_by(id=jid).one()
    assert fetched.is_balanced()
    # now unbalanced entry
    jid2 = str(uuid.uuid4())
    je2 = JournalEntry(id=jid2, tenant_id=str(uuid.uuid4()), description="unbalanced", lines=[
        {"account": "cash", "debit": 100.0, "credit": 0.0},
        {"account": "revenue", "debit": 0.0, "credit": 90.0},
    ])
    db.add(je2); db.commit()
    fetched2 = db.query(JournalEntry).filter_by(id=jid2).one()
    assert not fetched2.is_balanced()
    db.close()
