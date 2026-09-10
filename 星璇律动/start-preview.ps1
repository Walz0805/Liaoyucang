$ErrorActionPreference = 'Stop'
$previewNode = Get-Command node -ErrorAction SilentlyContinue
$previewNodePath = if ($previewNode) { $previewNode.Source } else { Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' }
if (-not (Test-Path -LiteralPath $previewNodePath)) { throw 'Node.js runtime not found.' }
$previewRunning = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if (-not $previewRunning) {
    Start-Process -FilePath $previewNodePath -ArgumentList 'server.cjs' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $PSScriptRoot 'preview.log') -RedirectStandardError (Join-Path $PSScriptRoot 'preview-error.log')
}
Write-Host 'Preview: http://127.0.0.1:5173/'
