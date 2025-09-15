
"""
File-backed Workflow & Approvals engine.

Data files:
 - data/workflows/workflow_rules.json  (dict rule_id -> rule)
 - data/workflows/workflow_instances.json (dict instance_id -> instance)

Rule structure:
{
  "id": "<uuid>",
  "tenant_id": "<tid>",
  "doc_type": "invoice",
  "conditions": {"min_amount": 100000},
  "required_roles": ["approver_lvl1","approver_lvl2"],
  "quorum": 2,
  "created_at": "<ts>"
}

Instance structure:
{
  "id": "<uuid>",
  "rule_id": "<rule_id>",
  "tenant_id": "<tid>",
  "doc_type": "invoice",
  "doc_id": "<doc id>",
  "state": "pending",
  "approvals": [
      {"user_id":"...", "role_name":"approver_lvl1","decision":"approved","comment":"ok","ts":...}
  ],
  "created_at":"<ts>"
}
"""
import json, pathlib, uuid, datetime
from typing import Dict, Any, List

BASE = pathlib.Path(__file__).resolve().parents[2] / "data" / "workflows"
BASE.mkdir(parents=True, exist_ok=True)

RULES_FILE = BASE / "workflow_rules.json"
INSTANCES_FILE = BASE / "workflow_instances.json"

def _ensure_file(p: pathlib.Path):
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump({}, f)

def _read(name_file: pathlib.Path) -> Dict:
    _ensure_file(name_file)
    with open(name_file, "r", encoding="utf-8") as f:
        return json.load(f)

def _write(name_file: pathlib.Path, obj: Dict):
    _ensure_file(name_file)
    with open(name_file.with_suffix(".tmp"), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)
    name_file.replace(name_file.with_suffix(""))

class WorkflowManager:
    def __init__(self):
        self.rules = _read(RULES_FILE)
        self.instances = _read(INSTANCES_FILE)

    def save(self):
        _write(RULES_FILE, self.rules)
        _write(INSTANCES_FILE, self.instances)

    def create_rule(self, tenant_id: str, doc_type: str, conditions: Dict[str, Any], required_roles: List[str], quorum: int = 1) -> Dict:
        rid = str(uuid.uuid4())
        rule = {
            "id": rid,
            "tenant_id": tenant_id,
            "doc_type": doc_type,
            "conditions": conditions,
            "required_roles": required_roles,
            "quorum": quorum,
            "created_at": datetime.datetime.utcnow().isoformat()+"Z"
        }
        self.rules[rid] = rule
        self.save()
        return rule

    def list_rules(self, tenant_id: str = None):
        if tenant_id:
            return [r for r in self.rules.values() if r.get("tenant_id")==tenant_id]
        return list(self.rules.values())

    def match_rule_for_doc(self, tenant_id: str, doc_type: str, doc: Dict[str,Any]):
        """
        Find the first rule that matches given document (very simple conditional logic).
        Conditions supported: min_amount, max_amount, vendor_in (list)
        """
        for r in self.rules.values():
            if r.get("tenant_id") != tenant_id:
                continue
            if r.get("doc_type") != doc_type:
                continue
            cond = r.get("conditions",{})
            # min_amount
            min_amt = cond.get("min_amount")
            max_amt = cond.get("max_amount")
            vendor_in = cond.get("vendor_in")
            amt = doc.get("amount")
            if min_amt is not None and (amt is None or amt < min_amt):
                continue
            if max_amt is not None and (amt is None or amt > max_amt):
                continue
            if vendor_in is not None and doc.get("vendor") not in vendor_in:
                continue
            return r
        return None

    def create_instance(self, rule_id: str, doc_id: str, tenant_id: str, doc_type: str) -> Dict:
        iid = str(uuid.uuid4())
        inst = {
            "id": iid,
            "rule_id": rule_id,
            "tenant_id": tenant_id,
            "doc_type": doc_type,
            "doc_id": doc_id,
            "state": "pending",
            "approvals": [],
            "created_at": datetime.datetime.utcnow().isoformat()+"Z"
        }
        self.instances[iid] = inst
        self.save()
        return inst

    def add_approval(self, instance_id: str, user_id: str, role_name: str, decision: str, comment: str = "") -> Dict:
        inst = self.instances.get(instance_id)
        if not inst:
            raise KeyError("instance not found")
        # append approval
        rec = {"user_id": user_id, "role_name": role_name, "decision": decision, "comment": comment, "ts": datetime.datetime.utcnow().isoformat()+"Z"}
        inst.setdefault("approvals", []).append(rec)
        # determine if quorum met
        rule = self.rules.get(inst.get("rule_id"))
        if rule:
            # count unique approvals from required roles with decision=approved
            req_roles = set(rule.get("required_roles", []))
            approved_roles = set([a["role_name"] for a in inst.get("approvals", []) if a.get("decision")=="approved" and a.get("role_name") in req_roles])
            if len(approved_roles) >= int(rule.get("quorum",1)):
                inst["state"] = "approved"
        self.instances[instance_id] = inst
        self.save()
        return rec

    def is_instance_approved(self, instance_id: str) -> bool:
        inst = self.instances.get(instance_id)
        if not inst:
            return False
        return inst.get("state") == "approved"

    def get_instance(self, instance_id: str) -> Dict:
        return self.instances.get(instance_id)

    def enforce_posting_allowed(self, tenant_id: str, doc_type: str, doc_id: str, doc: Dict) -> bool:
        """
        Called before posting a document to ledger.
        Returns True if allowed (no matching rule or rule satisfied), False if blocked pending approval.
        """
        rule = self.match_rule_for_doc(tenant_id, doc_type, doc)
        if not rule:
            return True
        # find existing instance for this doc if any
        for inst in self.instances.values():
            if inst.get("doc_id")==doc_id and inst.get("doc_type")==doc_type and inst.get("tenant_id")==tenant_id:
                return inst.get("state")=="approved"
        # no instance yet -> create one and block
        inst = self.create_instance(rule_id=rule["id"], doc_id=doc_id, tenant_id=tenant_id, doc_type=doc_type)
        return False
