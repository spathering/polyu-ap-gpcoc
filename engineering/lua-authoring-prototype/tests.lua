local Host = dofile('host.lua')
local passed = 0
local function eq(a,b,label)
  assert(a==b, (label or '') .. ': expected ' .. tostring(b) .. ', got ' .. tostring(a)); passed=passed+1
end
local function fixture(options)
  local initial = {nextId=1, holding={item='bagA'}, entities={
    actor={id='actor',scope='room',revision=1,kind='actor',hp=9,maxHp=12,armor=2,skills={spot=60}},
    bagA={id='bagA',scope='room',revision=1,kind='bag',capacity=5000},
    bagB={id='bagB',scope='room',revision=1,kind='bag',capacity=1000},
    item={id='item',scope='room',revision=1,kind='item',quantity=3,unitMass=400}
  }}
  local principal = {id='player',scope='room',canWrite=true,allowed={actor=true,bagA=true,bagB=true,item=true}}
  return Host.new(initial,options),principal
end
local check = Host.load('examples/01-check.lua')
local damage = Host.load('examples/02-damage.lua')
local transfer = Host.load('examples/03-transfer.lua')
local host,p = fixture({roll=function() return 25 end})
local c = {id='check',args={'actor','spot'}}
local r = host.execute(check,p,c)
eq(r.status,'committed'); eq(r.result,true); eq(#r.dice,1)
eq(host.execute(check,p,c).replayed,true)
host,p = fixture({roll=function() return 85 end})
eq(host.execute(check,p,c).result,false,'check failure is normal result')
-- Preview, atomic overlay, copy isolation and poisoned pcall.
host,p = fixture()
r=host.execute(damage,p,{id='d',args={'actor',7},preview=true})
eq(r.status,'preview'); eq(host.snapshot().entities.actor.hp,9)
r=host.execute(damage,p,{id='d',args={'actor',7}})
eq(r.status,'committed'); eq(host.snapshot().entities.actor.hp,4)
r.effects[1].lost=999
eq(host.execute(damage,p,{id='d',args={'actor',7}}).effects[1].lost,5)
eq(host.snapshot().entities.actor.hp,4,'replay does not reapply damage')
eq(host.execute(damage,p,{id='d',args={'actor',8}}).code,'IDEMPOTENCY_CONFLICT')
local double=Host.rule('double',{'actor'},function(a,id)
  a.damage(id,4); a.damage(id,4); return a.read(id).hp
end)
host,p=fixture(); r=host.execute(double,p,{id='double',args={'actor'}})
eq(r.result,5); eq(host.snapshot().entities.actor.hp,5); eq(host.snapshot().entities.actor.revision,2)
local caught=Host.rule('caught',{'actor'},function(a,id)
  a.damage(id,4); pcall(function() a.damage(id,-1) end); return true
end)
host,p=fixture(); r=host.execute(caught,p,{id='caught',args={'actor'}})
eq(r.status,'rejected'); eq(r.code,'INVALID_AMOUNT'); eq(host.snapshot().entities.actor.hp,9)
local crash=Host.rule('crash',{'actor'},function(a,id) a.damage(id,4); error('test failure') end)
eq(host.execute(crash,p,{id='crash',args={'actor'}}).code,'SCRIPT_ERROR'); eq(host.snapshot().entities.actor.hp,9)
local isolated=Host.rule('copy',{'actor'},function(a,id) local x=a.read(id); x.hp=0 end)
eq(host.execute(isolated,p,{id='copy',args={'actor'}}).status,'committed'); eq(host.snapshot().entities.actor.hp,9)
-- Transfer conservation, stable split identity, default whole stack and capacity rollback.
host,p=fixture(); r=host.execute(transfer,p,{id='t',args={'item','bagB',1}})
eq(r.status,'committed'); eq(r.result,'split-1')
local s=host.snapshot(); eq(s.entities.item.quantity,2); eq(s.entities['split-1'].quantity,1)
eq(s.holding['split-1'],'bagB'); eq(s.entities.bagA.revision,2); eq(s.entities.bagB.revision,2)
eq(host.execute(transfer,p,{id='t',args={'item','bagB',1}}).result,'split-1')
eq(host.snapshot().nextId,2)
host,p=fixture(); r=host.execute(transfer,p,{id='capacity',args={'item','bagB',3}})
eq(r.code,'CAPACITY_EXCEEDED'); eq(host.snapshot().entities.item.quantity,3); eq(host.snapshot().nextId,1)
local rollback=Host.rule('rollback',{'actor','item','bag'},function(a,actor,item,bag)
  a.damage(actor,7); a.transfer(item,bag,3)
end)
eq(host.execute(rollback,p,{id='rb',args={'actor','item','bagB'}}).status,'rejected'); eq(host.snapshot().entities.actor.hp,9)
local whole=Host.rule('whole',{'item','bag'},function(a,item,bag) return a.transfer(item,bag) end)
host,p=fixture({capacityPolicy=function() return true end})
eq(host.execute(whole,p,{id='whole',args={'item','bagB'}}).result,'item')
eq(host.snapshot().holding.item,'bagB'); eq(host.snapshot().entities.item.quantity,3)
-- Validation, revisions, permissions, scope, results, limits and custom rules.
host,p=fixture()
eq(host.execute(damage,p,{id='rev',args={'actor',7},expected={actor=99}}).code,'REVISION_CONFLICT')
eq(host.snapshot().entities.actor.hp,9)
eq(host.execute(damage,p,{id='bad',args={'actor',0/0}}).code,'INVALID_INPUT')
eq(host.execute(damage,p,{id='bad2',args={'actor',math.huge}}).code,'INVALID_INPUT')
eq(host.execute(damage,p,{id='bad3',args={'actor',{}}}).code,'INVALID_INPUT')
p.canWrite=false
eq(host.execute(damage,p,{id='no',args={'actor',7}}).code,'FORBIDDEN')
p.canWrite=true; p.allowed.actor=false
eq(host.execute(damage,p,{id='hidden',args={'actor',7}}).code,'NOT_FOUND_OR_FORBIDDEN')
p.allowed.actor=true; p.scope='other'
eq(host.execute(damage,p,{id='scope',args={'actor',7}}).code,'NOT_FOUND_OR_FORBIDDEN')
host,p=fixture(); host.execute(damage,p,{id='old',args={'actor',7}}); p.allowed.actor=false
eq(host.execute(damage,p,{id='old',args={'actor',7}}).code,'NOT_FOUND_OR_FORBIDDEN')
host,p=fixture({maxOperations=1})
eq(host.execute(double,p,{id='limit',args={'actor'}}).code,'OPERATION_LIMIT'); eq(host.snapshot().entities.actor.hp,9)
host,p=fixture({damagePolicy=function(actor,amount) return amount end})
host.execute(damage,p,{id='custom',args={'actor',3}}); eq(host.snapshot().entities.actor.hp,6)
local invalid=Host.rule('invalid',{'actor'},function(a,id) a.damage(id,3); return {} end)
host,p=fixture(); eq(host.execute(invalid,p,{id='result',args={'actor'}}).code,'INVALID_RESULT'); eq(host.snapshot().entities.actor.hp,9)
-- Loading definitions has no game-state effects; examples need no low-level effects/return protocol.
eq(type(check.run),'function'); eq(type(damage.run),'function'); eq(type(transfer.run),'function')
print('PASS ' .. passed .. ' assertions (' .. _VERSION .. ')')
