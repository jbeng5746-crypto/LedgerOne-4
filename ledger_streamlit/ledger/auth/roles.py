import os, json, hashlib, uuid, datetime, pathlib, random, string
BASE = pathlib.Path(__file__).resolve().parents[2] / "data"
BASE.mkdir(parents=True, exist_ok=True)

def _data_path(name: str):
    p = BASE / (name + ".json")
    if not p.exists():
        with open(p,"w",encoding="utf-8") as f: json.dump({},f)
    return p

def _read(name: str):
    with open(_data_path(name),"r",encoding="utf-8") as f: return json.load(f)

def _write(name: str, obj):
    with open(_data_path(name),"w",encoding="utf-8") as f: json.dump(obj,f,indent=2,default=str)

def _hash_password(pw: str, salt: bytes | None = None) -> str: 
    if salt is None: 
        salt = os.urandom(32)
    pwdhash = hashlib.pbkdf2_hmac('sha256', pw.encode('utf-8'), salt, 100000)
    return salt.hex() + ':' + pwdhash.hex()

def _verify_password(stored_password: str, provided_password: str) -> bool:
    salt, pwdhash = stored_password.split(':')
    return stored_password == _hash_password(provided_password, bytes.fromhex(salt))
def _random_password(): return "".join(random.choice(string.ascii_letters+string.digits) for _ in range(12))
def _now(): return datetime.datetime.utcnow().isoformat()+"Z"

class RoleManager:
    DEFAULT_ROLES = {
        "ceo": {"description":"Chief Executive Officer","permissions":["*"]},
        "finance_manager":{"description":"Finance Manager","permissions":["ledger.*","reports.*","payroll.*"]},
        "account_manager":{"description":"Account Manager","permissions":["invoices.*","ledger.*"]},
        "hr_manager":{"description":"HR Manager","permissions":["employees.*","payroll.view"]},
        "fleet_manager":{"description":"Fleet Manager","permissions":["fleet.*"]},
        "payroll_officer":{"description":"Payroll Officer","permissions":["payroll.run","payroll.view"]},
        "approver_lvl1":{"description":"Level 1 Approver","permissions":["approvals.approve_lvl1"]},
        "approver_lvl2":{"description":"Level 2 Approver","permissions":["approvals.approve_lvl2"]},
        "viewer":{"description":"Read-only","permissions":["reports.view"]}
    }

    def __init__(self):
        self.tenants=_read("tenants")
        self.users=_read("users")
        self.roles=_read("roles")
        if "superadmin" not in self.roles:
            self.roles["superadmin"]={"id":"superadmin","tenant_id":None,"name":"superadmin","permissions":["*"],"created_at":_now(),"created_by":"system"}
            _write("roles",self.roles)

    def save(self):
        _write("tenants",self.tenants); _write("users",self.users); _write("roles",self.roles)

    def create_tenant_with_admin(self,tenant_name,admin_email,admin_password=None,industry="generic"):
        tid=str(uuid.uuid4()); self.tenants[tid]={"id":tid,"name":tenant_name,"industry":industry,"created_at":_now()}
        for rname,meta in self.DEFAULT_ROLES.items():
            rid=f"{tid}:{rname}"
            self.roles[rid]={"id":rid,"tenant_id":tid,"name":rname,"description":meta["description"],"permissions":meta["permissions"],"created_at":_now()}
        if admin_password is None: admin_password=_random_password()
        uid=str(uuid.uuid4())
        self.users[uid]={"id":uid,"tenant_id":tid,"email":admin_email,"password_hash":_hash_password(admin_password),"roles":[f"{tid}:ceo"],"created_at":_now()}
        self.save(); return {"tenant_id":tid,"user_id":uid,"password":admin_password}

    def get_user_effective_permissions(self,user_id):
        if user_id not in self.users: raise KeyError("user not found")
        perms=set()
        for rid in self.users[user_id].get("roles",[]):
            role=self.roles.get(rid)
            if role: perms.update(role.get("permissions",[]))
        return list(perms)

# Simple logout logic (later hooked to Streamlit session state)
def logout(session:dict):
    session.clear()
    return True
