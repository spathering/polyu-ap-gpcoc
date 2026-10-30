param()
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$compiler = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) { throw '需要 Windows .NET Framework 4.x x64 编译器。' }
$source = Join-Path $PSScriptRoot 'DesktopTools.cs'
$references = @('/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.Web.Extensions.dll','/r:System.IO.Compression.dll','/r:System.IO.Compression.FileSystem.dll')
& $compiler /nologo /target:winexe /platform:x64 /optimize+ /define:INSTALLER "/out:$(Join-Path $projectRoot '安装依赖.exe')" @references $source
if ($LASTEXITCODE -ne 0) { throw '安装 exe 编译失败。' }
& $compiler /nologo /target:winexe /platform:x64 /optimize+ "/out:$(Join-Path $projectRoot '启动OnlineCOC.exe')" @references $source
if ($LASTEXITCODE -ne 0) { throw '启动 exe 编译失败。' }
Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $projectRoot '安装依赖.exe'),(Join-Path $projectRoot '启动OnlineCOC.exe')
$record = [ordered]@{
    builtAt = (Get-Date).ToString('o')
    compiler = (Get-Item -LiteralPath $compiler).VersionInfo.FileVersion
    sourceSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToLowerInvariant()
    artifacts = @('安装依赖.exe', '启动OnlineCOC.exe') | ForEach-Object {
        [ordered]@{file=$_; sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $projectRoot $_)).Hash.ToLowerInvariant()}
    }
}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'build-info.json'), ($record | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
