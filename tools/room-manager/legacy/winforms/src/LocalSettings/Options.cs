using System;
using System.IO;
namespace RoomManager {
 public static class Options {
  public static int ObservationLimit=2000,WatchLimit=100,AdminPollMilliseconds=2000;
  public static string DefaultEndpoint="http://127.0.0.1:8765";
  public static void Load(string path){if(!File.Exists(path))return;var c=J.Parse(File.ReadAllText(path));ObservationLimit=J.I(c,"observationLimit",2000);WatchLimit=J.I(c,"watchLimit",100);AdminPollMilliseconds=J.I(c,"adminPollMilliseconds",2000);DefaultEndpoint=J.S(c,"defaultEndpoint",DefaultEndpoint);ApiClient.ValidateOrigin(DefaultEndpoint);if(ObservationLimit<1||ObservationLimit>2000||WatchLimit<1||WatchLimit>100||AdminPollMilliseconds<1000||AdminPollMilliseconds>60000)throw new ApiException("工具配置超出允许范围");}
 }
}
