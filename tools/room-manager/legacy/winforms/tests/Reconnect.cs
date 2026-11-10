using System;
using System.IO;
using System.Threading.Tasks;
using RoomManager;
class Reconnect {
 static async Task Run(string[] args){using(var c=new ApiClient(args[0])){await c.Login("kp",args[1]);for(int i=0;i<100&&!c.Connected;i++)await Task.Delay(100);if(!c.Connected)throw new Exception("初次连接失败");int old=c.Segment;string authority=J.S(c.View,"authorityEpoch");File.WriteAllText(Path.Combine(args[2],"restart.ready"),"ready");bool sawGap=false;for(int i=0;i<300;i++){if(!c.Connected&&c.View==null)sawGap=true;if(sawGap&&c.Connected&&c.Segment>old&&J.S(c.View,"authorityEpoch")!=authority){File.WriteAllText(Path.Combine(args[2],"reconnect.json"),J.Pretty(J.Obj("passed",3,"failed",0,"gapClearedView",true,"newSegment",true,"newAuthority",true)));Console.WriteLine("PASS 真实宿主重启：清空断线视图、新观察段、新 authority");return;}await Task.Delay(100);}throw new Exception("重连失败："+c.LastError);}}
 static int Main(string[] args){try{Run(args).GetAwaiter().GetResult();return 0;}catch(Exception ex){Console.WriteLine(ex);return 1;}}
}
