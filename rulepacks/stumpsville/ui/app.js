const app = document.querySelector('#app');
const dialog = document.querySelector('#dialog');
const base = new URL('.', location.href);
let state = null;
let csrf = '';
let setup = null;
let dialogSubmit = null;
let selectedLocation = 1;
let currentChannel = 'general';
let history = [];
let nextBefore = null;
let creation = {step:0,preset:'mul',name:'木栗',swap:''};
let lastStage = '';
let dirtyForm = null;
let acceptedHash = location.hash;
let busy = false;
let lastFocus = null;
let connection = '连接中';
let desktop = null, desktopAccount = '', consoleTab = 'control', selectedRequest = '', localAction = null, renderDeferred = false;
let executorBusy = false, sceneInstallTried = false;
const playerNav = [['play/scene','场景桌面']];
const gmNav = [['gm/console','控制台'],['gm/locations','地点'],['gm/library','资料'],['gm/session','场次']];
const icons = {weapon:'⚔',item:'◇',armor:'♧',condition:'✧',spell:'▤'};
const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const number = value => Number(value);
const route = () => location.hash.replace(/^#\/?/,'') || 'lobby';
const button = (label, action, data = {}, style = '') => `<button type="button" class="${style}" data-action="${action}" data-args="${escape(JSON.stringify(data))}">${label}</button>`;
const link = (label, path) => `<a href="#/${path}">${label}</a>`;
const field = (label, name, value = '', type = 'text') => `<label>${label}<input name="${name}" type="${type}" value="${escape(value)}" ${type==='password'?'autocomplete="current-password"':''}></label>`;
const area = (label,name,value='') => `<label>${label}<textarea name="${name}">${escape(value)}</textarea></label>`;
const select = (label,name,options,value) => `<label>${label}<select name="${name}">${options.map(([key,text])=>`<option value="${escape(key)}" ${String(key)===String(value)?'selected':''}>${escape(text)}</option>`).join('')}</select></label>`;
const heading = (id,title,actions='') => `<div class="page-head"><div><div class="eyebrow">${id} · STUMPSVILLE</div><h1>${title}</h1></div><div class="actions">${actions}</div></div>`;
const panel = (title,body,kind='') => `<section class="panel ${kind}"><h2>${title}</h2>${body}</section>`;
const empty = text => `<div class="empty">${escape(text)}</div>`;
const actorOptions = () => (state.characters || [state.character].filter(Boolean)).map(x=>[x.instanceId,x.name]);
const pendingKey = () => 'stumpsville.pending.' + base.pathname + '.' + state.accountId;
const independentLogin = () => '<a class="account-link" href="/" target="_blank" rel="noopener">新开独立登录页</a>';
const rulingMode = () => select('结算方式','ruling',[['auto',state.automation?.enabled?'自动结算':'请求 KP（自动裁决已关闭）'],['manual','主动请求 KP 裁决']],'auto');
function submitAction(kind,input,data){return data?.get('ruling')==='manual'?perform('request',{kind,input,manual:true,text:'请 KP 裁决：'+(kind==='check'?'属性检定':'物品操作')}):perform(kind,input);}
function myRulings(){
  return panel('我的裁决申请',state.requests.filter(x=>x.account===state.accountId&&x.status!=='automatic').slice(-20).reverse().map(x=>`<article class="receipt"><strong>${escape(x.text||x.kind)}</strong><p>${{pending:'等待 KP 裁决',approved:'KP 已批准',rejected:'KP 已拒绝'}[x.status]||escape(x.status)} · ${escape(x.reason||'')}</p>${x.result?'<p>'+escape(resultText(x.result))+'</p>':''}</article>`).join('')||empty('没有待处理申请'));
}

async function api(path, body) {
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (csrf) headers['X-CSRF-Token'] = csrf;
  const response = await fetch(new URL(path,base), {method:body===undefined?'GET':'POST',headers,body:body===undefined?undefined:JSON.stringify(body),credentials:'same-origin'});
  const data = await response.json();
  if (!response.ok || (data.status === 'rejected' && data.commandId)) {
    const messages={RULE_FAILED:'行动未完成，请检查槽位、资源、开场与主持条件',VERSION_CONFLICT:'数据已改变，请刷新后重新确认',NOT_VISIBLE:'当前账号无权查看此内容',STALE_CATALOG:'规则版本已改变，请刷新后重新选择行动',RATE_LIMITED:'操作过快，请稍后恢复原行动',ROOM_PAUSED:'房间已暂停',CSRF_REQUIRED:'会话校验失败，请重新登录'};
    const error = new Error(messages[data.code] || data.code || '请求失败');
    error.status = response.status;
    throw error;
  }
  return data;
}

function toast(message) {
  const element = document.querySelector('#toast');
  element.textContent = message;
  element.style.display = 'block';
  clearTimeout(toast.timer);
  toast.timer = setTimeout(()=>element.style.display='none',5000);
}

function resultText(result) {
  if (!result || typeof result !== 'object') return typeof result==='string'&&/^[a-f0-9-]{24,}$/.test(result)?'操作完成':String(result ?? '操作完成');
  if (result.sceneAction) return [result.message,...(result.narrative||[])].join('\n');
  if (result.message) return result.message;
  if ('channelId' in result) return '频道操作已完成';
  if ('passed' in result) return `${result.attribute.toUpperCase()} 检定 · ${result.rolled} / ${result.target} · ${result.passed?'成功':'失败'}`;
  if ('damage' in result) return `伤害 ${result.damage} · 剩余 HP ${result.hp}${result.critical?' · 重伤':''}`;
  if ('round' in result) return `第 ${result.round} 回合${result.encounterDue?' · 请检查遭遇':''}`;
  if ('count' in result) return `生成数量 ${result.count}`;
  if ('entry' in result) return `${result.rolled} · ${result.entry}`;
  if ('rolled' in result) return `骰点 ${result.rolled}`;
  if ('total' in result) return `骰点合计 ${result.total}`;
  if ('ready' in result) return result.ready?'已准备':'已取消准备';
  if ('operation' in result && 'slot' in result) return `${{move:'移动物品',use:'使用物品',light:'点亮光源',extinguish:'熄灭光源'}[result.operation]||'物品操作'} · 槽位 ${result.slot}${result.operation==='move'?' → '+result.target:result.operation==='use'?' · 剩余用量 '+result.uses:''}${result.overloaded?' · 当前超载':''}`;
  if ('location' in result) return '已到达 '+(state?.locations.find(p=>p.index===result.location)?.name||'地点 '+result.location);
  if ('uses' in result) return `操作完成 · 剩余用量 ${result.uses}`;
  return Object.entries(result).map(([key,value])=>`${key} · ${typeof value==='object'?JSON.stringify(value):value}`).join('\n');
}

async function refresh(render = true) {
  state = await api('package/state');
  connection = '已同步';
  if (render) renderPage();
}

async function perform(operation,args,existing) {
  if (busy) return;
  if(!existing && localStorage.getItem(pendingKey())) throw new Error('请先恢复待确认的原行动');
  busy = true;
  const body = existing || {id:crypto.randomUUID(),operation,args};
  const key = pendingKey();
  localStorage.setItem(key,JSON.stringify(body));
  localAction = {status:'submitting',text:'正在提交行动，等待服务器确认…'};
  updateActivity();
  try {
    const result = await api('package/action',body);
    localStorage.removeItem(key);
    dirtyForm = null;
    closeDialog();
    localAction = null;
    await refresh();
    toast(result.status==='processing'?'预设行动已提交，结算进度见“最近行动”。':resultText(result));
    return result;
  } catch(error) {
    localAction = {status:'error',text:error.message + (error.status>=400&&error.status<500?'；行动未完成。':'；结果尚未确认，请恢复原行动。')};
    updateActivity();
    toast(error.message);
    if (error.status === 400 || error.status === 403 || error.status === 409) localStorage.removeItem(key);
    throw error;
  } finally {
    busy = false;
  }
}

function openDialog(title,body,onSubmit,label='确认',id='S14') {
  lastFocus = document.activeElement;
  dialogSubmit = onSubmit;
  dialog.innerHTML = `<div class="dialog-head"><h2 id="dialog-title"><span class="eyebrow">${id}</span> ${title}</h2>${button('关闭','close',{},'quiet')}</div><form id="dialog-form"><div class="dialog-body">${body}<div class="dialog-actions">${button('取消','close')}${onSubmit?`<button class="primary" type="submit">${label}</button>`:''}</div></div></form>`;
  if (!dialog.open) dialog.showModal();
}

function closeDialog() {
  dialog.close();
  dialogSubmit = null;
  if (lastFocus?.isConnected) lastFocus.focus();
}

function statCards(character) {
  const n = character.numbers;
  return `<div class="statgrid">${['str','dex','wil'].map(key=>`<div class="stat">${button(key.toUpperCase(),'check',{attribute:key},'quiet')}<strong>${n[key]} / ${n[key+'Max']}</strong></div>`).join('')}</div><div class="row"><strong>HP ${n.hp} / ${n.maxHp}</strong><span>护甲 ${n.armor}</span><span>${n.pips}p</span></div>`;
}

function mapView(locations,current) {
  const positions={1:[90,280],2:[90,180],3:[270,180],4:[120,65],5:[290,65],6:[460,65],7:[460,180],8:[640,180],9:[640,280],10:[460,280]};
  const edges=locations.flatMap(x=>x.exits.filter(y=>y>x.index&&locations.some(l=>l.index===y)).map(y=>{
    const [x1,y1]=positions[x.index],[x2,y2]=positions[y];
    const door=state.doors?.[[x.index,y].sort((a,b)=>a-b).join('-')]||x.doors?.[String(y)]||'open';
    if(x.index===3&&y===8)return `<path d="M${x1} ${y1} C${x1} 255 ${x2} 255 ${x2} ${y2}" class="${door==='open'?'':'closed'}"/>`;
    return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="${door==='open'?'':'closed'}"/>`;
  })).join('');
  const nodes=locations.map(x=>{const [left,top]=positions[x.index];return `<g role="button" tabindex="0" aria-label="${escape(x.name)}" data-action="location" data-args="${escape(JSON.stringify({index:x.index}))}" class="${x.index===current?'current':''}" transform="translate(${left},${top})"><rect x="-64" y="-24" width="128" height="48" rx="9"/><text text-anchor="middle" y="5">${String(x.index).padStart(2,'0')} ${escape(x.name)}</text>${x.index===current?'<circle cx="57" cy="-20" r="6"/>':''}</g>`;}).join('');
  return `<div class="node-map"><svg viewBox="10 20 710 310" aria-label="已知地点与通路">${edges}${nodes}</svg></div><div class="map compact-map">${locations.map(x=>button(`${String(x.index).padStart(2,'0')} ${escape(x.name)}`,'location',{index:x.index},x.index===current?'current':'')).join('')}</div><p class="map-links">实线：通路开启　虚线：关闭或锁住　圆点：当前位置或选择</p>`;
}

function renderEntry() {
  app.innerHTML = `<section class="entry"><div class="entry-card"><div class="eyebrow">一场属于小鼠的冒险</div><h1>树桩镇</h1><div class="subtitle">STUMPSVILLE</div><p>带上火把、针剑与一点勇气。<br>树桩深处，故事正在等待。</p><div class="notice">${setup?.canSetup?'首次准备 · 创建独立游玩存档':'服务可连接 · 请登录你的账号'}</div><form id="entry-form">${setup?.canSetup?'':field('账号','loginName','kp')}${field(setup?.canSetup?'设置初始密码（8–128位）':'密码','password','','password')}${setup?.canSetup?'<p class="muted">将建立 kp、player1、player2 三个测试账号，共用本次初始密码。</p>':''}<button class="primary" type="submit">${setup?.canSetup?'准备树桩镇':'进入冒险'}</button><div id="entry-error" role="alert"></div></form><p>${independentLogin()}</p><p class="muted">每个独立登录页可使用不同账号；复制相同页面地址则共享该入口的会话。</p><p class="muted">Mausritter · OnlineCOC 配置包</p></div></section>`;
}

function renderPage() {
  if (!state) return renderEntry();
  restoreDesktop();
  let path = route();
  const legacyPanels = {'play/character':'inventory','play/journal':'clues','play/records':'records'};
  if(legacyPanels[path]){
    if(state.role==='kp'){consoleTab='messages';path='gm/console';}
    else {desktop[legacyPanels[path]]={open:true,collapsed:false};desktop.front=legacyPanels[path];if(path==='play/character')desktop.status={open:true,collapsed:false};saveDesktop();path='play/scene';}
    historyReplace('#/'+path);acceptedHash=location.hash;
  }
  if(['gm/overview','gm/encounters'].includes(path)){consoleTab=path==='gm/encounters'?'rulings':'control';path='gm/console';historyReplace('#/'+path);acceptedHash=location.hash;}
  if(/^gm\/locations\/\d+$/.test(path)){selectedLocation=Number(path.split('/')[2]);path='gm/locations';}
  const gm = state.role === 'kp';
  const navigation = gm ? gmNav : playerNav;
  document.body.classList.toggle('scene-workspace',!gm&&path==='play/scene');
  const pending = localStorage.getItem(pendingKey());
  app.innerHTML = `<header class="topbar"><div class="brand"><span class="brand-symbol">♧</span><span>树桩镇<small>STUMPSVILLE</small></span></div><div class="toptools"><span class="identity">${gm?'主持 KP':'玩家'} · ${escape(state.accountId)}</span><span class="tag" id="connection">${connection}</span>${button('规则','rules',{},'quiet')}${button('偏好','preferences',{},'quiet')}${button('退出','logout',{},'quiet')}${independentLogin()}</div></header>${pending?`<div class="pendingbar">有一项操作结果待确认 ${button('恢复原行动','recover',{},'small')}</div>`:''}<div class="shell"><nav class="sidebar" aria-label="主导航">${navigation.map(([url,label])=>`<a href="#/${url}" class="${path.startsWith(url)?'active':''}">${label}</a>`).join('')}<div class="divider"></div><a class="secondary" href="#/lobby">入场大厅</a><a class="secondary" href="#/recap">场次回顾</a><img class="mouse-mark" src="art/mouse.png" alt=""></nav><main id="main"></main></div>`;
  const main = document.querySelector('#main');
  if (!state.initialized) {
    main.innerHTML = heading('准备','安装树桩镇') + panel('房间尚未准备',gm?button('安装规则与十地点','initialize',{},'primary'):empty('等待主持安装配置包'));
    return;
  }
  if (path.startsWith('gm/') && !gm) {
    main.innerHTML = heading('S16','无权访问') + empty('此页面需要主持权限');
    return;
  }
  const routes = {
    'lobby':lobbyPage,'character/new':creationPage,'ready':readyPage,
    'play/scene':workspacePage,'gm/console':consolePage,'gm/locations':locationsPage,
    'gm/library':libraryPage,'gm/session':sessionPage,'recap':recapPage
  };
  main.innerHTML = (routes[path] || (()=>heading('S16','页面不存在')+link('返回大厅','lobby')))();
  if(document.querySelector('#chat-history')) loadChat().catch(error=>toast(error.message));
  updateActivity();
}

function lobbyPage() {
  const character = state.character;
  return heading('P02','入场大厅',state.role==='kp'?button('进入主持台','navigate',{path:'gm/console'},'primary'):'')+
    `<div class="grid2">${panel('你的冒险小鼠',character?`<img class="portrait" src="art/mouse.png" alt="小鼠冒险者"><h2>${escape(character.name)}</h2>${statCards(character)}${button('核对装备并准备','navigate',{path:'ready'},'primary')}`:empty('还没有分配角色'))}${panel('开始之前',`<p>首轮探索树桩镇十个地点，由主持推进场景、处理机关与叙事裁定。</p>${state.draft?`<div class="notice">草稿 · ${escape(state.draft.name)} · ${escape(state.draft.status)}<br>${escape(state.draft.reason||'')}</div>`:''}${!character?button('创建或认领小鼠','navigate',{path:'character/new'},'primary'):''}<p class="muted">角色审核完成后，核对物品栏并标记准备。</p>`)}</div>`;
}

function creationPage() {
  const preset=creation.preset==='random'?state.generatedCharacter:state.presets.find(x=>x.id===creation.preset);
  const steps=['身份','属性','装备','确认'];
  let body='';
  if(creation.step===0) body=`<div class="grid2">${state.presets.map(p=>`<article class="preset"><img src="art/mouse.png" alt=""><h3>${escape(p.name)}</h3><p>${escape(p.description)}</p>${button('采用预设','choose-preset',{preset:p.id,name:p.name},'primary')}</article>`).join('')}</div><p>预设为自制角色。随机建角：三项属性取3d6最高两骰，HP与钱币各d6。</p>${button('生成随机角色','create-roll',{},'primary')}`;
  if(creation.step===1) body=`<form id="creation-form">${field('小鼠姓名','name',creation.name)}<p>STR ${preset?.str} · DEX ${preset?.dex} · WIL ${preset?.wil} · HP ${preset?.hp} · ${preset?.pips}p</p>${creation.preset==='random'?select('可交换任意两项属性一次','swap',[['','不交换'],['str-dex','STR ↔ DEX'],['str-wil','STR ↔ WIL'],['dex-wil','DEX ↔ WIL']],creation.swap):''}<button class="primary">下一步：装备</button></form>`;
  if(creation.step===2) body=`<p>起始预设包含：针剑、火把、口粮、绳索。</p><div class="notice">随机角色请由主持按 HP 与钱币交叉查背景表，核定两件背景物品及低属性补偿。这里的装备是待审核草稿。</div>${button('下一步：确认','create-next',{},'primary')}`;
  if(creation.step===3) body=`<h3>${escape(creation.name)}</h3><p>来源 · ${creation.preset==='random'?'随机建角':'自制预设'}；属性交换 · ${escape(creation.swap||'无')}</p><p>提交后等待主持核定数值、背景装备与角色归属。</p>${button('提交审核','create-submit',{},'primary')}`;
  return heading('P03','创建小鼠')+panel(steps.map((x,i)=>`${i+1}. ${x}`).join(' → '),body+`<div class="divider"></div>${creation.step?button('上一步','create-back'):''}`);
}

function readyPage() {
  const c=state.character;
  if (!c) return heading('P04','等待开场')+empty('请先提交角色并等待主持审核');
  const started=state.session?.numbers.phase===1;
  return heading('P04','等待开场')+panel(escape(c.name),`${statCards(c)}<p>物品栏与角色已完成审核，请核对后准备。</p><div class="actions">${button(c.numbers.ready?'取消准备':'我已准备','ready',{ready:!c.numbers.ready},'primary')}${button('查看背包','navigate',{path:'play/character'})}${started&&c.numbers.ready?button('进入场景','navigate',{path:'play/scene'},'primary'):''}</div><p class="muted">${started?'主持已开场':'主持尚未开场'}</p>`);
}

function scenePage() {
  const c=state.character;
  if (!c) return heading('P05','场景探索')+empty('请先在大厅完成角色审核');
  if(!c.numbers.ready||state.session?.numbers.phase!==1)return heading('P05','场景探索')+panel('等待开场',link('核对角色并准备','ready'));
  const place=state.locations.find(x=>x.index===c.numbers.location);
  if (!place) return heading('P05','场景探索')+empty('当前地点尚未公开，请联系主持');
  return heading('P05',`${String(place.index).padStart(2,'0')} ${escape(place.name)}`,`<span class="tag">第 ${state.session?.numbers.round||0} 回合</span>`)+`<div class="layout-aside"><div>${place.index===3?'<img class="scene-art" src="art/courtyard.png" alt="树桩庭院的池塘与梯子">':`<div class="scene-placeholder"><div><strong>${String(place.index).padStart(2,'0')}</strong><h2>${escape(place.name)}</h2></div></div>`}<p>${escape(place.description)}</p>${panel('已经发现',mapView(state.locations,place.index))}</div><aside>${panel('你想做什么？',`<p class="muted">${state.automation.ready?(state.automation.enabled?'自动裁决已开启':'自动裁决已关闭'):'等待 KP 升级自动裁决规则'}</p><div class="stack">${sceneButtons(place)}${place.exits.map(index=>button('前往 '+escape(state.locations.find(x=>x.index===index)?.name||''),'travel',{destination:index})).join('')}${button('自由行动','request',{kind:'free'})}${button('请求 KP 裁决','review')}${button('属性检定','check',{},'primary')}</div>`)}${sceneStatusPanel()}${panel('随身资源',`<p>HP ${c.numbers.hp}/${c.numbers.maxHp} · 护甲 ${c.numbers.armor}</p><p>当前光源 ${c.numbers.litSlot?'已点亮':'未点亮'}</p>${button('打开背包','navigate',{path:'play/character'})}`)}</aside></div>`;
}

function inventoryCards(c) {
  const n=c.numbers;
  const covered={};
  for(let slot=1;slot<=10;slot++){
    const def=state.items[String(n['item'+slot])];
    if(!def) continue;
    let cells=[slot];
      if(def.slots===2) cells=[slot,slot+1];
    if(def.slots===4) cells=[slot,slot+1,slot+3,slot+4];
    cells.slice(1).forEach(index=>covered[index]=slot);
  }
  let coins=Math.ceil(Math.max(0,n.pips-250)/250);
  for(let slot=10;slot>=1;slot--){if(coins&&!covered[slot]&&!n['item'+slot]){covered[slot]=-1;coins--;}}
  const card=slot=>{
    const index=n['item'+slot],def=state.items[String(index)];
    if(covered[slot]) return `<div class="slot occupied"><span class="number">${slot}</span><span>${covered[slot]===-1?'钱币袋':'↖ 占用'}</span></div>`;
    if(!def) return `<div class="slot"><span class="number">${slot}</span><span class="muted">空</span></div>`;
    return `<button class="slot occupied" data-action="item" data-args="${escape(JSON.stringify({slot}))}"><span class="number">${slot}</span><span class="item-icon">${icons[def.kind]||'◇'}</span><strong>${escape(def.name)}</strong><span class="uses">${def.uses?'■'.repeat(n['uses'+slot])+'□'.repeat(Math.max(0,def.uses-n['uses'+slot])):''}</span></button>`;
  };
  return `<div class="inventory"><section class="slotgroup"><h3>双手 · 2格</h3><div class="slots vertical">${[1,2].map(card).join('')}</div></section><section class="slotgroup"><h3>身体 · 2格</h3><div class="slots vertical">${[3,4].map(card).join('')}</div></section><section class="slotgroup"><h3>背包 · 6格</h3><div class="slots">${[5,6,7,8,9,10].map(card).join('')}</div></section></div><h3 style="margin-top:24px">超载区</h3><div class="overflow">${Array.from({length:10},(_,i)=>i+11).filter(i=>n['item'+i]).map(card).join('')||'<p class="muted">当前没有超载物品</p>'}</div>`;
}

async function loadChat(older=false) {
  if(!state?.channels[currentChannel]) currentChannel=Object.keys(state?.channels||{})[0]||'general';
  const account=state.accountId;
  const channel=currentChannel;
  const result=await api('api/v1/chat/history',{channelId:channel,limit:50,...(older&&nextBefore?{before:nextBefore}:{})});
  if(!state || state.accountId!==account || !document.querySelector('#chat-history')) return;
  if(channel!==currentChannel)return;
  history=older?[...result.items,...history]:result.items;
  nextBefore=result.nextBefore;
  const target=document.querySelector('#chat-history');
  if(target) target.innerHTML=history.map(x=>`<div class="chatmessage"><small>${escape(x.speakerName||x.senderAccountId)}</small><p>${escape(x.text||(x.card?resultText(x.card.result):'消息已撤回'))}</p>${x.senderAccountId===account&&x.text?button('编辑','chat-edit',{messageId:x.messageId,revision:x.revision,text:x.text},'small quiet')+button('撤回','retract',{messageId:x.messageId,revision:x.revision},'small quiet'):''}</div>`).join('')||empty('这里还没有消息');
}

function charactersTable() {
  return `<table><thead><tr><th>角色</th><th>资源</th><th>状态</th><th>管理</th></tr></thead><tbody>${state.characters.map(c=>`<tr><td><strong>${escape(c.name)}</strong><br><small>${escape(c.owner)}</small></td><td>HP ${c.numbers.hp}/${c.numbers.maxHp}<br>STR ${c.numbers.str} · DEX ${c.numbers.dex} · WIL ${c.numbers.wil}</td><td>${c.numbers.ready?'已准备':'未准备'}<br>地点 ${c.numbers.location}</td><td>${button('数值','actor-edit',{id:c.instanceId},'small')}${button('授予物品','grant',{actor:c.instanceId},'small')}${button('恢复','rest',{actor:c.instanceId},'small')}</td></tr>`).join('')}</tbody></table>`;
}

function locationsPage() {
  const place=state.allLocations[String(selectedLocation)]||Object.values(state.allLocations)[0];
  const doors=place.exits.map(x=>{const edge=[place.index,x].sort((a,b)=>a-b).join('-');return button(`通往 ${x} · ${{open:'开启',closed:'关闭',locked:'锁住'}[state.doors[edge]]}`,'door',{edge});}).join('');
  const stock=place.stock.map(x=>`<div class="row"><span>${escape(state.items[String(x.item)]?.name)} × ${x.count}</span>${x.count?button('领取','take-stock',{index:place.index,item:x.item},'small'):''}</div>`).join('');
  return heading('P10','地点与揭示',button('查看公开预览','preview',{index:place.index}))+`<div class="layout-aside"><div>${panel(`${place.index} ${escape(place.name)}`,`<form id="location-form"><input type="hidden" name="index" value="${place.index}"><input type="hidden" name="revision" value="${place.revision||0}"><div class="grid2"><div>${area('公开描述','description',place.description)}</div><div>${area('KP 主持真相','truth',place.truth)}</div></div><div class="actions"><button class="primary">保存草稿</button>${button('发布预览','publish',{index:place.index})}</div></form><h3>通路与门</h3><div class="actions">${doors}</div><h3>库存</h3>${stock||'<p class="muted">无固定物品</p>'}${place.index===4?button('首次生成铜锅盘','generate',{kind:'pots'}):''}${place.index===7?button('首次生成鼠帮人数','generate',{kind:'rats'}):''}<h3>生物</h3>${state.npcs.filter(x=>x.numbers.location===place.index).map(x=>`<p>${escape(x.name)} · HP ${x.numbers.hp}</p>`).join('')||'<p class="muted">未登记生物</p>'}`,'private')}</div><aside>${panel('地点索引',`<div class="stack">${Object.values(state.allLocations).map(x=>button(`${String(x.index).padStart(2,'0')} ${escape(x.name)}`,'select-location',{index:x.index},x.index===place.index?'primary':'')).join('')}</div>`)}</aside></div>`;
}

function libraryPage() {
  return heading('P12','资料与配置',button('导出配置包','export'))+panel('资料状态',`<p>${escape(state.sourceStatus)}</p><div class="actions">${button('导入并检查','stage',{},'primary')}${button('安装包内规则','install')}${button('查看规则速查','rules')}${button('编辑随机表','tables')}</div>`)+panel('配置修订',state.ruleRevisions.map(r=>`<div class="receipt"><code>${escape(r)}</code> ${r===state.catalog.rulesetRevision?'<span class="tag">当前</span>':''}<div class="actions">${button('隔离预览','rules-preview',{revision:r})}${button('激活 / 回退','rules-activate',{revision:r})}</div></div>`).join(''))+panel('物品与状态',`<div class="grid3">${Object.entries(state.items).map(([index,item])=>`<article class="receipt"><h3>${icons[item.kind]||'◇'} ${escape(item.name)}</h3><p>${escape(item.description)}</p><small>${item.slots} 槽 · ${item.uses} 格用量</small></article>`).join('')}</div>`)+panel('场景遭遇表',state.encounters.map((x,i)=>`<p>${i+1} · ${escape(x)}</p>`).join(''));
}

function sessionPage() {
  return heading('P13','场次与存档')+panel('存档与账号',`<p>房间状态 · ${escape(state.roomStatus)}</p>${button('创建完整备份','backup',{},'primary')}<p class="muted">账号密码通过本机账号工具维护。回合、角色审核、自动裁决与暂停控制统一在主持控制台。</p>${link('返回主持控制台','gm/console')}`)+panel('场次回顾',`<form id="recap-form">${area('拟公开回顾','recapDraft',state.recapDraft)}${area('KP 私密备注','recapPrivate',state.recapPrivate)}<label><input type="checkbox" name="publish">同时发布公开回顾</label><button class="primary">保存回顾</button></form>`);
}

function recapPage() {
  return heading('P14','场次回顾')+panel('我们的探索',`<p style="white-space:pre-wrap">${escape(state.recap||'主持还没有发布本次探索回顾。')}</p>${mapView(state.locations,state.character?.numbers.location)}<div class="actions">${state.roomStatus==='active'&&state.session.numbers.phase===1?button('继续探索','navigate',{path:state.role==='kp'?'gm/console':'play/scene'},'primary'):'<span class="tag">等待主持恢复探索</span>'}${button('返回大厅','navigate',{path:'lobby'})}</div>`);
}

async function rawCommand(op,args) {
  return {result:await perform('chat',{operation:op,input:args})};
}

const paneNames = {status:'角色状态',inventory:'背包装备',clues:'线索手记',records:'记录消息'};
function desktopKey(){return 'sv.desktop.'+base.pathname+'.'+state.accountId;}
function restoreDesktop(){
  const key=desktopKey();
  if(desktopAccount===key)return;
  desktopAccount=key;
  try{desktop=JSON.parse(localStorage.getItem(key)||'{}');}catch{desktop={};}
  for(const name of Object.keys(paneNames))desktop[name]??={open:false,collapsed:false};
  desktop.front??='status';desktop.seen??=[];
  localAction=null;
}
function saveDesktop(){localStorage.setItem(desktopKey(),JSON.stringify(desktop));}
function unreadEvents(){return (state.events||[]).filter(e=>!desktop.seen.includes(e.account+':'+e.id)).length;}
function unreadMessages(){return Object.values(state.channels||{}).reduce((n,c)=>n+(c.unreadCount||0),0);}
function markEventsRead(){desktop.seen=(state.events||[]).map(e=>e.account+':'+e.id);saveDesktop();}
function sceneButtons(place){
  if(!state.sceneAutomation?.ready)return '<p class="notice">预设行动规则尚未安装，请主持在控制台安装场景规则。</p>';
  return (!state.sceneAutomation.executorOnline?'<p class="notice">自动执行端离线。保持一个 KP 页面在线后，预设行动会自动结算，无需逐项确认。</p>':'')+(state.autoSceneTasks?.length?'<p class="notice">预设行动正在自动队列中，请等待结果。</p>':'')+(state.sceneActions||[]).map(a=>button(escape(a.label),'scene-action',{id:a.id})).join('');
}
function sceneStatusPanel(){
  const s=state.sceneStatus||{};
  if(!s.facts?.length&&!s.supplies?.length)return '';
  return panel('现场变化',`<div class="scene-facts">${(s.facts||[]).map(f=>`<p><strong>${escape(f.label)}</strong> · ${escape(f.value)}</p>`).join('')}${(s.supplies||[]).map(x=>`<p>${escape(x.name)} · 剩余 ${x.count}</p>`).join('')}</div>`);
}
function sceneResult(result){
  if(!result?.sceneAction)return '';
  const changeText=(c,value)=>{
    if(['trapState','gateTrap'].includes(c.key))return ['未处理','已解除','已触发'][value]??value;
    if(['gateOpen','hallDoor','ironOpen','caveOpen'].includes(c.key))return value?'开启':'关闭';
    if(c.key==='villagersFreed')return value?'脱困':'被困';
    if(c.key==='ernieAwake')return value?'醒来':'熟睡';
    if(['spidersAlert','ratsAlert','snakeAlert'].includes(c.key))return value?'警觉':'尚未警觉';
    const quantities=['cheese1','moneyRemaining','idolRemaining','potsRemaining','fluteRemaining','paddleRemaining','clothRemaining','cheese10'];
    if(typeof value==='number'&&!quantities.includes(c.key))return value?'是':'否';
    return value;
  };
  return `<div class="scene-result"><p class="muted">${escape(result.process)}</p>${(result.checks||[]).map(r=>`<div class="scene-check"><strong>${escape(r.label)}</strong><div class="dice-result ${r.passed?'passed':'failed'}"><strong>${r.rolled}</strong><span>${escape(r.attribute.toUpperCase())} ≤ ${r.target}<br>${r.passed?'成功':'失败'} · ${r.mode==='disadvantage'?'劣势取高':'普通'}</span></div><small>d20：${r.first}${r.second?'、'+r.second:''} → 采用 ${r.rolled}</small></div>`).join('')}${(result.rolls||[]).length?`<ul class="scene-rolls">${result.rolls.map(r=>`<li>${escape(r.label)} · d${r.sides} → <b>${r.value}</b></li>`).join('')}</ul>`:''}<ol class="scene-narrative">${(result.narrative||[]).map(line=>`<li>${escape(line)}</li>`).join('')}</ol>${result.stateChanges?.length?`<h4>场景变化</h4><ul class="change-list">${result.stateChanges.map(c=>`<li><span>${escape(c.label.replace(/（0待处理[^）]*）/,''))}</span><span><del>${escape(changeText(c,c.before))}</del> <b>→ ${escape(changeText(c,c.after))}</b></span></li>`).join('')}</ul>`:''}${result.clues?.length?`<p class="notice">线索已记录：${result.clues.map(c=>escape(c.title)).join('、')}</p>`:''}</div>`;
}
function eventCard(e,compact=false){
  const automatic=e.status==='processing',waiting=e.status==='pending'||automatic, denied=e.status==='rejected';
  const label=automatic?'等待自动结算':waiting?'等待 KP':denied?'KP 已拒绝':e.result?.outcome==='blocked'?'条件不满足':e.status==='approved'?'KP 已裁决':'已结算';
  const r=e.result&&typeof e.result==='object'?e.result:{message:e.result?'操作已完成。':''};
  const dice='passed' in r?`<div class="dice-result ${r.passed?'passed':'failed'}"><strong>${r.rolled}</strong><span>${escape(r.attribute?.toUpperCase())} ≤ ${r.target}<br>${r.passed?'检定成功':'检定失败'} · ${{normal:'普通',advantage:'优势取低',disadvantage:'劣势取高'}[r.mode]||''}</span></div><p class="muted">d20：${r.first}${r.second?'、'+r.second:''} → 采用 ${r.rolled}</p>`:'';
  const changes=(e.changes||[]).map(c=>`<li><span>${escape(c.label)}</span><span><del>${escape(c.before)}</del> <b>→ ${escape(c.after)}</b></span></li>`).join('');
  return `<article class="event-card ${waiting?'waiting':denied?'denied':''}" data-event-id="${escape(e.id)}"><div class="event-head"><strong>${escape(e.title)}</strong><span class="tag">${label}</span></div><small class="muted">${new Date(e.time*1000).toLocaleString()} · ${e.mode==='kp'?'主持裁决':'自动结算'}${state.role==='kp'?' · '+escape(e.account):''}</small>${compact?'':`<ol class="action-steps"><li class="done">已提交</li><li class="${waiting?'current':'done'}">${e.mode==='kp'?'等待主持':'规则判定'}</li><li class="${waiting?'':'done'}">${waiting?'待结算':denied?'已拒绝':e.mechanical?'已结算':'已回复'}</li></ol>`}${e.text&&!compact?'<p>'+escape(e.text)+'</p>':''}${sceneResult(r)||dice||(!waiting?'<p>'+escape(Object.keys(r).length?resultText(r):denied?'本次申请未执行。':e.mechanical?'规则已执行。':'已记录主持结论；此回复不自动修改角色。')+'</p>':'<p>申请已送达主持；尚未投骰或扣减资源。</p>')}${e.reason?`<p class="ruling-reason">${waiting?'转交原因':'裁决说明'}：${escape(e.reason)}</p>`:''}${changes?`<ul class="change-list">${changes}</ul>`:!waiting?'<p class="muted">本次没有角色资源变化。</p>':''}${!compact&&state.character&&e.receiptId?button('请求复核','review',{receiptId:e.receiptId,text:'请复核：'+e.title},'small quiet'):''}</article>`;
}
function activityFeed(){
  const events=(state.events||[]).slice().reverse();
  return `<div class="activity-feed">${events.map(e=>eventCard(e)).join('')||empty('还没有行动记录。提交行动后，过程和变化会保存在这里。')}</div>`;
}
function updateActivity(){
  const target=document.querySelector('#action-feedback');
  if(!target||!state)return;
  const latest=(state.events||[]).at(-1);
  const pending=state.requests.filter(r=>r.account===state.accountId&&r.status==='pending').length;
  target.innerHTML=`${localAction?`<div class="notice ${localAction.status==='error'?'error':''}">${escape(localAction.text)}</div>`:''}${latest?`<details class="latest-action" ${localAction?'':'open'}><summary>最近行动 · ${escape(latest.title)}${pending?' · '+pending+' 项等待主持':''}</summary>${eventCard(latest,true)}</details>`:'<p class="muted">提交行动后，这里会显示结算过程、资源变化和主持回复。</p>'}`;
  const badge=document.querySelector('[data-unread]');if(badge)badge.textContent=(unreadEvents()+unreadMessages())||'';
}
function chatPanel(){
  const channels=Object.values(state.channels);
  if(!channels.some(x=>x.channelId===currentChannel))currentChannel=channels[0]?.channelId||'general';
  return `<p class="message-status">待处理消息 · ${unreadMessages()} 条未读</p>${select('选择频道','channel',channels.map(x=>[x.channelId,x.name+(x.unreadCount?' · '+x.unreadCount+' 条未读':'')]),currentChannel)}<div id="chat-history" class="chatbox" aria-live="polite"></div><div class="actions">${button('较早记录','chat-older',{},'small')}${button('标为已读','chat-read',{},'small')}</div><form id="chat-form">${area('消息','text')}<button class="primary">发送</button> ${button('建立私聊','direct')}${state.role==='kp'?button('创建频道','channel-create'):''}</form>`;
}
function paneContent(name){
  const c=state.character;
  if(name==='status')return c?`<div class="character-mini"><img src="art/mouse.png" alt=""><div><h3>${escape(c.name)}</h3><p>等级 ${c.numbers.level} · XP ${c.numbers.xp} · Grit ${c.numbers.grit}</p><span class="tag">${c.numbers.incapacitated?'失能':'可行动'}</span></div></div>${statCards(c)}<p>光源：${c.numbers.litSlot?'槽位 '+c.numbers.litSlot+' 已点亮':'未点亮'}</p>${button('属性检定','check',{},'primary')}`:empty('请先认领角色');
  if(name==='inventory')return c?inventoryCards(c):empty('请先认领角色');
  if(name==='clues'){
    const clues=state.locations.flatMap(p=>p.clues.map(c=>({...c,place:p.name})));
    return field('检索已公开内容','clue-search')+(clues.map(c=>`<article class="receipt clue"><h3>${escape(c.title)}</h3><small>${escape(c.place)}</small><p>${escape(c.text)}</p></article>`).join('')||empty('主持尚未发布线索'))+`<form id="note-form">${area('我的手记 · 仅本人可见','text',state.note)}<button class="primary">保存手记</button></form>`;
  }
  return `<div class="actions">${button('标记记录已读','events-read',{},'small')}${button('请求 KP 裁决','review',{},'small')}</div><details><summary>我的裁决申请 · ${state.requests.filter(r=>r.account===state.accountId&&r.status==='pending').length} 待处理</summary>${myRulings()}</details><h3>行动过程与结果</h3>${activityFeed()}<details class="legacy-receipts"><summary>原始回执与摘要分享</summary>${state.receipts.slice().reverse().map(r=>`<div class="receipt"><p>${escape(resultText(r.result))}</p>${['check','inventory','ready'].includes(r.operation)&&r.result.status!=='pending'?button('分享摘要','share',{id:r.id},'small'):''}${button('请求复核','review',{receiptId:r.id,text:'请复核：'+resultText(r.result)},'small')}</div>`).join('')}</details><h3>频道消息</h3>${chatPanel()}`;
}
function floatingPanel(name){
  const p=desktop[name];if(!p.open)return '';
  return `<section class="floating-panel pane-${name} ${p.collapsed?'collapsed':''} ${desktop.front===name?'front':''}" aria-label="${paneNames[name]}悬浮面板"><header class="floating-head">${button(paneNames[name],'pane-front',{name},'pane-title quiet')}<div>${button(p.collapsed?'展开':'折叠','pane-collapse',{name},'small quiet')}${button('关闭','pane-close',{name},'small quiet')}</div></header><div class="floating-body" ${p.collapsed?'hidden':''}>${p.collapsed?'':paneContent(name)}</div></section>`;
}
function workspacePage(){
  const feedback='<section id="action-feedback" aria-label="最近行动反馈" aria-live="polite"></section>';
  const scene=scenePage(), marker='<div class="layout-aside">';
  return `<div class="scene-base">${scene.includes(marker)?scene.replace(marker,feedback+marker):scene+feedback}</div><div class="desktop-panels">${Object.keys(paneNames).map(floatingPanel).join('')}</div><nav class="desktop-dock" aria-label="场景面板">${Object.entries(paneNames).map(([name,label])=>`<button type="button" data-action="pane-toggle" data-args="${escape(JSON.stringify({name}))}" aria-pressed="${desktop[name].open}">${label}${name==='records'?'<b class="unread-dot" data-unread>'+ (unreadEvents()||'')+'</b>':''}</button>`).join('')}${button('收起全部','panes-hide',{},'quiet small')}</nav>`;
}
function requestDescription(r){
  const a=r.args.input||r.args;
  const kind={scene:'场景预设',travel:'移动',check:'检定',inventory:'物品操作',transfer:'转交',review:'复核',free:'自由行动',interact:'场景互动'}[r.kind]||r.kind;
  const detail=r.kind==='scene'?((state.sceneDefinitions||[]).find(x=>x.id===a.action)?.choices.find(c=>c.id===a.choice)?.label||a.choice):r.kind==='check'?`${a.attribute?.toUpperCase()} · ${{normal:'普通',advantage:'优势',disadvantage:'劣势'}[a.mode]||''}`:r.kind==='inventory'?`${{move:'移动',use:'使用',light:'点亮',extinguish:'熄灭'}[a.operation]||a.operation} · 槽位 ${a.slot}${a.operation==='move'?' → '+a.value:''}`:r.kind==='travel'?'前往 '+(state.allLocations?.[String(a.destination)]?.name||a.destination):r.kind==='transfer'?`槽位 ${a.slot} → ${state.team.find(t=>t.account===a.targetAccount)?.name||a.targetAccount} 的槽位 ${a.destination}`:'';
  return `${kind}${detail?' · '+detail:''}`;
}
function rulingQueue(){
  return state.requests.filter(r=>r.status==='pending').map(r=>`<article class="queue-item ${selectedRequest===r.id?'selected':''}"><small>${escape(r.account)} · ${new Date(r.time*1000).toLocaleTimeString()}</small><strong>${escape(requestDescription(r))}</strong><p>${escape(r.text||'等待主持处理')}</p>${button('查看并裁决','console-request',{id:r.id},'primary small')}</article>`).join('')||empty('没有待处理行动');
}
function rulingDetail(){
  const r=state.requests.find(r=>r.id===selectedRequest)||state.requests.find(r=>r.status==='pending');
  if(!r)return empty('玩家提交行动申请后，可在这里查看上下文并裁决。');
  selectedRequest=r.id;
  const actor=state.characters.find(c=>c.instanceId===r.actor);
  return `<h3>${escape(requestDescription(r))}</h3><p>${escape(r.account)} · ${escape(actor?.name||'角色')} · ${escape(state.allLocations[String(r.location)]?.name||'')}</p><blockquote>${escape(r.text||'')}</blockquote><p>转交原因：${escape(r.reason||'玩家申请')}</p>${actor?`<p>当前资源：HP ${actor.numbers.hp}/${actor.numbers.maxHp} · STR ${actor.numbers.str} / DEX ${actor.numbers.dex} / WIL ${actor.numbers.wil}</p>`:''}${r.status==='pending'?`<form id="ruling-form"><input type="hidden" name="requestId" value="${escape(r.id)}">${select('裁决决定','approve',[['yes','批准'],['no','拒绝']],'yes')}${area('裁决依据与给玩家的回复','reason')}<p class="muted">${['check','inventory','travel','transfer','scene'].includes(r.kind)?'批准后执行规则，结算结果与资源变化会送达相关玩家。':'此类申请记录主持回复，数值影响请使用控制台工具另行结算。'}</p><button class="primary" type="submit">保存裁决并通知玩家</button></form>`:`<span class="tag">${r.status==='approved'?'已批准':'已拒绝'}</span><p>${escape(r.reason||'未附说明')}</p>`}`;
}
function consolePage(){
  const pending=state.requests.filter(r=>r.status==='pending').length;
  const drafts=Object.values(state.drafts).filter(d=>d.status==='submitted');
  const controls=`<div class="console-controls"><div><small>探索时钟</small><strong>第 ${state.session?.numbers.round||0} 回合</strong></div><div class="actions">${button('开场 / 继续','start',{},'primary')}${button('推进回合','round')}${button(state.roomStatus==='paused'?'恢复房间':'暂停房间','room',{status:state.roomStatus==='paused'?'active':'paused'})}${button(state.automation.ready?(state.automation.enabled?'关闭自动裁决':'开启自动裁决'):'升级自动裁决','automation-console')}</div></div>`;
  let content='';
  if(consoleTab==='control')content=`<div class="console-columns"><div>${panel('队伍与资源',charactersTable())}${panel('场景生物与遭遇工具',`<div class="actions">${button('掷遭遇检查','generate',{kind:'encounter'})}${button('抽取遭遇内容','generate',{kind:'encounter-table'})}${button('反应骰','generate',{kind:'reaction'})}${button('战利品骰','generate',{kind:'loot'})}${button('角色伤害','damage')}${!state.sceneAutomation?.ready?button('安装场景规则','scene-install',{},'primary'):''}${button('创建生物','npc-create')}</div>${(state.npcs||[]).map(n=>`<div class="row"><span>${escape(n.name)} · HP ${n.numbers.hp}/${n.numbers.maxHp}</span><div>${button('伤害','damage',{actor:n.instanceId},'small')}${button('士气','morale',{actor:n.instanceId},'small')}${button('数值','actor-edit',{id:n.instanceId},'small')}</div></div>`).join('')}`)}${panel('完整地点图',mapView(Object.values(state.allLocations),selectedLocation))}</div><aside>${panel('待处理行动 · '+pending,rulingQueue())}${panel('建角审核 · '+drafts.length,drafts.map(d=>`<article class="receipt"><strong>${escape(d.name)} · ${escape(d.account)}</strong><p>STR ${d.str} / DEX ${d.dex} / WIL ${d.wil} · HP ${d.hp}</p>${button('审核通过','approve',{account:d.account},'primary small')}${button('退回修改','reject',{account:d.account},'small')}</article>`).join('')||empty('没有待审核角色'))}</aside></div>`;
  if(consoleTab==='rulings')content=`<div class="ruling-columns">${panel('待处理队列',rulingQueue())}${panel('裁决详情',rulingDetail(),'ruling-detail')}</div><details><summary>近期裁决与自动行动</summary>${activityFeed()}</details>`;
  if(consoleTab==='messages')content=`<div class="grid2">${panel('频道与待处理消息',chatPanel())}${panel('行动通知',button('标记记录已读','events-read',{},'small')+activityFeed())}</div>`;
  return heading('P09','主持控制台',`<span class="tag">待处理 ${pending+drafts.length}</span><span class="tag">自动裁决${state.automation.enabled?'开启':'关闭'}</span><span class="tag">${state.sceneAutomation?.executorOnline?'自动执行端在线':'正在连接自动执行端'}</span>`)+`<section class="kp-console" aria-label="主持统一控制台">${controls}<nav class="console-tabs" aria-label="控制台面板">${[['control','控制与队伍'],['rulings','待处理与裁决 · '+pending],['messages','消息与记录 · '+unreadMessages()+' 未读']].map(([tab,label])=>button(label,'console-tab',{tab},consoleTab===tab?'primary':'')).join('')}</nav><div class="console-content">${content}</div></section>`;
}

function changePane(name,change){
  if(dirtyForm){toast('请先保存正在编辑的内容，再切换面板。');return;}
  Object.assign(desktop[name],change);desktop.front=name;saveDesktop();renderPage();
}

const actions = {
  'scene-action':({id})=>{
    const a=state.sceneActions.find(x=>x.id===id);
    openDialog(a.label,`<p>${escape(a.hint)}</p>${select('选择具体做法','scene-choice',a.choices.map(c=>[c.id,c.label]),a.choices[0].id)}<div id="scene-process" class="notice">${escape(a.choices[0].process)}</div>${select('结算方式','ruling',[['auto','按预设自动结算'],['manual','主动请求 KP 裁决']],'auto')}`,data=>perform('scene.action',{action:id,choice:data.get('scene-choice'),manual:data.get('ruling')==='manual'}),'执行行动','S18');
    dialog.dataset.sceneAction=id;
  },
  'scene-install':()=>openDialog('安装场景预设规则','<p>为当前存档补充场景规则和有限库存状态，保留已有角色与资料。</p>',()=>perform('scene.install',{}),'安装','S14'),
  'pane-toggle':({name})=>changePane(name,{open:desktop.front!==name||desktop[name].collapsed?true:!desktop[name].open,collapsed:false}),
  'pane-close':({name})=>changePane(name,{open:false}),
  'pane-collapse':({name})=>changePane(name,{collapsed:!desktop[name].collapsed}),
  'pane-front':({name})=>{desktop.front=name;saveDesktop();document.querySelectorAll('.floating-panel').forEach(p=>p.classList.toggle('front',p.classList.contains('pane-'+name)));},
  'panes-hide':()=>{if(dirtyForm)return toast('请先保存正在编辑的内容。');for(const name of Object.keys(paneNames))desktop[name].open=false;saveDesktop();renderPage();},
  'events-read':()=>{markEventsRead();renderPage();},
  'console-tab':({tab})=>{if(dirtyForm)return toast('请先保存当前表单。');consoleTab=tab;renderPage();},
  'console-request':({id})=>{if(dirtyForm)return toast('请先完成当前裁决。');selectedRequest=id;consoleTab='rulings';renderPage();},
  'automation-console':()=>state.automation.ready?actions.automation({enabled:!state.automation.enabled}):actions.install(),
  close:closeDialog,
  navigate:({path})=>{location.hash='/'+path;},
  initialize:()=>perform('initialize',{}),
  recover:()=>{const body=JSON.parse(localStorage.getItem(pendingKey())); return perform(body.operation,body.args,body);},
  logout:async()=>{await api('api/v1/logout',{});state=null;csrf='';history=[];closeDialog();location.hash='/entry';renderEntry();},
  draft:args=>openDialog('为小鼠取个名字',field('名字','name',args.name),data=>perform('draft',{preset:args.preset,name:data.get('name')}),'提交审核','P03'),
  'choose-preset':args=>{creation={...args,step:1,swap:''};renderPage();},
  'create-roll':async()=>{await perform('draft.roll',{});creation={step:1,preset:'random',name:'',swap:''};renderPage();},
  'create-next':()=>{creation.step++;renderPage();},
  'create-back':()=>{creation.step--;renderPage();},
  'create-submit':async()=>{await perform('draft',{preset:creation.preset,name:creation.name,swap:creation.swap});location.hash='/ready';},
  ready:args=>perform('ready',args),
  check:args=>openDialog('属性检定',select('属性','attribute',[['str','STR 力量'],['dex','DEX 敏捷'],['wil','WIL 意志']],args.attribute||'dex')+select('情境','mode',[['normal','普通'],['advantage','优势'],['disadvantage','劣势']],'normal')+rulingMode(),data=>submitAction('check',{attribute:data.get('attribute'),mode:data.get('mode')},data),'投骰','S02'),
  request:args=>openDialog('向主持描述行动',area('行动意图','text',args.text||''),data=>perform('request',{kind:args.kind||'free',text:data.get('text')}),'提交请求','S10'),
  travel:args=>openDialog('前往已知地点','<p>公开、相邻且开启的通路可自动通行；主动申请时等待 KP 批准。</p>'+rulingMode(),data=>perform('request',{kind:'travel',destination:args.destination,manual:data.get('ruling')==='manual',text:'移动到已知地点 '+args.destination}),'确认移动','S07'),
  automation:args=>openDialog('自动裁决设置',`<p>${args.enabled?'开启后，规则明确的行动由系统直接结算。':'关闭后，检定、物品操作与移动将进入主持队列。'}已有申请仍等待主持处理。</p>`,()=>perform('automation.configure',args),'保存设置','S14'),
  review:args=>openDialog('请求 KP 裁决',area('事件描述与裁决诉求','text',args.text||'')+`<p class="muted">${args.receiptId?'关联你已完成的行动，复核不会自动重掷或重复扣减。':'描述当前事件，由 KP 判断并回复。'}</p>`,data=>perform('request',{kind:'review',text:data.get('text'),...(args.receiptId?{receiptId:args.receiptId}:{})}),'提交申请','S10'),
  location:args=>{if(state.role==='kp'){selectedLocation=args.index;location.hash='/gm/locations/'+args.index;renderPage();}else{const p=state.locations.find(x=>x.index===args.index);openDialog(p.name,'<p>'+escape(p.description)+'</p>',null,'','S07');}},
  'select-location':args=>{selectedLocation=args.index;location.hash='/gm/locations/'+args.index;renderPage();},
  start:()=>perform('world',{operation:'start',round:state.session.numbers.round}),
  round:()=>openDialog('推进一个探索回合',`<p>当前为第 ${state.session.numbers.round} 回合。确认后同步更新所有角色的燃烧计时。</p>`,()=>perform('world',{operation:'round',round:state.session.numbers.round}),'推进一次','S12'),
  generate:args=>perform('generate',args),
  approve:args=>perform('approve',args),
  reject:args=>openDialog('退回角色草稿',area('修改建议','reason'),data=>perform('approve',{...args,reject:true,reason:data.get('reason')}),'退回','S10'),
  resolve:args=>{const request=state.requests.find(x=>x.id===args.id);openDialog('主持裁定','<p>'+escape(request.text||request.kind)+'</p><p>'+escape(request.reason||'')+'</p>'+(request.kind==='review'?'<p>复核只记录裁定说明，必要的数值修正请另用主持管理工具执行。</p>':'')+select('决定','approve',[['yes','批准'],['no','拒绝']],'yes')+area('裁定依据','reason'),data=>perform('resolve',{requestId:args.id,approve:data.get('approve')==='yes',reason:data.get('reason')}),'保存裁定','S10');},
  publish:args=>{const p=state.allLocations[String(args.index)];const old=state.published[String(args.index)];openDialog('发布预览',`<span class="tag">受众 · 房间成员</span><h3>${escape(p.name)}</h3><div class="grid2"><div><h3>当前公开</h3><p>${escape(old?.description||'尚未发布')}</p></div><div><h3>拟发布</h3><p>${escape(p.description)}</p></div></div>${p.clues.map(x=>`<label><input type="checkbox" name="clue" value="${escape(x.id)}" ${old?.clues.some(c=>c.id===x.id)?'checked':''}> ${escape(x.title)}<br>${escape(x.text)}</label>`).join('')}<p class="muted">仅发布已保存的描述和勾选线索，主持真相保持私密。</p>`,data=>perform('location.publish',{...args,clues:data.getAll('clue')}),'公开此地点','S08');},
  preview:async args=>{const account=state.members.find(x=>x.role==='player')?.accountId;if(!account)return toast('房间内还没有玩家');const data=await api('package/state?preview='+encodeURIComponent(account));openDialog('玩家公开预览',`<div class="notice">只读 · ${escape(account)} · 包侧公开投影</div>${mapView(data.locations,1)}<p>${escape(data.locations.find(x=>x.index===args.index)?.description||'该地点尚未公开')}</p>`,null,'','S09');},
  damage:args=>openDialog('伤害与豁免',select('目标','actor',[...actorOptions(),...(state.npcs||[]).map(x=>[x.instanceId,x.name])],args.actor)+field('伤害骰最终值（减甲前）','amount',1,'number')+select('溢出扣减属性','attribute',[['str','STR'],['dex','DEX（蜘蛛毒伤）']],'str'),data=>perform('damage',{actor:data.get('actor'),amount:number(data.get('amount')),attribute:data.get('attribute')}),'确认结算','S11'),
  grant:args=>openDialog('授予物品',select('物品','item',Object.entries(state.items).map(([id,x])=>[id,x.name]),1)+field('起始槽位（1–10，超载11–20）','slot',5,'number'),data=>{const item=number(data.get('item'));return perform('grant',{actor:args.actor,item,slot:number(data.get('slot')),uses:state.items[String(item)].uses});},'授予','S01'),
  rest:args=>openDialog('主持确认休息',select('休息类型','kind',[['short','短休 · 一探索轮'],['long','长休 · 吃饭与睡眠'],['full','完整休整 · 安全地一周']],'short')+select('长休时若 HP 已满，恢复哪项属性','attribute',[['str','STR'],['dex','DEX'],['wil','WIL']],'str')+'<p class="muted">确认食物、水、照料及安全条件；恢复不自动推进时间，请另行推进探索轮。</p>',data=>perform('rest',{actor:args.actor,kind:data.get('kind'),attribute:data.get('attribute')}),'执行恢复','S03'),
  'actor-edit':args=>{const c=[...(state.characters||[]),...(state.npcs||[])].find(x=>x.instanceId===args.id);openDialog('主持数值调整',select('字段','key',[['hp','HP'],['str','STR'],['dex','DEX'],['wil','WIL'],['armor','护甲'],['pips','钱币'],['xp','XP'],['level','等级'],['grit','Grit']],'hp')+field('新的数值','value',c.numbers.hp,'number'),data=>perform('actor.update',{id:args.id,numbers:{[data.get('key')]:number(data.get('value'))}}),'保存','S14');},
  room:args=>openDialog('确认房间状态','<p>将房间设为 '+escape(args.status==='paused'?'暂停':'运行')+'。</p>',()=>perform('room',args),'确认','S14'),
  backup:()=>openDialog('创建完整备份','<p>保存宿主房间备份与包侧手记、草稿和请求记录。</p>',()=>perform('backup',{}),'创建备份','S14'),
  rules:()=>openDialog('规则速查',state.rules.map(x=>`<h3>${escape(x.title)}</h3><p>${escape(x.text)}</p><a href="${escape(x.source)}" target="_blank" rel="noreferrer">原版 SRD</a>`).join('<hr>'),null,'','S13'),
  preferences:()=>openDialog('偏好与帮助',select('界面字号','font',[['16','标准'],['18','较大'],['20','大字']],localStorage.getItem('sv.font')||'16')+'<label><input type="checkbox" name="reduce">减少动画</label><p>Tab 切换控件，Enter 确认，Esc 关闭弹窗。断线时请恢复原行动。</p>',data=>{localStorage.setItem('sv.font',data.get('font'));document.documentElement.style.fontSize=data.get('font')+'px';document.body.classList.toggle('reduce-motion',data.has('reduce'));closeDialog();},'保存','S17'),
  install:()=>openDialog('安装当前规则版本','<p>完整检查包内 Lua 与 JSON 后激活新修订，已有角色资源保留。</p>',()=>perform('rules.install',{}),'检查并安装','S14'),
  export:async()=>{const data=await api('package/bundle');const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='stumpsville-bundle.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);},
  item:({slot})=>{const n=state.character.numbers;const def=state.items[String(n['item'+slot])];openDialog(def.name,`<p>${escape(def.description)}</p><p>占用 ${def.slots} 格 · 剩余用量 ${n['uses'+slot]} / ${def.uses}</p><div class="actions">${def.uses&&def.kind!=='spell'?button('使用 / 检查用量','use',{slot}):''}${def.kind==='spell'?button('请求施法裁定','request',{kind:'free',text:'施放 '+def.name+'，请主持核定力量、用量与效果'}):''}${def.light?button(n.litSlot===slot?'熄灭':'点亮','light',{slot,operation:n.litSlot===slot?'extinguish':'light'}):''}${button('移动物品','move-item',{slot})}${button('请求转交','transfer',{slot})}</div>`,null,'','S01');},
  use:({slot})=>openDialog('确认物品用量','<p>根据物品规则消耗用量或掷使用骰。</p>'+rulingMode(),data=>submitAction('inventory',{operation:'use',slot,value:0},data),'确认使用','S03'),
  light:({slot,operation})=>perform('inventory',{operation,slot,value:0}),
  'move-item':({slot})=>openDialog('移动到另一个槽位',field('目标槽位（1–10，超载11–20）','value',5,'number')+rulingMode(),data=>submitAction('inventory',{operation:'move',slot,value:number(data.get('value'))},data),'移动','S04'),
  transfer:({slot})=>openDialog('请求转交物品',select('接收队友','targetAccount',state.team.filter(x=>x.account!==state.accountId).map(x=>[x.account,x.name]))+field('接收槽位','destination',5,'number'),data=>perform('request',{kind:'transfer',slot,targetAccount:data.get('targetAccount'),destination:number(data.get('destination')),text:'请求转交槽位 '+slot+' 的物品'}),'提交主持','S05'),
  share:({id})=>{const receipt=state.receipts.find(x=>x.id===id);openDialog('分享回执摘要',`<p>${escape(resultText(receipt.result))}</p>`+select('发布到频道','channelId',Object.values(state.channels).filter(x=>x.canPost).map(x=>[x.channelId,x.name]),currentChannel)+'<p class="muted">由包侧读取原回执生成文字摘要。角色私密数据不会随摘要一同公开。</p>',data=>perform('share.receipt',{receiptId:id,channelId:data.get('channelId')}),'发布摘要','S06');},
  'chat-older':()=>nextBefore?loadChat(true):toast('已经到达最早记录'),
  'chat-read':()=>rawCommand('chat.read',{channelId:currentChannel,sequence:history.at(-1)?.sequence||0}),
  'chat-edit':args=>openDialog('编辑消息',area('消息','text',args.text),data=>rawCommand('chat.message.edit',{channelId:currentChannel,messageId:args.messageId,revision:args.revision,text:data.get('text')}),'保存','S06'),
  'channel-create':()=>openDialog('创建频道',field('频道名称','name')+select('范围','kind',[['room','公共'],['group','分组']],'room')+state.members.filter(x=>x.accountId!==state.accountId).map(x=>`<label><input type="checkbox" name="member" value="${escape(x.accountId)}"> ${escape(x.nickname)}</label>`).join(''),data=>rawCommand('chat.channel.create',{name:data.get('name'),kind:data.get('kind'),...(data.get('kind')==='group'?{participants:[state.accountId,...data.getAll('member')]}:{})}),'创建','S06'),
  'door':args=>openDialog('通路状态',select('门或通路','status',[['open','开启'],['closed','关闭'],['locked','锁住']],state.doors[args.edge]),data=>perform('door',{edge:args.edge,status:data.get('status')}),'保存','S14'),
  'take-stock':args=>openDialog('从地点领取',select('接收角色','actor',state.characters.filter(x=>x.numbers.location===args.index).map(x=>[x.instanceId,x.name]))+field('放入槽位','slot',7,'number'),data=>perform('stock.take',{...args,actor:data.get('actor'),slot:number(data.get('slot'))}),'确认领取','S01'),
  morale:args=>perform('morale',args),
  'npc-create':()=>openDialog('新建主持生物',field('名称','name')+['str','dex','wil','hp','armor','location'].map((x,i)=>field({str:'STR',dex:'DEX',wil:'WIL',hp:'HP',armor:'护甲',location:'地点编号'}[x],x,[9,9,9,3,0,1][i],'number')).join('')+'<p class="muted">默认是SRD通用小鼠，专属角色请按原版输入。</p>',data=>perform('npc.create',{name:data.get('name'),numbers:Object.fromEntries(['str','dex','wil','hp','armor','location'].map(x=>[x,number(data.get(x))]))}),'创建','S10'),
  'tables':()=>openDialog('主持随机表',area('d6 遭遇内容（每行一项，共6行）','encounters',state.encounters.join('\n'))+area('d20 战利品（每行一项，共20行）','loot',state.loot.join('\n')),data=>perform('tables.save',{encounters:data.get('encounters').split('\n'),loot:data.get('loot').split('\n')}),'保存','S14'),
  'stage':()=>openDialog('导入与检查','<label>选择导出的配置包 JSON<input type="file" id="bundle-file" accept=".json"></label><p>检查不会激活规则；通过后可在隔离快照预览。</p>',async()=>{const f=document.querySelector('#bundle-file').files[0];if(!f)throw new Error('请选择 JSON 文件');if(f.size>131072)throw new Error('配置文件超过本机接口限制');const data=JSON.parse(await f.text());const result=await perform('rules.stage',{bundle:data});lastStage=result.revision;renderPage();},'检查暂存','S14'),
  'rules-preview':({revision})=>openDialog('隔离预览',select('规则','rule',[['sv.layout','物品栏布局'],['sv.check','属性检定']],'sv.layout')+select('角色','actor',actorOptions()),async data=>{const rule=data.get('rule');const input={actor:data.get('actor'),...(rule==='sv.check'?{attribute:'dex',mode:'normal'}:{})};const result=await perform('rules.preview',{revision,rule,input});openDialog('预览结果','<pre>'+escape(JSON.stringify(result,null,2))+'</pre>',null,'','S14');},'运行预览','S14'),
  'rules-activate':args=>openDialog('激活 / 回退修订','<p>将使用修订 '+escape(args.revision)+'。已有角色数值不会自动迁移。</p>',()=>perform('rules.activate',args),'确认激活','S14'),
  direct:async()=>{const people=await api('api/v1/chat/members');openDialog('建立私聊',select('成员','accountId',people.items.filter(x=>x.accountId!==state.accountId).map(x=>[x.accountId,x.nickname])),async data=>{const result=await rawCommand('chat.direct.open',{accountId:data.get('accountId')});currentChannel=result.result.channelId;closeDialog();await refresh();},'进入私聊','S06');},
  retract:async args=>{await rawCommand('chat.message.retract',{channelId:currentChannel,...args});await loadChat();}
};

document.addEventListener('click',async event=>{
  const target=event.target.closest('[data-action]');
  if(!target)return;
  const action=actions[target.dataset.action];
  if(!action)return;
  target.disabled=true;
  try { await action(JSON.parse(target.dataset.args||'{}')); }
  catch(error){toast(error.message);}
  finally { if(target.isConnected)target.disabled=false; }
});
document.addEventListener('change',event=>{
  if(event.target.name==='scene-choice'){
    const a=state.sceneActions.find(x=>x.id===dialog.dataset.sceneAction);
    document.querySelector('#scene-process').textContent=a.choices.find(c=>c.id===event.target.value).process;
  }
  if(event.target.name==='channel'){currentChannel=event.target.value;loadChat().catch(error=>toast(error.message));}
});
document.addEventListener('input',event=>{
  const form=event.target.closest('form');
  if(form&&['note-form','location-form','recap-form','creation-form','chat-form','ruling-form'].includes(form.id))dirtyForm=form.id;
  if(event.target.name==='clue-search'){const q=event.target.value.toLocaleLowerCase();document.querySelectorAll('.clue').forEach(x=>x.hidden=!x.textContent.toLocaleLowerCase().includes(q));}
});
document.addEventListener('keydown',event=>{if(event.target.matches('g[role=button]')&&['Enter',' '].includes(event.key)){event.preventDefault();event.target.dispatchEvent(new MouseEvent('click',{bubbles:true}));}});
document.addEventListener('submit',async event=>{
  event.preventDefault();
  const form=event.target,data=new FormData(form);
  const submit=form.querySelector('[type=submit],button:not([type])');
  if(submit)submit.disabled=true;
  try{
    if(form.id==='entry-form'){
      if(setup.canSetup){await api('setup',{password:data.get('password')});setup=await api('setup/status');renderEntry();toast('准备完成，请登录');}
      else{const me=await api('api/v1/login',Object.fromEntries(data));csrf=me.csrf;await refresh(false);location.hash='/lobby';renderPage();}
    }else if(form.id==='dialog-form'&&dialogSubmit){await dialogSubmit(data);}
    else if(form.id==='creation-form'){creation.name=data.get('name');creation.swap=data.get('swap')||'';creation.step=2;renderPage();}
    else if(form.id==='note-form'){await perform('note',{text:data.get('text')});}
    else if(form.id==='ruling-form'){await perform('resolve',{requestId:data.get('requestId'),approve:data.get('approve')==='yes',reason:data.get('reason')});}
    else if(form.id==='location-form'){await perform('location.save',{index:number(data.get('index')),revision:number(data.get('revision')),description:data.get('description'),truth:data.get('truth')});}
    else if(form.id==='recap-form'){await perform('recap',{recapDraft:data.get('recapDraft'),recapPrivate:data.get('recapPrivate'),publish:data.has('publish')});}
    else if(form.id==='chat-form'){await rawCommand('chat.message.send',{channelId:currentChannel,text:data.get('text')});form.reset();await loadChat();}
  }catch(error){const target=document.querySelector('#entry-error');if(target)target.textContent=error.message;toast(error.message);}
  finally{if(submit?.isConnected)submit.disabled=false;}
});
window.addEventListener('hashchange',()=>{
  if(dirtyForm){
    const target=location.hash;
    historyReplace(acceptedHash);
    openDialog('尚有未保存的修改','<p>取消可返回继续编辑；放弃后前往目标页面。</p>',()=>{dirtyForm=null;closeDialog();location.hash=target;},'放弃修改并离开','S14');
    return;
  }
  acceptedHash=location.hash;closeDialog();renderPage();window.scrollTo(0,0);
});
function historyReplace(hash){window.history.replaceState(null,'',location.pathname+location.search+hash);}
window.addEventListener('beforeunload',event=>{if(dirtyForm){event.preventDefault();event.returnValue='';}});
dialog.addEventListener('cancel',()=>{dialogSubmit=null;});
document.documentElement.style.fontSize=(localStorage.getItem('sv.font')||'16')+'px';
async function boot(){
  try{
    setup=await api('setup/status');
    if(setup.ready){try{const me=await api('api/v1/me');csrf=me.csrf;await refresh(false);}catch{state=null;}}
    renderPage();
  }catch(error){app.innerHTML=empty('连接失败 · '+error.message);}
}
async function runAutoScenes(){
  if(!state||state.role!=='kp'||!state.initialized||executorBusy||busy)return;
  executorBusy=true;
  try{
    if(!state.sceneAutomation?.ready&&!sceneInstallTried){
      sceneInstallTried=true;
      await api('package/action',{id:'scene-install-v1',operation:'scene.install',args:{}});
      renderDeferred=true;
    }
    const ready=await api('package/scene-executor',{});
    for(const job of ready.jobs){
      await api('package/action',{id:job.commandId,operation:'scene.autorun',args:{jobId:job.id}});
      renderDeferred=true;
    }
  }catch(error){
    const label=document.querySelector('#connection');
    if(label)label.textContent='自动执行暂缓 · '+error.message;
  }finally{executorBusy=false;}
}
if(base.pathname==='/'){
  const bytes=crypto.getRandomValues(new Uint8Array(12));
  const slot='tab-'+Array.from(bytes,x=>x.toString(16).padStart(2,'0')).join('');
  location.replace('/sessions/'+slot+'/'+location.hash);
}else await boot();
setInterval(async()=>{
  if(!state||busy)return;
  try{
    const next=await api('package/state');
    const changed=JSON.stringify(next)!==JSON.stringify(state);
    state=next;connection='已同步';
    const editing=['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName);
    if(changed)renderDeferred=true;
    if(renderDeferred&&!editing&&!dialog.open&&!dirtyForm){renderDeferred=false;renderPage();}
    else if(changed)updateActivity();
    if(document.querySelector('#chat-history')&&!busy)await loadChat();
    await runAutoScenes();
    const label=document.querySelector('#connection');if(label)label.textContent='已同步';
  }catch(error){
    connection='连接中断';
    const label=document.querySelector('#connection');if(label)label.textContent=connection;
    if(error.status===401){state=null;csrf='';history=[];closeDialog();renderEntry();}
  }
},2500);

