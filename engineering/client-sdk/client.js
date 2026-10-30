export class HttpTransport {
 async request(path,{method='GET',body,csrf}={}){const r=await fetch('/api/v1/'+path,{method,credentials:'same-origin',headers:{...(body?{'Content-Type':'application/json'}:{}),...(csrf?{'X-CSRF-Token':csrf}:{})},body:body?JSON.stringify(body):undefined});const v=await r.json();if(!r.ok)throw Object.assign(new Error(v.code||r.statusText),v);return v;}
 open(onMessage,onClose){const ws=new WebSocket(location.origin.replace('http','ws')+'/api/v1/connect');ws.onmessage=e=>onMessage(JSON.parse(e.data));ws.onclose=onClose;return ws;}
}
export class Client {
 constructor(transport=new HttpTransport()){this.transport=transport;this.view=null;this.connected=false;this.pending=new Map();}
 async login(loginName,password){this.csrf=(await this.transport.request('login',{method:'POST',body:{loginName,password}})).csrf;this.connect();}
 async resume(){this.csrf=(await this.transport.request('me')).csrf;this.connect();}
 connect(){this.stopped=false;this.parts=null;this.socket=this.transport.open(m=>{
  if(m.type==='reset'){this.view=null;this.connected=false;this.onChange?.();}
  if(m.type==='snapshot.begin'&&Number.isInteger(m.parts)&&m.parts>0&&m.parts<=128)this.parts={id:m.id,count:m.parts,values:Array(m.parts).fill(null)};
  if(m.type==='snapshot.part'&&this.parts?.id===m.id)this.parts.values[m.index]=m.data;
  if(m.type==='snapshot.end'&&this.parts?.id===m.id){if(this.parts.values.length===this.parts.count&&this.parts.values.every(x=>typeof x==='string')){this.view=JSON.parse(this.parts.values.join(''));this.connected=true;this.onChange?.();}this.parts=null;}
 },()=>{this.connected=false;this.view=null;this.parts=null;this.onChange?.();if(!this.stopped)this.timer=setTimeout(()=>this.connect(),1500);});}
 async command(op,args,id=crypto.randomUUID()){
  if(!this.connected)throw new Error('DISCONNECTED');const v=this.view;let m=this.pending.get(id);
  if(m&&(m.payload.op!==op||JSON.stringify(m.payload.args)!==JSON.stringify(args)))throw new Error('COMMAND_ID_CONFLICT');if(!m){m={protocolVersion:1,type:'command',requestId:crypto.randomUUID(),roomId:v.roomId,payload:{commandId:id,runId:v.runId,authorityEpoch:v.authorityEpoch,catalogRevision:v.catalog.revision,rulesetRevision:v.catalog.rulesetRevision,expectedViews:op.startsWith('chat.')?{}:Object.fromEntries(Object.values(v.entities).filter(e=>JSON.stringify(args).includes(JSON.stringify(e.instanceId))).map(e=>[e.instanceId,e.viewToken])),op,args:structuredClone(args)}};this.pending.set(id,m);}
  try{const r=await this.transport.request('commands',{method:'POST',csrf:this.csrf,body:m});return r;}catch(e){e.commandId=id;throw e;}
 }
 async receipt(id){return this.transport.request('receipts/'+encodeURIComponent(id));}
 async chatMembers(){return this.transport.request('chat/members');}
 async chatHistory(channelId,{before,limit=50}={}){return this.transport.request('chat/history',{method:'POST',csrf:this.csrf,body:{channelId,...(before!==undefined?{before}:{}),limit}});}
 async sendChat(channelId,text,options={},id=crypto.randomUUID()){return this.command('chat.message.send',{...options,channelId,text},id);}
 async openDirect(accountId,id=crypto.randomUUID()){return this.command('chat.direct.open',{accountId},id);}
 async markChatRead(channelId,sequence,id=crypto.randomUUID()){return this.command('chat.read',{channelId,sequence},id);}
 async calculate(rule,input){return this.transport.request('calculate',{method:'POST',csrf:this.csrf,body:{rule,input}});}
 async logout(){this.stopped=true;clearTimeout(this.timer);await this.transport.request('logout',{method:'POST',csrf:this.csrf});this.socket?.close();this.view=null;this.connected=false;this.pending.clear();this.onChange?.();}
}
