$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$compiler = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$output = Join-Path $root 'dist'
New-Item -ItemType Directory -Force -Path $output | Out-Null
$sources = Get-ChildItem -LiteralPath (Join-Path $root 'src') -Filter *.cs -Recurse | ForEach-Object { $_.FullName }
& $compiler /nologo /target:winexe /platform:x64 /optimize+ /utf8output "/win32manifest:$root/app.manifest" /reference:System.dll /reference:System.Core.dll /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /reference:System.Web.Extensions.dll /reference:System.Net.Http.dll "/out:$output/RoomManager.exe" $sources
if ($LASTEXITCODE -ne 0) { throw '编译失败' }
@'
<?xml version="1.0" encoding="utf-8" ?>
<configuration><startup><supportedRuntime version="v4.0" sku=".NETFramework,Version=v4.8" /></startup><System.Windows.Forms.ApplicationConfigurationSection><add key="DpiAwareness" value="PerMonitorV2" /></System.Windows.Forms.ApplicationConfigurationSection></configuration>
'@ | Set-Content -LiteralPath "$output/RoomManager.exe.config" -Encoding UTF8
$sha = [System.Security.Cryptography.SHA256]::Create()
try { $hash = [BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes("$output/RoomManager.exe"))).Replace('-', '').ToLowerInvariant() } finally { $sha.Dispose() }
$stamp = [DateTimeOffset]::Now.ToString('o')
@"
{"version":"0.1.0","protocolVersion":1,"framework":".NET Framework 4.8","platform":"Windows x64","sha256":"$hash","builtAt":"$stamp"}
"@ | Set-Content -LiteralPath "$output/release.json" -Encoding UTF8

Copy-Item -LiteralPath "$root/tool-config.json" -Destination "$output/tool-config.json" -Force
Copy-Item -LiteralPath "$root/dependency-manifest.json" -Destination "$output/dependency-manifest.json" -Force
$sourceRecords = @()
foreach ($file in ($sources | Sort-Object)) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { $digest = [BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($file))).Replace('-', '').ToLowerInvariant() } finally { $sha.Dispose() }
    $relative = $file.Substring($root.Length + 1).Replace('\', '/')
    $sourceRecords += "$digest  $relative"
}
$sourceRecords | Set-Content -LiteralPath "$output/source-sha256.txt" -Encoding UTF8
Copy-Item -LiteralPath "$root/tests/contract-baseline.json" -Destination "$output/contract-baseline.json" -Force
@'
OnlineCOC Room Manager 0.1.0

需要 Windows x64 和 .NET Framework 4.8。复制本目录全部文件即可运行。
先单独启动 OnlineCOC 宿主，再运行 RoomManager.exe，输入本机宿主地址及 KP 账号密码。
默认地址 http://127.0.0.1:8765，可在界面修改；程序不启动或停止宿主。

选数据类别、选对象、选操作，勾选需要提交的可选字段。结构字段使用 JSON。
实体冲突后保留草稿，可比较最新值并重建编辑基线；其他操作没有统一原子版本保护。
观察到的变化仅为接收到的样本，断线中间变化无法补齐。
备份仅由宿主创建并返回 ID，不含身份库，不提供列表、导出或恢复。

tool-config.json 可设置地址、观察/关注上限和轮询间隔；修改后重启工具。
本地关注和命令查询元信息保存在 %LOCALAPPDATA%/OnlineCOC/RoomManager。
多个实例可使用 RoomManager.exe --settings-dir 独立目录，避免覆盖彼此设置。
密码、Cookie、完整命令和观察数值不保存到本地设置。
'@ | Set-Content -LiteralPath "$output/README.txt" -Encoding UTF8
