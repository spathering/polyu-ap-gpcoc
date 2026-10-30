import copy
import pytest
from onlinecoc.host import Host
from onlinecoc.errors import DomainError

def message(h,account,op,args,id="test"):
    v=h.project(account)
    return {"protocolVersion":1,"type":"command","requestId":"request","roomId":"demo","payload":{"commandId":id,"authorityEpoch":v["authorityEpoch"],"runId":v["runId"],"catalogRevision":v["catalog"]["revision"],"rulesetRevision":v["catalog"]["rulesetRevision"],"op":op,"args":args}}
def invoke(h,account,rule,input,id="test"):
    return h.command(account,message(h,account,"action.invoke",{"actionId":rule,"input":input},id))
@pytest.fixture
def host(tmp_path):
    h=Host(tmp_path/"data",bootstrap="test-password")
    yield h
    h.close()
def test_transfer_dedupe_restart(host):
    h=host;m=message(h,"player1","action.invoke",{"actionId":"demo.transfer","input":{"item":"item-player1","bag":"bag-player2","quantity":1}})
    r=h.command("player1",m);assert r["status"]=="committed",r
    assert h.command("player1",m)==r
    assert h.state()["entities"]["item-player1"]["numbers"]["quantity"]==2
    bad=copy.deepcopy(m);bad["payload"]["args"]["input"]["quantity"]=2
    with pytest.raises(DomainError,match="COMMAND_ID_CONFLICT"):h.command("player1",bad)
    h.close();h.__init__(h.path)
    assert h.command("player1",m)==r
    assert h.state()["entities"][r["result"]]["numbers"]["quantity"]==1

def test_readonly_and_permissions(host):
    g=host.store.generation
    assert host.calculate("player1","demo.attack",{"actor":"actor-player1"})==7
    assert host.store.generation==g
    assert "secret-clue" not in host.project("player1")["entities"]
    r=invoke(host,"player1","demo.damage",{"actor":"actor-player2","amount":7})
    assert r["status"]=="rejected",r
    assert host.state()["entities"]["actor-player2"]["numbers"]["hp"]==9

def test_old_flow_lock_and_restart(host):
    s=host.state();s["entities"]["skill-player1"]["numbers"]["value"]=0;host.commit(s)
    r=invoke(host,"player1","demo.ruling",{"actor":"actor-player1","skill":"skill-player1","amount":7})
    fid=r["result"]["flowId"];assert host.state()["flows"][fid]["status"]=="waiting"
    wait=next(iter(host.state()["waits"].values()));old=host.state()["activeRuleset"]
    sources=copy.deepcopy(host.state()["artifacts"][old]["sources"])
    for name,source in sources.items():sources[name]=source.replace("amount-r.number", "100+amount-r.number")
    new=host.command("kp",message(host,"kp","rule.stage",{"sources":sources},"stage"))["result"]
    host.command("kp",message(host,"kp","rule.activate",{"revision":new},"activate"))
    host.close();host.__init__(host.path)
    assert host.state()["waits"][wait["id"]]["deadline"]==wait["deadline"]
    r=host.command("kp",message(host,"kp","flow.respond",{"waitId":wait["id"],"revision":1,"answer":True},"respond"))
    assert r["status"]=="committed",r
    assert host.state()["flows"][fid]["status"]=="completed",host.state()["flows"][fid]
    assert host.state()["entities"]["actor-player1"]["numbers"]["hp"]==4

def test_failure_rolls_back(host):
    s=host.state();sources=copy.deepcopy(s["artifacts"][s["activeRuleset"]]["sources"])
    sources["broken.lua"]="return rule('broken', {'actor'}, function(r,a) r.damage(a,7); error('failure') end)"
    revision=host.command("kp",message(host,"kp","rule.stage",{"sources":sources},"stage"))["result"]
    host.command("kp",message(host,"kp","rule.activate",{"revision":revision},"activate"))
    assert invoke(host,"player1","broken",{"actor":"actor-player1"})["status"]=="rejected"
    assert host.state()["entities"]["actor-player1"]["numbers"]["hp"]==9

def test_personal_progress_and_revocation(host):
    args={"ownerKind":"member","ownerId":"member-player1","eventKey":"clue","value":True}
    assert host.command("kp",message(host,"kp","progress.set",args))["status"]=="committed"
    assert host.project("player1")["progress"] and not host.project("player2")["progress"]
    host.command("kp",message(host,"kp","member.update",{"accountId":"player1","active":False},"revoke"))
    with pytest.raises(DomainError):host.project("player1")
