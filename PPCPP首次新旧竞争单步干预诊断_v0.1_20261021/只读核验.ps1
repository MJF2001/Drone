$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $taskRoot
& (Join-Path $projectRoot '运行环境/python/python.exe') -B -X utf8 (Join-Path $taskRoot 'verify.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
