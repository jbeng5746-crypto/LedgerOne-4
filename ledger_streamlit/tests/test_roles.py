import pytest
from ledger.auth.roles import RoleManager

def test_signup_creates_tenant_and_admin():
    rm=RoleManager()
    res=rm.create_tenant_with_admin("TestCo","admin@testco.local","TestPass!")
    tid=res["tenant_id"]; uid=res["user_id"]
    assert tid in rm.tenants
    assert uid in rm.users
    roles=rm.users[uid]["roles"]
    assert any(r.endswith(":ceo") for r in roles)

def test_default_roles_exist():
    rm=RoleManager()
    if not rm.tenants:
        res=rm.create_tenant_with_admin("SmallCo","admin@small.local","pw"); tid=res["tenant_id"]
    else: tid=list(rm.tenants.keys())[0]
    tenant_roles=[v["name"] for k,v in rm.roles.items() if v.get("tenant_id")==tid]
    expected={"ceo","finance_manager","account_manager","hr_manager","fleet_manager","payroll_officer","approver_lvl1","approver_lvl2","viewer"}
    assert expected.issubset(set(tenant_roles))
