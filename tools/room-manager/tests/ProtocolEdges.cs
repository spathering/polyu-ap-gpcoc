using System;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Net.Sockets;
using System.Text;
using System.Threading.Tasks;
using RoomManager;
class ProtocolEdges {
 static int count;static void Assert(bool c,string text){if(!c)throw new Exception(text);count++;Console.WriteLine("PASS "+text);}
 static async Task Run(string[] args){
  var cookies=new CookieContainer();using(var http=new HttpClient(new HttpClientHandler {CookieContainer=cookies,UseProxy=false,AllowAutoRedirect=false})){http.BaseAddress=new Uri(args[0]);http.DefaultRequestHeaders.Add("Origin",args[0]);var login=await http.PostAsync("api/v1/login",new StringContent(J.Text(J.Obj("loginName","kp","password",args[1])),Encoding.UTF8,"application/json"));var parsed=J.Parse(await login.Content.ReadAsStringAsync());var missing=await http.PostAsync("api/v1/backup",new StringContent("{}",Encoding.UTF8,"application/json"));Assert(!missing.IsSuccessStatusCode,"有效 Cookie 但缺 CSRF 被拒绝");http.DefaultRequestHeaders.Add("X-CSRF-Token",J.S(parsed,"csrf"));http.DefaultRequestHeaders.Remove("Origin");http.DefaultRequestHeaders.Add("Origin","http://evil.invalid");var bad=await http.PostAsync("api/v1/backup",new StringContent("{}",Encoding.UTF8,"application/json"));Assert(!bad.IsSuccessStatusCode,"错误 Origin 被拒绝");http.DefaultRequestHeaders.Remove("Origin");http.DefaultRequestHeaders.Add("Origin",args[0]);await http.PostAsync("api/v1/logout",new StringContent("{}",Encoding.UTF8,"application/json"));Assert(!(await http.GetAsync("api/v1/admin")).IsSuccessStatusCode,"会话注销后管理查询拒绝");}
  var listener=new TcpListener(IPAddress.Loopback,0);listener.Start();int port=((IPEndPoint)listener.LocalEndpoint).Port;var server=Task.Run(async()=>{using(var socket=await listener.AcceptTcpClientAsync()){var stream=socket.GetStream();var buffer=new byte[8192];await stream.ReadAsync(buffer,0,buffer.Length);byte[] response=Encoding.ASCII.GetBytes("HTTP/1.1 302 Found\r\nLocation: http://127.0.0.1:1/\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}");await stream.WriteAsync(response,0,response.Length);}});using(var redirect=new ApiClient("http://127.0.0.1:"+port)){try{await redirect.Login("kp",args[1]);throw new Exception("未拒绝跳转");}catch(ApiException e){Assert(e.Status==302,"连接跳转不跟随");}}await server;listener.Stop();
  using(var unavailable=new ApiClient("http://127.0.0.1:"+port)){bool failed=false;try{await unavailable.Login("kp",args[1]);}catch(HttpRequestException){failed=true;}Assert(failed&&!unavailable.Connected&&unavailable.View==null,"服务未启动没有半份会话");}
  var cfg=Path.Combine(args[2],"options.json");File.WriteAllText(cfg,J.Text(J.Obj("observationLimit",2001)));try{Options.Load(cfg);throw new Exception("配置限额未校验");}catch(ApiException){Assert(true,"配置限额拒绝");}finally{Options.ObservationLimit=2000;}
  File.WriteAllText(Path.Combine(args[2],"protocol-edges.json"),J.Pretty(J.Obj("passed",count,"failed",0)));
 }
 static int Main(string[] args){try{Run(args).GetAwaiter().GetResult();return 0;}catch(Exception ex){Console.WriteLine(ex);return 1;}}
}
