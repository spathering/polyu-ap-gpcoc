using System;
using System.Collections.Generic;
using System.Linq;
namespace RoomManager {
 public sealed class Observer {
  readonly List<object> records=new List<object>();readonly List<int> sizes=new List<int>();readonly object gate=new object();int bytes;public int Dropped {get;private set;}string session=Guid.NewGuid().ToString("N");object beforeRoot,afterRoot;
  public List<object> Records {get {lock(gate)return records.ToList();}}
  readonly Dictionary<string,object> baselines=new Dictionary<string,object>();
  public void Reset(){lock(gate){baselines.Clear();records.Clear();sizes.Clear();bytes=0;Dropped=0;session=Guid.NewGuid().ToString("N");beforeRoot=afterRoot=null;}}
  public void Sample(string source,object value){lock(gate){object prior;if(baselines.TryGetValue(source,out prior)){beforeRoot=prior;afterRoot=value;Diff(source,"",prior,true,value,true);}baselines[source]=J.Clone(value);beforeRoot=afterRoot=null;}}
  void Diff(string source,string path,object a,bool hasA,object b,bool hasB){
   if(hasA&&hasB&&J.Canon(a)==J.Canon(b))return;
   if(hasA&&hasB&&a is Dictionary<string,object>&&b is Dictionary<string,object>){var x=J.D(a);var y=J.D(b);foreach(var key in x.Keys.Union(y.Keys).OrderBy(k=>k)){if(key=="viewToken")continue;Diff(source,path+"/"+Escape(key),J.Get(a,key),x.ContainsKey(key),J.Get(b,key),y.ContainsKey(key));}return;}
   var segments=path.Split('/').Skip(1).Select(s=>s.Replace("~1","/").Replace("~0","~")).ToArray();string collection=segments.Length>0?segments[0]:"",id=segments.Length>1?segments[1]:"";var beforeObject=J.Get(J.Get(beforeRoot,collection),id);var afterObject=J.Get(J.Get(afterRoot,collection),id);
   var record=J.Obj("observationId",Guid.NewGuid().ToString("N"),"sessionId",session,"receivedAt",DateTimeOffset.Now.ToString("o"),"source",source,"collection",collection,"objectId",id,"beforeRevision",J.Get(beforeObject,"revision"),"afterRevision",J.Get(afterObject,"revision"),"path",path,"kind",!hasB?"不再可见":!hasA?"首次可见":"变化","beforePresent",hasA,"before",a,"afterPresent",hasB,"after",b);int size=System.Text.Encoding.UTF8.GetByteCount(J.Text(record));records.Add(record);sizes.Add(size);bytes+=size;while(records.Count>Options.ObservationLimit||bytes>16*1024*1024){bytes-=sizes[0];sizes.RemoveAt(0);records.RemoveAt(0);Dropped++;}
  }
  public static string Escape(string s){return s.Replace("~","~0").Replace("/","~1");}
  public static object Collections(object data){var result=J.Obj();foreach(var pair in J.D(data)){if(pair.Key=="audit"||pair.Key=="metrics"||pair.Key=="runtime"||pair.Key=="store")continue;var items=J.List(pair.Value);if(pair.Value is object[]||pair.Value is System.Collections.ArrayList){var map=J.Obj();foreach(var item in items){string id=J.S(item,"id",J.S(item,"accountId",J.S(item,"configurationId",J.S(item,"assetId",J.S(item,"flowId",J.Text(item))))));map[id]=item;}result[pair.Key]=map;}else result[pair.Key]=pair.Value;}return result;}
 }
}
