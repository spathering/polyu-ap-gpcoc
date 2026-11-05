using System;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Net;
using System.Threading;
using System.Security.Cryptography;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using System.Collections.Generic;

internal static class PackLauncher
{
    [StructLayout(LayoutKind.Sequential)]
    private struct BasicLimits
    {
        public long ProcessTime, JobTime;
        public uint Flags;
        public UIntPtr MinWorkingSet, MaxWorkingSet;
        public uint ActiveProcesses;
        public UIntPtr Affinity;
        public uint Priority, Scheduling;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct IoCounters
    {
        public ulong ReadOperations, WriteOperations, OtherOperations;
        public ulong ReadBytes, WriteBytes, OtherBytes;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct ExtendedLimits
    {
        public BasicLimits Basic;
        public IoCounters Io;
        public UIntPtr ProcessMemory, JobMemory, PeakProcessMemory, PeakJobMemory;
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr CreateJobObject(IntPtr attributes, string name);
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool SetInformationJobObject(IntPtr job, int informationClass,
                                                       ref ExtendedLimits information, uint size);
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
    [DllImport("kernel32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CloseHandle(IntPtr handle);

    // Held by this process only. OS closes it on exit and terminates descendants.
    // Do not explicitly close it while this launcher is itself a member of the job.
    private static IntPtr lifetimeJob;

    private static void ProtectProcessTree()
    {
        lifetimeJob = CreateJobObject(IntPtr.Zero, null);
        if (lifetimeJob == IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error());
        var limits = new ExtendedLimits();
        limits.Basic.Flags = 0x2000; // JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if (!SetInformationJobObject(lifetimeJob, 9, ref limits, (uint)Marshal.SizeOf(limits)) ||
            !AssignProcessToJobObject(lifetimeJob, Process.GetCurrentProcess().Handle))
        {
            int error = Marshal.GetLastWin32Error();
            CloseHandle(lifetimeJob);
            lifetimeJob = IntPtr.Zero;
            throw new Win32Exception(error, "无法建立启动进程的退出清理机制");
        }
    }

    private static string Quote(string value)
    {
        var output = new StringBuilder("\"");
        int slashes = 0;
        foreach (char c in value)
        {
            if (c == '\\') { slashes++; continue; }
            if (c == '"') output.Append('\\', slashes * 2 + 1);
            else output.Append('\\', slashes);
            output.Append(c);
            slashes = 0;
        }
        output.Append('\\', slashes * 2);
        return output.Append('"').ToString();
    }

    private static string FindPython(string pack)
    {
        DirectoryInfo parent = new DirectoryInfo(pack);
        while (parent != null)
        {
            string python = Path.Combine(parent.FullName, "engineering", ".venv", "Scripts", "python.exe");
            string host = Path.Combine(parent.FullName, "engineering", "backend", "scripts", "run.py");
            if (File.Exists(python) && File.Exists(host)) return python;
            parent = parent.Parent;
        }
        throw new FileNotFoundException("未找到项目运行环境。请把配置包放在 OnlineCOC 项目的 rulepacks 目录，并按工程文档准备 engineering/.venv。");
    }

    private static string Fingerprint(string pack)
    {
        using(var sha=SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(Path.GetFullPath(pack).TrimEnd('\\','/').ToLowerInvariant()))).Replace("-","").ToLowerInvariant();
    }
    private static bool Probe(string origin,string fingerprint,out bool occupied)
    {
        occupied=false;
        try {
            var request=(HttpWebRequest)WebRequest.Create(origin+"/launcher/info");request.Timeout=1200;request.Proxy=null;
            using(var response=request.GetResponse()) using(var reader=new StreamReader(response.GetResponseStream())) {
                occupied=true;
                var data=new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(reader.ReadToEnd());
                return (string)data["packId"]=="mini-detective-pack" && (string)data["workspace"]==fingerprint;
            }
        } catch(WebException e) { occupied=e.Response!=null;return false; }
        catch { occupied=true;return false; }
    }
    [STAThread]
    private static int Main(string[] args)
    {
        bool service=false;string capture=null,dataDir=null;int port=8888;
        string pack=AppDomain.CurrentDomain.BaseDirectory;
        try {
            for(int i=0;i<args.Length;i++) {
                if(args[i]=="--service")service=true;
                else if(args[i]=="--port")port=Int32.Parse(args[++i]);
                else if(args[i]=="--data-dir")dataDir=Path.GetFullPath(args[++i]);
                else if(args[i]=="--capture")capture=Path.GetFullPath(args[++i]);
                else throw new ArgumentException("未知参数："+args[i]);
            }
            if(port<1024||port>65535)throw new ArgumentException("端口须在1024至65535之间");
            string fingerprint=Fingerprint(pack),origin="http://127.0.0.1:"+port;
            if(service) {
                bool created;
                using(var lifetime=new Mutex(true,"Local\\MiniDetectiveService-"+fingerprint+"-"+port,out created)) {
                    if(!created)return 0;
                    ProtectProcessTree();
                    var command=new StringBuilder("-B ").Append(Quote(Path.Combine(pack,"tools","launch.py"))).Append(" --no-browser --port ").Append(port);
                    if(dataDir!=null)command.Append(" --data-dir ").Append(Quote(dataDir));
                    var start=new ProcessStartInfo(FindPython(pack),command.ToString());
                    start.UseShellExecute=false;start.CreateNoWindow=true;start.WorkingDirectory=pack;
                    start.RedirectStandardOutput=true;start.RedirectStandardError=true;
                    start.EnvironmentVariables["PYTHONDONTWRITEBYTECODE"]="1";
                    start.EnvironmentVariables["PYTHONIOENCODING"]="utf-8";
                    start.EnvironmentVariables["MD_LAUNCHER_PID"]=Process.GetCurrentProcess().Id.ToString();
                    string logs=Path.Combine(pack,"runtime");Directory.CreateDirectory(logs);object gate=new object();
                    DataReceivedEventHandler logger=delegate(object sender,DataReceivedEventArgs e){if(e.Data!=null)lock(gate){try{File.AppendAllText(Path.Combine(logs,"launcher.log"),DateTime.Now.ToString("s")+" "+e.Data+Environment.NewLine,Encoding.UTF8);}catch{}}};
                    using(var child=Process.Start(start)) { child.OutputDataReceived+=logger;child.ErrorDataReceived+=logger;child.BeginOutputReadLine();child.BeginErrorReadLine();child.WaitForExit();return child.ExitCode; }
                }
            }
            using(var startup=new Mutex(false,"Local\\MiniDetectiveStartup-"+fingerprint+"-"+port)) {
                bool held=false;
                try {
                    try{held=startup.WaitOne(TimeSpan.FromSeconds(70));}catch(AbandonedMutexException){held=true;}
                    if(!held)throw new Exception("正在启动服务，请稍后重试");
                    bool occupied;
                    if(!Probe(origin,fingerprint,out occupied)) {
                        if(occupied)throw new Exception("端口已被其他服务使用，未打开该页面");
                        string cmd="--service --port "+port;
                        if(dataDir!=null)cmd+=" --data-dir "+Quote(dataDir);
                        var start=new ProcessStartInfo(Application.ExecutablePath,cmd);start.UseShellExecute=false;start.CreateNoWindow=true;start.WindowStyle=ProcessWindowStyle.Hidden;start.WorkingDirectory=pack;
                        Process.Start(start);
                        bool ready=false;
                        for(int i=0;i<150;i++){Thread.Sleep(200);if(Probe(origin,fingerprint,out occupied)){ready=true;break;}if(occupied)throw new Exception("服务端口身份不匹配");}
                        if(!ready)throw new Exception("服务未能启动，请查看runtime/launcher.log");
                    }
                } finally{if(held)startup.ReleaseMutex();}
            }
#if PLAYER1
            string slot="player1";
#elif PLAYER2
            string slot="player2";
#elif PLAYER3
            string slot="player3";
#elif PLAYER4
            string slot="player4";
#else
            string slot="kp";
#endif
            string url=origin+"/sessions/"+slot+"/";
            if(capture!=null)File.WriteAllText(capture,url,new UTF8Encoding(false));
            else Process.Start(new ProcessStartInfo(url){UseShellExecute=true});
            return 0;
        } catch(Exception error) {
            if(!service) { if(capture!=null)Console.Error.WriteLine(error.Message); else MessageBox.Show(error.Message,"铃蔓回转录启动失败",MessageBoxButtons.OK,MessageBoxIcon.Error); }
            return 1;
        }
    }
}
