$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
& (Join-Path $projectRoot '运行环境\python\python.exe') -B -X utf8 (Join-Path $PSScriptRoot 'verify.py')
if ($LASTEXITCODE -ne 0) { throw '封存及独立审核回执核验失败' }
