[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$SourceDir,
    [string]$OutputDir,
    [string]$Version,
    [string]$CompilerPath
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$config = Get-Content -LiteralPath (Join-Path $projectRoot 'release_config.json') -Raw | ConvertFrom-Json
if (-not $Version) { $Version = $config.version }
if ($Version -notmatch '^\d{4}\.\d{2}\.\d{2}-r\d+(?:-[a-zA-Z0-9.]+)?$') {
    throw 'Expected version YYYY.MM.DD-rN with optional local suffix.'
}
$numericVersion = [regex]::Match($Version, '^(\d{4})\.(\d{2})\.(\d{2})-r(\d+)')
$fileVersion = ($numericVersion.Groups[1..4] | ForEach-Object { [int]$_.Value }) -join '.'
$sourcePath = (Resolve-Path -LiteralPath $SourceDir).Path
foreach ($item in @('AutoE7.exe', '_internal', 'assets', 'scenarios.json', 'release_config.json')) {
    if (-not (Test-Path -LiteralPath (Join-Path $sourcePath $item))) { throw "Missing application payload: $item" }
}
$payloadConfig = Get-Content -LiteralPath (Join-Path $sourcePath 'release_config.json') -Raw | ConvertFrom-Json
if ($payloadConfig.version -ne $Version) { throw 'Installer version must match the staged application version.' }
if (-not $OutputDir) { $OutputDir = Join-Path $projectRoot 'release' }
$outputPath = [IO.Path]::GetFullPath($OutputDir)
[IO.Directory]::CreateDirectory($outputPath) | Out-Null

if (-not $CompilerPath) {
    $compilerCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($compilerCommand) { $CompilerPath = $compilerCommand.Source }
    foreach ($candidate in @(
        (Join-Path $projectRoot '.build-deps\inno\ISCC.exe'),
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )) {
        if (-not $CompilerPath -and (Test-Path -LiteralPath $candidate)) { $CompilerPath = $candidate }
    }
}
if (-not $CompilerPath -or -not (Test-Path -LiteralPath $CompilerPath)) {
    throw 'Inno Setup 6 ISCC.exe was not found. Install Inno Setup or pass -CompilerPath.'
}
$logDir = Join-Path $projectRoot "build/installer-$Version"
[IO.Directory]::CreateDirectory($logDir) | Out-Null
$logFile = Join-Path $logDir 'build.log'
& $CompilerPath "/DSourceDir=$sourcePath" "/DOutputDir=$outputPath" "/DAppVersion=$Version" "/DAppFileVersion=$fileVersion" (Join-Path $PSScriptRoot 'AutoE7.iss') 2>&1 | Tee-Object -FilePath $logFile
if ($LASTEXITCODE -ne 0) { throw "Installer compilation failed. See $logFile" }
$installerPath = Join-Path $outputPath "AutoE7-Setup-$Version.exe"
if (-not (Test-Path -LiteralPath $installerPath)) { throw 'Compiler reported success but the installer was not created.' }
$digest = (Get-FileHash -LiteralPath $installerPath -Algorithm SHA256).Hash.ToLowerInvariant()
[IO.File]::WriteAllText("$installerPath.sha256", "$digest  $([IO.Path]::GetFileName($installerPath))`n", [Text.UTF8Encoding]::new($false))
Write-Output "Installer: $installerPath"
Write-Output "Build log: $logFile"
