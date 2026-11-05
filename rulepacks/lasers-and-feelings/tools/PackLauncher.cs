using System;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

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

    private static int Main(string[] args)
    {
        Console.OutputEncoding = new UTF8Encoding(false);
        try
        {
            string pack = AppDomain.CurrentDomain.BaseDirectory;
            string script = Path.Combine(pack, "tools", "launch.py");
            if (!File.Exists(script)) throw new FileNotFoundException("缺少 tools/launch.py。请保留完整配置包，不要单独移动这个 exe。");
            string python = FindPython(pack);
            ProtectProcessTree();
            var command = new StringBuilder("-B ").Append(Quote(script));
            foreach (string arg in args) command.Append(' ').Append(Quote(arg));
            var start = new ProcessStartInfo(python, command.ToString());
            start.UseShellExecute = false;
            start.WorkingDirectory = pack;
            start.EnvironmentVariables["PYTHONDONTWRITEBYTECODE"] = "1";
            start.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
            // Ctrl+C reaches Python too; allow its finally block to stop the host.
            Console.CancelKeyPress += delegate(object sender, ConsoleCancelEventArgs e) { e.Cancel = true; };
            using (var child = Process.Start(start))
            {
                child.WaitForExit();
                if (child.ExitCode != 0) PauseOnError();
                return child.ExitCode;
            }
        }
        catch (Exception error)
        {
            Console.Error.WriteLine("激光与情感启动失败：" + error.Message);
            PauseOnError();
            return 1;
        }
    }

    private static void PauseOnError()
    {
        if (!Console.IsInputRedirected)
        {
            Console.Error.WriteLine("按回车关闭窗口。");
            Console.ReadLine();
        }
    }
}
