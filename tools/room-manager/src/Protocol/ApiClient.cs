using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
namespace RoomManager {
 public sealed class ApiClient:IDisposable {
  public readonly Uri Origin;readonly HttpClient http;readonly CookieContainer cookies=new CookieContainer();readonly CancellationTokenSource stop=new CancellationTokenSource();readonly object gate=new object();
  object view;public object Contracts {get;private set;}public string Csrf {get;private set;}public string Account {get;private set;}
  public volatile bool Connected;public volatile string LastError="";public int Segment {get;private set;}public Task Receiver {get;private set;}
  public object View {get {lock(gate)return view==null?null:J.Clone(view);}}
  public static Uri ValidateOrigin(string address){Uri u;if(!Uri.TryCreate(address,UriKind.Absolute,out u)||u.Scheme!="http"||(u.Host!="127.0.0.1"&&u.Host!="localhost")||u.AbsolutePath!="/"||u.Query!=""||u.Fragment!=""||u.UserInfo!="")throw new ApiException("仅支持 http://127.0.0.1:端口 或 http://localhost:端口");return u;}
  public ApiClient(string address){Origin=ValidateOrigin(address);var handler=new HttpClientHandler {CookieContainer=cookies,UseCookies=true,AllowAutoRedirect=false,UseProxy=false};http=new HttpClient(handler);http.BaseAddress=Origin;http.Timeout=TimeSpan.FromSeconds(15);}
  public async Task<object> Request(string path,string method="GET",object body=null,byte[] raw=null,string fileName=null,string visibility="public"){
   using(var req=new HttpRequestMessage(new HttpMethod(method),"api/v1/"+path)){
    req.Headers.TryAddWithoutValidation("Origin",Origin.GetLeftPart(UriPartial.Authority));if(Csrf!=null)req.Headers.TryAddWithoutValidation("X-CSRF-Token",Csrf);
    if(raw!=null){if(raw.Length>10*1024*1024)throw new ApiException("LIMIT_EXCEEDED");req.Content=new ByteArrayContent(raw);req.Headers.TryAddWithoutValidation("x-asset-name",Uri.EscapeDataString(fileName??"asset"));req.Headers.TryAddWithoutValidation("x-asset-visibility",visibility);}
    else if(body!=null){string json=J.Text(body);if(Encoding.UTF8.GetByteCount(json)>65536)throw new ApiException("LIMIT_EXCEEDED：命令不得超过 64 KiB");req.Content=new StringContent(json,Encoding.UTF8,"application/json");}
    using(var response=await http.SendAsync(req,HttpCompletionOption.ResponseHeadersRead,stop.Token).ConfigureAwait(false)){
     using(var linked=CancellationTokenSource.CreateLinkedTokenSource(stop.Token)){linked.CancelAfter(TimeSpan.FromSeconds(15));byte[] data=await BoundedRead(await response.Content.ReadAsStreamAsync().ConfigureAwait(false),16*1024*1024,linked.Token).ConfigureAwait(false);
      object result;try{result=J.Parse(Encoding.UTF8.GetString(data));}catch{throw new ApiException("INVALID_SERVER_RESPONSE",(int)response.StatusCode);}
      if(!response.IsSuccessStatusCode)throw new ApiException(J.S(result,"code","HTTP_"+(int)response.StatusCode),(int)response.StatusCode);return result;
     }
    }
   }
  }
  static async Task<byte[]> BoundedRead(Stream input,int limit,CancellationToken ct){using(input)using(var output=new MemoryStream()){byte[] buffer=new byte[8192];int n;while((n=await input.ReadAsync(buffer,0,buffer.Length,ct).ConfigureAwait(false))>0){if(output.Length+n>limit)throw new ApiException("RESPONSE_TOO_LARGE");output.Write(buffer,0,n);}return output.ToArray();}}
  public async Task<byte[]> Download(string id){using(var req=new HttpRequestMessage(HttpMethod.Get,"api/v1/assets/"+Uri.EscapeDataString(id)))using(var response=await http.SendAsync(req,HttpCompletionOption.ResponseHeadersRead,stop.Token).ConfigureAwait(false)){if(!response.IsSuccessStatusCode)throw new ApiException("DOWNLOAD_DENIED",(int)response.StatusCode);using(var linked=CancellationTokenSource.CreateLinkedTokenSource(stop.Token)){linked.CancelAfter(15000);return await BoundedRead(await response.Content.ReadAsStreamAsync().ConfigureAwait(false),10*1024*1024,linked.Token).ConfigureAwait(false);}}}
  static void CheckView(object v){if(J.S(v,"role")!="kp")throw new ApiException("需要 KP 权限",403);foreach(string key in new[]{"roomId","runId","authorityEpoch","authorizationEpoch","accountId","entities","catalog"})if(!J.D(v).ContainsKey(key))throw new ApiException("PROTOCOL_UNSUPPORTED");}
  public async Task Login(string account,string password){var cap=await Request("capabilities");if(J.I(cap,"protocolVersion")!=1)throw new ApiException("PROTOCOL_UNSUPPORTED");var result=await Request("login","POST",J.Obj("loginName",account,"password",password));Csrf=J.S(result,"csrf");var v=await Request("view");CheckView(v);Account=J.S(v,"accountId");Contracts=await Request("contracts");if(J.I(Contracts,"protocolVersion")!=1||J.D(J.Get(Contracts,"operations")).Count==0)throw new ApiException("PROTOCOL_UNSUPPORTED");lock(gate)view=v;Receiver=Task.Run((Func<Task>)ReceiveLoop);}
  public async Task<object> Admin(){var result=await Request("admin");var v=await Request("view");CheckView(v);var prior=View;if(prior!=null&&(J.S(v,"accountId")!=Account||J.S(v,"authorizationEpoch")!=J.S(prior,"authorizationEpoch")))throw new ApiException("AUTH_RESET",403);return result;}
  async Task ReceiveLoop(){int delay=500;while(!stop.IsCancellationRequested){Connected=false;lock(gate){Segment++;view=null;}try{using(var ws=new ClientWebSocket()){ws.Options.Cookies=cookies;ws.Options.SetRequestHeader("Origin",Origin.GetLeftPart(UriPartial.Authority));ws.Options.KeepAliveInterval=TimeSpan.FromSeconds(10);var uri=new UriBuilder(Origin){Scheme="ws",Path="api/v1/connect"}.Uri;using(var linked=CancellationTokenSource.CreateLinkedTokenSource(stop.Token)){linked.CancelAfter(10000);await ws.ConnectAsync(uri,linked.Token).ConfigureAwait(false);}var assembler=new SnapshotAssembler();byte[] buffer=new byte[32768];string authEpoch=null;string authority=null;
    while(!stop.IsCancellationRequested&&ws.State==WebSocketState.Open){using(var data=new MemoryStream()){WebSocketReceiveResult r;do{r=await ws.ReceiveAsync(new ArraySegment<byte>(buffer),stop.Token).ConfigureAwait(false);if(r.MessageType==WebSocketMessageType.Close)throw new ApiException(r.CloseStatus==WebSocketCloseStatus.MessageTooBig?"SNAPSHOT_TOO_LARGE":"连接中断");if(r.MessageType!=WebSocketMessageType.Text||data.Length+r.Count>256*1024)throw new ApiException("WS_INVALID");data.Write(buffer,0,r.Count);}while(!r.EndOfMessage);var next=assembler.Accept(J.Parse(Encoding.UTF8.GetString(data.ToArray())));if(next!=null){CheckView(next);if(J.S(next,"accountId")!=Account)throw new ApiException("AUTH_RESET",403);string epoch=J.S(next,"authorizationEpoch");if(authEpoch!=null&&epoch!=authEpoch)throw new ApiException("AUTH_RESET",403);if(authority!=null&&authority!=J.S(next,"authorityEpoch")){lock(gate)Segment++;}authEpoch=epoch;authority=J.S(next,"authorityEpoch");lock(gate)view=next;LastError="";Connected=true;delay=500;}}}
   }}catch(OperationCanceledException){if(stop.IsCancellationRequested)break;LastError="连接超时";}catch(ApiException e){LastError=e.Message;if(e.Status==403||e.Message=="AUTH_RESET"||e.Message=="需要 KP 权限"){stop.Cancel();}}catch(Exception){LastError="连接中断，正在重连";}finally{Connected=false;lock(gate)view=null;}try{await Task.Delay(delay,stop.Token).ConfigureAwait(false);}catch(OperationCanceledException){break;}delay=Math.Min(delay*2,5000);}}
  public object Envelope(string op,object args,object tokens=null){var v=View;if(!Connected||v==null)throw new ApiException("DISCONNECTED");if(!J.D(J.Get(Contracts,"operations")).ContainsKey(op))throw new ApiException("UNKNOWN_OPERATION");return J.Obj("protocolVersion",1,"type","command","requestId",Guid.NewGuid().ToString("N"),"roomId",J.Get(v,"roomId"),"payload",J.Obj("commandId",Guid.NewGuid().ToString("N"),"authorityEpoch",J.Get(v,"authorityEpoch"),"runId",J.Get(v,"runId"),"catalogRevision",J.Get(J.Get(v,"catalog"),"revision"),"rulesetRevision",J.Get(J.Get(v,"catalog"),"rulesetRevision"),"expectedViews",tokens??J.Obj(),"op",op,"args",J.Clone(args)));}
  public Task<object> Send(object envelope){if(!Connected)throw new ApiException("DISCONNECTED");return Request("commands","POST",envelope);}
  public Task<object> Receipt(string id){return Request("receipts/"+Uri.EscapeDataString(id));}
  public async Task Logout(){try{if(Csrf!=null)await Request("logout","POST",J.Obj());}finally{Dispose();}}
  public void Dispose(){stop.Cancel();Connected=false;lock(gate)view=null;Csrf=null;http.Dispose();}
 }
}
