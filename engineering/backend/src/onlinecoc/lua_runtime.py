"""Spawned Lua 5.4 execution with a narrow JSON/Pipe boundary."""
import multiprocessing as mp
import time, math
from lupa.lua54 import LuaRuntime, lua_type
from .errors import DomainError, require
from .execution import Execution

BOOT = """
function()
 local function rule(id, inputs, run, opts)
   opts=opts or {}; return {id=id, inputs=inputs, run=run, mode=opts.mode or 'action', dependencies=opts.dependencies or {}, public=opts.public~=false, kp=opts.kp or false}
 end
 local function step(id, run, opts) return {id=id,kind='step',run=run,options=opts or {}} end
 local function ask(id, opts) return {id=id,kind='wait',options=opts} end
 local function flow(id, inputs, nodes) return {id=id,inputs=inputs,nodes=nodes,mode='flow',dependencies={},public=true,kp=false} end
 return function(source,name)
   local env={rule=rule,flow=flow,step=step,ask=ask, assert=assert,error=error,pcall=pcall,
     type=type,tostring=tostring,tonumber=tonumber,ipairs=ipairs,pairs=pairs,select=select,
     math={min=math.min,max=math.max,floor=math.floor,ceil=math.ceil,abs=math.abs},
     string={format=string.format,sub=string.sub,len=string.len,lower=string.lower,upper=string.upper},
     table={insert=table.insert,concat=table.concat,sort=table.sort}}
   local chunk,err=load(source,'@'..name,'t',env)
   if not chunk then error(err) end
   return chunk()
 end
end
"""

def convert(value, seen=None):
    if lua_type(value)=="table":
        seen=set() if seen is None else seen
        # Bounded traversal also catches cycles without relying on proxy identity.
        require(len(seen)<32,"INVALID_LUA_RESULT")
        marker=repr(value);require(marker not in seen,"INVALID_LUA_RESULT")
        seen=seen|{marker}; keys=list(value.keys())
        if keys and all(type(k)==int for k in keys) and sorted(keys)==list(range(1,len(keys)+1)):
            return [convert(value[k],seen) for k in range(1,len(keys)+1)]
        require(all(isinstance(k,str) for k in keys),"INVALID_LUA_RESULT")
        return {k:convert(value[k],seen) for k in keys}
    require(value is None or type(value) in (str,int,float,bool),"INVALID_LUA_RESULT")
    if type(value) in (float,int):require(math.isfinite(value) and abs(value)<=2**53-1,"INVALID_LUA_RESULT")
    return value

def worker(pipe, sources, job):
    try:
        def denied(*args): raise AttributeError("access denied")
        lua=LuaRuntime(register_eval=False,register_builtins=False,attribute_filter=denied,max_memory=32*1024*1024)
        load=lua.eval(BOOT)(); definitions={}
        for name,source in sources.items():
            d=load(source,name);require(lua_type(d)=="table" and isinstance(d["id"],str),"RULE_INVALID")
            require(d["id"] not in definitions,"DUPLICATE_RULE"); definitions[d["id"]]=d
        meta={}
        for key,d in definitions.items():
            raw=convert(d["inputs"]);require(isinstance(raw,list) or raw=={},"RULE_INVALID")
            inputs={}
            for item in raw:
                require(isinstance(item,str),"RULE_INVALID");name,sep,kind=item.partition(':')
                require(name and name not in inputs,"RULE_INVALID");inputs[name]=kind if sep else name
            if d["mode"]!='flow':require(lua_type(d["run"])=='function',"RULE_INVALID")
            nodes=[]
            if d["mode"]=="flow":
                for index in range(1,len(d["nodes"])+1):
                    node=d["nodes"][index];require(node["kind"]=="wait" or lua_type(node["run"])=="function","FLOW_INVALID");nodes.append({"id":node["id"],"kind":node["kind"],"options":convert(node["options"])})
            meta[key]={"id":key,"inputs":inputs,"mode":d["mode"],"dependencies":convert(d["dependencies"]) or [],"public":bool(d["public"]),"kp":bool(d["kp"]),"nodes":nodes}
        if job["kind"]=="inspect":pipe.send({"ok":True,"metadata":meta});return
        def random(sides):
            pipe.send({"random":sides});answer=pipe.recv()
            if "error" in answer:raise DomainError(answer["error"])
            return answer["value"]
        ctx=Execution(job["state"],job["account"],job["mode"],random)
        api=lua.table();stack=[]
        def table(v): return lua.table_from(v,recursive=True) if isinstance(v,(dict,list)) else v
        def bind(name,fn):
            def wrapped(*args):return table(ctx.guard(fn,*args))
            api[name]=wrapped
        bind("hasTag",ctx.has_tag);bind("matches",ctx.matches);bind("related",ctx.related)
        bind("read",ctx.read);bind("number",ctx.number);bind("set",ctx.write);bind("roll",ctx.roll)
        bind("ownedSkill",ctx.owned_skill);bind("items",ctx.items);bind("move",ctx.transfer)
        def data(name):
            require(name in job.get("data",{}),"DATA_NOT_FOUND");return job["data"][name]
        bind("readData",data)
        bind("result",lambda name:job.get("results",{}).get(name))
        def call(ruleid,*args):
            require(ruleid in definitions and ruleid not in stack and len(stack)<32,"RULE_CYCLE_OR_MISSING")
            d=definitions[ruleid]
            require(d["mode"]!="flow" and (ctx.mode=="action" or d["mode"]=="calculation"),"READ_ONLY")
            stack.append(ruleid)
            try:return d["run"](api,*args)
            finally:stack.pop()
        bind("call",call)
        for name in ("check","damage","transfer"):
            bind(name,lambda *args,n=name:call("demo.lib."+n,*args))
        d=definitions[job["rule"]]; args=[job["input"][k] for k in meta[job["rule"]]["inputs"]]
        if job.get("node"):
            node=next(x for x in d["nodes"].values() if x["id"]==job["node"])
            result=node["run"](api,*args)
        else:result=call(job["rule"],*args)
        output=ctx.finish(); output["result"]=convert(result);pipe.send({"ok":True,**output})
    except BaseException as e:
        pipe.send({"ok":False,"code":getattr(e,"code","RULE_FAILED"),"diagnostic":str(e)[:2000]})
    finally:pipe.close()

def execute(sources,job,random=None,timeout=10):
    started=time.perf_counter();context=mp.get_context("spawn");parent,child=context.Pipe()
    proc=context.Process(target=worker,args=(child,sources,job),daemon=True)
    proc.start();child.close();deadline=time.monotonic()+timeout
    try:
        while time.monotonic()<deadline:
            if parent.poll(.05):
                try:message=parent.recv()
                except EOFError:raise DomainError("WORKER_EXITED")
                if "random" in message:
                    try:parent.send({"value":random(message["random"])})
                    except Exception as e:parent.send({"error":getattr(e,"code","RANDOM_FAILED")})
                else:
                    if not message["ok"]:raise DomainError(message["code"],message["diagnostic"])
                    message["workerMs"]=(time.perf_counter()-started)*1000
                    return message
            if not proc.is_alive():raise DomainError("WORKER_EXITED")
        raise DomainError("RULE_TIMEOUT")
    finally:
        if proc.is_alive():proc.terminate()
        proc.join(3)
        if proc.is_alive():proc.kill();proc.join()
        parent.close()
