
import uuid
from ledger.approvals.engine import WorkflowManager
from ledger.auth.roles import RoleManager

def test_workflow_approval_flow(tmp_path):
    # Setup role manager and workflow manager
    rm = RoleManager()
    # create a tenant for this test
    res = rm.create_tenant_with_admin("WFTestCo", "admin@wftest.local", admin_password="Pw123!")
    tid = res["tenant_id"]
    # ensure approver roles exist (they are created by RoleManager)
    # Create a rule: for invoices with amount >= 100000 require approver_lvl1 and approver_lvl2 with quorum 2
    wm = WorkflowManager()
    rule = wm.create_rule(tenant_id=tid, doc_type="invoice", conditions={"min_amount":100000}, required_roles=["approver_lvl1","approver_lvl2"], quorum=2)
    # Create a document that matches the rule
    doc_id = str(uuid.uuid4())
    doc = {"id":doc_id, "amount":150000, "vendor":"BigVendor"}
    # enforce_posting_allowed should create an instance and return False (blocked)
    allowed_initial = wm.enforce_posting_allowed(tenant_id=tid, doc_type="invoice", doc_id=doc_id, doc=doc)
    assert allowed_initial is False
    # find the created instance
    insts = list(wm.instances.values())
    assert any(i["doc_id"]==doc_id for i in insts)
    instance = next(i for i in insts if i["doc_id"]==doc_id)
    iid = instance["id"]
    # approve as approver_lvl1
    # create a user with that role
    uid = str(uuid.uuid4())
    rm.users[uid] = {"id":uid,"tenant_id":tid,"email":"approver1@wf.local","password_hash":"x","roles":[f"{tid}:approver_lvl1"],"created_at":rm._now()}
    rm.save()
    wm.add_approval(instance_id=iid, user_id=uid, role_name="approver_lvl1", decision="approved", comment="ok")
    # still not enough (quorum 2)
    assert wm.is_instance_approved(iid) is False
    # approve as approver_lvl2
    uid2 = str(uuid.uuid4())
    rm.users[uid2] = {"id":uid2,"tenant_id":tid,"email":"approver2@wf.local","password_hash":"x","roles":[f"{tid}:approver_lvl2"],"created_at":rm._now()}
    rm.save()
    wm.add_approval(instance_id=iid, user_id=uid2, role_name="approver_lvl2", decision="approved", comment="ok2")
    # now instance should be approved
    assert wm.is_instance_approved(iid) is True
    # enforce_posting_allowed should now return True for same doc
    allowed_after = wm.enforce_posting_allowed(tenant_id=tid, doc_type="invoice", doc_id=doc_id, doc=doc)
    assert allowed_after is True
