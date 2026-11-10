using System;
using System.IO;
using System.Windows.Forms;
namespace RoomManager {static class Program {
 [STAThread]static void Main(string[] args){Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);string directory=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"OnlineCOC","RoomManager");for(int i=0;i<args.Length-1;i++)if(args[i]=="--settings-dir")directory=Path.GetFullPath(args[++i]);try{Options.Load(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"tool-config.json"));Application.Run(new MainForm(new Settings(directory)));}catch(Exception ex){MessageBox.Show(ex.Message,"启动失败");}}
}}
