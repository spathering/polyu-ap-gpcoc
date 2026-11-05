const $ = id => document.getElementById(id);
const slot = location.pathname.match(/^\/sessions\/(kp|player1|player2)\//)?.[1] || '';
const base = slot ? `/sessions/${slot}/` : '/';
const journalKey = account => slot ? `lf-journal:slot:${slot}:${account}` : 'lf-journal:'+account;
const sessionLinks = () => `<nav class="session-switch" aria-label="同机多账号测试"><span>同机测试入口：</span>${[['kp','KP'],['player1','玩家1'],['player2','玩家2']].map(([id,name])=>`<a href="/sessions/${id}/" target="_blank" rel="noopener">${name} 测试窗口 ↗</a>`).join('')}<small>当前入口：${slot||'默认'}；各入口独立登录</small></nav>`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const S = {auth:false, csrf:null, view:null, members:[], channel:'general', messages:[], revision:null,
  nextBefore:null, reply:null, connected:false, busy:false, refreshing:false, journal:null, data:null, bundle:null};
let renderKey='';
let noticeTimer;
function notice(text) { $('notice').textContent = text; $('notice').style.display='block'; clearTimeout(noticeTimer); noticeTimer=setTimeout(()=>$('notice').style.display='none',6500); }
class ApiError extends Error { constructor(data, status) { super(data.code || '请求失败'); this.data=data; this.status=status; } }
async function api(path, body) {
  let response;
  try { response=await fetch(base+'api/v1'+path,{method:body===undefined?'GET':'POST',credentials:'same-origin',
    headers:{'Content-Type':'application/json',...(S.csrf?{'X-CSRF-Token':S.csrf}:{})},
    body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(25000)}); }
  catch { throw new Error('连接中断，操作结果可能尚未确认'); }
  const data=await response.json();
  if(!response.ok) throw new ApiError(data,response.status);
  return data;
}
const ref=(index,path='result')=>({$ref:`${index}.${path}`});
function resolve(value, results) {
  if(Array.isArray(value)) return value.map(v=>resolve(v,results));
  if(value && typeof value==='object') {
    if(Object.keys(value).length===1 && value.$ref) return value.$ref.split('.').reduce((o,k)=>o[k],results);
    return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,resolve(v,results)]));
  }
  return value;
}
function saveJournal() { localStorage.setItem(journalKey(S.view.accountId),JSON.stringify(S.journal)); }
async function makeEnvelope(op,args) {
  const v=await api('/view');
  if(v.accountId!==S.view.accountId) throw new Error('登录身份已改变，请重新登录');
  return {protocolVersion:1,type:'command',requestId:crypto.randomUUID(),roomId:v.roomId,payload:{
    commandId:crypto.randomUUID(),authorityEpoch:v.authorityEpoch,runId:v.runId,
    catalogRevision:v.catalog.revision,rulesetRevision:v.catalog.rulesetRevision,expectedViews:{},op,args}};
}
async function plan(label,steps) {
  if(S.busy || S.journal?.plan) throw new Error('请先恢复或处理上一个操作');
  S.journal.plan={label,steps,index:0,results:[],envelope:null,error:null,knownFailure:false};
  saveJournal();
  return executePlan();
}
async function executePlan() {
  const p=S.journal.plan;
  if(!p || S.busy) return;
  S.busy=true; draw();
  try {
    while(p.index<p.steps.length) {
      const step=p.steps[p.index];
      if(!p.envelope) { p.envelope=await makeEnvelope(step.op,resolve(step.args,p.results)); saveJournal(); }
      let receipt=await api('/receipts/'+p.envelope.payload.commandId);
      if(receipt.status==='unknown') receipt=await api('/commands',p.envelope);
      if(receipt.status==='pending' || receipt.status==='unknown') throw new Error('主机仍在处理，请稍后恢复此操作');
      if(receipt.status!=='committed') throw new ApiError({code:receipt.code||'规则拒绝'},409);
      if(step.key) S.journal.receipts[step.key]=receipt.commandId;
      p.results.push(receipt); p.index++; p.envelope=null; p.error=null; p.knownFailure=false; saveJournal();
    }
    const result=p.results.at(-1)?.result;
    S.journal.plan=null; saveJournal(); notice(p.label+'已完成');
    return result;
  } catch(error) {
    p.error=error.message; p.knownFailure=error instanceof ApiError; saveJournal();
    notice(p.knownFailure?'操作被拒绝：'+error.message+'。已完成的步骤保留。':error.message+'；请使用恢复操作，避免重复提交。');
  } finally { S.busy=false; await refresh(); draw(); }
}
const step=(op,args,key)=>({op,args,...(key?{key}:{})});
const invoke=(id,inputs,key)=>step('action.invoke',{actionId:id,input:inputs},key);
const all=configuration=>Object.values(S.view?.entities||{}).filter(e=>e.configurationId===configuration && e.lifecycle==='active');
const related=(id,type)=>Object.values(S.view?.relations||{}).filter(r=>r.sourceId===id && r.relationType===type).map(r=>r.targetId);
const entity=id=>S.view.entities[id];
const id=e=>e.instanceId;
const options=(values,current)=>values.map(([value,label])=>`<option value="${esc(value)}" ${String(current)===String(value)?'selected':''}>${esc(label)}</option>`).join('');
const indexed=(values,offset=1)=>values.map((v,i)=>[i+offset,v]);
const select=(name,values,current)=>`<select id="${esc(name)}" name="${esc(name)}">${options(values,current)}</select>`;
const label=(title,input)=>`<label>${esc(title)}${input.replace(/^<(input|select|textarea)\b/,`<$1 aria-label="${esc(title)}"`)}</label>`;
const button=(text,action,value='',kind='secondary')=>`<button type="button" class="${kind}" data-do="${action}" data-value="${esc(value)}">${esc(text)}</button>`;
const sourceOf=record=>entity(related(id(record),'source')[0]);
const phaseText=['准备中','协助开放','协助已关闭','已取消'];
function diceHTML(n) {
  return `<div class="dice">${Array.from({length:n.dice||0},(_,i)=>n['die'+(i+1)]).map(d=>
    `<span class="die ${d===n.number?'insight':(n.mode===0?d<n.number:d>n.number)?'':'fail'}" title="${d===n.number?'特殊洞察，同时成功':''}">${d}</span>`).join('')}</div>`;
}
function cards() {
  return all('lf.character').map(e=>{
    const n=e.numbers;
    const bio=Object.values(S.view.progress||{}).find(p=>p.ownerId===id(e)&&p.eventKey==='lf.bio')?.value;
    return `<div class="chip"><div class="character-head"><div><strong>${esc(e.name)}</strong><br><small>${esc(S.data.styles[n.style-1])} · ${esc(S.data.jobs[n.job-1])}</small></div><span class="number">${n.number}</span></div>
      <div class="rule-comparison"><span>激光：掷出 ≤ ${n.number}</span><span>情感：掷出 ≥ ${n.number}</span></div>
      <small>恰好 ${n.number}：成功并获得洞察<br>目标：${esc(n.goal?S.data.goals[n.goal-1]:bio?.goalText||'自定义目标')}</small>
      <p><span class="badge">${e.owner===S.view.accountId?'我的角色':esc(S.members.find(m=>m.accountId===e.owner)?.nickname||e.owner)}</span></p></div>`;
  }).join('')||'<p class="empty">故事从一个名字开始。先向主持人申请角色。</p>';
}
function shipHTML() {
  const ship=all('lf.ship')[0];
  if(!ship) return '<p class="muted">共同选择两项优势和一个问题，由主持人保存。</p>';
  const n=ship.numbers;
  return `<p><strong>${esc(ship.name)}</strong></p><p>${esc(S.data.strengths[n.first-1])} · ${esc(S.data.strengths[n.second-1])}</p><small>${esc(S.data.problems[n.problem-1])}</small>`;
}
function messagesHTML() {
  return S.messages.map(m=>{
    if(m.deleted) return '<div class="message muted">消息已撤回</div>';
    const member=S.members.find(v=>v.accountId===m.senderAccountId);
    let content;
    if(m.kind==='action') {
      const r=m.card.result||{};
      content=`<div class="card"><small>主机结果 · ${esc(m.card.ruleId)}</small>${r.kind==='insight'?`<p class="message-text">洞察问题：${esc(r.question)}</p>`:
        `${Array.isArray(r.dice)?`<div class="dice">${r.dice.map(d=>`<span class="die ${d===r.number?'insight':''}">${d}</span>`).join('')}</div>`:''}<strong>${esc(S.data.tiers[r.tier]||'规则结果')}</strong><p>${r.successes??0} 次成功 · ${r.insights??0} 个相等骰</p>`}</div>`;
    } else content=`<div class="message-text">${esc(m.text)}</div>`;
    const canAnswer=S.view.role==='kp' && m.kind==='action' && m.card.ruleId==='lf.question' && entity(m.card.result.participant)?.numbers.questionState===1;
    return `<article class="message" data-message="${esc(m.messageId)}"><div class="message-head"><strong>${esc(m.speakerName||member?.nickname||m.senderAccountId)}</strong><span>${member?.role==='kp'?'主持人 · ':''}${new Date(m.createdAt*1000).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'})}</span></div>
      ${m.replyTo?'<small>↳ 回复本频道较早消息</small>':''}${content}<div class="toolbar">${button('回复','reply',m.messageId,'secondary small')}
      ${m.senderAccountId===S.view.accountId&&m.kind==='text'?button('编辑','edit',m.messageId,'secondary small'):''}
      ${m.senderAccountId===S.view.accountId||S.view.role==='kp'?button('撤回','retract',m.messageId,'secondary small'):''}
      ${S.view.role==='kp'&&m.kind==='text'&&m.text.startsWith('角色申请：')?button('填入建卡表','approve-draft',m.messageId,'secondary small'):''}</div>
      ${canAnswer?`<form id="answer-${esc(m.messageId)}" data-form="answer" data-message="${esc(m.messageId)}" data-record="${esc(m.card.result.participant)}">${label('如实回答',`<textarea name="answer" maxlength="4000" required></textarea>`)}<button>回复并标记已回答</button></form>`:''}</article>`;
  }).join('')||'<p class="empty">还没有记录。向船员描述眼前的星空。</p>';
}
function actionsHTML() {
  return all('lf.action').sort((a,b)=>(b.numbers.order||0)-(a.numbers.order||0)).map(action=>{
    const records=related(id(action),'references').map(entity).filter(Boolean);
    const phase=action.numbers.phase, main=records.find(r=>r.numbers.role===1);
    return `<article class="action"><h3>${esc(action.name)}</h3><span class="badge">${main?.numbers.state===1?'检定已完成':phaseText[phase]||'未知状态'}</span>
      ${records.map(record=>{
        const n=record.numbers, mine=record.owner===S.view.accountId;
        const receipt=S.journal.receipts['roll:'+id(record)];
        return `<div class="chip"><small>${n.role===1?'主行动':'协助'} · ${esc(record.name)} · ${n.mode===0?'激光':'情感'}<br>基础 1 + 准备 ${n.prepared} + 专长 ${n.expert}${n.role===1?' + 协助 '+action.numbers.bonus:''}</small>
          ${n.state===1?`${diceHTML(n)}<strong>${esc(S.data.tiers[Math.min(n.successes,3)])}</strong> <small>${n.successes} 成功${n.insights?' · 特殊洞察':''}</small>`:'<p class="muted">尚未检定</p>'}
          ${mine&&n.state===0&&((n.role===2&&phase===1)||(n.role===1&&phase===2))?button(n.role===2?'进行协助检定':'进行主检定','roll',id(record),'primary'):''}
          ${mine&&receipt?button('分享到当前频道','share',receipt,'secondary small'):''}
          ${mine&&n.state===1&&n.insights>0&&n.questionState===0&&phase!==3?`<form id="question-${esc(id(record))}" data-form="question" data-record="${esc(id(record))}">${label('特殊洞察：向主持人提问',`<textarea name="question" maxlength="1000" placeholder="谁在幕后操纵这一切？" required></textarea>`)}<label class="inline-check"><input type="checkbox" name="private" checked>仅向主持人提问</label><button>提交洞察问题</button></form>`:''}
          ${n.questionState===1?`<p class="flow-status">洞察待回答${mine&&S.journal.receipts['question:'+id(record)]?` · ${button('重新分享问题','share',S.journal.receipts['question:'+id(record)],'secondary small')}`:''}</p>`:''}
          ${n.questionState===2?'<p class="save-status">洞察已回答，文字保留在问答频道</p>':''}</div>`;
      }).join('')}
      ${S.view.role==='kp'&&main?.numbers.state!==1?`<div class="toolbar">${phase===0?button('开放此草稿','open',id(action)):''}${phase===1?button('关闭协助窗口','close',id(action),'primary'):''}${phase!==3?button('取消行动','cancel',id(action),'secondary'):''}</div>`:''}</article>`;
  }).join('')||'<p class="empty">遇到风险时，由主持人建立一次检定。</p>';
}
function characterForm(kp) {
  return `<form id="character-form" data-form="character">${kp?label('归属玩家',select('owner',S.members.map(m=>[m.accountId,m.nickname||m.accountId]),'player1')):''}
    ${label('角色姓名','<input name="name" maxlength="200" required placeholder="例如：星河">')}
    <div class="split">${label('角色数值',select('number',[2,3,4,5].map(n=>[n,n]),3))}${label('风格',select('style',indexed(S.data.styles),1))}</div>
    ${label('职责',select('job',indexed(S.data.jobs),1))}${label('目标',select('goal',[[0,'自定义目标'],...indexed(S.data.goals)],1))}
    ${label('自定义目标／补充说明','<textarea name="goalText" maxlength="800" placeholder="选择自定义目标时填写"></textarea>')}
    <button>${kp?'确认创建角色':'发送角色申请'}</button></form>`;
}
function gmHTML() {
  const chars=all('lf.character');
  return `<section class="panel"><div class="eyebrow">Game master</div><h2>主持工作台</h2><details><summary>创建角色</summary>${characterForm(true)}</details>
    <details><summary>共同创建飞船</summary><form id="ship-form" data-form="ship"><div class="split">${label('第一项优势',select('first',indexed(S.data.strengths),1))}${label('第二项优势',select('second',indexed(S.data.strengths),2))}</div>${label('飞船问题',select('problem',indexed(S.data.problems),1))}<button>保存飞船</button></form></details>
    <details open><summary>建立风险检定</summary><form id="action-form" data-form="action">${label('行动意图','<input name="title" maxlength="200" placeholder="穿过敌舰的封锁线" required>')}${label('主行动角色',select('main',chars.map(c=>[id(c),c.name])))}<div class="split">${label('主行动方式',select('mode',[[0,'激光：理性与精准'],[1,'情感：直觉与热情']],0))}<div><label class="inline-check"><input type="checkbox" name="prepared">已充分准备</label><label class="inline-check"><input type="checkbox" name="expert">属于角色专长</label></div></div>
      <small>选取协助者。每个账号最多一位角色，主行动人不能协助自己。</small>${chars.map(c=>`<div class="slot"><label class="inline-check"><input type="checkbox" name="helpers" value="${esc(id(c))}">${esc(c.name)}</label>${label('协助方式',select('mode-'+id(c),[[0,'激光'],[1,'情感']],0))}<label class="inline-check"><input name="prepared-${esc(id(c))}" type="checkbox">已准备</label><label class="inline-check"><input name="expert-${esc(id(c))}" type="checkbox">有专长</label></div>`).join('')}
      <button ${chars.length?'':'disabled'}>确认裁定并开放协助</button></form></details>
    <details><summary>冒险生成器 · 主持人私密</summary><form id="adventure-form" data-form="adventure">${['threats','intents','objects','consequences'].map((key,i)=>label(['威胁','意图','对象','后果'][i],select(key,[[0,'掷 d6 随机生成'],...indexed(S.data[key])],0))).join('')}<button>生成并保存私密设定</button></form><div id="adventure-result">${S.adventure?`<p>${esc(Object.values(S.adventure).map(v=>v.text).join(' · '))}</p>`:'<small>私密设定不会自动发布到聊天。</small>'}</div></details>
    <details><summary>发布场景与叙事</summary><form id="scene-form" data-form="scene">${label('场景标题','<input name="title" maxlength="200" required>')}${label('玩家可知的描述','<textarea name="description" maxlength="3600" required></textarea>')}<button>向当前频道发布场景</button></form></details></section>`;
}
function preserve() {
  const forms={};
  document.querySelectorAll('form[id]').forEach(form=>{ forms[form.id]=Array.from(form.elements).filter(e=>e.name).map(e=>({name:e.name,value:e.value,checked:e.checked})); });
  return {forms,focus:document.activeElement?.id,position:document.activeElement?.selectionStart,
    chat:$('history')?{top:$('history').scrollTop,bottom:$('history').scrollHeight-$('history').scrollTop-$('history').clientHeight<30}:null,
    details:Array.from(document.querySelectorAll('details')).map(e=>e.open)};
}
function restore(saved) {
  for(const [formId,values] of Object.entries(saved.forms)) {
    const form=$(formId); if(!form) continue;
    for(const old of values) { const input=Array.from(form.elements).find(e=>e.name===old.name&&(e.type!=='checkbox'||e.value===old.value)); if(input) { input.value=old.value; if(input.type==='checkbox')input.checked=old.checked; } }
  }
  document.querySelectorAll('details').forEach((e,i)=>{if(saved.details[i]!==undefined)e.open=saved.details[i];});
  if(saved.focus&&$(saved.focus)) { $(saved.focus).focus({preventScroll:true}); try{$(saved.focus).setSelectionRange(saved.position,saved.position);}catch{} }
  if($('history')&&saved.chat) $('history').scrollTop=saved.chat.bottom?$('history').scrollHeight:saved.chat.top;
}
function draw() {
  const saved=preserve();
  if(!S.view) {
    document.title=(slot||'登录')+' · 激光与情感';
    $('app').innerHTML=`<main class="login"><section class="intro"><div class="eyebrow">RAPTOR / FIELD JOURNAL</div><h1>向未知处航行。<br>让故事发生。</h1><p>一张角色卡，几颗六面骰，<br>和愿意一起冒险的船员。</p><small>Lasers & Feelings · John Harper</small></section><section class="login-form"><div class="eyebrow">激光与情感</div><h2>进入跑团桌面</h2>${sessionLinks()}<form id="login-form" data-form="login">${label('账号',`<input id="login-name" name="loginName" autocomplete="username" value="${slot}" required>`)}${label('密码','<input id="login-password" name="password" type="password" autocomplete="current-password" required>')}<button>登录</button></form><p class="muted">首次启动由主机设置密码。默认账号：kp、player1、player2。同机多账号测试请分别打开下面的三个入口，可在同一浏览器的普通标签页登录。</p><p><a href="${base}original.pdf" target="_blank" rel="noopener">阅读完整一页规则书 ↗</a></p></section></main>`;
    restore(saved); return;
  }
  document.title=S.view.accountId+' · 激光与情感';
  const v=S.view, kp=v.role==='kp', installed=v.catalog.actions.some(a=>a.id==='lf.main');
  const latest=all('lf.scene').filter(e=>e.numbers.published===1).sort((a,b)=>b.numbers.order-a.numbers.order)[0];
  const p=S.journal?.plan;
  $('app').innerHTML=`<header><div><div class="mono">RAPTOR / SESSION JOURNAL</div><h1>激光与情感</h1></div><div class="header-meta"><span><i class="dot ${S.connected?'':'off'}"></i>${S.connected?'已连接':'连接中断'}</span><span>${esc(v.accountId)} · ${kp?'主持人':'玩家'}</span>${button('退出','logout','','secondary small')}</div></header>${sessionLinks()}
    <main class="layout"><aside class="stack"><section class="panel"><div class="eyebrow">The crew</div><h2>船员档案</h2>${cards()}</section><section class="panel"><div class="eyebrow">Our ship</div><h2>共同的飞船</h2>${shipHTML()}</section><section class="panel"><h2>随身装备</h2><p class="muted">${S.data.equipment.map(esc).join('<br>')}</p></section></aside>
    <div class="stack">${p?`<section class="panel pending"><h2>操作待处理</h2><p>${esc(p.label)} · 第 ${p.index+1}/${p.steps.length} 步</p><p class="long">${esc(p.error||'正在提交，请勿重复操作')}</p><div class="toolbar">${button(p.knownFailure?'重试失败步骤':'查询并恢复原提交','resume','','primary')}${(!p.envelope||p.knownFailure)?button('放弃剩余步骤','abandon'):''}</div><small>已提交步骤保留；恢复不会重复已完成的检定。</small></section>`:''}
    <section class="panel scene"><div class="eyebrow">Current scene</div><h2>${esc(latest?.name||'未知宇域')}</h2><p>Darcy 船长仍在医疗舱。眼前的选择，交给你们。</p><small>描述意图 → 主持裁定 → 协助与掷骰 → 推动故事</small></section>
    <section class="panel"><div class="eyebrow">Story & conversation</div><h2>故事记录</h2><div class="split">${label('当前频道',select('channel',Object.values(v.chatChannels).map(c=>[c.channelId,c.name]),S.channel))}${label('私聊成员',select('dm-person',S.members.filter(m=>m.accountId!==v.accountId).map(m=>[m.accountId,m.nickname||m.accountId])))}</div><div class="toolbar">${button('打开私聊','open-dm')}${button('标为已读','read')}</div><div id="history" class="scroll">${S.nextBefore?button('加载更早记录','older','','secondary small'):''}${messagesHTML()}</div>
    <form id="chat-form" data-form="chat">${S.reply?`<p class="muted">正在回复所选消息 ${button('取消回复','clear-reply','','secondary small')}</p>`:''}${label('以谁的身份发言',select('speaker',[["",'本人'],...all('lf.character').filter(c=>kp||c.owner===v.accountId).map(c=>[id(c),c.name])]))}${label('接下来，你做什么？','<textarea id="chat-text" name="text" maxlength="4000" required placeholder="描述行动、回应船员，或告诉主持人你的想法…"></textarea>')}<button ${v.chatChannels[S.channel]?.canPost?'':'disabled'}>发送</button></form></section>
    <section class="panel"><h2>规则速查</h2><p>激光用理性与精准，情感用直觉与热情。基础 1d6，准备和专长各 +1d；成功协助再 +1d。恰好等于角色数值时，既成功又获得洞察。</p><small>0 成功：局势恶化；1：勉强完成并付代价；2：良好完成；3 及以上：关键成功。每次检定一个洞察问题；每账号一位协助角色，无自助或递归协助。这些边界裁定随包记录。</small></section></div>
    <aside class="stack"><section class="panel"><div class="eyebrow">Actions & decisions</div><h2>行动与待办</h2>${installed?actionsHTML():`<p>本房间尚未激活《激光与情感》规则。</p>${kp?`${button('导入并激活本包','install','','primary')}<p class="muted">将替换本房间当前激活的规则组；请使用本包独立存档。</p>`:'<p class="muted">等待主持人导入配置包。</p>'}`}</section>
    ${kp?gmHTML():`<section class="panel"><h2>申请角色</h2><p class="muted">申请发送到当前频道，由主持人审核后创建。</p>${characterForm(false)}</section>`}</aside></main>
    <footer>Lasers & Feelings v1.4 © John Harper · CC BY 4.0 · 本项目中文整理与软件实现，未经原作者审定。<a href="${base}original.pdf" target="_blank" rel="noopener">完整官方规则书</a> · <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">许可</a><br>骰值由主机计算并保存；卡片分享与行动提交相互独立。</footer>`;
  document.querySelectorAll('input,textarea').forEach(e=>{ if(!e.id) e.id=(e.form?.id||'field')+'-'+e.name+'-'+(e.type==='checkbox'?e.value:''); });
  restore(saved);
  if(S.busy || p || !S.connected) document.querySelectorAll('button').forEach(b=>{if(!['resume','abandon'].includes(b.dataset.do)) b.disabled=true;});
  if(S.busy) document.querySelectorAll('[data-do="resume"],[data-do="abandon"]').forEach(b=>b.disabled=true);
}
async function history(older=false) {
  if(!S.view?.chatChannels[S.channel]) return;
  const channel=S.channel, account=S.view.accountId, revision=S.view.chatChannels[channel].revision;
  const page=await api('/chat/history',{channelId:channel,limit:50,...(older&&S.nextBefore?{before:S.nextBefore}:{})});
  if(S.channel!==channel || S.view?.accountId!==account || S.view.chatChannels[channel]?.revision!==revision) return;
  S.messages=older?[...page.items,...S.messages]:page.items;
  S.nextBefore=page.nextBefore; S.revision=revision;
}
async function refresh() {
  if(!S.auth||S.refreshing) return;
  S.refreshing=true;
  try {
    const v=await api('/view');
    if(S.view?.accountId!==v.accountId) {
      S.messages=[];S.revision=null;S.reply=null;
      try {S.journal=JSON.parse(localStorage.getItem(journalKey(v.accountId))||'null');}catch{S.journal=null;}
      S.journal ||= {receipts:{},plan:null};
    }
    S.view=v; S.connected=true;
    S.members=(await api('/chat/members')).items;
    const memberId=S.members.find(m=>m.accountId===v.accountId)?.memberId;
    S.adventure=Object.values(v.progress).find(p=>p.ownerKind==='member'&&p.ownerId===memberId&&p.eventKey==='lf.adventure')?.value;
    if(!v.chatChannels[S.channel]) {S.channel=Object.keys(v.chatChannels)[0];S.messages=[];S.revision=null;}
    if(S.channel && S.revision!==v.chatChannels[S.channel]?.revision) { S.messages=[]; await history(); }
    const nextKey=JSON.stringify([v,S.members,S.channel,S.messages]);
    if(nextKey!==renderKey) {renderKey=nextKey;draw();}
  } catch(error) {
    S.connected=false;S.messages=[];S.revision=null;renderKey='';
    if(error.status===401||error.status===403) {S.view=null;S.auth=false;S.csrf=null;S.members=[];S.journal=null;}
    draw();
  } finally {S.refreshing=false;}
}

function characterSteps(data,owner) {
  const name=data.get('name').trim(), goal=Number(data.get('goal')), goalText=data.get('goalText').trim();
  if(!name || (!goal&&!goalText)) throw new Error('请填写姓名和自定义目标');
  return [step('entity.create',{configurationId:'lf.character',name,owner,visibility:'public'}),
    invoke('lf.profile',{actor:ref(0),number:Number(data.get('number')),style:Number(data.get('style')),job:Number(data.get('job')),goal}),
    step('progress.set',{ownerKind:'entity',ownerId:ref(0),eventKey:'lf.bio',value:{goalText}})];
}
document.addEventListener('submit',async event=>{
  const form=event.target;if(!form.dataset.form)return;event.preventDefault();const data=new FormData(form);
  try {
    if(form.dataset.form==='login') {
      const auth=await api('/login',{loginName:data.get('loginName'),password:data.get('password')});
      S.csrf=auth.csrf;S.auth=true;renderKey='';form.reset();await refresh();return;
    }
    if(!S.connected||S.busy||S.journal.plan)throw new Error('请先完成当前操作并恢复连接');
    switch(form.dataset.form) {
      case 'chat': await plan('发送消息',[step('chat.message.send',{channelId:S.channel,text:data.get('text').trim(),...(S.reply?{replyTo:S.reply}:{}),...(data.get('speaker')?{speakerId:data.get('speaker')}:{})})]);if(!S.journal.plan){S.reply=null;$('chat-form')?.reset();draw();}break;
      case 'character': {
        if(S.view.role==='kp') await plan('创建角色',characterSteps(data,data.get('owner')));
        else await plan('发送角色申请',[step('chat.message.send',{channelId:S.channel,text:'角色申请：'+JSON.stringify(Object.fromEntries(data))})]);
        break;
      }
      case 'ship': {
        const ship=all('lf.ship')[0], steps=[];
        if(!ship)steps.push(step('entity.create',{configurationId:'lf.ship',owner:S.view.accountId,name:'Raptor',visibility:'public'}));
        steps.push(invoke('lf.ship',{actor:ship?id(ship):ref(0),first:Number(data.get('first')),second:Number(data.get('second')),problem:Number(data.get('problem'))}));
        await plan('保存飞船',steps);break;
      }
      case 'action': {
        const main=entity(data.get('main')), chosen=[main,...data.getAll('helpers').map(entity)];
        if(!main||new Set(chosen.map(c=>c.owner)).size!==chosen.length)throw new Error('主行动与协助必须来自不同账号');
        if(chosen.length>30)throw new Error('一次最多 30 位参与者，请拆分行动');
        const steps=[step('entity.create',{configurationId:'lf.action',owner:S.view.accountId,name:data.get('title').trim(),visibility:'public',numbers:{order:Math.max(0,...all('lf.action').map(a=>a.numbers.order||0))+1}})];
        for(let i=0;i<chosen.length;i++) {
          const c=chosen[i], n=steps.length, cid=id(c), number=c.numbers.number;
          steps.push(step('entity.create',{configurationId:'lf.participant',name:c.name,owner:c.owner,visibility:'public',numbers:{role:i===0?1:2,number,
            mode:Number(data.get(i===0?'mode':'mode-'+cid)),prepared:data.has(i===0?'prepared':'prepared-'+cid)?1:0,expert:data.has(i===0?'expert':'expert-'+cid)?1:0}}));
          for(const [sourceId,targetId,relationType] of [[ref(n),ref(0),'references'],[ref(n),cid,'source'],[ref(0),ref(n),'references']])steps.push(step('relation.set',{sourceId,targetId,relationType}));
        }
        steps.push(invoke('lf.open',{actor:ref(0)}));await plan('建立行动',steps);break;
      }
      case 'question': {
        const record=form.dataset.record, text=data.get('question').trim();if(!text)throw new Error('请填写洞察问题');
        const gm=S.members.find(m=>m.role==='kp'&&m.accountId!==S.view.accountId), steps=[];
        if(data.has('private')&&gm)steps.push(step('chat.direct.open',{accountId:gm.accountId}));
        const n=steps.length;steps.push(invoke('lf.question',{actor:record,question:text},'question:'+record));
        steps.push(step('chat.message.share',{channelId:n===1?ref(0,'result.channelId'):S.channel,commandId:ref(n,'commandId')}));
        const shared=await plan('提交并分享洞察问题',steps);if(shared?.channelId){S.channel=shared.channelId;S.revision=null;S.reply=null;await refresh();}break;
      }
      case 'answer': await plan('回答洞察',[step('chat.message.send',{channelId:S.channel,text:data.get('answer').trim(),replyTo:form.dataset.message}),invoke('lf.answer',{actor:form.dataset.record})]);break;
      case 'adventure': await plan('生成私密冒险',[invoke('lf.adventure',{threat:Number(data.get('threats')),intent:Number(data.get('intents')),object:Number(data.get('objects')),consequence:Number(data.get('consequences'))}),step('progress.set',{ownerKind:'member',ownerId:S.members.find(m=>m.accountId===S.view.accountId).memberId,eventKey:'lf.adventure',value:ref(0)})]);break;
      case 'scene': {
        if(S.view.chatChannels[S.channel]?.kind!=='room')throw new Error('请切换到公共频道后发布场景');
        await plan('发布场景',[step('entity.create',{configurationId:'lf.scene',owner:S.view.accountId,name:data.get('title').trim(),visibility:'public',numbers:{order:Math.max(0,...all('lf.scene').map(e=>e.numbers.order))+1,published:0}}),
          step('chat.message.send',{channelId:S.channel,text:'【场景】'+data.get('title').trim()+'\n'+data.get('description').trim()}),step('entity.update',{id:ref(0),numbers:{published:1}})]);break;
      }
    }
  } catch(error) {notice(error.message);}
});
document.addEventListener('click',async event=>{
  const b=event.target.closest('[data-do]');if(!b)return;const value=b.dataset.value;
  try {
    switch(b.dataset.do) {
      case 'resume': if(S.journal.plan?.knownFailure){S.journal.plan.envelope=null;S.journal.plan.knownFailure=false;saveJournal();}await executePlan();break;
      case 'abandon': if(confirm('放弃尚未执行的步骤？已经提交的数据与骰值仍会保留。')){S.journal.plan=null;saveJournal();draw();}break;
      case 'logout': await api('/logout',{});localStorage.removeItem(journalKey(S.view.accountId));S.auth=false;S.view=null;S.csrf=null;S.messages=[];S.journal=null;renderKey='';draw();break;
      case 'install': if(confirm('在本独立房间导入并激活《激光与情感》？当前激活的规则组会被替换。'))await plan('导入配置包',[step('rule.stage',{sources:S.bundle.sources,data:S.bundle.data}),step('rule.activate',{revision:ref(0)}),...S.bundle.configurations.map(c=>step('configuration.put',c))]);break;
      case 'roll': {const e=entity(value);await plan('掷骰',[invoke(e.numbers.role===1?'lf.main':'lf.help',{actor:value},'roll:'+value)]);break;}
      case 'share': await plan('分享主机结果',[step('chat.message.share',{channelId:S.channel,commandId:value})]);break;
      case 'close': if(confirm('关闭协助窗口？尚未检定的协助者将不再计入。'))await plan('关闭协助窗口',[invoke('lf.close',{actor:value})]);break;
      case 'cancel': if(confirm('取消本次行动？已发生的协助骰值仍会保留。'))await plan('取消行动',[invoke('lf.cancel',{actor:value})]);break;
      case 'open': await plan('开放行动',[invoke('lf.open',{actor:value})]);break;
      case 'reply': S.reply=value;draw();$('chat-text').focus();break;
      case 'clear-reply': S.reply=null;draw();break;
      case 'older': await history(true);draw();break;
      case 'open-dm': {const target=$('dm-person').value;const result=await plan('打开私聊',[step('chat.direct.open',{accountId:target})]);if(result){S.channel=result.channelId;S.revision=null;S.reply=null;await refresh();}break;}
      case 'read': await plan('更新已读位置',[step('chat.read',{channelId:S.channel,sequence:S.view.chatChannels[S.channel].lastSequence})]);break;
      case 'edit': {const m=S.messages.find(m=>m.messageId===value), text=prompt('编辑消息',m.text);if(text!==null)await plan('编辑消息',[step('chat.message.edit',{channelId:S.channel,messageId:value,revision:m.revision,text})]);break;}
      case 'retract': {const m=S.messages.find(m=>m.messageId===value);if(confirm('撤回此消息？'))await plan('撤回消息',[step('chat.message.retract',{channelId:S.channel,messageId:value,revision:m.revision})]);break;}
      case 'approve-draft': {const m=S.messages.find(m=>m.messageId===value), draft=JSON.parse(m.text.slice('角色申请：'.length)), form=$('character-form');for(const [key,v]of Object.entries({...draft,owner:m.senderAccountId})){const e=form.elements.namedItem(key);if(e)e.value=v;}form.closest('details').open=true;form.scrollIntoView({behavior:'smooth'});break;}
    }
  } catch(error) {notice(error.message);}
});
document.addEventListener('change',async event=>{if(event.target.id==='channel'){S.channel=event.target.value;S.reply=null;S.messages=[];S.revision=null;await refresh();}});
try {
  [S.data,S.bundle]=await Promise.all([fetch(base+'package/data.json').then(r=>r.json()),fetch(base+'package/bundle.json').then(r=>r.json())]);
  const me=await api('/me'); S.csrf=me.csrf;S.auth=true;await refresh();
} catch { draw(); }
setInterval(()=>refresh(),1200);
