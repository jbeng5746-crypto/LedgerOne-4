
from sqlalchemy import (
    Column, String, Integer, Float, ForeignKey, DateTime, Boolean, JSON, Table, Text
)
from sqlalchemy.orm import relationship
from datetime import datetime
from ledger.db.session import Base

# association table for user roles
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
)

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    industry = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="tenant")
    roles = relationship("Role", back_populates="tenant")

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    email = Column(String, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_superadmin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="users")
    roles = relationship("Role", secondary=user_roles, back_populates="users")

class Role(Base):
    __tablename__ = "roles"
    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    permissions = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="roles")
    users = relationship("User", secondary=user_roles, back_populates="roles")

class WorkflowRule(Base):
    __tablename__ = "workflow_rules"
    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    doc_type = Column(String, nullable=False)
    conditions = Column(JSON, default={})
    required_roles = Column(JSON, default=[])
    quorum = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

class ApprovalRecord(Base):
    __tablename__ = "approval_records"
    id = Column(String, primary_key=True)
    workflow_instance_id = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role_id = Column(String, ForeignKey("roles.id"), nullable=False)
    decision = Column(String, nullable=False)  # 'approved' / 'rejected'
    comment = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Vendor(Base):
    __tablename__ = "vendors"
    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    canonical_name = Column(String, nullable=True)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

class Asset(Base):
    __tablename__ = "assets"
    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    description = Column(String, nullable=False)
    purchase_price = Column(Float, default=0.0)
    purchase_date = Column(DateTime, default=datetime.utcnow)
    depreciation_method = Column(String, default="straight_line")
    depreciation_life_months = Column(Integer, default=60)
    created_at = Column(DateTime, default=datetime.utcnow)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="KES")
    date = Column(DateTime, default=datetime.utcnow)
    description = Column(String, nullable=True)
    canonical_doc = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

class JournalEntry(Base):
    __tablename__ = "journal_entries"
    id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    entry_date = Column(DateTime, default=datetime.utcnow)
    description = Column(String, nullable=True)
    lines = Column(JSON, default=[])  # list of {account, debit, credit}
    posted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def is_balanced(self):
        total_debit = sum([l.get("debit", 0) for l in (self.lines or [])])
        total_credit = sum([l.get("credit", 0) for l in (self.lines or [])])
        return abs(total_debit - total_credit) < 1e-6
