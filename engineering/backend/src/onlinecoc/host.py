import copy, hashlib, json, secrets, threading, time
from pathlib import Path
from jsonschema import Draft202012Validator
from onlinecoc_data import FileDataStore, StoreError, canonical
from .model import demo_state, validate, member, visible, writable, uid, entity
from .errors import DomainError, require
from .identity import Identity
from .registry import stage
from .lua_runtime import execute
from .contracts import check, validate_operation
from . import chat

class Host:
    def __init__(self,directory,*,bootstrap=None,fault=None,clock=time.time,store_factory=FileDataStore):
        self.path=Path(directory);self.path.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock();self.capacity=threading.BoundedSemaphore(128)
        self.metrics={'commands':[],'commits':[],'workers':[]};self.clock=clock;self.fault=fault;self.epoch=uid();self.views={}
        self.identity=Identity(self.path/'identity',store_factory)
        try:self.store=store_factory(self.path/'rooms/demo')
        except Exception:self.identity.close();raise
        try:
            if self.store.snapshot()[1] is None:
                require(bootstrap is not None,"INITIALIZATION_REQUIRED")
                accounts=[('kp','kp'),('player1','player'),('player2','player')]
                for account,_ in accounts:
                    if account not in self.identity.store.snapshot()[1]['accounts']:self.identity.create(account,bootstrap)
                state=demo_state(accounts)
                folder=Path(__file__).resolve().parents[3]/'rulepacks/demo'
                artifact=stage({p.name:p.read_text(encoding='utf-8') for p in folder.glob('*.lua')},{p.name:json.loads(p.read_text(encoding='utf-8')) for p in folder.glob('*.json')})
                state['artifacts'][artifact['revision']]=artifact;state['activeRuleset']=artifact['revision']
                validate(state);self.store.commit(0,state)
            state=self.state()
            if "chat" not in state:
                validate(state)
                state["chat"]=chat.initial_state();self.commit(state)
            self.recover()
        except BaseException:
            self.close();raise
    def state(self):return self.store.snapshot()[1]
    def commit(self,state):
        start=time.perf_counter();validate(state);self.store.commit(self.store.generation,state)
        self.metrics['commits'].append((time.perf_counter()-start)*1000);self.metrics['commits']=self.metrics['commits'][-1000:]
    def hit(self,stage):
        if self.fault:self.fault(stage)
    def kp(self,account):require(member(self.state(),account)['role']=='kp','PERMISSION_DENIED')
    def auth(self,token):
        with self.lock:return self.identity.authenticate(token)
    def catalog(self,account):
        s=self.state();m=member(s,account);a=s['artifacts'][s['activeRuleset']]
        return {'revision':s['activeRuleset']+':'+str(m['authorizationEpoch']),'rulesetRevision':s['activeRuleset'],
                'actions':[v for v in a['metadata'].values() if v['public'] and (not v['kp'] or m['role']=='kp')]}
    def project(self,account):
        with self.lock:
            s=self.state();m=member(s,account);entities={}
            for id,e in s['entities'].items():
                if e['lifecycle']=='active' and visible(s,account,e):
                    out=copy.deepcopy(e)
                    if m['role']!='kp':out['metadata'].pop('secret',None)
                    # Tokens are random and stable only for this visible object version and principal.
                    key=(account,m['authorizationEpoch'],id,e['revision'])
                    if key not in self.views:self.views[key]=secrets.token_urlsafe(18)
                    out['viewToken']=self.views[key];entities[id]=out
            relations={k:v for k,v in s['relations'].items() if v['sourceId'] in entities and v['targetId'] in entities}
            waits={k:v for k,v in s['waits'].items() if v['status']=='waiting' and (m['role']=='kp' or (v['role']=='initiator' and v['account']==account))}
            progress={k:v for k,v in s['progress'].items() if m['role']=='kp' or (v['ownerKind']=='member' and v['ownerId']==m['memberId']) or (v['ownerKind']=='entity' and v['ownerId'] in entities and entities[v['ownerId']]['owner']==account)}
            flows={k:{x:v[x] for x in ('id','rule','status','cursor','error') if x in v} for k,v in s['flows'].items() if m['role']=='kp' or v['account']==account}
            return {'roomId':s['roomId'],'name':s['name'],'runId':s['runId'],'status':s['status'],'authorityEpoch':self.epoch,'authorizationEpoch':m['authorizationEpoch'],
                    'accountId':account,'role':m['role'],'entities':entities,'relations':relations,'progress':progress,'waits':waits,'flows':flows,'catalog':self.catalog(account),'chatChannels':chat.project(s,account)}
    def receipt(self,account,id):
        s=self.state();member(s,account);rec=s['commands'].get(account+':'+id)
        if not rec:return {'status':'unknown','commandId':id}
        if rec['status']=='pending':return {'status':'pending','commandId':id}
        result=copy.deepcopy(rec['receipt'])
        if (rec.get('op') or '').startswith('chat.'):
            cid=result.get('result',{}).get('channelId')
            if cid and not chat.can_read(s,account,s['chat']['channels'].get(cid)):result.pop('result',None)
            return result
        if member(s,account)['role']!='kp' and rec.get('op') not in ('action.invoke','behavior.invoke','entity.patch','flow.respond',None):result.pop('result',None)
        if any(k!='@relations' and (k not in s['entities'] or not visible(s,account,s['entities'][k])) for k in rec.get('reads',{})):
            result.pop('result',None)
        return result
    def snapshot_for_execution(self,s):
        return {k:copy.deepcopy(s[k]) for k in ('schemaVersion','roomId','entities','relations','members','configurations','progress','collectionRevision')}
    def dispatch(self,token,csrf,message):
        require(self.capacity.acquire(blocking=False),'LIMIT_EXCEEDED')
        start=time.perf_counter()
        try:
            with self.lock:
                wait=(time.perf_counter()-start)*1000;session=self.identity.authenticate(token)
                require(session['csrf']==csrf,'PERMISSION_DENIED')
                result=self.command(session['accountId'],message)
                self.metrics['commands'].append({'queueMs':wait,'totalMs':(time.perf_counter()-start)*1000})
                self.metrics['commands']=self.metrics['commands'][-1000:]
                return result
        finally:self.capacity.release()
    def command(self,account,message):
        require(self.capacity.acquire(blocking=False),'LIMIT_EXCEEDED')
        try:
            with self.lock:
                check('command',message);s=self.state();m=member(s,account)
                require(message['roomId']==s['roomId'],'NOT_VISIBLE')
                p=message['payload'];key=account+':'+p['commandId'];signature=hashlib.sha256(canonical(p)).hexdigest()
                if key in s['commands']:
                    require(s['commands'][key]['signature']==signature,'COMMAND_ID_CONFLICT')
                    if s['commands'][key]['status']=='pending':self.run_attempt(key)
                    return self.receipt(account,p['commandId'])
                require(p['authorityEpoch']==self.epoch,'STALE_AUTHORITY')
                for id,token in p.get('expectedViews',{}).items():
                    e=s['entities'].get(id);require(e and self.views.get((account,m['authorizationEpoch'],id,e['revision']))==token,'VERSION_CONFLICT')
                op,args=p['op'],p['args']
                rec={'signature':signature,'status':'pending','account':account,'id':p['commandId'],'op':op,'args':copy.deepcopy(args),'random':[]}
                validate_operation(op,args)
                if op=='behavior.invoke':
                    e=s['entities'].get(args['entityId']);require(e and visible(s,account,e),'NOT_VISIBLE')
                    binding=e['rules'].get(args['event']) or s['configurations'][e['configurationId']].get('behaviors',{}).get(args['event'])
                    require(binding,'NOT_VISIBLE');args={'actionId':binding['ruleId'],'input':args['input']}
                if op in ('action.invoke','behavior.invoke'):
                    require(s['status']=='active','ROOM_PAUSED')
                    cat=self.catalog(account);require(p.get('catalogRevision')==cat['revision'] and p.get('rulesetRevision')==s['activeRuleset'],'STALE_CATALOG')
                    require(p.get('runId')==s['runId'],'STALE_AUTHORITY')
                    require(set(args)=={'actionId','input'})
                    metadata=s['artifacts'][s['activeRuleset']]['metadata'].get(args['actionId'])
                    require(metadata and metadata['public'] and (not metadata['kp'] or m['role']=='kp'),'PERMISSION_DENIED')
                    try:Draft202012Validator(metadata['schema']).validate(args['input'])
                    except Exception:raise DomainError('INPUT_INVALID')
                    require(metadata['mode']!='calculation','READ_ONLY_QUERY_REQUIRED')
                    rec.update(rule=args['actionId'],input=args['input'],ruleset=s['activeRuleset'],snapshot=self.snapshot_for_execution(s))
                    if metadata['mode']=='flow':
                        flowid=uid();flow={'id':flowid,'account':account,'rule':rec['rule'],'input':rec['input'],'ruleset':rec['ruleset'],'cursor':metadata['nodes'][0]['id'],'status':'running','results':{}}
                        s['flows'][flowid]=flow;rec['status']='committed';rec['receipt']={'status':'committed','commandId':rec['id'],'result':{'flowId':flowid}}
                        s['commands'][key]=rec;self.commit(s);self.advance(flowid);return self.receipt(account,rec['id'])
                    s['commands'][key]=rec;self.hit('before_t1');self.commit(s);self.hit('after_t1');self.run_attempt(key)
                else:
                    s['commands'][key]=rec
                    try:
                        result=self.manage(s,account,op,args)
                        validate(s);rec['status']='committed';rec['receipt']={'status':'committed','commandId':rec['id'],'result':result}
                        s['audit'].append({'commandId':rec['id'],'account':account,'op':op,'at':self.clock()})
                        if op.startswith('chat.'):self.hit('before_chat_commit')
                        self.commit(s)
                        if op.startswith('chat.'):self.hit('after_chat_commit')
                    except DomainError as e:
                        s=self.state();rec['status']='rejected';rec['receipt']={'status':'rejected','commandId':rec['id'],'code':e.code};s['commands'][key]=rec;self.commit(s)
                    self.tick()
                return self.receipt(account,p['commandId'])
        finally:self.capacity.release()
    def run_attempt(self,key):
        s=self.state();rec=s['commands'][key];account=rec['account'];artifact=s['artifacts'][rec['ruleset']];ordinal=0
        def random(sides):
            nonlocal ordinal
            current=self.state();r=current['commands'][key];i=ordinal;ordinal+=1
            if i<len(r['random']):require(r['random'][i]['sides']==sides,'RANDOM_TRACE_CONFLICT');return r['random'][i]['value']
            value=secrets.randbelow(sides)+1;r['random'].append({'sides':sides,'value':value});self.commit(current);self.hit('after_random');return value
        try:
            member(s,account)
            out=execute(artifact['sources'],{'kind':'run','rule':rec['rule'],'input':rec['input'],'mode':'action','state':rec['snapshot'],'account':account,'node':rec.get('node'),'data':artifact['data'],'results':rec.get('results',{})},random)
            self.metrics['workers'].append(out['workerMs']);self.metrics['workers']=self.metrics['workers'][-1000:]
            current=self.state();member(current,account)
            require(current['members'][account]['authorizationEpoch']==rec['snapshot']['members'][account]['authorizationEpoch'],'PERMISSION_DENIED')
            for id,revision in out['reads'].items():
                actual=current['collectionRevision'] if id=='@relations' else current['entities'].get(id,{}).get('revision')
                require(actual==revision,'VERSION_CONFLICT')
            for id,e in out['entities'].items():
                if e!=rec['snapshot']['entities'].get(id):e['revision']=current['entities'].get(id,{}).get('revision',0)+1;current['entities'][id]=e
            if out['relations']!=rec['snapshot']['relations']:
                current['relations']=out['relations'];current['collectionRevision']+=1
            r=current['commands'][key];r['status']='committed';r['reads']=out['reads'];r.pop('snapshot',None)
            r['receipt']={'status':'committed','commandId':r['id'],'result':out['result']}
            current['audit'].append({'commandId':r['id'],'account':account,'rule':r['rule'],'ruleset':r['ruleset'],'random':r['random'],'effects':out['effects'],'at':self.clock()})
            current['outbox'].append({'id':uid(),'commandId':r['id']})
            if rec.get('flowId'):self.finish_node(current,rec['flowId'],rec['node'],out['result'])
            self.hit('before_t2');self.commit(current);self.hit('after_t2')
        except DomainError as e:
            current=self.state();r=current['commands'][key];r['status']='rejected';r.pop('snapshot',None);r['receipt']={'status':'rejected','commandId':r['id'],'code':e.code}
            if rec.get('flowId'):current['flows'][rec['flowId']].update(status='needs_attention',error=e.code)
            self.commit(current)
    def nodes(self,s,flow):return s['artifacts'][flow['ruleset']]['metadata'][flow['rule']]['nodes']
    def move_flow(self,s,flow,nextid):
        flow['cursor']=nextid
        if nextid=='end':flow['status']='completed';return
        node=next(n for n in self.nodes(s,flow) if n['id']==nextid)
        if node['kind']=='wait':
            waitid=flow['id']+':'+nextid;opts=node['options']
            s['waits'].setdefault(waitid,{'id':waitid,'flowId':flow['id'],'node':nextid,'account':flow['account'],'role':opts['role'],'deadline':self.clock()+opts['seconds'],'status':'waiting','revision':1,'options':opts})
            flow['status']='waiting'
        else:flow['status']='running'
    def finish_node(self,s,flowid,nodeid,result):
        flow=s['flows'][flowid];nodes=self.nodes(s,flow);node=next(n for n in nodes if n['id']==nodeid);index=nodes.index(node)
        if 'yes' in node['options']:require(type(result) is bool,'FLOW_BRANCH_NOT_BOOLEAN')
        flow['results'][nodeid]=result;default=nodes[index+1]['id'] if index+1<len(nodes) else 'end'
        nextid=node['options'].get('yes' if result else 'no',default)
        self.move_flow(s,flow,nextid)
    def advance(self,flowid):
        for _ in range(32):
            s=self.state();flow=s['flows'][flowid]
            if flow['status']!='running' or s['status']!='active':return
            node=next(n for n in self.nodes(s,flow) if n['id']==flow['cursor'])
            if node['kind']=='wait':self.move_flow(s,flow,node['id']);self.commit(s);return
            id='flow:'+flowid+':'+node['id']+':'+str(flow.get('attempt',0));key=flow['account']+':'+id
            if key not in s['commands']:
                s['commands'][key]={'id':id,'account':flow['account'],'signature':id,'status':'pending','rule':flow['rule'],'input':flow['input'],'ruleset':flow['ruleset'],'snapshot':self.snapshot_for_execution(s),'random':[],'flowId':flowid,'node':node['id'],'results':copy.deepcopy(flow['results'])}
                self.commit(s)
            if self.state()['commands'][key]['status']=='pending':self.run_attempt(key)
            else:return
    def tick(self):
        with self.lock:
            s=self.state()
            if s['status']!='active':return
            changed=False
            for w in s['waits'].values():
                if w['status']=='waiting' and w['deadline']<=self.clock():
                    w.update(status='timeout',resolvedAt=self.clock(),revision=w['revision']+1);self.move_flow(s,s['flows'][w['flowId']],w['options']['timeout']);changed=True
            if changed:self.commit(s)
            for f in list(self.state()['flows']):self.advance(f)
    def recover(self):
        with self.lock:
            validate(self.state())
            for key,r in list(self.state()['commands'].items()):
                if r['status']=='pending':self.run_attempt(key)
            self.tick()
    def calculate(self,account,rule,input):
        with self.lock:
            s=self.state();member(s,account);artifact=s['artifacts'][s['activeRuleset']];m=artifact['metadata'].get(rule)
            require(m and m['public'] and m['mode']=='calculation' and (not m['kp'] or member(s,account)['role']=='kp'),'NOT_VISIBLE')
            try:Draft202012Validator(m['schema']).validate(input)
            except Exception:raise DomainError('INPUT_INVALID')
            return execute(artifact['sources'],{'kind':'run','rule':rule,'input':input,'mode':'calculation','state':self.snapshot_for_execution(s),'account':account,'data':artifact['data']})['result']
    def manage(self,s,account,op,args):
        m=member(s,account)
        if op.startswith('chat.'):return chat.apply(s,account,op,args,self.clock())
        if op=='flow.respond':
            require(s['status']=='active','ROOM_PAUSED')
            require(set(args)=={'waitId','revision','answer'} and type(args['answer']) is bool)
            w=s['waits'].get(args['waitId']);require(w and w['status']=='waiting' and w['revision']==args['revision'],'FLOW_ALREADY_RESOLVED')
            require((w['role']=='kp' and m['role']=='kp') or (w['role']=='initiator' and w['account']==account),'PERMISSION_DENIED')
            require(self.clock()<w['deadline'],'FLOW_ALREADY_RESOLVED')
            w.update(status='answered',answer=args['answer'],resolvedAt=self.clock(),revision=w['revision']+1)
            self.move_flow(s,s['flows'][w['flowId']],w['options']['yes' if args['answer'] else 'no']);return True
        if op=='entity.patch':
            require(set(args)=={'id','name'} and isinstance(args['name'],str))
            e=s['entities'].get(args['id']);require(e and writable(s,account,e),'NOT_VISIBLE');e['name']=args['name'];e['revision']+=1;return e['instanceId']
        require(m['role']=='kp','PERMISSION_DENIED')
        if op=='room.status':
            require(set(args)=={'status'} and args['status'] in ('active','paused','archived'));s['status']=args['status'];return True
        if op=='member.update':
            require(set(args)<={'accountId','active','role'} and args['accountId'] in s['members'])
            target=s['members'][args['accountId']]
            if 'active' in args:require(type(args['active']) is bool);target['active']=args['active']
            if 'role' in args:require(args['role'] in ('kp','player'));target['role']=args['role']
            require(any(x['active'] and x['role']=='kp' for x in s['members'].values()))
            target['authorizationEpoch']+=1;return True
        if op=='rule.stage':
            require(set(args)<={'sources','data'} and 'sources' in args);artifact=stage(args['sources'],args.get('data'));s['artifacts'][artifact['revision']]=artifact;return artifact['revision']
        if op=='rule.activate':
            require(set(args)=={'revision'} and args['revision'] in s['artifacts']);s['activeRuleset']=args['revision'];return args['revision']
        if op=='member.add':
            require(args['accountId'] in self.identity.store.snapshot()[1]['accounts'],'NOT_VISIBLE')
            require(args['accountId'] not in s['members'],'MEMBER_EXISTS')
            s['members'][args['accountId']]={'memberId':uid(),'accountId':args['accountId'],'role':args['role'],'active':True,'authorizationEpoch':1,'metadata':{}};return True
        if op=='configuration.put':
            old=s['configurations'].get(args['configurationId'])
            require(not old or old==args or old['revision']!=args['revision'],'VERSION_CONFLICT')
            require(not old or old['typeRef']==args['typeRef'],'REFERENCE_CONFLICT')
            for binding in args.get('behaviors',{}).values():require(binding['ruleId'] in s['artifacts'][s['activeRuleset']]['metadata'],'REFERENCE_CONFLICT')
            s['configurations'][args['configurationId']]=copy.deepcopy(args);return args['configurationId']
        if op=='configuration.remove':
            require(args['id'] in s['configurations'],'NOT_VISIBLE')
            require(not any(e['configurationId']==args['id'] for e in s['entities'].values()),'REFERENCE_CONFLICT')
            del s['configurations'][args['id']];return True
        if op=='entity.update':
            e=s['entities'].get(args['id']);require(e,'NOT_VISIBLE')
            for binding in args.get('rules',{}).values():require(binding['ruleId'] in s['artifacts'][s['activeRuleset']]['metadata'],'REFERENCE_CONFLICT')
            for field in ('numbers','tags','owner','visibility','rules'):
                if field in args:
                    if field=='numbers':e[field].update(args[field])
                    else:e[field]=copy.deepcopy(args[field])
            e['revision']+=1;return e['instanceId']
        if op=='asset.attach':
            e=s['entities'].get(args['entityId']);require(e and args['assetId'] in s['assets'],'REFERENCE_CONFLICT')
            refs=e['components'].setdefault('core.assets',[])
            if args['assetId'] not in refs:refs.append(args['assetId'])
            e['revision']+=1;return True
        if op=='asset.remove':
            require(args['assetId'] in s['assets'],'NOT_VISIBLE')
            require(not any(args['assetId'] in e['components'].get('core.assets',[]) for e in s['entities'].values()),'REFERENCE_CONFLICT')
            require(not any(args['assetId'] in msg['assetIds'] for ms in s['chat']['messages'].values() for msg in ms),'REFERENCE_CONFLICT')
            del s['assets'][args['assetId']];return True
        if op=='flow.retry':
            f=s['flows'].get(args['flowId']);require(f and f['status']=='needs_attention','FLOW_NOT_RETRYABLE')
            f.update(status='running',attempt=f.get('attempt',0)+1);f.pop('error',None);return True
        if op=='entity.create':
            require(set(args)<={'configurationId','name','numbers','owner','visibility'} and args['configurationId'] in s['configurations'])
            config=s['configurations'][args['configurationId']];id=uid();e=entity(id,config['typeRef'],args.get('name','新对象'),args.get('owner'),**{**config['defaults'],**args.get('numbers',{})});e['configurationId']=args['configurationId'];e['configurationRevision']=config['revision'];e['visibility']=args.get('visibility','public')
            if e['typeRef']=='bag':e['components']={'core.container':{'allowed':['item','weapon']}}
            s['entities'][id]=e;return id
        if op=='entity.archive':
            require(set(args)=={'id'});e=s['entities'].get(args['id']);require(e,'NOT_VISIBLE');require(not any(args['id'] in (r['sourceId'],r['targetId']) for r in s['relations'].values()),'REFERENCE_CONFLICT');e['lifecycle']='archived';e['revision']+=1;return True
        if op=='relation.set':
            id=uid();s['relations'][id]={'relationId':id,'revision':1,'tags':[],'metadata':{},**args};s['collectionRevision']+=1;return id
        if op=='relation.remove':
            require(set(args)=={'id'} and args['id'] in s['relations']);del s['relations'][args['id']];s['collectionRevision']+=1;return True
        if op=='progress.set':
            require(set(args)=={'ownerKind','ownerId','eventKey','value'} and args['ownerKind'] in ('member','entity'))
            key=args['ownerKind']+':'+args['ownerId']+':'+args['eventKey'];s['progress'][key]={**args,'revision':s['progress'].get(key,{}).get('revision',0)+1};return key
        if op=='flow.cancel':
            require(set(args)=={'flowId'} and args['flowId'] in s['flows']);f=s['flows'][args['flowId']];f['status']='cancelled'
            for w in s['waits'].values():
                if w['flowId']==f['id'] and w['status']=='waiting':w['status']='cancelled';w['revision']+=1
            return True
        raise DomainError('UNKNOWN_OPERATION')
    def chat_members(self,account):
        with self.lock:
            s=self.state();member(s,account);accounts=self.identity.store.snapshot()[1]['accounts']
            return [{'accountId':a,'memberId':m['memberId'],'nickname':accounts[a]['nickname'],'role':m['role']}
                    for a,m in s['members'].items() if m['active'] and a in accounts and not accounts[a]['disabled']]
    def chat_history(self,account,channel_id,before=None,limit=50):
        with self.lock:
            s=self.state();member(s,account)
            return chat.history(s,account,channel_id,before,limit)
    def query(self,account,collection,equals=None):
        with self.lock:
            view=self.project(account);require(collection in ('entities','relations','progress','waits','flows'),'PERMISSION_DENIED')
            equals=equals or {};require(isinstance(equals,dict) and len(equals)<=8)
            return [x for x in view[collection].values() if all(x.get(k)==v for k,v in equals.items())][:1000]
    def close(self):self.store.close();self.identity.close()
