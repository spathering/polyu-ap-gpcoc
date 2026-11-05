$ErrorActionPreference = 'Stop'
$packRoot = Split-Path $PSScriptRoot -Parent
$compiler = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) {
    $compiler = Join-Path $env:WINDIR 'Microsoft.NET/Framework/v4.0.30319/csc.exe'
}
if (-not (Test-Path -LiteralPath $compiler)) {
    throw '缺少 Windows .NET Framework C# 编译器。运行已有 exe 不需要重新编译。'
}
$source = Join-Path $PSScriptRoot 'PackLauncher.cs'
$output = Join-Path $packRoot '启动激光与情感.exe'
& $compiler /nologo /target:exe /platform:anycpu /optimize+ /utf8output /codepage:65001 "/out:$output" $source
if ($LASTEXITCODE -ne 0) { throw '启动器编译失败。' }
$metadata = [ordered]@{
    source = 'tools/PackLauncher.cs'
    sourceSha256 = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
    executable = '启动激光与情感.exe'
    executableSha256 = (Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash.ToLowerInvariant()
    compilerVersion = [Diagnostics.FileVersionInfo]::GetVersionInfo($compiler).FileVersion
    builtAt = [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(8)).ToString('o')
}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'launcher-build.json'), ($metadata | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
Write-Output $output
