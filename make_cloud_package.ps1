# 生成云函数上传包 cloud/scut-jw-fc.zip
# 包含 fetch.py / cloud_handler.py / config.json（凭据为空，运行时由环境变量注入）
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$pkg = Join-Path $env:TEMP "scut-jw-pkg"
Remove-Item -Recurse -Force $pkg -ErrorAction SilentlyContinue
New-Item -ItemType Directory $pkg | Out-Null

Copy-Item (Join-Path $root "fetch.py") $pkg
Copy-Item (Join-Path $root "cloud_handler.py") $pkg
Copy-Item (Join-Path $root "config.example.json") (Join-Path $pkg "config.json")

$out = Join-Path $root "cloud"
New-Item -ItemType Directory -Force $out | Out-Null
$zip = Join-Path $out "scut-jw-fc.zip"
Compress-Archive -Path (Join-Path $pkg "*") -DestinationPath $zip -Force

Write-Host "已生成: $zip"
Get-ChildItem $pkg | Select-Object Name, Length | Format-Table
