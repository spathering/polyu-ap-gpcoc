$ErrorActionPreference='Stop'
$pack=Split-Path $PSScriptRoot -Parent
$source=Join-Path $PSScriptRoot 'ServiceManager.cs'
$output=Join-Path $pack '配置包服务管理.exe'
$compiler=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
& $compiler /nologo /target:winexe /platform:x64 /optimize+ /codepage:65001 /r:System.dll /r:System.Core.dll /r:System.Drawing.dll /r:System.Windows.Forms.dll /r:System.Web.Extensions.dll /r:System.Security.dll /r:System.Management.dll "/out:$output" $source
if($LASTEXITCODE -ne 0){throw '服务管理器编译失败'}
$record=[ordered]@{builtAt=[DateTimeOffset]::Now.ToString('o');source='tools/ServiceManager.cs';executable='配置包服务管理.exe';sourceSha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant();exeSha256=(Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash.ToLowerInvariant()}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'service-manager-build.json'),($record|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
$output
