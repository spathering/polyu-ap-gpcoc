import copy, math
from .errors import require, DomainError
from .model import visible,writable,finite,uid,validate

class Execution:
    def __init__(self,state,account,mode,random):
        self.state=copy.deepcopy(state); self.account=account;self.mode=mode;self.random=random
        self.original=copy.deepcopy(state);self.reads={};self.failed=False;self.operations=0;self.effects=[]
    def guard(self,fn,*args):
        try:
            self.operations+=1;require(self.operations<=2048,"LIMIT_EXCEEDED")
            return fn(*args)
        except Exception:
            self.failed=True;raise
    def read(self,id):
        e=self.state["entities"].get(id)
        require(e and e["lifecycle"]=="active" and visible(self.state,self.account,e),"NOT_VISIBLE")
        if id in self.original["entities"]:self.reads.setdefault(id,self.original["entities"][id]["revision"])
        out=copy.deepcopy(e)
        if self.state["members"][self.account]["role"]!="kp": out["metadata"].pop("secret",None)
        return out
    def has_tag(self,id,tag):return tag in self.read(id)['tags']
    def matches(self,id,configuration):return self.read(id)['configurationId']==configuration
    def related(self,id,relation_type):
        self.read(id);self.reads['@relations']=self.original['collectionRevision']
        return [self.read(r['targetId'])['instanceId'] for r in sorted(self.state['relations'].values(),key=lambda x:x['relationId']) if r['sourceId']==id and r['relationType']==relation_type]
    def number(self,id,key):
        e=self.read(id);require(key in e["numbers"],"INPUT_INVALID");return e["numbers"][key]
    def write(self,id,key,value):
        require(self.mode=="action","READ_ONLY")
        e=self.read(id);require(writable(self.state,self.account,e),"PERMISSION_DENIED")
        require(key not in ("quantity","unitMass","capacity") and key in e["numbers"] and finite(value))
        self.state["entities"][id]["numbers"][key]=value
        self.effects.append({"type":"number","id":id,"key":key,"value":value})
    def owned_skill(self,actor,skill):
        self.read(actor);self.read(skill)
        require(writable(self.state,self.account,self.state["entities"][actor]),"PERMISSION_DENIED")
        require(any(r["sourceId"]==actor and r["targetId"]==skill and r["relationType"]=="owns-skill" for r in self.state["relations"].values()),"REFERENCE_CONFLICT")
        self.reads["@relations"]=self.state["collectionRevision"]
        return True
    def roll(self,sides):
        require(self.mode=="action","READ_ONLY");require(type(sides)==int and 1<=sides<=1000000)
        return self.random(sides)
    def items(self,bag):
        self.read(bag);self.reads["@relations"]=self.state["collectionRevision"]
        return [self.read(r["targetId"]) for r in sorted(self.state["relations"].values(),key=lambda x:x["relationId"]) if r["sourceId"]==bag and r["relationType"]=="contains"]
    def transfer(self,item,bag,quantity=None):
        require(self.mode=="action","READ_ONLY")
        e=self.read(item);target=self.read(bag)
        require(writable(self.state,self.account,e),"PERMISSION_DENIED")
        require(target["typeRef"]=="bag")
        edges=[r for r in self.state["relations"].values() if r["targetId"]==item and r["relationType"]=="contains"]
        require(len(edges)==1,"REFERENCE_CONFLICT")
        edge=edges[0];source=self.read(edge["sourceId"])
        require(writable(self.state,self.account,source),"PERMISSION_DENIED")
        require(source["instanceId"]!=bag)
        quantity=e["numbers"]["quantity"] if quantity is None else quantity
        require(type(quantity)==int and 0<quantity<=e["numbers"]["quantity"],"QUANTITY_INVALID")
        self.reads["@relations"]=self.state["collectionRevision"]
        if quantity==e["numbers"]["quantity"]:
            self.state["relations"][edge["relationId"]]["sourceId"]=bag
            self.state["relations"][edge["relationId"]]["revision"]+=1
            target_id=item
        else:
            self.state["entities"][item]["numbers"]["quantity"]-=quantity
            target_id=uid();child=copy.deepcopy(e);child["instanceId"]=target_id;child["revision"]=0
            child["numbers"]["quantity"]=quantity;self.state["entities"][target_id]=child
            rid=uid();self.state["relations"][rid]={"relationId":rid,"sourceId":bag,"targetId":target_id,"relationType":"contains","revision":1,"tags":[],"metadata":{}}
        self.state["entities"][target_id]["owner"]=target["owner"]
        self.state["entities"][source["instanceId"]]["revision"]+=1
        self.state["entities"][bag]["revision"]+=1
        self.effects.append({"type":"transfer","item":item,"target":target_id,"quantity":quantity,"bag":bag})
        return target_id
    def finish(self):
        require(not self.failed,"EXECUTION_REJECTED")
        require(len(self.effects)<=256,"LIMIT_EXCEEDED");validate(self.state)
        return {"entities":self.state["entities"],"relations":self.state["relations"],"reads":self.reads,"effects":self.effects}
