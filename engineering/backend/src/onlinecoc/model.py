import copy, math, uuid
from .errors import require
from .contracts import validate_model
from . import chat

KINDS={"actor","bag","item","weapon","skill","status"}
def uid(): return uuid.uuid4().hex

def finite(value): return type(value) in (int,float) and math.isfinite(value) and abs(value)<=2**53-1

def entity(id,kind,name,owner=None,**numbers):
    return {"instanceId":id,"roomId":"demo","configurationId":"demo."+kind,"configurationRevision":"1",
            "typeRef":kind,"schemaVersion":1,"revision":1,"lifecycle":"active","name":name,
            "owner":owner,"visibility":"public","metadata":{},"tags":[],"numbers":numbers,"components":{},"rules":{}}

def demo_state(accounts):
    entities={}
    relations={}
    members={}
    for n,(account,role) in enumerate(accounts):
        mid="member-"+account
        members[account]={"memberId":mid,"accountId":account,"role":role,"active":True,"authorizationEpoch":1,"metadata":{}}
        if role=="player":
            actor="actor-"+account; bag="bag-"+account; skill="skill-"+account
            entities[actor]=entity(actor,"actor","调查员 "+str(n),account,hp=9,maxHp=10,armor=2,attack=5)
            entities[bag]=entity(bag,"bag","背包 "+str(n),account,capacity=2000)
            entities[bag]["components"]={"core.container":{"allowed":["item","weapon"]}}
            entities[skill]=entity(skill,"skill","侦查",account,value=60)
            for kind,target in [("owns-container",bag),("owns-skill",skill)]:
                rid=uid();relations[rid]={"relationId":rid,"sourceId":actor,"targetId":target,"relationType":kind,"revision":1,"tags":[],"metadata":{}}
            item="item-"+account
            entities[item]=entity(item,"item","补给品",account,quantity=3,unitMass=400,durability=85)
            rid=uid();relations[rid]={"relationId":rid,"sourceId":bag,"targetId":item,"relationType":"contains","revision":1,"tags":[],"metadata":{}}
    secret=entity("secret-clue","item","隐藏线索",None,quantity=1,unitMass=0)
    secret["visibility"]="kp";entities["secret-clue"]=secret
    configs={"demo."+k:{"configurationId":"demo."+k,"revision":"1","typeRef":k,"defaults":({"hp":10,"maxHp":10,"armor":0,"attack":0} if k=="actor" else {"quantity":1,"unitMass":0} if k in ("item","weapon") else {"capacity":2000} if k=="bag" else {"value":0} if k=="skill" else {}),"behaviors":{}} for k in KINDS}
    return {"schemaVersion":1,"roomId":"demo","name":"首测调查室","runId":uid(),"status":"active",
            "entities":entities,"relations":relations,"members":members,"progress":{},"configurations":configs,
            "commands":{},"flows":{},"waits":{},"artifacts":{},"activeRuleset":None,"assets":{},"chat":chat.initial_state(),"audit":[],"outbox":[],"collectionRevision":1}

def validate(state):
    require(state["schemaVersion"]==1,"SCHEMA_UNSUPPORTED")
    if "commands" in state:validate_model("Room",state)
    if "chat" in state:chat.validate(state)
    entities=state["entities"]; held={}; graph={}
    for collection,kind in (("configurations","Configuration"),("members","Member"),("assets","Asset"),("progress","Progress"),("flows","Flow"),("waits","Wait"),("artifacts","RuleArtifact")):
        for value in state.get(collection,{}).values():validate_model(kind,value)
    for key,e in entities.items():
        validate_model("Entity",e)
        require(e["owner"] is None or e["owner"] in state["members"],"REFERENCE_CONFLICT")
        require(key==e["instanceId"] and e["roomId"]==state["roomId"])
        require(e["typeRef"] in KINDS and e["lifecycle"] in ("active","archived"))
        require(all(finite(v) for v in e["numbers"].values()))
        require(e["configurationId"] in state["configurations"],"REFERENCE_CONFLICT")
        require(len(e["name"])<=200 and len(e["tags"])<=64)
        if "core.container" in e["components"]:validate_model("Container",e["components"]["core.container"])
        nums=e["numbers"]
        if e["typeRef"] in ("item","weapon") and e["lifecycle"]=="active":
            require(type(nums.get("quantity")) is int and nums["quantity"]>0 and nums.get("unitMass",0)>=0)
        if e["typeRef"]=="actor": require(0<=nums.get("hp",0)<=nums.get("maxHp",0))
    for key,r in state["relations"].items():
        validate_model("Relation",r)
        require(key==r["relationId"] and r["sourceId"] in entities and r["targetId"] in entities,"REFERENCE_CONFLICT")
        a,b=entities[r["sourceId"]],entities[r["targetId"]]
        require(a["lifecycle"]==b["lifecycle"]=="active","REFERENCE_CONFLICT")
        require(r["relationType"] in {"contains","owns-container","equipped","owns-skill","affects","source","references"})
        if r["relationType"]=="contains":
            require("core.container" in a["components"],"REFERENCE_CONFLICT")
            require(b["typeRef"] in a["components"]["core.container"]["allowed"],"REFERENCE_CONFLICT")
            require(b["instanceId"] not in held,"MULTIPLE_OWNERS");held[b["instanceId"]]=a["instanceId"]
        if r["relationType"] in ("contains","owns-container"):
            graph.setdefault(r["sourceId"],[]).append(r["targetId"])
        if r["relationType"]=="owns-container": require(a["typeRef"]=="actor" and b["typeRef"]=="bag")
        if r["relationType"]=="owns-skill": require(a["typeRef"]=="actor" and b["typeRef"]=="skill")
        if r["relationType"]=="equipped": require(a["owner"]==b["owner"] and b["typeRef"]=="weapon")
    def walk(node,path):
        require(node not in path,"REFERENCE_CYCLE")
        for child in graph.get(node,[]): walk(child,path|{node})
    for node in graph: walk(node,set())
    for rec in state["progress"].values():
        valid=rec["ownerId"] in entities if rec["ownerKind"]=="entity" else any(m["memberId"]==rec["ownerId"] for m in state["members"].values())
        require(valid,"REFERENCE_CONFLICT")

def member(state,account):
    m=state["members"].get(account)
    require(m and m["active"],"PERMISSION_DENIED")
    return m

def visible(state,account,e):
    m=member(state,account)
    return m["role"]=="kp" or e.get("visibility")=="public" or e.get("owner")==account

def writable(state,account,e):
    return member(state,account)["role"]=="kp" or e.get("owner")==account
