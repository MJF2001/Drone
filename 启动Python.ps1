param([Parameter(ValueFromRemainingArguments=$true)][string[]]$PythonArgs)
$ErrorActionPreference = 'Stop'
$packageRoot = $PSScriptRoot
$runtimeRoot = Join-Path $packageRoot '运行环境'
$pythonExe = Join-Path $runtimeRoot 'python\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Host '首次启动：解压本包Python运行环境。'
    Expand-Archive -LiteralPath (Join-Path $runtimeRoot 'python312_windows_x64.zip') -DestinationPath $runtimeRoot
}
$algorithmRoot = Join-Path $packageRoot '研究方案_剩余覆盖重规划_20261009\算法小型验证_20261010'
$oldPythonPath = $env:PYTHONPATH
$oldPythonHome = $env:PYTHONHOME
try {
    $env:PYTHONPATH = (Join-Path $algorithmRoot '.deps') + ';' + $packageRoot + ';' + $algorithmRoot
    $env:PYTHONHOME = Join-Path $runtimeRoot 'python'
    Push-Location -LiteralPath $algorithmRoot
    try { & $pythonExe -X utf8 @PythonArgs; $pythonExit = $LASTEXITCODE }
    finally { Pop-Location }
} finally {
    $env:PYTHONPATH = $oldPythonPath
    $env:PYTHONHOME = $oldPythonHome
}
exit $pythonExit
