-- Host transaction for a validated, finite scene recipe. Never public to PL.
return rule('sv.scene.resolve', {'actor', 'scene:actor', 'world:actor', 'action:text', 'choice:text'}, function(r, actor, scene, world, action, choice)
  assert(r.matches(actor,'sv.character') and r.matches(scene,'sv.scene') and r.matches(world,'sv.world'),'SV_SCENE_TARGET')
  assert(r.number(actor,'approved')==1 and r.number(actor,'ready')==1,'SV_NOT_READY')
  assert(r.number(actor,'incapacitated')==0 and r.number(actor,'str')>0 and r.number(actor,'dex')>0 and r.number(actor,'wil')>0,'SV_CANNOT_ACT')
  local session=r.related(actor,'source')[1]
  assert(session and r.number(session,'phase')==1,'SV_SESSION_NOT_STARTED')
  local spec=nil
  for _,a in ipairs(r.readData('scene-actions.json').actions) do if a.id==action then spec=a end end
  assert(spec and r.number(actor,'location')==spec.location,'SV_SCENE_LOCATION')
  local valid=false
  for _,c in ipairs(spec.choices) do if c.id==choice then valid=true end end
  assert(valid,'SV_SCENE_CHOICE')
  local game=r.readData('game.json')
  local out={title=spec.label,sceneAction=action,choice=choice,narrative={},checks={},rolls={},stateChanges={},clues={},outcome='success',cost=0}
  local reveal,doors={},{}
  local function say(s) out.narrative[#out.narrative+1]=s end
  local function get(k) return r.number(scene,k) end
  local function set(k,v,label)
    local old=get(k)
    if old~=v then r.set(scene,k,v);out.stateChanges[#out.stateChanges+1]={key=k,label=label,before=old,after=v} end
  end
  local function fail(s) out.outcome='blocked';say(s) end
  local function clue(id,title,text)
    out.clues[#out.clues+1]={id=id,title=title,text=text,location=spec.location}
  end
  local function dice(sides,label)
    local v=r.roll(sides);out.rolls[#out.rolls+1]={sides=sides,value=v,label=label};return v
  end
  local function check(attribute,label)
    local layout=r.call('sv.layout',actor)
    local mode=(layout.overloaded or (layout.injured and (attribute=='str' or attribute=='dex'))) and 'disadvantage' or 'normal'
    local first=r.roll(20);local second=mode=='disadvantage' and r.roll(20) or 0
    local rolled=math.max(first,second);local target=r.number(actor,attribute)
    local passed=rolled<=target
    out.checks[#out.checks+1]={attribute=attribute,first=first,second=second,rolled=rolled,target=target,passed=passed,mode=mode,label=label}
    r.set(actor,'checks',r.number(actor,'checks')+1);r.set(actor,'lastRoll',rolled)
    if not passed then out.outcome='failure' end
    return passed
  end
  local function hurt(amount,attribute)
    local result=r.call('sv.damage',actor,amount,attribute or 'str')
    out.damage=result
    if result.save>0 then out.checks[#out.checks+1]={attribute=result.attribute,first=result.save,second=0,rolled=result.save,target=result.remaining,passed=not result.critical,mode='normal',label='重伤豁免'} end
    say('扣除护甲后受到 '..result.damage..' 点伤害，HP 剩余 '..result.hp..'。')
    if result.critical then say('角色已失能，需要恢复后才能继续行动。') end
    if result.dead then say('STR 已降至 0。') end
  end
  local function has(item)
    for i=1,20 do if r.number(actor,'item'..i)==item and (game.items[item].uses==0 or r.number(actor,'uses'..i)>0) then return i end end
    return nil
  end
  local function free_slot(item)
    local layout=r.call('sv.layout',actor);local def=game.items[item]
    for s=1,20 do
      local cells={s};local ok=true
      if s<=10 and def.slots==2 then
        if def.shape=='offhand-body' and s<=4 then ok=s==2;cells={2,3}
        elseif s<=4 then ok=s==1 or s==3;cells={s,s+1}
        else ok=s==5 or s==6 or s==8 or s==9;cells={s,s+1} end
      elseif s<=10 and def.slots==4 then ok=s==5 or s==6;cells={s,s+1,s+3,s+4} end
      for _,c in ipairs(cells) do if layout.occupied[tostring(c)] then ok=false end end
      if ok then return s end
    end
    return nil
  end
  local function take(item,key,label)
    if get(key)<=0 then fail('这里已经没有可领取的'..game.items[item].name..'。');return false end
    local slot=free_slot(item)
    if not slot then fail('所有槽位均已占用，物品仍留在原处；整理背包后可再取。');return false end
    r.call('sv.grant',actor,item,slot,game.items[item].uses)
    set(key,get(key)-1,label)
    say('获得'..game.items[item].name..'，放入槽位 '..slot..(slot>10 and '（超载区）。' or '。'))
    return true
  end
  local function consume(item,label)
    local slot=has(item)
    if not slot then fail('需要一件仍有用量的'..game.items[item].name..'。');return false end
    r.set(actor,'uses'..slot,r.number(actor,'uses'..slot)-1)
    say(label..'，消耗槽位 '..slot..' 的一格用量。');return true
  end
  local function discover_ground()
    set('trapKnown',1,'入口机关已识别')
    clue('tunnel-trap','入口地面的压痕','地面有落石留下的压痕，奶酪连接着触发装置；直接取走会有危险。')
    reveal={2}
  end
  local function rats()
    if r.number(world,'generated7')==0 then
      local n=dice(6,'鼠帮人数')+dice(6,'鼠帮人数')
      r.set(world,'rats',n);r.set(world,'generated7',1)
    end
    set('ratsObserved',1,'鼠帮已观察')
    say('厅堂里有 '..r.number(world,'rats')..' 只鼠帮成员；桶后有一道锁门，杂物旁放着蛇笛。')
  end
  local function deal()
    set('ratsDeal',1,'已取得鼠帮通行许可');set('hallDoor',1,'大厅后门已开放')
    doors={{edge='7-8',status='open'}};reveal={8}
    say('鼠帮同意放行，并用蛇笛完成这次交换。')
    if get('fluteRemaining')>0 then take(9,'fluteRemaining','蛇笛剩余数量') end
  end

  if action=='tunnel-ground' then
    discover_ground();say('你避开压痕，辨认出奶酪与上方落石的连接，并找到了通往主门的路线。')
  elseif action=='tunnel-cheese' then
    if choice=='inspect' then
      discover_ground();say('奶酪是机关诱饵。现在已经记录连接的位置，检查本身不会触发机关。')
    elseif get('cheese1')==0 then fail('奶酪已经被取走。')
    elseif not free_slot(6) then fail('背包没有可用槽位，奶酪留在原处。')
    elseif choice=='careful' and get('trapKnown')==0 then fail('先检查奶酪周围或观察地面，确认连接后才能拆解。')
    else
      out.cost=1;reveal={2}
      if get('trapState')==0 then
        if choice=='careful' and check('dex','解除奶酪的机关连接') then
          set('trapState',1,'入口机关（0待处理/1解除/2触发）');say('连接被稳妥解除，落石没有落下。')
        else
          set('trapState',2,'入口机关（0待处理/1解除/2触发）');hurt(dice(12,'入口落石伤害'))
          say('落石已经落下，机关不会再次触发。')
          if choice=='careful' or r.number(actor,'incapacitated')==1 or r.number(actor,'str')==0 then say('奶酪暂留原地。') end
        end
      else say('入口机关已经失效，可以安全取走奶酪。') end
      if out.outcome~='failure' and r.number(actor,'incapacitated')==0 and r.number(actor,'str')>0 then take(6,'cheese1','入口奶酪剩余数量') end
    end
  elseif action=='gate-handle' then
    set('gateKnown',1,'主门结构已识别');say('转动把手会使石板倾倒。门框上有可以绑绳固定的位置。')
    clue('gate-trap','倾倒的石板门','用绳索固定后再转动把手可避开倾倒；直接开启则需要躲避石板。')
  elseif action=='gate-open' then
    if get('gateOpen')==1 then say('石板门已经打开，可以前往庭院。');reveal={3}
    elseif choice=='brace' and get('gateKnown')==0 then fail('先检查把手和门框，确定固定位置。')
    elseif choice=='brace' and not has(4) then fail('需要仍有用量的绳索固定石板；也可以另选直接开门。')
    else
      out.cost=1
      if choice=='brace' then consume(4,'固定石板');set('gateTrap',1,'石板机关（0待处理/1解除/2触发）')
      elseif get('gateTrap')==0 then
        local avoided=check('dex','躲避倾倒石板');local amount=dice(20,'石板伤害')
        if avoided then amount=math.floor(amount/2);say('豁免成功，石板伤害减半。') end
        set('gateTrap',2,'石板机关（0待处理/1解除/2触发）');hurt(amount)
      end
      set('gateOpen',1,'石板门已打开');doors={{edge='2-3',status='open'}};reveal={3}
      say('石板门已经打开，庭院及其通路出现在已知地图上。')
    end
  elseif action=='courtyard-pool' then
    if choice=='inspect' then
      set('poolKnown',1,'池底宝物已发现');say('水下有一尊金叶鼠像和一只钱袋。鼠像占四格，钱袋内共有 140p。')
      clue('pool-treasure','池底的宝物','池底有四格金叶鼠像与钱袋；领取以现场剩余库存为准。')
    elseif get('poolKnown')==0 then fail('先查看池底，确定打捞目标。')
    elseif (choice=='money' and get('moneyRemaining')==0) or (choice=='idol' and get('idolRemaining')==0) then fail('这件宝物已经被取走。')
    elseif choice=='idol' and not free_slot(7) then fail('无法安置鼠像，宝物仍在池底。')
    else
      out.cost=1
      if check('dex','潜入池底打捞') then
        if choice=='money' then
          local amount=get('moneyRemaining');r.set(actor,'pips',r.number(actor,'pips')+amount);set('moneyRemaining',0,'池底剩余钱币');say('取得钱袋，钱币增加 '..amount..'p。')
        else take(7,'idolRemaining','池底鼠像剩余数量') end
      else hurt(dice(4,'潜水磕碰伤害'));say('你被水流推回岸边，宝物仍留在池底。') end
    end
  elseif action=='courtyard-ladders' then
    set('laddersKnown',1,'庭院路线已辨认');reveal={4,5,6,7,8};say('梯子通往三间房屋，地面通路连接大厅和奶酪工厂；这些地点已加入地图。')
  elseif action=='house-pots' then
    if r.number(world,'generated4')==0 then
      local count=dice(6,'首次搜查器具数量');r.set(world,'generated4',1);r.set(world,'pots',count);set('potsRemaining',count,'剩余铜锅盘');out.cost=1
    end
    set('potsKnown',1,'器具已整理');say('现场剩余 '..get('potsRemaining')..' 件铜锅盘，每件价值 10p。')
    if choice=='take' then take(8,'potsRemaining','剩余铜锅盘') end
  elseif action=='house-painting' then
    set('paintingRead',1,'节庆画已阅读');say('旧画描绘了庭院中央的一尊金色鼠像，与池底的物件相符。')
    clue('festival','旧日节庆画','旧画记录了庭院节庆时的布置，池底鼠像原本是庭院的陈设。')
  elseif action=='web-inspect' then
    set('webKnown',1,'蛛网屋危险已识别');say('两只蜘蛛在网线深处活动，网后困着两名村民。保持距离观察没有惊动它们。')
    clue('web-captives','蛛网后的村民','网线后困着 Roquefort 和 Paneer；携带可用武器可以尝试割断束缚。')
  elseif action=='web-call' then
    if choice=='whisper' then
      set('villagersContacted',1,'已联系被困村民');say('Roquefort 和 Paneer 低声回应，指出可以割断的网线。')
      clue('villager-reply','被困者的回应','两名村民尚能行动，束缚他们的网线可以割断，但附近有蜘蛛。')
    elseif get('villagersFreed')==1 then say('两名村民已经脱困，正在安全的庭院等待。')
    elseif not has(1) then fail('需要仍有用量的针剑才能执行这个固定救援做法。')
    else
      out.cost=1
      if check('dex','避开网线割断束缚') then
        set('villagersFreed',1,'两名村民已脱困');say('束缚被割开，两名村民沿梯子撤到庭院。')
        clue('villagers-rescued','Roquefort 与 Paneer 已脱困','你完成了救援，两名村民已撤到庭院。')
      else set('spidersAlert',1,'蜘蛛已警觉');hurt(dice(6,'蜘蛛毒咬伤害'),'dex');say('网线惊动了蜘蛛，救援尚未完成。') end
    end
  elseif action=='hall-observe' then rats()
  elseif action=='hall-negotiate' then
    rats()
    if get('ratsDeal')==1 then say('鼠帮仍认可之前的通行约定。');if get('fluteRemaining')>0 then take(9,'fluteRemaining','蛇笛剩余数量') end
    elseif choice=='food' then if consume(3,'提供口粮') then out.cost=1;deal() end
    elseif get('ratsTalked')==1 then fail('鼠帮已经拒绝这番说辞；可选择提供口粮，不会重复掷骰刷取结果。')
    else
      out.cost=1;set('ratsTalked',1,'已尝试口头交涉')
      if check('wil','说服鼠帮允许通行') then deal()
      else set('ratsAlert',1,'鼠帮保持戒备');say('鼠帮拒绝放行，但愿意用食物交换；后门仍锁住，蛇笛未取得。') end
    end
  elseif action=='factory-equipment' then
    if choice=='inspect' then
      set('factoryKnown',1,'工厂设备已检查');say('Jack 介绍了搅拌桨、滤布与升降机，并允许你取用留下的工具。')
      clue('factory-tools','工厂器具与升降机','工厂有有限数量的搅拌桨、滤布；升降机可以返回庭院。')
    elseif get('factoryKnown')==0 then fail('先检查设备并询问 Jack。')
    elseif choice=='paddle' then take(10,'paddleRemaining','剩余搅拌桨')
    else take(11,'clothRemaining','剩余滤布') end
  elseif action=='factory-exits' then
    if choice=='survey' then
      set('roofKnown',1,'工厂出口已辨认');reveal={3,7,9};say('你找到升降机、通往蛇笼的铁门和屋顶货口；桶后通往大厅的门仍遵循其锁闭状态。')
      clue('factory-exits','工厂出口','升降机通庭院，铁门通蛇笼，屋顶有通往室外的货口。')
    elseif choice=='iron' then
      if get('ironOpen')==0 then out.cost=1 end
      set('ironOpen',1,'工厂铁门已打开');doors={{edge='8-9',status='open'}};reveal={9};say('通往蛇笼的铁门已开放。')
    else r.set(actor,'location',3);reveal={3};say('你乘升降机返回庭院。');out.cost=1 end
  elseif action=='cage-gate' then
    set('snakeKnown',1,'守卫蛇已发现')
    if choice=='inspect' then say('洞窟在另一道铁门后。守卫蛇盘踞在门前，接近门闩需要先安抚它或冒险绕过。')
    elseif get('snakeCalmed')==0 then fail('守卫蛇尚未平静；可用蛇笛安抚，或从“聆听”选择潜行绕过。')
    else set('caveOpen',1,'洞窟铁门已开放');doors={{edge='9-10',status='open'}};reveal={10};say('你从平静的守卫蛇旁经过，打开了洞窟铁门。') end
  elseif action=='cage-listen' then
    set('snakeKnown',1,'守卫蛇已发现')
    if choice=='listen' then
      say('呼吸声与鳞片摩擦声来自同一条守卫蛇。它仍在门边，没有生成新的蛇。')
      clue('snake-rhythm','守卫蛇的动静','可以用蛇笛安抚守卫，或冒险绕过它开启洞窟铁门。')
    elseif choice=='flute' then
      if not has(9) then fail('需要携带蛇笛；可返回大厅交涉获取。')
      else set('snakeCalmed',1,'守卫蛇已平静');say('笛声让守卫蛇放松下来，现在可以靠近铁门。');out.cost=1 end
    else
      out.cost=1
      if get('caveOpen')==1 then say('通向洞窟的门已经打开。');out.cost=0
      elseif check('dex','绕过守卫蛇开启铁门') then
        set('caveOpen',1,'洞窟铁门已开放');doors={{edge='9-10',status='open'}};reveal={10};say('你抓住间隙拉开门闩，通路已经开放。')
      else set('snakeAlert',1,'守卫蛇已警觉');hurt(dice(8,'守卫蛇咬击伤害'));say('守卫蛇拦住去路，铁门仍未开启。') end
    end
  elseif action=='cave-cheese' then
    if choice=='inspect' then set('agingKnown',1,'奶酪库存已清点');say('这里还剩 '..get('cheese10')..' 轮奶酪，每轮价值 100p。')
    elseif get('cheese10')==0 then fail('这里的奶酪已取完。')
    elseif not free_slot(6) then fail('没有可用槽位，奶酪仍在原处。')
    elseif get('ernieAwake')==1 and get('ernieSpoken')==0 then fail('Ernie 已经醒来，先与他交谈取得许可。')
    else
      out.cost=1
      if get('ernieSpoken')==1 or check('dex','不惊动睡者取走奶酪') then take(6,'cheese10','熟成洞剩余奶酪')
      else set('ernieAwake',1,'Ernie 已醒来');say('动静惊醒了 Ernie，你停下动作，奶酪数量没有减少。') end
    end
  elseif action=='cave-sleeper' then
    set('ernieKnown',1,'Ernie 已被辨认')
    if choice=='observe' then say(get('ernieAwake')==1 and 'Ernie 已醒来，正看着洞中的动静。' or 'Ernie 正在熟睡。贸然搬动奶酪可能惊醒他。')
    else
      if get('ernieSpoken')==0 then out.cost=1 end
      set('ernieAwake',1,'Ernie 已醒来');set('ernieSpoken',1,'已与 Ernie 交谈');set('northKnown',1,'北方线索已取得')
      say('Ernie 允许你取用这里的奶酪，并指出失踪者的后续去向在北方。线索已加入记录。')
      clue('north','北方据点的线索','交谈得知，后续调查应前往北方的一处据点。树桩镇这一阶段的追踪线索已取得。')
    end
  end
  if out.cost>0 then
    local next=r.call('sv.world',session,'round',r.number(session,'round'))
    out.round=next.round;out.encounterDue=next.encounterDue
    say('经过一个探索轮，现在是第 '..next.round..' 回合；光源用量按已有规则结算。')
  end
  if #out.checks==0 and #out.rolls==0 then out.process='本做法不需要投骰，按现场条件直接判定。' else out.process='宿主已完成以下投骰与判定。' end
  return {public=out,reveals=reveal,doors=doors,sceneState=r.read(scene).numbers}
end, {kp=true,dependencies={'sv.layout','sv.damage','sv.grant','sv.world'}})
