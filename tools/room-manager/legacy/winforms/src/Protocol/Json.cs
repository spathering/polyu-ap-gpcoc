using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Web.Script.Serialization;
namespace RoomManager {
 public static class J {
  public static JavaScriptSerializer Serializer(){return new JavaScriptSerializer { MaxJsonLength=16*1024*1024, RecursionLimit=128 };}
  public static object Parse(string text){return Serializer().DeserializeObject(text);}
  public static string Text(object value){return Serializer().Serialize(value);}
  public static Dictionary<string,object> D(object value){return value as Dictionary<string,object> ?? new Dictionary<string,object>();}
  public static object Get(object value,string key,object fallback=null){object result;return D(value).TryGetValue(key,out result)?result:fallback;}
  public static string S(object value,string key,string fallback=""){return Convert.ToString(Get(value,key,fallback));}
  public static int I(object value,string key,int fallback=0){return Convert.ToInt32(Get(value,key,fallback));}
  public static bool B(object value,string key,bool fallback=false){return Convert.ToBoolean(Get(value,key,fallback));}
  public static Dictionary<string,object> Obj(params object[] pairs){var d=new Dictionary<string,object>();for(int i=0;i<pairs.Length;i+=2)d[(string)pairs[i]]=pairs[i+1];return d;}
  public static List<object> List(object value){var a=value as IEnumerable;if(a==null||value is string||value is IDictionary)return new List<object>();return a.Cast<object>().ToList();}
  public static object Clone(object value){return Parse(Text(value));}
  public static string Canon(object value){var d=value as Dictionary<string,object>;if(d!=null)return "{"+String.Join(",",d.OrderBy(x=>x.Key,StringComparer.Ordinal).Select(x=>Text(x.Key)+":"+Canon(x.Value)))+"}";if(value is IEnumerable&&!(value is string))return "["+String.Join(",",List(value).Select(Canon))+"]";return Text(value);}
  public static string Pretty(object value,int indent=0){var d=value as Dictionary<string,object>;string pad=new string(' ',indent), child=pad+"  ";if(d!=null){if(d.Count==0)return "{}";return "{\r\n"+String.Join(",\r\n",d.Select(x=>child+Text(x.Key)+": "+Pretty(x.Value,indent+2)))+"\r\n"+pad+"}";}if(value is IEnumerable&&!(value is string)){var l=List(value);if(l.Count==0)return "[]";return "[\r\n"+String.Join(",\r\n",l.Select(x=>child+Pretty(x,indent+2)))+"\r\n"+pad+"]";}return Text(value);}
 }
 public class ApiException:Exception {public readonly int Status;public ApiException(string code,int status=0):base(code){Status=status;}}
 public sealed class SnapshotAssembler {
  string id;string[] parts;int bytes; readonly int maxBytes;
  public SnapshotAssembler(int maximum=2097152){maxBytes=maximum;}
  public void Reset(){id=null;parts=null;bytes=0;}
  public object Accept(object msg){string type=J.S(msg,"type");if(type=="reset"){Reset();throw new ApiException("AUTH_RESET");}
   if(type=="snapshot.begin"){if(parts!=null)throw new ApiException("SNAPSHOT_INCOMPLETE");int n=J.I(msg,"parts");if(n<1||n>128||J.S(msg,"id")=="")throw new ApiException("SNAPSHOT_INVALID");id=J.S(msg,"id");parts=new string[n];bytes=0;return null;}
   if(type=="snapshot.part"){int i=J.I(msg,"index",-1);if(parts==null||J.S(msg,"id")!=id||i<0||i>=parts.Length||parts[i]!=null||!(J.Get(msg,"data") is string))throw new ApiException("SNAPSHOT_INVALID");string text=J.S(msg,"data");bytes+=Encoding.UTF8.GetByteCount(text);if(bytes>maxBytes)throw new ApiException("SNAPSHOT_TOO_LARGE");parts[i]=text;return null;}
   if(type=="snapshot.end"){if(parts==null||J.S(msg,"id")!=id||parts.Any(x=>x==null))throw new ApiException("SNAPSHOT_INCOMPLETE");var value=J.Parse(String.Concat(parts));Reset();if(!(value is Dictionary<string,object>))throw new ApiException("SNAPSHOT_INVALID");return value;}
   if(type!="pong")throw new ApiException("PROTOCOL_UNSUPPORTED");return null;
  }
 }
}
