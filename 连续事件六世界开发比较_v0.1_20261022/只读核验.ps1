$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot '..\运行环境\python\python.exe') -B -X utf8 (Join-Path $PSScriptRoot 'verify.py')
if ($LASTEXITCODE -ne 0) { throw '只读核验失败' }
