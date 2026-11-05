using System;
using System.Linq;
namespace RoomManager {
 public static class Validate {
  public static void Check(object schema,object value,string path="参数"){
   object type=J.Get(schema,"type");var types=type is string?new[]{(string)type}:J.List(type).Select(Convert.ToString).ToArray();
   string actual=value==null?"null":value is string?"string":value is bool?"boolean":value is System.Collections.Generic.Dictionary<string,object>?"object":value is object[]?"array":"number";
   if(types.Length>0&&!types.Contains(actual)&&!(actual=="number"&&types.Contains("integer")&&Convert.ToDouble(value)%1==0))throw new ApiException(path+" 类型应为 "+String.Join("/",types));
   var choices=J.List(J.Get(schema,"enum"));if(choices.Count>0&&!choices.Any(x=>J.Canon(x)==J.Canon(value)))throw new ApiException(path+" 不在可选值中");
   if(value is string){int n=((string)value).Length;if(n<J.I(schema,"minLength")||n>J.I(schema,"maxLength",Int32.MaxValue))throw new ApiException(path+" 长度超限");}
   if(actual=="number"){double n=Convert.ToDouble(value);if(Double.IsNaN(n)||Double.IsInfinity(n)||n<Convert.ToDouble(J.Get(schema,"minimum",Double.MinValue))||n>Convert.ToDouble(J.Get(schema,"maximum",Double.MaxValue)))throw new ApiException(path+" 数值超限");}
   if(actual=="object"){var d=J.D(value);if(d.Count>J.I(schema,"maxProperties",Int32.MaxValue))throw new ApiException(path+" 字段过多");foreach(var key in J.List(J.Get(schema,"required")))if(!d.ContainsKey(Convert.ToString(key)))throw new ApiException(path+" 缺少 "+key);var props=J.D(J.Get(schema,"properties"));foreach(var pair in d){if(props.ContainsKey(pair.Key))Check(props[pair.Key],pair.Value,path+"."+pair.Key);else{object additional=J.Get(schema,"additionalProperties",true);if(additional is bool&&!(bool)additional)throw new ApiException(path+" 未知字段 "+pair.Key);if(additional is System.Collections.Generic.Dictionary<string,object>)Check(additional,pair.Value,path+"."+pair.Key);}}}
   if(actual=="array"){var list=J.List(value);if(list.Count>J.I(schema,"maxItems",Int32.MaxValue)||list.Count<J.I(schema,"minItems"))throw new ApiException(path+" 项数超限");foreach(var item in list)if(J.Get(schema,"items")!=null)Check(J.Get(schema,"items"),item,path+"[]");if(J.B(schema,"uniqueItems")&&list.Select(J.Canon).Distinct().Count()!=list.Count)throw new ApiException(path+" 不允许重复项");}
  }
 }
}
