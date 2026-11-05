using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Diagnostics;
using System.Management;
using System.Security.Cryptography;
using System.Web.Script.Serialization;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Drawing;

internal sealed class PackService {
    internal readonly string Pack, Fingerprint, Origin;
    internal readonly int Port;
    internal string Data;
    internal static readonly JavaScriptSerializer Json=new JavaScriptSerializer();
    internal PackService(int port,string data) {
        Pack=Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory).TrimEnd('\\','/');Port=port;
        Data=Path.GetFullPath(data??Path.Combine(Pack,"runtime","room"));Origin="http://127.0.0.1:"+port;
        using(var sha=SHA256.Create())Fingerprint=BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(Pack.ToLowerInvariant()))).Replace("-","").ToLowerInvariant();
    }
    internal static string Quote(string value) { // Windows CRT argument quoting
        var b=new StringBuilder("\"");int n=0;
        foreach(char c in value){if(c=='\\'){n++;continue;}b.Append('\\',c=='"'?n*2+1:n);b.Append(c);n=0;}
        return b.Append('\\',n*2).Append('"').ToString();
    }
    Dictionary<string,object> Request(string route,string key=null) {
        var r=(HttpWebRequest)WebRequest.Create(Origin+route);r.Proxy=null;r.AllowAutoRedirect=false;r.Timeout=key==null?1500:25000;r.ReadWriteTimeout=r.Timeout;
        if(key!=null){r.Method="POST";r.ContentType="application/json";r.Headers["X-Mini-Pack-Control"]=key;byte[] body=Encoding.UTF8.GetBytes("{}");r.ContentLength=body.Length;using(var stream=r.GetRequestStream())stream.Write(body,0,body.Length);}
        using(var response=r.GetResponse())using(var reader=new StreamReader(response.GetResponseStream(),Encoding.UTF8))return Json.Deserialize<Dictionary<string,object>>(reader.ReadToEnd());
    }
    internal Dictionary<string,object> Info() {
        try {
            var value=Request("/launcher/info");
            if((string)value["packId"]!="mini-detective-pack"||(string)value["workspace"]!=Fingerprint)throw new InvalidOperationException("端口属于其他配置包或工作区，已拒绝操作。");
            return value;
        }catch(WebException e){if(e.Response!=null)throw new InvalidOperationException("该端口正在提供其他服务，已拒绝操作。");return null;}
    }
    bool PortBusy(){foreach(var endpoint in System.Net.NetworkInformation.IPGlobalProperties.GetIPGlobalProperties().GetActiveTcpListeners())if(endpoint.Port==Port&&(IPAddress.IsLoopback(endpoint.Address)||endpoint.Address.Equals(IPAddress.Any)||endpoint.Address.Equals(IPAddress.IPv6Any)))return true;return false;}
    static string[] Arguments(string command) {
        int count;IntPtr ptr=CommandLineToArgvW(command,out count);if(ptr==IntPtr.Zero)return new string[0];
        try{var values=new string[count];for(int i=0;i<count;i++)values[i]=System.Runtime.InteropServices.Marshal.PtrToStringUni(System.Runtime.InteropServices.Marshal.ReadIntPtr(ptr,i*IntPtr.Size));return values;}finally{LocalFree(ptr);}
    }
    [System.Runtime.InteropServices.DllImport("shell32.dll",CharSet=System.Runtime.InteropServices.CharSet.Unicode)]static extern IntPtr CommandLineToArgvW(string text,out int argc);
    [System.Runtime.InteropServices.DllImport("kernel32.dll")]static extern IntPtr LocalFree(IntPtr ptr);
    internal Process Supervisor(int expected=0) {
        Process found=null;
        using(var search=new ManagementObjectSearcher("SELECT ProcessId,ExecutablePath,CommandLine FROM Win32_Process WHERE Name='KP主持人.exe' OR Name='PL1观察员.exe' OR Name='PL2护卫.exe' OR Name='PL3文献员.exe' OR Name='PL4医护员.exe'"))foreach(ManagementObject row in search.Get()) {
            try {
                int pid=Convert.ToInt32(row["ProcessId"]);if(expected>0&&pid!=expected)continue;
                string executable=Convert.ToString(row["ExecutablePath"]);
                if(!String.Equals(Path.GetDirectoryName(executable),Pack,StringComparison.OrdinalIgnoreCase))continue;
                string[] args=Arguments(Convert.ToString(row["CommandLine"]));bool service=false;int port=8888;string actualData=Path.Combine(Pack,"runtime","room");
                for(int i=1;i<args.Length;i++){if(args[i]=="--service")service=true;else if(args[i]=="--port"&&i+1<args.Length)port=Int32.Parse(args[++i]);else if(args[i]=="--data-dir"&&i+1<args.Length)actualData=Path.GetFullPath(args[++i]);}
                if(!service||port!=Port)continue;
                if(found!=null)throw new InvalidOperationException("发现多个匹配的监督进程，请先核对实例。");
                found=Process.GetProcessById(pid);DateTime started=found.StartTime;Data=actualData;
            }catch(ArgumentException){}catch(System.ComponentModel.Win32Exception){}
        }
        return found;
    }
    internal Dictionary<string,object> Status() {
        var info=Info();var supervisor=Supervisor(info==null?0:Convert.ToInt32(info["supervisorPid"]));
        if(info!=null){info["state"]="running";if(info.ContainsKey("dataDirectory")&&info["dataDirectory"]!=null)Data=(string)info["dataDirectory"];return info;}
        if(supervisor!=null)return new Dictionary<string,object>{{"state","starting"},{"supervisorPid",supervisor.Id}};
        return new Dictionary<string,object>{{"state",PortBusy()?"occupied":"stopped"}};
    }
    internal void Start() {
        using(var mutex=new Mutex(false,"Local\\MiniDetectiveStartup-"+Fingerprint+"-"+Port)) {
            bool held=false;
            try {
                try{held=mutex.WaitOne(TimeSpan.FromSeconds(70));}catch(AbandonedMutexException){held=true;}
                if(!held)throw new Exception("其他入口正在操作服务，请稍后重试。");
                var current=Status();string state=(string)current["state"];
                if(state=="running")return;
                if(state=="occupied")throw new Exception("端口已被其他程序使用。");
                if(state=="stopped") {
                    var start=new ProcessStartInfo(Path.Combine(Pack,"KP主持人.exe"),"--service --port "+Port+" --data-dir "+Quote(Data));
                    start.UseShellExecute=true;start.WindowStyle=ProcessWindowStyle.Hidden;start.WorkingDirectory=Pack;
                    Process.Start(start);
                }
                for(int i=0;i<120;i++){Thread.Sleep(250);if(Info()!=null)return;}
                throw new Exception("服务未就绪，请查看 runtime/launcher.log。");
            }finally{if(held)mutex.ReleaseMutex();}
        }
    }
    static List<Process> Tree(int root) {
        var result=new List<Process>();var pending=new Queue<int>();pending.Enqueue(root);
        while(pending.Count>0){int parent=pending.Dequeue();using(var search=new ManagementObjectSearcher("SELECT ProcessId FROM Win32_Process WHERE ParentProcessId="+parent))foreach(ManagementObject row in search.Get()){
            try{var p=Process.GetProcessById(Convert.ToInt32(row["ProcessId"]));DateTime t=p.StartTime;result.Add(p);pending.Enqueue(p.Id);}catch(ArgumentException){}
        }}return result;
    }
    static void KillCaptured(Process process) {
        // Process object pins identity; compare start time again before any kill.
        DateTime start=process.StartTime;
        try{using(var current=Process.GetProcessById(process.Id)){if(current.StartTime==start&&!current.HasExited)current.Kill();}}catch(ArgumentException){}catch(InvalidOperationException){}
    }
    internal void Stop() {
        var info=Info();if(info!=null&&info.ContainsKey("dataDirectory")&&info["dataDirectory"]!=null)Data=(string)info["dataDirectory"];int id=info==null?0:Convert.ToInt32(info["supervisorPid"]);var supervisor=Supervisor(id);
        if(info==null&&supervisor==null){if(PortBusy())throw new Exception("端口被其他程序占用，已拒绝关闭。");return;}
        string recordFile=Path.Combine(Pack,"runtime","service-control-"+Port+".json");
        if(info!=null&&info.ContainsKey("localStop")&&(bool)info["localStop"]&&File.Exists(recordFile)) {
            var record=Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(recordFile,Encoding.UTF8));
            if((string)record["workspace"]!=Fingerprint||Convert.ToInt32(record["pid"])!=Convert.ToInt32(info["pid"]))throw new Exception("本机控制记录已过期，请刷新状态。");
            byte[] bytes=ProtectedData.Unprotect(Convert.FromBase64String((string)record["protectedKey"]),null,DataProtectionScope.CurrentUser);
            string key=Encoding.UTF8.GetString(bytes);Array.Clear(bytes,0,bytes.Length);
            var children=Tree(Convert.ToInt32(info["pid"]));
            var answer=Request("/launcher/stop",key);key=null;
            if(!(bool)answer["stopping"])throw new Exception("服务未接受停止请求。");
            for(int i=0;i<100;i++){Thread.Sleep(200);if(Info()==null){for(int j=children.Count-1;j>=0;j--)try{if(!children[j].HasExited)KillCaptured(children[j]);}catch(InvalidOperationException){}if(supervisor!=null)supervisor.WaitForExit(10000);return;}}
            throw new Exception("停止尚未完成，请稍后刷新。");
        }
        if(supervisor==null)throw new Exception("此旧服务未由账号入口监督启动，请在原终端按 Ctrl+C 停止后重新启动。");
        // Backwards compatibility: only the verified native supervisor owns the
        // Windows Job that contains this pack's Python and room-host processes.
        KillCaptured(supervisor);supervisor.WaitForExit(10000);
        for(int i=0;i<50;i++){if(!PortBusy())return;Thread.Sleep(200);}
        throw new Exception("相关进程仍在退出，请刷新状态。");
    }
}

internal sealed class ServiceWindow:Form {
    readonly PackService service;readonly bool smoke;readonly string result;
    readonly Label status=new Label{AutoSize=true,Text="正在读取状态…"};
    readonly TextBox path=new TextBox{Width=610};
    readonly Button start=new Button{Text="启动服务",AutoSize=true},stop=new Button{Text="停止服务",AutoSize=true},restart=new Button{Text="重启服务",AutoSize=true};
    bool busy;
    internal ServiceWindow(PackService controller,bool test,string output) {
        service=controller;smoke=test;result=output;Text="铃蔓回转录 · 配置包服务管理";Size=new Size(780,330);MinimumSize=new Size(720,330);Font=new Font("Microsoft YaHei UI",10);
        var panel=new FlowLayoutPanel{Dock=DockStyle.Fill,Padding=new Padding(22),FlowDirection=FlowDirection.TopDown,WrapContents=false};
        panel.Controls.Add(new Label{Text="配置包后台服务",Font=new Font(Font.FontFamily,16),AutoSize=true});panel.Controls.Add(status);
        panel.Controls.Add(new Label{Text="存档目录（服务停止后可修改）",AutoSize=true});path.Text=service.Data;panel.Controls.Add(path);
        var buttons=new FlowLayoutPanel{AutoSize=true,Width=700};buttons.Controls.AddRange(new Control[]{start,stop,restart});
        var open=new Button{Text="打开 KP 页面",AutoSize=true};buttons.Controls.Add(open);panel.Controls.Add(buttons);
        panel.Controls.Add(new Label{Text="地址："+service.Origin+"\n关闭此窗口不会停止服务。停止服务会保留已提交的游戏进度。",AutoSize=true});Controls.Add(panel);
        start.Click+=async(s,e)=>await Run(()=>{service.Data=Path.GetFullPath(path.Text);service.Start();});
        stop.Click+=async(s,e)=>{if(MessageBox.Show("停止本配置包后台服务及其房间进程？页面将断开，存档保留。","停止服务",MessageBoxButtons.OKCancel)==DialogResult.OK)await Run(service.Stop);};
        restart.Click+=async(s,e)=>{if(MessageBox.Show("重启本配置包服务并保留存档？","重启服务",MessageBoxButtons.OKCancel)==DialogResult.OK)await Run(()=>{service.Stop();service.Start();});};
        open.Click+=(s,e)=>{Process.Start(new ProcessStartInfo(service.Origin+"/sessions/kp/"){UseShellExecute=true});};
        var timer=new System.Windows.Forms.Timer{Interval=2500};timer.Tick+=async(s,e)=>{if(!busy)await Run(null);};
        Shown+=async(s,e)=>{await Run(null);if(smoke){if(result!=null)File.WriteAllText(result,PackService.Json.Serialize(new{windowLoaded=true}),Encoding.UTF8);Close();}else timer.Start();};
        FormClosed+=(s,e)=>timer.Dispose();FormClosing+=(s,e)=>{if(busy&&!smoke)e.Cancel=true;};
    }
    async Task Run(Action action) {
        if(busy)return;busy=true;start.Enabled=stop.Enabled=restart.Enabled=path.Enabled=false;
        try {
            var snapshot=await Task.Run(()=>{if(action!=null)action();return service.Status();});string state=(string)snapshot["state"];
            status.Text=state=="running"?"● 服务运行中":state=="starting"?"● 服务启动中或等待响应":state=="stopped"?"○ 服务已停止":"端口被其他程序占用";
            path.Text=service.Data;start.Enabled=state=="stopped";stop.Enabled=restart.Enabled=state=="running"||state=="starting";path.Enabled=state=="stopped";
        }catch(Exception error){status.Text=error.Message;start.Enabled=stop.Enabled=restart.Enabled=true;}finally{busy=false;}
    }
}

internal static class ServiceManager {
    [STAThread] static int Main(string[] args) {
        int port=8888;string data=null,command=null,result=null;bool smoke=false;
        try {
            for(int i=0;i<args.Length;i++)switch(args[i]){
                case "--port":port=Int32.Parse(args[++i]);break;case "--data-dir":data=args[++i];break;case "--result":result=args[++i];break;
                case "--start":case "--stop":case "--restart":case "--status":command=args[i];break;case "--smoke":smoke=true;break;default:throw new ArgumentException("未知参数："+args[i]);
            }
            if(port<1024||port>65535)throw new ArgumentException("端口须在1024至65535之间。");
            var service=new PackService(port,data);
            if(command!=null){if(command=="--start")service.Start();else if(command=="--stop")service.Stop();else if(command=="--restart"){service.Stop();service.Start();}var text=PackService.Json.Serialize(service.Status());if(result!=null)File.WriteAllText(result,text,Encoding.UTF8);else Console.WriteLine(text);return 0;}
            Application.EnableVisualStyles();Application.Run(new ServiceWindow(service,smoke,result));return 0;
        }catch(Exception error){if(result!=null)File.WriteAllText(result,PackService.Json.Serialize(new{error=error.Message}),Encoding.UTF8);else if(command!=null)Console.Error.WriteLine(error.Message);else MessageBox.Show(error.Message,"配置包服务管理");return 1;}
    }
}
