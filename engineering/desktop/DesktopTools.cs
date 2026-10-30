using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace OnlineCOC.Desktop {
public sealed class PythonSettings {
    public string version, archiveUrl, sha256, directory, cacheFile;
}
public sealed class DependencySettings {
    public string lockFile, environmentRoot, indexUrl, wheelDirectory;
    public bool offline;
    public string[] probeModules;
}
public sealed class ApplicationSettings {
    public string entryPoint, dataDirectory;
    public int port, startupTimeoutSeconds;
    public bool openBrowser;
}
public sealed class Settings {
    public int schemaVersion;
    public PythonSettings python;
    public DependencySettings dependencies;
    public ApplicationSettings application;
    public string logsDirectory;
}
public sealed class Options {
    public string Config;
    public bool Headless, Check, NoBrowser;
    public int RunSeconds;
    public static Options Parse(string[] args) {
        var o = new Options();
        for (int i = 0; i < args.Length; i++) {
            switch (args[i]) {
                case "--config": o.Config = args[++i]; break;
                case "--headless": o.Headless = true; break;
                case "--check": o.Check = true; break;
                case "--no-browser": o.NoBrowser = true; break;
                case "--run-seconds": o.RunSeconds = int.Parse(args[++i]); break;
                default: throw new Exception("未知参数：" + args[i]);
            }
        }
        if (o.RunSeconds < 0) throw new Exception("运行秒数不能为负数。");
        return o;
    }
}
// A job owns only processes created by this tool; closing it terminates its child tree.
public sealed class ChildJob : IDisposable {
    [StructLayout(LayoutKind.Sequential)] struct Basic {
        public long ProcessTime, JobTime;
        public uint Flags;
        public UIntPtr MinimumWorkingSet, MaximumWorkingSet;
        public uint ActiveProcessLimit;
        public UIntPtr Affinity;
        public uint Priority, Scheduling;
    }
    [StructLayout(LayoutKind.Sequential)] struct IoCounters {
        public ulong ReadOps, WriteOps, OtherOps, ReadBytes, WriteBytes, OtherBytes;
    }
    [StructLayout(LayoutKind.Sequential)] struct Extended {
        public Basic Basic;
        public IoCounters Io;
        public UIntPtr ProcessMemory, JobMemory, PeakProcessMemory, PeakJobMemory;
    }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern IntPtr CreateJobObject(IntPtr a, string name);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool SetInformationJobObject(IntPtr job, int kind, IntPtr info, uint length);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
    IntPtr handle;
    public ChildJob(Process process) {
        handle = CreateJobObject(IntPtr.Zero, null);
        if (handle == IntPtr.Zero) throw new Win32Exception();
        var data = new Extended(); data.Basic.Flags = 0x2000; // KILL_ON_JOB_CLOSE
        int size = Marshal.SizeOf(data); IntPtr memory = Marshal.AllocHGlobal(size);
        try {
            Marshal.StructureToPtr(data, memory, false);
            if (!SetInformationJobObject(handle, 9, memory, (uint)size) || !AssignProcessToJobObject(handle, process.Handle))
                throw new Win32Exception();
        } catch { Dispose(); try { process.Kill(); } catch {} throw; }
        finally { Marshal.FreeHGlobal(memory); }
    }
    public void Dispose() { if (handle != IntPtr.Zero) { CloseHandle(handle); handle = IntPtr.Zero; } }
}
public sealed class Engine : IDisposable {
    public readonly string Root, ConfigPath, LogPath, EnvironmentDirectory;
    public readonly Settings Config;
    public readonly ManualResetEvent Stop = new ManualResetEvent(false);
    public Action<string> OnLog;
    public Action OnReady;
    public Func<string> AskPassword;
    readonly Options options;
    readonly StreamWriter log;
    readonly object logLock = new object();
    bool disposed;
    readonly string fingerprint;
    public string Url { get { return "http://127.0.0.1:" + Config.application.port; } }
    public Engine(Options options) {
        this.options = options;
        Root = Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory).TrimEnd(Path.DirectorySeparatorChar);
        ConfigPath = Path.GetFullPath(options.Config ?? Path.Combine(Root, "launcher-config.json"));
        Config = new JavaScriptSerializer().Deserialize<Settings>(File.ReadAllText(ConfigPath, Encoding.UTF8));
        Validate();
        string lockPath = Inside(Config.dependencies.lockFile);
        fingerprint = Hash(Encoding.UTF8.GetBytes(Root.ToLowerInvariant() + "\n" + Config.python.version + "\n" + Config.python.sha256 + "\n" + File.ReadAllText(lockPath)));
        EnvironmentDirectory = Path.Combine(Inside(Config.dependencies.environmentRoot), fingerprint.Substring(0, 20));
        string logs = Inside(Config.logsDirectory); Directory.CreateDirectory(logs);
        LogPath = Path.Combine(logs, DateTime.Now.ToString("yyyyMMdd-HHmmss") + "-" + Process.GetCurrentProcess().Id + ".log");
        log = new StreamWriter(LogPath, false, new UTF8Encoding(false)); log.AutoFlush = true;
    }
    void Validate() {
        if (Config == null || Config.schemaVersion != 1 || Config.python == null || Config.dependencies == null || Config.application == null)
            throw new Exception("配置格式不支持。请检查 launcher-config.json。");
        if (!Environment.Is64BitOperatingSystem || !Environment.Is64BitProcess) throw new Exception("需要 Windows x64。");
        if (!Regex.IsMatch(Config.python.version ?? "", @"^\d+\.\d+\.\d+$") || !Regex.IsMatch(Config.python.sha256 ?? "", @"^[0-9a-fA-F]{64}$"))
            throw new Exception("Python 版本或 SHA-256 配置无效。");
        SecureUrl(Config.python.archiveUrl); SecureUrl(Config.dependencies.indexUrl);
        if (Config.application.port < 1024 || Config.application.port > 65535 || Config.application.startupTimeoutSeconds < 5 || Config.application.startupTimeoutSeconds > 600)
            throw new Exception("端口或启动超时配置无效。");
        foreach (string path in new [] {Config.python.directory, Config.python.cacheFile, Config.dependencies.lockFile, Config.dependencies.environmentRoot,
                     Config.dependencies.wheelDirectory, Config.application.entryPoint, Config.application.dataDirectory, Config.logsDirectory}) Inside(path);
        if (Config.dependencies.probeModules == null || Config.dependencies.probeModules.Length == 0) throw new Exception("缺少依赖导入检查项。");
        foreach (string module in Config.dependencies.probeModules) if (!Regex.IsMatch(module, @"^[A-Za-z0-9_.]+$")) throw new Exception("依赖检查模块名无效。");
        if (!File.Exists(Inside(Config.application.entryPoint))) throw new Exception("缺少工程代码。两个 exe 必须放在完整工程根目录。");
    }
    static void SecureUrl(string text) {
        Uri uri;
        if (!Uri.TryCreate(text, UriKind.Absolute, out uri) || uri.Scheme != "https" || uri.UserInfo.Length != 0)
            throw new Exception("下载地址和软件源须为不含账号密码的 HTTPS URL。");
    }
    public string Inside(string relative) {
        if (string.IsNullOrWhiteSpace(relative) || Path.IsPathRooted(relative)) throw new Exception("配置路径必须相对工程根目录。");
        string path = Path.GetFullPath(Path.Combine(Root, relative.Replace('/', Path.DirectorySeparatorChar)));
        if (!path.StartsWith(Root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) throw new Exception("配置路径越出工程目录：" + relative);
        return path;
    }
    public static string Hash(byte[] bytes) { using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant(); }
    static string FileHash(string path) { using (var sha = SHA256.Create()) using (var stream = File.OpenRead(path)) return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant(); }
    public static string Quote(string text) {
        // Windows CommandLineToArgv/CRT escaping; no shell interpolation.
        var b = new StringBuilder("\""); int slashes = 0;
        foreach (char c in text) {
            if (c == '\\') { slashes++; continue; }
            if (c == '"') { b.Append('\\', slashes * 2 + 1).Append('"'); slashes = 0; continue; }
            b.Append('\\', slashes).Append(c); slashes = 0;
        }
        return b.Append('\\', slashes * 2).Append('"').ToString();
    }
    public void Write(string message) {
        if (message == null) return;
        lock (logLock) { if (disposed) return; log.WriteLine(DateTime.Now.ToString("HH:mm:ss") + " " + message); }
        Console.WriteLine(message); if (OnLog != null) OnLog(message);
    }
    Process Start(string executable, IEnumerable<string> arguments, string password = null) {
        var info = new ProcessStartInfo(executable, string.Join(" ", arguments.Select(Quote)));
        info.WorkingDirectory = Root; info.UseShellExecute = false; info.CreateNoWindow = true;
        info.RedirectStandardOutput = true; info.RedirectStandardError = true; info.RedirectStandardInput = true;
        info.StandardOutputEncoding = Encoding.UTF8; info.StandardErrorEncoding = Encoding.UTF8;
        info.EnvironmentVariables["PYTHONUTF8"] = "1"; info.EnvironmentVariables["PYTHONUNBUFFERED"] = "1";
        info.EnvironmentVariables.Remove("PYTHONHOME"); info.EnvironmentVariables.Remove("PYTHONPATH");
        info.EnvironmentVariables.Remove("ONLINECOC_BOOTSTRAP_PASSWORD");
        if (password != null) info.EnvironmentVariables["ONLINECOC_BOOTSTRAP_PASSWORD"] = password;
        var process = new Process(); process.StartInfo = info; process.Start(); return process;
    }
    int Run(string executable, IEnumerable<string> arguments) {
        if (Stop.WaitOne(0)) throw new OperationCanceledException();
        using (var process = Start(executable, arguments)) using (var job = new ChildJob(process)) {
            process.OutputDataReceived += (s,e) => Write(e.Data); process.ErrorDataReceived += (s,e) => Write(e.Data);
            process.BeginOutputReadLine(); process.BeginErrorReadLine();
            while (!process.WaitForExit(100)) if (Stop.WaitOne(0)) throw new OperationCanceledException();
            process.WaitForExit(); return process.ExitCode;
        }
    }
    void MustRun(string executable, params string[] arguments) {
        int code = Run(executable, arguments); if (code != 0) throw new Exception("子进程执行失败，退出码 " + code + "。详情见日志。");
    }
    string PythonExe { get { return Path.Combine(Inside(Config.python.directory), "python.exe"); } }
    string VenvPython { get { return Path.Combine(EnvironmentDirectory, "Scripts", "python.exe"); } }
    string ReadyFile { get { return Path.Combine(EnvironmentDirectory, "onlinecoc-ready.txt"); } }
    bool IsReady() { return File.Exists(VenvPython) && File.Exists(ReadyFile) && File.ReadAllText(ReadyFile).Trim() == fingerprint; }
    void CheckPython(string exe) {
        MustRun(exe, "-I", "-c", "import sys,struct; assert '.'.join(map(str,sys.version_info[:3])) == '" + Config.python.version + "' and struct.calcsize('P') == 8; print('PYTHON_OK')");
    }
    void BootstrapPython() {
        if (File.Exists(PythonExe)) { CheckPython(PythonExe); return; }
        string target = Inside(Config.python.directory), archive = Inside(Config.python.cacheFile);
        if (Directory.Exists(target)) throw new Exception("Python 目录不完整，请保留日志并移走该目录后重试：" + target);
        Directory.CreateDirectory(Path.GetDirectoryName(archive));
        if (!File.Exists(archive)) {
            if (Config.dependencies.offline) throw new Exception("离线模式缺少 Python 压缩包：" + archive);
            Write("下载 Python " + Config.python.version + " 官方完整运行时……");
            string temporary = archive + "." + Guid.NewGuid().ToString("N") + ".partial";
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
            using (var client = new WebClient()) using (var completed = new ManualResetEvent(false)) {
                Exception failure = null; bool cancelled = false;
                client.DownloadFileCompleted += (s,e) => { failure = e.Error; cancelled = e.Cancelled; completed.Set(); };
                client.DownloadFileAsync(new Uri(Config.python.archiveUrl), temporary);
                while (!completed.WaitOne(100)) if (Stop.WaitOne(0)) client.CancelAsync();
                if (cancelled || Stop.WaitOne(0)) throw new OperationCanceledException();
                if (failure != null) throw new Exception("下载失败：" + failure.Message, failure);
            }
            if (!string.Equals(FileHash(temporary), Config.python.sha256, StringComparison.OrdinalIgnoreCase)) throw new Exception("Python 下载摘要不匹配，未执行下载内容。");
            File.Move(temporary, archive);
        }
        if (!string.Equals(FileHash(archive), Config.python.sha256, StringComparison.OrdinalIgnoreCase)) throw new Exception("Python 缓存摘要不匹配：" + archive);
        string staging = target + ".extracting-" + Guid.NewGuid().ToString("N"); Directory.CreateDirectory(staging);
        Write("校验通过，展开项目内 Python……");
        using (var zip = ZipFile.OpenRead(archive)) foreach (var entry in zip.Entries) {
            if (Stop.WaitOne(0)) throw new OperationCanceledException();
            string dest = Path.GetFullPath(Path.Combine(staging, entry.FullName));
            if (!dest.StartsWith(staging + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) throw new Exception("压缩包包含越界路径。");
            if (entry.Name.Length == 0) Directory.CreateDirectory(dest);
            else { Directory.CreateDirectory(Path.GetDirectoryName(dest)); entry.ExtractToFile(dest, false); }
        }
        CheckPython(Path.Combine(staging, "python.exe"));
        // Both resolved paths are under the validated project runtime directory.
        Directory.Move(staging, target);
    }
    public void Verify() {
        if (!IsReady()) throw new Exception("依赖尚未安装，或锁文件/工程位置已变化。请运行安装依赖.exe。");
        CheckPython(VenvPython);
        MustRun(VenvPython, "-I", Inside("engineering/desktop/verify_environment.py"), ConfigPath, Root);
        MustRun(VenvPython, "-I", "-m", "pip", "check");
    }
    public void Install() {
        BootstrapPython();
        if (IsReady()) {
            try { Verify(); Write("依赖已就绪，无需重复安装。"); return; }
            catch (OperationCanceledException) { throw; }
            catch (Exception) { Write("现有依赖校验未通过，按锁文件修复……"); File.Delete(ReadyFile); }
        }
        Write("建立独立依赖环境……");
        Directory.CreateDirectory(Path.GetDirectoryName(EnvironmentDirectory));
        MustRun(PythonExe, "-I", "-m", "venv", EnvironmentDirectory);
        var args = new List<string> {"-I", "-m", "pip", "--isolated", "install", "--disable-pip-version-check", "--require-hashes", "--only-binary=:all:", "--force-reinstall", "-r", Inside(Config.dependencies.lockFile)};
        string wheels = Inside(Config.dependencies.wheelDirectory);
        if (Config.dependencies.offline) args.Add("--no-index");
        else { args.Add("--index-url"); args.Add(Config.dependencies.indexUrl); }
        if (Directory.Exists(wheels)) { args.Add("--find-links"); args.Add(wheels); }
        Write("按共享 lock 文件安装并校验依赖……"); MustRun(VenvPython, args.ToArray());
        MustRun(VenvPython, "-I", Inside("engineering/desktop/verify_environment.py"), ConfigPath, Root);
        MustRun(VenvPython, "-I", "-m", "pip", "check");
        File.WriteAllText(ReadyFile, fingerprint, new UTF8Encoding(false)); Write("依赖安装完成。");
    }
    public void Serve() {
        if (!IsReady()) Install(); else Verify();
        string data = Inside(Config.application.dataDirectory);
        string generations = Path.Combine(data, "rooms", "demo", "generations");
        string password = null;
        if (!Directory.Exists(generations) || Directory.GetFiles(generations, "*.json").Length == 0) {
            password = Environment.GetEnvironmentVariable("ONLINECOC_BOOTSTRAP_PASSWORD");
            if (password == null && AskPassword != null) password = AskPassword();
            if (password == null || password.Length < 8) throw new Exception("首次启动需设置至少 8 位初始密码。无人值守测试可通过 ONLINECOC_BOOTSTRAP_PASSWORD 提供。");
        }
        if (Stop.WaitOne(0)) return;
        var listener = new TcpListener(IPAddress.Loopback, Config.application.port);
        try { listener.Start(); } catch (SocketException) { throw new Exception("端口已被占用，请关闭旧服务或修改配置中的 port。"); } finally { listener.Stop(); }
        Write("启动房间，等待本机服务就绪……");
        using (var process = Start(VenvPython, new [] {"-I", Inside(Config.application.entryPoint), "--data-dir", data, "--port", Config.application.port.ToString()}, password))
        using (var job = new ChildJob(process)) using (var ready = new ManualResetEvent(false)) {
            password = null;
            process.OutputDataReceived += (s,e) => { if (e.Data == "ONLINECOC_READY") ready.Set(); else Write(e.Data); };
            process.ErrorDataReceived += (s,e) => Write(e.Data); process.BeginOutputReadLine(); process.BeginErrorReadLine();
            var watch = Stopwatch.StartNew();
            while (!ready.WaitOne(100)) {
                if (process.HasExited) { process.WaitForExit(); throw new Exception("服务未能启动，详情见日志。"); }
                if (Stop.WaitOne(0)) break;
                if (watch.Elapsed.TotalSeconds > Config.application.startupTimeoutSeconds) throw new Exception("服务启动超时，详情见日志。");
            }
            if (!Stop.WaitOne(0)) {
                Write("服务已就绪：" + Url + "；关闭此窗口会停止本次服务。"); if (OnReady != null) OnReady();
                if (Config.application.openBrowser && !options.NoBrowser) OpenBrowser();
            }
            watch.Restart();
            while (!Stop.WaitOne(100) && !process.HasExited) {
                if (options.RunSeconds > 0 && watch.Elapsed.TotalSeconds >= options.RunSeconds) Stop.Set();
            }
            if (!process.HasExited) {
                Write("正在保存状态并停止服务……");
                try { process.StandardInput.WriteLine("stop"); process.StandardInput.Close(); } catch (IOException) {}
                if (!process.WaitForExit(30000)) { Write("停止超时，结束本次服务进程树；下次按文件恢复。"); job.Dispose(); process.WaitForExit(5000); }
            }
            process.WaitForExit();
            if (process.ExitCode != 0) throw new Exception("服务已退出，退出码 " + process.ExitCode + "。请查看日志。");
            Write("服务已停止。");
        }
    }
    public void OpenBrowser() { Process.Start(new ProcessStartInfo(Url) {UseShellExecute = true}); }
    public void Execute() {
        string mutexPath = Inside("engineering/.runtime/desktop-tools.lock"); Directory.CreateDirectory(Path.GetDirectoryName(mutexPath));
        FileStream exclusive;
        try { exclusive = new FileStream(mutexPath, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None); }
        catch (IOException) { throw new Exception("本工程已有安装或启动窗口，请先使用或关闭原窗口。"); }
        using (exclusive) {
            Write("配置：" + ConfigPath); Write("日志：" + LogPath);
            if (options.Check) { Verify(); return; }
#if INSTALLER
            Install();
#else
            Serve();
#endif
        }
    }
    public void Dispose() { Stop.Dispose(); lock (logLock) { disposed=true; log.Dispose(); } }
}
public sealed class PasswordDialog : Form {
    public string Password { get { return first.Text; } }
    readonly TextBox first = new TextBox {UseSystemPasswordChar=true, Dock=DockStyle.Fill};
    readonly TextBox second = new TextBox {UseSystemPasswordChar=true, Dock=DockStyle.Fill};
    public PasswordDialog() {
        Text = "首次建立房间"; Width=430; Height=240; StartPosition=FormStartPosition.CenterParent; FormBorderStyle=FormBorderStyle.FixedDialog; MaximizeBox=false; MinimizeBox=false;
        var panel = new TableLayoutPanel {Dock=DockStyle.Fill, Padding=new Padding(18), ColumnCount=1, RowCount=5};
        panel.Controls.Add(new Label {Text="设置 kp / player1 / player2 的初始密码（至少 8 位）", AutoSize=true}); panel.Controls.Add(first);
        panel.Controls.Add(new Label {Text="再次输入密码", AutoSize=true}); panel.Controls.Add(second);
        var ok = new Button {Text="建立并启动", Dock=DockStyle.Right, Width=130};
        ok.Click += (s,e) => { if (first.Text.Length < 8 || first.Text != second.Text) MessageBox.Show(this,"两次密码须一致且至少 8 位。"); else {DialogResult=DialogResult.OK; Close();} };
        panel.Controls.Add(ok); Controls.Add(panel); AcceptButton=ok;
    }
}
public sealed class MainWindow : Form {
    readonly Engine engine; bool busy=true, closing=false;
    readonly TextBox output = new TextBox {Multiline=true, ReadOnly=true, ScrollBars=ScrollBars.Vertical, Dock=DockStyle.Fill, BackColor=Color.White};
    readonly Label status = new Label {Text="正在准备……", AutoSize=true, Dock=DockStyle.Top, Padding=new Padding(0,8,0,12)};
    readonly Button stop = new Button {Text="取消 / 停止", Width=120};
    readonly Button browser = new Button {Text="打开页面", Width=120, Enabled=false};
    public MainWindow(Engine engine) {
        this.engine=engine;
#if INSTALLER
        Text="OnlineCOC · 安装依赖";
#else
        Text="OnlineCOC · 启动服务";
#endif
        Width=760; Height=520; MinimumSize=new Size(600,380); StartPosition=FormStartPosition.CenterScreen;
        Font=new Font("Microsoft YaHei UI",9); Padding=new Padding(18);
        var buttons=new FlowLayoutPanel {Dock=DockStyle.Bottom,Height=44,Padding=new Padding(0,10,0,0)};
        var logs=new Button {Text="查看日志",Width=120}; logs.Click+=(s,e)=>Process.Start(new ProcessStartInfo("notepad.exe",Engine.Quote(engine.LogPath)){UseShellExecute=true});
        stop.Click+=(s,e)=>{if(busy){engine.Stop.Set();status.Text="正在停止……";}else Close();};
        browser.Click+=(s,e)=>engine.OpenBrowser(); buttons.Controls.Add(browser);buttons.Controls.Add(logs);buttons.Controls.Add(stop);
        Controls.Add(output);Controls.Add(status);Controls.Add(buttons);
        engine.OnLog=message=>UI(()=>{if(output.TextLength>60000)output.Text=output.Text.Substring(output.TextLength-40000);output.AppendText(message+Environment.NewLine);});
        engine.OnReady=()=>UI(()=>{status.Text="服务运行中 · "+engine.Url;browser.Enabled=true;});
        engine.AskPassword=()=> (string)Invoke(new Func<string>(()=>{using(var dialog=new PasswordDialog())return dialog.ShowDialog(this)==DialogResult.OK?dialog.Password:null;}));
        Shown+=(s,e)=>Task.Run(()=>{
            bool success=false;
            try {engine.Execute();success=true;} catch(OperationCanceledException){engine.Write("操作已取消，未标记为安装成功。");} catch(Exception error){engine.Write("错误："+error.Message);}
            UI(()=>{busy=false;browser.Enabled=false;stop.Text="关闭";status.Text=success?"操作完成":"操作未完成，请查看下方日志";if(closing)Close();});
        });
        FormClosing+=(s,e)=>{if(busy){closing=true;e.Cancel=true;engine.Stop.Set();status.Text="正在停止，请稍候……";}};
    }
    void UI(Action action){try { if(!IsDisposed && IsHandleCreated)BeginInvoke(action); } catch(InvalidOperationException) {}}
}
static class Program {
    [STAThread] static int Main(string[] args) {
        // WinExe has no console code-page handle. Write redirected streams directly.
        try {
            Console.SetOut(new StreamWriter(Console.OpenStandardOutput(), new UTF8Encoding(false)) {AutoFlush=true});
            Console.SetError(new StreamWriter(Console.OpenStandardError(), new UTF8Encoding(false)) {AutoFlush=true});
        } catch(IOException) { Console.SetOut(TextWriter.Null); Console.SetError(TextWriter.Null); }
        Options options=null;
        try {
            options=Options.Parse(args);
            using(var engine=new Engine(options)) {
                if(options.Headless){try {engine.Execute();return 0;}catch(Exception error){engine.Write("错误："+error.Message);return 1;}}
                Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
                using(var window=new MainWindow(engine))Application.Run(window);
            }
            return 0;
        } catch(Exception error){if(options!=null&&options.Headless)Console.Error.WriteLine(error.Message);else MessageBox.Show(error.Message,"OnlineCOC",MessageBoxButtons.OK,MessageBoxIcon.Error);return 1;}
    }
}
}