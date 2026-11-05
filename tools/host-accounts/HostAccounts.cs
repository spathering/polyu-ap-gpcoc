using System;
using System.IO;
using System.Net;
using System.Text;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using System.Drawing;
using System.Threading.Tasks;

class Rejected:Exception {public Rejected(string message):base(message){}}

static class Program {
    public static JavaScriptSerializer Json = new JavaScriptSerializer();
    [STAThread] static int Main(string[] args) {
        string directory = args.Length==2 ? args[1] : Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "OnlineCOC", "HostControl");
        Application.EnableVisualStyles();
        if(args.Length==2 && args[0]=="--probe") {
            var records=Discover(directory);
            Console.WriteLine(Json.Serialize(records.Select(r=>Call(r,"accounts",null)).ToArray()));
            return records.Count>0?0:2;
        }
        Application.Run(new AccountsForm(directory,args.Length==2 && args[0]=="--smoke"));
        return Environment.ExitCode;
    }
    public static List<Dictionary<string,object>> Discover(string dir) {
        var list=new List<Dictionary<string,object>>();
        if(!Directory.Exists(dir))return list;
        foreach(string file in Directory.GetFiles(dir,"*.json")) {
            try {
                var record=Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(file,Encoding.UTF8));
                var uri=new Uri((string)record["url"]);
                if(uri.Scheme!="http" || uri.Host!="127.0.0.1" || uri.AbsolutePath!="/" || uri.Query!="" || uri.UserInfo!="" || uri.Fragment!="")continue;
                Call(record,"accounts",null);list.Add(record);
            } catch { /* stale, old or inaccessible host records are not selectable */ }
        }
        return list;
    }
    public static object Call(Dictionary<string,object> record,string route,object body) {
        var raw=ProtectedData.Unprotect(Convert.FromBase64String((string)record["protectedKey"]),null,DataProtectionScope.CurrentUser);
        var request=(HttpWebRequest)WebRequest.Create((string)record["url"]+"/api/v1/host-control/"+route);
        request.Proxy=null;request.AllowAutoRedirect=false;request.Timeout=5000;request.ReadWriteTimeout=5000;
        request.Headers["X-OnlineCOC-Instance"]=(string)record["instanceId"];
        request.Headers["X-OnlineCOC-Host-Key"]=Encoding.UTF8.GetString(raw);Array.Clear(raw,0,raw.Length);
        if(body!=null) {
            request.Method="POST";request.ContentType="application/json";
            var bytes=Encoding.UTF8.GetBytes(Json.Serialize(body));request.ContentLength=bytes.Length;
            using(var stream=request.GetRequestStream())stream.Write(bytes,0,bytes.Length);
            Array.Clear(bytes,0,bytes.Length);
        }
        try {
            using(var response=(HttpWebResponse)request.GetResponse())
            using(var reader=new StreamReader(response.GetResponseStream())) {
                if(response.StatusCode!=HttpStatusCode.OK)throw new Exception("服务器返回异常状态");
                var result=Json.Deserialize<Dictionary<string,object>>(reader.ReadToEnd());
                if(result.ContainsKey("instanceId") && (string)result["instanceId"]!=(string)record["instanceId"])throw new Exception("实例已变化，请重新扫描");
                return result;
            }
        } catch(WebException error) {
            if(error.Response!=null)using(var reader=new StreamReader(error.Response.GetResponseStream())) {
                var result=Json.Deserialize<Dictionary<string,object>>(reader.ReadToEnd());
                string code=result.ContainsKey("code")?(string)result["code"]:"操作失败";
                if(((HttpWebResponse)error.Response).StatusCode==HttpStatusCode.Conflict)throw new Rejected(code);
                throw new Exception(code);
            }
            throw new Exception("连接中断，提交结果可能未知；请查询原操作结果。");
        }
    }
}

class AccountsForm:Form {
    readonly string directory; readonly bool smoke;
    ComboBox hosts=new ComboBox {DropDownStyle=ComboBoxStyle.DropDownList,Width=770};
    DataGridView grid=new DataGridView {Dock=DockStyle.Fill,ReadOnly=true,AllowUserToAddRows=false,AllowUserToDeleteRows=false,MultiSelect=false,SelectionMode=DataGridViewSelectionMode.FullRowSelect,AutoSizeColumnsMode=DataGridViewAutoSizeColumnsMode.Fill};
    TextBox login=new TextBox {Width=180}, password=new TextBox {Width=180,UseSystemPasswordChar=true}, confirm=new TextBox {Width=180,UseSystemPasswordChar=true};
    Label status=new Label {Dock=DockStyle.Bottom,Height=55,Padding=new Padding(8)};
    Button scan=new Button {Text="扫描本机实例",AutoSize=true}, refresh=new Button {Text="刷新账号",AutoSize=true}, create=new Button {Text="创建账号",AutoSize=true}, reset=new Button {Text="重设所选账号密码",AutoSize=true}, recover=new Button {Text="查询原操作结果",AutoSize=true,Enabled=false};
    List<Dictionary<string,object>> records=new List<Dictionary<string,object>>();
    Dictionary<string,object> pending, pendingHost;
    bool selecting;
    public AccountsForm(string path,bool test) {
        directory=path;smoke=test;Text="OnlineCOC · 主机账号管理";Size=new Size(1000,650);MinimumSize=new Size(900,550);Font=new Font("Microsoft YaHei UI",10);
        var top=new FlowLayoutPanel {Dock=DockStyle.Top,Height=94,Padding=new Padding(8)};
        top.Controls.Add(new Label {Text="当前 Windows 用户启动的本机实例",AutoSize=true});top.Controls.Add(scan);top.Controls.Add(refresh);top.SetFlowBreak(refresh,true);top.Controls.Add(hosts);
        var edit=new FlowLayoutPanel {Dock=DockStyle.Bottom,Height=140,Padding=new Padding(8)};
        edit.Controls.Add(new Label {Text="新建登录名",AutoSize=true});edit.Controls.Add(login);edit.Controls.Add(new Label {Text="新密码",AutoSize=true});edit.Controls.Add(password);edit.Controls.Add(new Label {Text="确认密码",AutoSize=true});edit.Controls.Add(confirm);edit.SetFlowBreak(confirm,true);
        edit.Controls.Add(create);edit.Controls.Add(reset);edit.Controls.Add(recover);edit.SetFlowBreak(recover,true);
        edit.Controls.Add(new Label {Text="密码至少 8 位。重设会注销目标账号的旧会话。新账号需另外绑定房间成员。",AutoSize=true});
        grid.Columns.Add("accountId","账号 ID");grid.Columns.Add("loginName","登录名");grid.Columns.Add("nickname","昵称");grid.Columns.Add("state","可用状态");grid.Columns.Add("role","房间角色");
        Controls.Add(grid);Controls.Add(top);Controls.Add(edit);Controls.Add(status);
        scan.Click+=async(s,e)=>await Run(Scan);refresh.Click+=async(s,e)=>await Run(LoadAccounts);
        hosts.SelectedIndexChanged+=async(s,e)=>{if(!selecting)await Run(LoadAccounts);};
        create.Click+=async(s,e)=>await Change("create");reset.Click+=async(s,e)=>await Change("password");recover.Click+=async(s,e)=>await Run(Recover);
        Shown+=async(s,e)=>{await Run(Scan);if(smoke){Environment.ExitCode=records.Count>0 && grid.Rows.Count>0?0:3;Close();}};
        FormClosing+=(s,e)=>{if(pending!=null && !smoke && MessageBox.Show("操作结果尚未确认。关闭后将失去本次查询编号，确认关闭？","未决操作",MessageBoxButtons.YesNo)!=DialogResult.Yes)e.Cancel=true;};
    }
    Dictionary<string,object> Selected {get {if(hosts.SelectedIndex<0)throw new Exception("本机没有可用实例。请先在本机启动新版宿主，再扫描。");return records[hosts.SelectedIndex];}}
    void Busy(bool busy) {scan.Enabled=refresh.Enabled=hosts.Enabled=create.Enabled=reset.Enabled=login.Enabled=password.Enabled=confirm.Enabled=!busy && pending==null;recover.Enabled=!busy && pending!=null;}
    async Task Run(Func<Task> action) {Busy(true);try {await action();}catch(Rejected e){if(pending!=null)pending.Remove("password");pending=null;pendingHost=null;status.Text="操作被拒绝："+e.Message;}catch(Exception e){status.Text=e.Message;}finally{Busy(false);}}
    async Task Scan() {
        records=await Task.Run(()=>Program.Discover(directory));selecting=true;hosts.Items.Clear();
        foreach(var r in records)hosts.Items.Add(r["url"]+"  |  PID "+r["pid"]+"  |  "+r["dataDirectory"]);
        if(records.Count>0){hosts.SelectedIndex=0;selecting=false;await LoadAccounts();}else {selecting=false;grid.Rows.Clear();status.Text="本机未发现可用主机实例。仅有客户端或旧版宿主时不可使用。";}
    }
    async Task LoadAccounts() {
        var record=Selected;
        var result=(Dictionary<string,object>)await Task.Run(()=>Program.Call(record,"accounts",null));grid.Rows.Clear();
        foreach(var item in (System.Collections.IEnumerable)result["items"]) {
            var a=(Dictionary<string,object>)item;
            grid.Rows.Add(a["accountId"],a["loginName"],a["nickname"],(bool)a["disabled"]?"已停用":"可用",a["roomRole"]??"未绑定");
        }
        status.Text="已连接本机实例："+result["dataDirectory"]+"。密码原文不可查询。";
    }
    async Task Change(string operation) {
        await Run(async()=>{
            var record=Selected;
            if(password.Text.Length<8 || password.Text.Length>1024 || password.Text!=confirm.Text)throw new Exception("请填写 8–1024 位新密码，并确保两次输入一致。");
            string account=operation=="create"?login.Text.Trim():grid.SelectedRows.Count>0?Convert.ToString(grid.SelectedRows[0].Cells[0].Value):"";
            if(account.Length==0)throw new Exception("请输入新建登录名或选中目标账号。");
            if(MessageBox.Show((operation=="create"?"创建账号 ":"重设密码并注销旧会话：")+account+"\n实例："+record["dataDirectory"],"确认目标实例与账号",MessageBoxButtons.OKCancel)!=DialogResult.OK)return;
            pendingHost=record;pending=new Dictionary<string,object>{{"requestId",Guid.NewGuid().ToString()},{"operation",operation},{"accountId",account},{"password",password.Text}};
            password.Clear();confirm.Clear();
            await Submit();
        });
    }
    async Task Submit() {
        var result=(Dictionary<string,object>)await Task.Run(()=>Program.Call(pendingHost,"accounts",pending));
        if((string)result["status"]!="committed")throw new Exception("操作结果未知，请查询原操作结果。");
        pending.Remove("password");pending=null;pendingHost=null;await LoadAccounts();status.Text="操作已完成；密码未保存到工具设置或日志。";
    }
    async Task Recover() {
        var fresh=await Task.Run(()=>Program.Discover(directory));
        var replacement=fresh.FirstOrDefault(r=>String.Equals((string)r["dataDirectory"],(string)pendingHost["dataDirectory"],StringComparison.OrdinalIgnoreCase));
        if(replacement==null)throw new Exception("原实例尚未恢复，请启动同一存档后再查询。");
        pendingHost=replacement;
        var result=(Dictionary<string,object>)await Task.Run(()=>Program.Call(pendingHost,"receipts/"+pending["requestId"],null));
        if((string)result["status"]=="unknown") {await Submit();return;}
        pending.Remove("password");pending=null;pendingHost=null;await LoadAccounts();status.Text="已确认原操作完成，无需重复提交。";
    }
}
