using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
namespace RoomManager {
 public sealed class Settings {
  readonly string path;
  public List<object> Watches=new List<object>();public List<object> Commands=new List<object>();
  public Settings(string directory){Directory.CreateDirectory(directory);path=Path.Combine(directory,"settings.json");if(File.Exists(path))try{var data=J.Parse(File.ReadAllText(path));Watches=J.List(J.Get(data,"watches")).Take(100).ToList();Commands=J.List(J.Get(data,"commands")).Take(200).ToList();}catch{}}
  public void Save(){var data=J.Obj("watches",Watches,"commands",Commands.Take(200).ToArray());string temporary=path+"."+Guid.NewGuid().ToString("N")+".tmp";File.WriteAllText(temporary,J.Pretty(data),new System.Text.UTF8Encoding(false));if(File.Exists(path))File.Replace(temporary,path,null);else File.Move(temporary,path);}
  public void Remember(string endpoint,object view,object envelope){var p=J.Get(envelope,"payload");Commands.Insert(0,J.Obj("endpoint",endpoint,"accountId",J.Get(view,"accountId"),"roomId",J.Get(view,"roomId"),"runId",J.Get(view,"runId"),"commandId",J.Get(p,"commandId"),"op",J.Get(p,"op")));if(Commands.Count>200)Commands.RemoveAt(200);Save();}
 }
}
