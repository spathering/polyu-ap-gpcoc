// Game-facing navigation and deterministic pack workflows. Technical transport
// remains in app.js; raw command payloads never become screen content.
const labels={constitution:'体质',strength:'力量',speed:'速度',observation:'侦察',spirit:'精神',intellect:'智力',die:'骰点',target:'目标值',passed:'通过',damage:'伤害',hp:'剩余HP',stamina:'剩余体力',count:'数量',weapon:'武器加值',avoided:'闪避成功',day:'游戏日',slot:'轮次',kind:'行动',name:'姓名',talent:'窄专长',text:'说明',destination:'目的地',dice:'骰点',dodge:'闪避',ending:'结局'};
const kinds={explore:'探索',move:'移动',sleep:'睡眠',soothe:'安抚',wait:'等待',hint:'提示'};
export function humanResult(v){
  if(v===null||v===undefined)return '已完成';
  if(typeof v==='boolean')return v?'是':'否';
  if(Array.isArray(v))return v.map(humanResult).join('、');
  if(typeof v==='object'){
    if('die'in v&&'target'in v)return `检定 ${v.die} / ${v.target}，${v.passed?'成功':'未成功'}`;
    const fields=Object.entries(v).filter(([k])=>labels[k]);
    return fields.length?fields.map(([k,x])=>labels[k]+'：'+humanResult(x)).join('；'):'操作已由主机记录';
  }
  return kinds[v]||String(v);
}
export function humanMessage(m){
  if(m.deleted)return '消息已撤回';
  if(m.kind==='action')return humanResult(m.card?.result);
  const text=m.text||'';
  if(/^【(计划|角色申请)】\s*\{/.test(text)){
    try{return text.slice(0,text.indexOf('】')+1)+'\n'+humanResult(JSON.parse(text.slice(text.indexOf('】')+1)))}catch{return '历史申请格式不完整，请联系提交者补充说明'}
  }
  return text;
}

export function refine(ctx){
  const {S,$,esc,base,kp,mine,actor,all,mid,progress,input,select,btn,actopts,place,locationOptions,notice,api,command,invoke,tellKp,status,chars,historyHTML,actorPicker,channelPicker,createForm,oldRoom,oldLog,oldRefresh,oldRenderWindows,draw,initialize}=ctx;
  const empty={ready:false,enabled:false,logs:[],needs:[],knowledge:{},items:[],puzzles:[],party:[]};
  const auto=()=>S.automation||empty;
  const world=()=>all('md.world')[0]?.numbers||{day:1,slot:1};
  function timeLine(){const w=world();return `<div class="state-line"><strong>第${w.day}日 · ${esc(S.data?.slots?.[w.slot-1]||'上午1')}</strong><span>${w.closed?'调查时钟已结束':!auto().enabled?'人工处理：行动提交 KP':auto().ready?'常规行动自动结算':'自动会话到期，请 KP 重新登录'}</span></div>`}
  function logs(limit=30){return auto().logs.slice(0,limit).map(l=>`<article class="message"><div class="message-head"><span>${esc(l.account==='*'?'场景公告':l.account)}</span><time>${new Date(l.created*1000).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'})}</time></div><p>${esc(l.text)}</p></article>`).join('')||'<p class="empty">行动完成后，结果会记录在这里。</p>'}
  function queue(){return S.queue.map((q,i)=>`<button class="queue-entry" data-do="queue-select" data-value="${i}"><strong>${esc(q.title||'历史申请')}</strong><span>${esc(q.account||q.senderAccountId||'')}</span><p>${esc(humanMessage(q).slice(0,100))}</p></button>`).join('')||'<p class="empty">没有需要裁决的事项。</p>'}
  function choices(){return auto().needs.filter(n=>n.state==='open'&&['确认接收道具','选择防御'].includes(n.title)).map(n=>`<article class="decision"><h3>${esc(n.title)}</h3><p>${esc(n.text)}</p><div class="toolbar">${n.title==='选择防御'?btn('对抗','respond',n.id+'|counter','primary')+btn('闪避','respond',n.id+'|dodge'):btn('接收','respond',n.id+'|accept','primary')+btn('拒绝','respond',n.id+'|decline')}</div></article>`).join('')}
  function desk(){
    if(!kp())return actionPage();
    return `${timeLine()}<div class="overview"><article><small>需要裁决</small><strong>${S.queue.length}</strong><span>只处理规则之外的判断</span></article><article><small>调查员</small><strong>${all('md.character').filter(e=>e.owner!=='kp').length}</strong><span>资源由主机统一更新</span></article><article><small>自动处理</small><strong>${auto().enabled?'已开启':'已关闭'}</strong><span>${auto().enabled?'普通行动仅写入日志':'后续行动进入裁定队列'}</span></article></div><div class="columns"><section class="panel"><div class="section-head"><div><div class="eyebrow">DECISIONS</div><h2>等待你的判断</h2></div>${btn('独立裁定窗口','window','queue')}</div>${queue()}<p class="muted">${auto().enabled?'处理特殊方法、近义答案与剧情分歧；常规行动直接完成。':'人工模式：处理玩家提交的行动，使用管理表单结算后再反馈。'}</p></section><section class="panel"><div class="eyebrow">ACTIVITY</div><h2>自动行动日志</h2><div class="feed">${logs()}</div></section></div>`;
  }
  const sceneFor=()=>auto().scenes?.[actor()?.instanceId];
  function sceneControl(label,kind,value,available=true,reason='',extra=''){
    return `<button type="button" data-do="${kind}" data-value="${esc(value)}" ${extra} ${available?'':'disabled'}>${esc(label)}</button>${reason?`<small class="action-reason">${esc(reason)}</small>`:''}`;
  }
  function actionPage(){
    const e=actor();
    if(!e)return `<section class="panel"><h2>尚无调查员</h2><p>请 KP 建立角色后进入场景。</p>${createForm(false)}</section>`;
    const scene=sceneFor();
    if(!scene)return `${timeLine()}<section class="panel"><h2>正在同步当前场景</h2><p>连接主机后将显示当前地点、可前往的场景和现场行动。</p></section>`;
    const loc=scene.location,mode=auto().enabled?'执行':'申请',open=id=>S.sceneDetails?.[e.instanceId+':'+loc.index+':'+id]?'open':'';
    return `${timeLine()}${choices()}${auto().pending||S.autoPending?`<div class="decision">上一项行动的结果待确认。${btn('恢复原行动','recover-auto','','primary')}</div>`:''}<div id="scene-workspace" class="scene-workspace"><section class="scene-main"><section class="panel scene-intro"><div class="section-head"><div><div class="eyebrow">CURRENT SCENE</div><h2>${esc(loc.name)}</h2></div><span class="badge">${scene.searched?'已探索':'尚未探索'}</span></div>${actorPicker()}${status(e)}<p class="scene-text">${esc(loc.description)}</p><div class="scene-features"><span>调查重点</span>${(scene.features||[]).map(f=>`<span class="feature">${esc(f)}</span>`).join('')}</div><p class="muted">${auto().enabled?'选择行动后由主机结算，结果和发现会留在本页。':'人工模式：选择行动后交给 KP，不自动扣费或掷骰。'}</p></section><section class="panel" id="scene-actions"><h2>在这里做什么</h2><div class="scene-action-grid">${scene.actions.map(a=>`<article class="scene-action ${a.available?'':'unavailable'}"><strong>${esc(a.label)}</strong><small>${esc(a.cost)}</small>${sceneControl(mode+' · '+a.label,'scene-action',a.kind,a.available,a.reason,a.kind==='explore'?'class="primary"':'')}</article>`).join('')}</div></section><section class="panel" id="scene-investigation"><div class="section-head"><h2>现场调查与发现</h2><span class="muted">${scene.searched?'继续检查机关或领取物品':'先探索一次，展开现场交互'}</span></div>${!scene.searched?`<div class="empty">调查重点位于上方。选择“探索当前场景”，取得线索后，机关和物品会在此出现。</div>`:`<div id="scene-puzzles">${scene.puzzles.map(p=>`<details class="puzzle" id="scene-${p.id}" data-scene-detail="${p.id}" ${open(p.id)}><summary>${esc(p.name)} · ${p.solved?'已解开':'可检查'}</summary><p>${esc(p.prompt)}</p>${p.solved?'<p class="badge">机关已解开</p>':`<form id="puzzle-${esc(p.id)}" data-form="puzzle"><input type="hidden" name="puzzle" value="${esc(p.id)}">${input('你的回答','answer','text','','required maxlength="500"')}<button ${p.available?'':'disabled'}>${mode}尝试开启</button>${p.reason?'<small>'+esc(p.reason)+'</small>':''}</form>`}</details>`).join('')}</div><div id="scene-items" class="grid">${scene.items.map(i=>`<article class="card"><h3>${esc(i.name)}</h3><p>${esc(i.effect)}</p>${sceneControl(mode+'领取','take-item',i.index,i.available,i.reason)}</article>`).join('')}</div>${!scene.puzzles.length&&!scene.items.length?'<p class="muted">此处没有独立配置的机关或实体物品。可以再次侦察，或向 KP 描述更具体的调查方法。</p>':''}`}</section>${scene.endings.length?`<section class="panel"><h2>最终选择</h2><div class="scene-action-grid">${scene.endings.map(x=>`<article class="scene-action">${sceneControl(x.label,'scene-ending',x.choice,x.available,x.reason)}</article>`).join('')}</div></section>`:''}<details class="panel" id="scene-special" data-scene-detail="special" ${open('special')}><summary>特殊方法与角色互动</summary><form id="special-form" data-form="special"><input type="hidden" name="actor" value="${esc(e.instanceId)}"><label>描述调查方法或目标<textarea name="text" required maxlength="2000" placeholder="例如：检查墙后是否有夹层、与现场人物谈判……"></textarea></label><button>提交给 KP 裁决</button></form><form id="attack-choice-form" data-form="attack-choice">${select('攻击对象','target',(auto().party||[]).filter(p=>p.id!==e.instanceId).map(p=>[p.id,p.name]))}<button>发起攻击，由对方选择防御</button></form>${btn('联系 KP','private')}</details><details class="panel" data-scene-detail="recent" ${open('recent')}><summary>最近行动记录</summary><div class="feed compact-feed">${logs(5)}</div></details></section><aside class="scene-sidebar"><section class="panel" id="scene-navigation"><div class="section-head"><h2>可以去哪里</h2><span class="muted">从${esc(loc.name)}出发</span></div><p class="muted">前往占一次主要行动；“前往并探索”同时花费体力。</p><div class="scene-exits">${scene.exits.filter(x=>!x.via).map(x=>exitRow(x,mode)).join('')||'<p>当前没有可见出口。</p>'}</div>${scene.exits.some(x=>x.via)?`<details data-scene-detail="via" ${open('via')}><summary>沿走廊可一次探索的房间</summary>${scene.exits.filter(x=>x.via).map(x=>exitRow(x,mode)).join('')}</details>`:''}</section>${miniMap(scene)}</aside></div>`;
  }
  function exitRow(exit,mode){return `<article class="scene-exit" data-exit="${exit.index}"><strong>${esc(exit.name)}</strong>${exit.via?'<small>'+esc(exit.via)+'</small>':''}<div class="toolbar">${!exit.via?sceneControl(mode+'前往','scene-travel',exit.index,exit.move,'','data-kind="move"'):''}${sceneControl(exit.via?'沿走廊探索':mode+'前往并探索','scene-travel',exit.index,exit.explore,'','data-kind="explore"')}</div>${exit.reason?'<small class="action-reason">'+esc(exit.reason)+'</small>':''}</article>`}
  function miniMap(scene){
    const nodes=scene.map.nodes,current=scene.location.id,center=nodes.find(n=>n.id===current),others=nodes.filter(n=>n.id!==current);
    const positions=new Map([[current,{x:310,y:210}]]);
    others.forEach((n,i)=>{const inner=i<8,count=inner?Math.min(8,others.length):others.length-8,angle=-Math.PI/2+(inner?i:i-8)*Math.PI*2/Math.max(1,count);positions.set(n.id,{x:310+Math.cos(angle)*(inner?145:250),y:210+Math.sin(angle)*(inner?100:175)})});
    const selected=nodes.find(n=>n.index===S.mapSelection),exit=scene.exits.find(x=>x.index===S.mapSelection);
    return `<details id="scene-map" class="panel scene-minimap" ${S.mapOpen?'open':''}><summary><span>小地图</span><small>${esc(scene.location.name)} · 点击展开／折叠</small></summary><div class="minimap-body"><p class="muted">金色为当前位置，绿色为已探索，灰色为周边未探索；虚线为未开放通路。选点只查看路线。</p><svg viewBox="0 0 620 420" role="img" aria-label="已知场景关系小地图">${scene.map.edges.map(edge=>{const a=positions.get(edge.from),b=positions.get(edge.to);return a&&b?`<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" class="${edge.blocked?'blocked':''}"/>`:''}).join('')}${[...others,...(center?[center]:[])].map(n=>{const p=positions.get(n.id);return `<a href="#" role="button" aria-label="查看${esc(n.name)}路线" data-do="map-node" data-value="${n.index}" class="${n.id===current?'current':n.explored?'explored':'nearby'}"><title>${esc(n.name)} · ${n.explored?'已探索':'未探索'}</title><rect x="${p.x-53}" y="${p.y-14}" width="106" height="29" rx="6"/><text x="${p.x}" y="${p.y+4}" text-anchor="middle">${esc(n.name)}</text></a>`}).join('')}</svg>${selected?`<div class="minimap-selection"><strong>${esc(selected.name)}</strong>${selected.id===current?'<p>你在这里。</p>':exit?exitRow(exit,auto().enabled?'执行':'申请'):'<p class="muted">当前不能直接抵达，请沿“可以去哪里”中的相邻场景逐步前往。</p>'}</div>`:''}</div></details>`;
  }
  function interaction(e){return `<details><summary>船、阵法与剧情选择</summary><form id="interaction-form" data-form="interaction">${select('操作','kind',[['hint','消耗1智力额度获取现场提示'],['open-maintenance','拉动管家房维修拉杆'],['start-boat','在船舱／地下控制室启动船'],['stop-tracking','关闭地下追踪阵法'],['boat-key','出示证据并承诺不再互杀']])}<button>执行所选互动</button></form><form id="ending-choice-form" data-form="choose-ending">${select('最终选择','choice',[[1,'归航'],[2,'携证归航'],[3,'留守'],[4,'前往神界'],[5,'困岛续章']])}<button>确认本人结局</button></form></details><details><summary>发起攻击，由对方选择防御</summary><form id="attack-choice-form" data-form="attack-choice">${select('目标','target',(auto().party||[]).filter(p=>p.id!==e.instanceId).map(p=>[p.id,p.name]))}<button>发送攻击请求</button></form></details>`}
  function cardsPage(){
    const k=auto().knowledge;
    return `<div class="subnav">${[['found','发现与机关'],['share','文字卡与分享']].map(([id,label])=>btn(label,'card-tab',id,(S.cardTab||'found')===id?'active':'')).join('')}</div>${S.cardTab==='share'?`<div class="columns"><section class="panel"><h2>制作文字线索卡</h2><form id="card-form" data-form="card">${input('标题','title','text','','required maxlength="100"')}<label>内容<textarea name="text" required maxlength="3000"></textarea></label>${select('分享给','audience',Object.values(S.view.chatChannels||{}).map(c=>[c.channelId,c.name||'私聊']),S.channel)}<button>发布文字卡</button></form></section><section class="panel"><h2>频道记录</h2>${channelPicker()}${historyHTML()}</section></div>`:`<div class="columns"><section class="panel"><h2>调查线索</h2>${(kp()?S.data.clues:k.clues||[]).map(c=>`<article class="card"><h3>线索 ${esc(c.id)}</h3><p>${esc(c.text)}</p></article>`).join('')||'<p class="empty">探索后，核心线索会自动保存。</p>'}</section><section class="panel"><h2>机关与谜题</h2>${(kp()?S.data.puzzles:auto().puzzles).map(p=>`<details class="puzzle"><summary>${esc(p.name)} ${(k.puzzles||[]).includes(p.id)?'· 已解开':''}</summary><p>${esc(p.prompt)}</p>${kp()?`<p class="muted">解法：${esc(p.answer)}</p>`:`<p class="muted">机关需要在所在场景中操作。</p>${btn('返回场景调查','page','desk')}`}</details>`).join('')||'<p class="empty">先探索地点，发现机关后可以直接尝试答案。</p>'}</section></div>`}`;
  }
  function mapPage(){
    const known=auto().knowledge,legacy=progress('md.known')||{};
    const revealed=[...(known.locations||[]),...(legacy.locations||[]),1].map(x=>typeof x==='object'?x:place(x)).filter(Boolean);
    const entries=kp()?S.data.locations:[...new Map(revealed.map(l=>[l.index,l])).values()];
    const groups=[['public','宅邸公共区',1,6],['rooms','宅邸内室',7,13],['island','岛屿',14,21],['shore','地下与海岸',22,23]];
    const tab=S.mapTab||'public',group=groups.find(g=>g[0]===tab)||groups[0];
    const places=entries.filter(l=>l.index>=group[2]&&l.index<=group[3]);
    let reveal='';
    if(kp()){
      const source=document.createElement('div');source.innerHTML=ctx.oldMap();
      reveal=`<details class="panel"><summary>向指定玩家补充地点描述</summary>${source.querySelector('#reveal-form')?.outerHTML||''}</details>`;
    }
    return `${timeLine()}<div class="subnav">${groups.map(([id,label,low,high])=>btn(label+' · '+entries.filter(l=>l.index>=low&&l.index<=high).length,'map-tab',id,tab===id?'active':'')).join('')}</div><section class="panel"><div class="section-head"><div><div class="eyebrow">ISLAND MAP</div><h2>${esc(group[1])}</h2></div>${btn('返回现场','page','desk')}</div><p class="muted">选择地点会填入行动表单；执行时检查通路和机关条件。</p><div class="grid">${places.map(l=>`<article class="card location ${actor()?.numbers.location===l.index?'current':''}"><h3>${esc(l.name)}</h3><p>${esc(kp()?l.description:known.descriptions?.[l.index]||legacy.descriptions?.[l.index]||'已知此处的入口，探索后可记录现场。')}</p>${kp()?`<small>相邻：${esc(l.adjacentIds?.map(id=>S.data.locations.find(x=>x.id===id)?.name||'').join('、'))}</small>`:''}<p>${btn('选择此地','map-plan',l.index)}</p></article>`).join('')||'<p class="empty">尚未发现此区域的地点。</p>'}</div></section>${reveal}`;
  }
  function inventory(){
    const e=actor();
    return `<div class="subnav">${[['items','持有道具'],['people','角色状态'],['found','现场领取']].map(([id,label])=>btn(label,'bag-tab',id,(S.bagTab||'items')===id?'active':'')).join('')}</div>${S.bagTab==='people'?`<section class="panel"><h2>角色状态</h2><div class="grid">${chars()}</div></section>`:S.bagTab==='found'?`<section class="panel"><h2>已探索地点的物品</h2><p class="muted">主机核验当前位置、解谜资格、共享库存、全队每日三件额度及四格容量。</p><div class="grid">${auto().items.filter(i=>i.location===place(e?.numbers.location)?.id).map(i=>`<article class="card"><h3>${esc(i.name)}</h3><p>${esc(i.effect)}</p>${btn('在场景中查看与领取','page',kp()?'plan':'desk')}</article>`).join('')||'<p class="empty">探索后，这里会列出可检查的物品。</p>'}</div></section>`:`<section class="panel"><div class="section-head"><h2>${kp()?'道具实例':'我的背包'}</h2>${btn('查看现场物品','bag-tab','found')}</div>${e?status(e):''}<div class="grid">${all('md.item').filter(i=>i.numbers.count>0).map(i=>`<article class="card"><h3>${esc(i.name)}</h3><p>${i.numbers.count}份 · ${i.numbers.star}星${i.numbers.equipped?' · 已装备':''}${i.numbers.charges?' · 剩余弹药 '+i.numbers.charges:''}</p><small>${i.numbers.confirmed?'卡片已确认':'卡片待确认'}${kp()?' · '+esc(i.owner):''}</small><div class="toolbar">${i.numbers.star?btn('装备','equip-auto',i.instanceId):''}${[4,5,20,21].includes(i.numbers.itemIndex)?btn('使用','consume-auto',i.instanceId):''}${btn('丢弃','discard-auto',i.instanceId)}</div>${!kp()?`<details><summary>转交给同伴</summary><form id="offer-${i.instanceId}" data-form="offer"><input type="hidden" name="item" value="${i.instanceId}">${select('接收者','target',(auto().party||[]).filter(p=>p.id!==e?.instanceId).map(p=>[p.id,p.name]))}<button>请求接收</button></form></details>`:''}</article>`).join('')||'<p class="empty">当前没有道具卡。</p>'}</div><details><summary>未定义的道具操作</summary><form id="item-request" data-form="special">${select('角色','actor',actopts())}<label>说明<textarea name="text" required maxlength="2000"></textarea></label><button>提交给 KP</button></form></details></section>`}`;
  }
  const managerTabs=[['rulings','裁定与沟通'],['characters','角色与战斗'],['items','道具管理'],['scenario','场景资料'],['setup','开局与存档']];
  function management(){
    if(!kp())return `<section class="panel">${createForm(false)}</section>`;
    const tab=S.manageTab||'rulings',source=document.createElement('div');source.innerHTML=oldRoom();
    const extract=(id,title='')=>{const node=source.querySelector('#'+id);return node?`<section class="panel">${title?'<h2>'+title+'</h2>':''}${node.outerHTML}</section>`:''};
    let content='';
    if(tab==='rulings')content=`<div class="columns"><section class="panel"><h2>必要裁定</h2>${queue()}<details><summary>人工修正常规行动</summary>${source.querySelector('#resolve-form')?.outerHTML||''}</details></section><section>${extract('feedback-form','单独反馈')}${extract('request-form','请求检定')}</section></div>`;
    if(tab==='characters')content=`<div class="columns"><section class="panel"><h2>角色</h2>${btn('建立缺失的4个预设角色','prepare-presets')}<details><summary>建立其他角色</summary>${createForm(true)}</details><div class="grid">${chars()}</div></section><section><section class="panel"><h2>NPC与特殊战斗</h2><p class="muted">玩家可在行动页发起攻击，由对方确认防御。</p>${btn('建立海岸追踪者','pursuer')}${source.querySelector('#combat-form')?.outerHTML||''}</section>${extract('damage-form','特殊伤害')}</section></div>`;
    if(tab==='items')content=`<div class="columns"><section class="panel"><h2>特殊道具发放</h2><p class="muted">普通领取在玩家背包中自动结算。此表处理额外剧情发放。</p><form id="grant-form" data-form="grant">${select('角色','actor',actopts())}${select('道具','item',S.data.items.map(i=>[i.index,i.name]))}<button>发放待确认卡片</button></form><h3>卡面审核</h3>${all('md.item').filter(i=>!i.numbers.confirmed&&i.numbers.count>0).map(i=>`<p>${esc(i.name)} · ${esc(i.owner)} ${btn('确认卡面','confirm-item',i.instanceId)}</p>`).join('')||'<p>没有待确认卡面。</p>'}</section><section>${extract('consume-form','特殊消耗处理')}${extract('transfer-item-form','主持协助转交')}</section></div>`;
    if(tab==='scenario'){
      const section=S.editSection||'locations',sections=[['locations','地点'],['items','道具'],['clues','线索'],['puzzles','谜题'],['npcs','人物'],['events','事件'],['endings','结局']];
      const fields={name:'名称',description:'描述',effect:'效果',text:'正文',method:'调查方法',successBonus:'成功奖励',leads:'指向',prompt:'题面',answer:'答案',success:'结果',alternative:'替代路径',gameTime:'时间',condition:'条件',initialPlacement:'初始分布',obtainCondition:'获取条件',quantity:'总库存',star:'星级',source:'来源',locationId:'地点引用',stackMax:'堆叠上限',slots:'卡槽占用'};
      content=`<section class="panel"><h2>场景资料</h2><p class="muted">按类别编辑单个字段。改写题面不会自动改变机关的标准答案；自动条件随本地配置包维护。</p><div class="subnav">${sections.map(([id,label])=>btn(label,'edit-section',id,section===id?'active':'')).join('')}</div><form id="scenario-edit-form" data-form="scenario-edit">${select('对象与字段','target',(S.data[section]||[]).flatMap((o,i)=>Object.keys(o).filter(k=>fields[k]&&['string','number'].includes(typeof o[k])).map(k=>[section+':'+i+':'+k,(o.name||o.id)+' · '+fields[k]])))}${btn('读取当前内容','load-field')}<label>新内容<textarea name="value" required maxlength="4000"></textarea></label><button>校验并发布修订</button></form></section>`;
    }
    if(tab==='setup')content=`<div class="columns"><section class="panel"><h2>开局准备与更新</h2>${btn('导入本地更新配置','install-local','','primary')}${btn('建立缺失的4个预设角色','prepare-presets')}<h3>世界时钟</h3><p class="muted">全员主要行动完成后自动推进；未完成的特殊裁决会暂停推进。</p>${btn('建立世界时钟','world')}${btn('人工结束本轮','advance')}<details><summary>修正世界机关与结局</summary>${source.querySelector('#worldflag-form')?.outerHTML||''}${source.querySelector('#ending-form')?.outerHTML||''}</details></section><section class="panel"><h2>存档与服务</h2>${btn('保存主机备份','backup-readable')}${btn('停止本机服务','shutdown')}<details><summary>配置文件导入与导出</summary>${source.querySelector('#upload-pack-form')?.outerHTML||''}${btn('导出当前配置文件','export-pack')}</details><p class="muted">自动化使用独立 KP 会话，关闭 KP 标签页后仍可处理。Windows 会按当前系统用户加密保存会话；到期后请 KP 再登录一次。</p></section></div>`;
    return `<div class="subnav">${managerTabs.map(([id,label])=>btn(label,'manage-tab',id,tab===id?'active':'')).join('')}</div>${content}`;
  }
  function records(){return `<div class="columns"><section class="panel"><h2>行动记录</h2><div class="feed">${logs(60)}</div><h3>裁决与选择反馈</h3>${auto().needs.filter(n=>n.state==='done').map(n=>`<article class="message"><strong>${esc(n.title)}</strong><p>${esc(n.reply)}</p></article>`).join('')||'<p class="muted">暂无反馈。</p>'}</section><section>${oldLog().replace(/<h2>.*?<\/h2>/,'<h2>连接与操作恢复</h2>').replace(/<p>请求 .*?的结果未确认。不会重新生成请求ID。<\/p>/,'<p>上一项管理操作的结果待确认。</p>')}${auto().pending||S.autoPending?`<section class="panel">${btn('恢复原行动','recover-auto','','primary')}</section>`:''}${!kp()?`<details class="panel"><summary>申请其他角色</summary>${createForm(false)}</details>`:''}</section></div>`}
  async function packageAPI(path,body){const r=await fetch(base+'package/'+path,{method:body===undefined?'GET':'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':S.csrf},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(40000)});const data=await r.json();if(!r.ok)throw new Error(data.code||'操作未完成');return data}
  const storageKey=()=> 'md-action:'+base+':'+S.view.accountId;
  async function action(kind,fields={},recover=false){
    if(S.autoBusy)throw new Error('正在处理行动，请稍候');
    if(!recover&&(S.autoPending||auto().pending))throw new Error('请先恢复上一项行动');
    const body=recover?(S.autoPending||auto().pending):{id:crypto.randomUUID(),kind,actor:actor()?.instanceId,...fields};
    if(!body)throw new Error('没有待恢复的行动');
    S.autoPending=body;sessionStorage.setItem(storageKey(),JSON.stringify(body));S.autoBusy=true;
    try{const result=await packageAPI('action',body);S.autoPending=null;sessionStorage.removeItem(storageKey());notice(result.message);return result}finally{S.autoBusy=false}
  }
  async function refresh(){
    if(refresh.runningWorkflow)return;refresh.runningWorkflow=true;
    await oldRefresh();if(!S.view){refresh.runningWorkflow=false;return;}
    try{
      if(refresh.account!==S.view.accountId){refresh.account=S.view.accountId;S.autoPending=null;S.automation=null;S.sceneDetails={};S.mapSelection=undefined;try{S.mapOpen=JSON.parse(localStorage.getItem('md-scene-map:'+base+S.view.accountId)||'false')}catch{S.mapOpen=false}}
      const prior=JSON.stringify(S.automation);S.automation=await packageAPI('automation');
      for(const scene of Object.values(auto().scenes||{}))for(const node of scene.map.nodes)if(!S.data.locations.some(l=>l.index===node.index))S.data.locations.push(node);
      if(!kp())S.data.locations=[...new Map([...S.data.locations,...(auto().knowledge.locations||[]).filter(l=>typeof l==='object')].map(l=>[l.index,l])).values()];
      if(!S.autoPending)try{S.autoPending=JSON.parse(sessionStorage.getItem(storageKey())||'null')}catch{}
      const legacy=S.queue.filter(q=>q.messageId);S.queue=kp()?[...auto().needs.filter(n=>n.state==='open'),...legacy]:[];
      const key=JSON.stringify(S.queue);if(prior!==JSON.stringify(S.automation)||key!==refresh.queueKey){refresh.queueKey=key;draw()}
    }catch{S.automation=empty}finally{refresh.runningWorkflow=false}
  }
  function renderWindows(){oldRenderWindows();if(!S.view)return;const e=$('queue');const body=e.querySelector('.window-body');if(body)body.innerHTML=queue();const heading=e.querySelector('strong');if(heading)heading.textContent='KP 裁定队列 · '+S.queue.length;const trigger=document.querySelector('header [data-do="window"][data-value="queue"]');if(trigger){trigger.textContent='待裁决 '+S.queue.length;trigger.classList.toggle('attention',S.queue.length>0)}if(kp()){const toolbar=document.querySelector('header .right');if(toolbar&&!toolbar.querySelector('[data-do=toggle-auto]'))toolbar.insertAdjacentHTML('afterbegin',`<button type="button" role="switch" aria-checked="${!!auto().enabled}" data-do="toggle-auto" class="auto-switch"><span class="switch-track" aria-hidden="true"></span>自动处理 · ${auto().enabled?'开':'关'}</button>`);if(toolbar&&!toolbar.querySelector('[data-do=advance]'))toolbar.insertAdjacentHTML('beforeend',`<button type="button" data-do="advance" ${world().closed||all('md.world').length!==1?'disabled':''}>下一轮</button>`)}}
  function catchError(error){notice(friendly(error.message))}
  function friendly(text){return ({MD_SLOT_USED:'本轮主要行动已完成',MD_NOT_SOOTHING_LOCATION:'请前往音乐室、浴场或桑拿房进行安抚',MD_REQUEST_PENDING:'请先完成待掷骰检定',MD_NO_AMMO:'弹药已经耗尽',MD_NO_INTELLECT:'今日提示额度已用完',AUTOMATION_UNAVAILABLE:'请停止服务后重新打开账号 exe，以载入自动行动服务'})[text]||text}
  const forms=new Set(['auto-plan','special','puzzle','interaction','choose-ending','attack-choice','offer','ruling','application']);
  document.addEventListener('submit',async ev=>{
    const f=ev.target.closest('form[data-form]');if(!f||!forms.has(f.dataset.form))return;
    ev.preventDefault();ev.stopImmediatePropagation();const d=new FormData(f),get=k=>d.get(k);
    try{
      switch(f.dataset.form){
        case 'auto-plan':await action(get('kind'),{actor:get('actor'),destination:Number(get('destination'))});break;
        case 'special':await action('special',{actor:get('actor')||actor()?.instanceId,text:get('text')});f.reset();break;
        case 'puzzle':await action('puzzle',{puzzle:get('puzzle'),answer:get('answer')});break;
        case 'interaction':await action(get('kind'),{choice:get('kind')==='boat-key'?'promise':''});break;
        case 'choose-ending':if(confirm('确认这名角色的最终选择？'))await action('ending',{choice:get('choice')});break;
        case 'attack-choice':await action('attack',{target:get('target')});break;
        case 'offer':await action('offer',{item:get('item'),target:get('target')});break;
        case 'ruling':await action('ruling',{target:get('target'),text:get('text')});$('detail').close();break;
        case 'application':{
          const keys=['constitution','strength','speed','observation','spirit','intellect'];if(keys.reduce((s,k)=>s+Number(get(k)),0)!==20)throw new Error('六维合计必须20');
          await tellKp('【角色申请】\n姓名：'+get('name')+'\n'+keys.map(k=>labels[k]+'：'+get(k)).join('，')+'\n窄专长：'+get('talent'));notice('角色申请已提交');break;
        }
      }
      await refresh();
    }catch(e){catchError(e);await refresh()}
  },true);
  const clicks=new Set(['advance','scene-action','scene-travel','scene-ending','map-node','map-plan','page','toggle-auto','manage-tab','card-tab','bag-tab','map-tab','edit-section','auto-check','auto-finish','auto-search','take-item','equip-auto','consume-auto','discard-auto','respond','recover-auto','queue-select','open-legacy','backup-readable','install-local','roll']);
  document.addEventListener('click',async ev=>{
    const b=ev.target.closest('[data-do]');if(!b||!clicks.has(b.dataset.do))return;
    if(b.dataset.do==='page'&&(b.dataset.value!=='map'||kp()))return;
    ev.preventDefault();ev.stopImmediatePropagation();const type=b.dataset.do,v=b.dataset.value;
    try{
      switch(type){
        case 'advance':{
          if(!kp())throw new Error('只有 KP 可以推进轮次');
          const w=world(),characters=all('md.character').filter(a=>a.owner!==S.view.accountId&&a.numbers.approved&&a.numbers.hp>0&&!a.numbers.ending);
          const unfinished=characters.filter(a=>!a.numbers.slotUsed||a.numbers.day!==w.day||a.numbers.slot!==w.slot).length,encounters=characters.filter(a=>a.numbers.encounterActive).length;
          if(!confirm(`结束当前轮次并推进？\n尚未完成主要行动：${unfinished}人；遭遇中：${encounters}人；待裁决：${S.queue.length}项。\n未决事项和遭遇会保留，角色轮次会同步。`))return;
          await action('advance');break;
        }
        case 'page':S.page='desk';S.mapOpen=true;draw();return;
        case 'map-plan':S.page=kp()?'plan':'desk';S.mapOpen=true;S.mapSelection=Number(v);draw();return;
        case 'map-node':S.mapSelection=Number(v);S.mapOpen=true;draw();return;
        case 'scene-action':{
          const scene=sceneFor(),selected=scene?.actions.find(a=>a.kind===v);if(!selected||!selected.available)throw new Error(selected?.reason||'场景尚未同步');
          if(v==='boat-key'&&!confirm('出示选拔证据，并明确承诺不再互杀？'))return;
          await action(v,{actor:scene.actor,destination:scene.location.index,...(selected.choice?{choice:selected.choice}:{})});break;
        }
        case 'scene-travel':{
          const scene=sceneFor(),exit=scene?.exits.find(x=>x.index===Number(v)),kind=b.dataset.kind;
          if(!exit||!exit[kind])throw new Error(exit?.reason||'当前不能沿此路前往');
          await action(kind,{actor:scene.actor,destination:exit.index});S.mapSelection=undefined;break;
        }
        case 'scene-ending':if(confirm('确认这名角色的最终选择？'))await action('ending',{choice:v});break;
        case 'toggle-auto':{if(S.switching)return;S.switching=true;try{const r=await packageAPI('automation',{enabled:!auto().enabled});notice(r.message)}finally{S.switching=false}break;}
        case 'manage-tab':S.manageTab=v;draw();return;
        case 'card-tab':S.cardTab=v;draw();return;
        case 'bag-tab':S.bagTab=v;draw();return;
        case 'map-tab':S.mapTab=v;draw();return;
        case 'edit-section':S.editSection=v;draw();return;
        case 'auto-check':case 'roll':await action('check',{actor:v});break;
        case 'auto-finish':await action('finish',{actor:v});break;
        case 'auto-search':await action('search',{actor:v});break;
        case 'take-item':await action('take',{item:Number(v)});break;
        case 'recover-auto':await action('',{},true);break;
        case 'equip-auto':case 'consume-auto':case 'discard-auto':{
          if(type==='discard-auto'&&!confirm('丢弃此道具并释放卡槽？'))return;
          const rel=Object.values(S.view.relations).find(r=>r.sourceId===v&&r.relationType==='source');await action(type.split('-')[0],{actor:rel?.targetId||actor()?.instanceId,item:v});break;
        }
        case 'respond':{const [target,choice]=v.split('|');await action('respond',{target,choice});break}
        case 'queue-select':{
          const q=S.queue[Number(v)];S.selected=q;
          $('detail-body').innerHTML=`<h2>${esc(q.title||'待处理申请')}</h2><p class="scene-text">${esc(humanMessage(q))}</p>${q.id?`<form id="ruling-form" data-form="ruling"><input type="hidden" name="target" value="${esc(q.id)}"><label>裁决反馈<textarea name="text" required maxlength="2000"></textarea></label><p class="muted">需要改动机关或角色时，请先在主持管理中完成修正，再记录反馈。</p><button>完成裁决并反馈</button></form>`:btn('打开主持处理台','open-legacy')+btn('标为已处理','complete-request')}`;
          $('detail').showModal();return;
        }
        case 'open-legacy':S.page='room';S.manageTab=S.selected.text.startsWith('【角色申请】')?'characters':'rulings';$('detail').close();draw();return;
        case 'backup-readable':await api('/backup',{});notice('主机一致备份已保存');return;
        case 'install-local':{
          if(!confirm('导入本地配置更新？已发布的场景文字修订将替换为本地内容，角色进度保留。'))return;
          const content=await packageAPI('bundle.json'),rev=await command('rule.stage',{sources:content.sources,data:content.data});await command('rule.activate',{revision:rev});for(const c of content.configurations)await command('configuration.put',c);S.bundle=content;S.data=content.data['scenario.json'];notice('配置已更新，角色进度保留');break;
        }
      }
      await refresh();
    }catch(e){catchError(e);await refresh()}
  },true);
  document.addEventListener('toggle',ev=>{
    if(!ev.target.isConnected||!S.view)return;
    if(ev.target.id==='scene-map'){S.mapOpen=ev.target.open;localStorage.setItem('md-scene-map:'+base+S.view.accountId,JSON.stringify(S.mapOpen))}
    const key=ev.target.dataset.sceneDetail,scene=sceneFor();
    if(key&&scene){S.sceneDetails??={};S.sceneDetails[scene.actor+':'+scene.location.index+':'+key]=ev.target.open}
  },true);
  document.addEventListener('keydown',ev=>{
    if(!S.view||ev.target.matches('input,textarea,select')||ev.target.isContentEditable||ev.key.toLowerCase()!=='m')return;
    ev.preventDefault();ev.stopImmediatePropagation();S.page=kp()?'plan':'desk';S.mapOpen=!S.mapOpen;draw();
  },true);
  return {desk,actionPage,mapPage,cardsPage,inventory,management,records,refresh,renderWindows};
}
