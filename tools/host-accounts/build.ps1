$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot 'HostAccounts.cs'
$output=Join-Path $PSScriptRoot 'HostAccounts.exe'
$compiler=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
& $compiler /nologo /target:winexe /platform:x64 /codepage:65001 /reference:System.dll /reference:System.Core.dll /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /reference:System.Web.Extensions.dll /reference:System.Security.dll "/out:$output" $source
if($LASTEXITCODE -ne 0){throw '编译失败'}
$record=@{builtAt=[DateTimeOffset]::Now.ToString('o');exeSha256=(Get-FileHash -LiteralPath "$PSScriptRoot/HostAccounts.exe" -Algorithm SHA256).Hash.ToLower();sourceSha256=(Get-FileHash -LiteralPath "$PSScriptRoot/HostAccounts.cs" -Algorithm SHA256).Hash.ToLower()}
$record | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/build-info.json" -Encoding UTF8
