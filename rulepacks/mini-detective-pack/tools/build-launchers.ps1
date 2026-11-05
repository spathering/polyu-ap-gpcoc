$ErrorActionPreference = 'Stop'
$pack = Split-Path $PSScriptRoot -Parent
$compiler = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) { throw '缺少.NET Framework C#编译器' }
$source = Join-Path $PSScriptRoot 'AccountLauncher.cs'
$targets = @(
    @{Name='KP主持人.exe';Define='KP';Account='kp'},
    @{Name='PL1观察员.exe';Define='PLAYER1';Account='player1'},
    @{Name='PL2护卫.exe';Define='PLAYER2';Account='player2'},
    @{Name='PL3文献员.exe';Define='PLAYER3';Account='player3'},
    @{Name='PL4医护员.exe';Define='PLAYER4';Account='player4'}
)
$records = foreach ($target in $targets) {
    $output = Join-Path $pack $target.Name
    & $compiler /nologo /target:winexe /platform:anycpu /optimize+ /utf8output /codepage:65001 /r:System.Windows.Forms.dll /r:System.Web.Extensions.dll "/define:$($target.Define)" "/out:$output" $source
    if ($LASTEXITCODE -ne 0) { throw ('编译失败：'+$target.Name) }
    [ordered]@{file=$target.Name;account=$target.Account;sha256=(Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash.ToLowerInvariant()}
}
$metadata = [ordered]@{source='tools/AccountLauncher.cs';sourceSha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant();compiler=[Diagnostics.FileVersionInfo]::GetVersionInfo($compiler).FileVersion;builtAt=[DateTimeOffset]::Now.ToOffset([TimeSpan]::FromHours(8)).ToString('o');executables=@($records)}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'launcher-build.json'),($metadata | ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
$records | ForEach-Object { Join-Path $pack $_.file }
