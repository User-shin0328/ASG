param([string]$Python = "$PSScriptRoot\..\.venv\Scripts\python.exe")
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $ProjectRoot
try {
    & $Python -m PyInstaller --noconfirm --clean --onefile --console --name ASG --paths . --distpath . --workpath build/pyinstaller --specpath build --add-data "$ProjectRoot/config;config" --add-data "$ProjectRoot/fixtures/documents;fixtures/documents" --add-data "$ProjectRoot/dashboard/index.html;dashboard" --add-data "$ProjectRoot/dashboard/app.css;dashboard" --add-data "$ProjectRoot/dashboard/app.js;dashboard" launcher/asg.py
    if ($LASTEXITCODE -ne 0) { throw 'Executable build failed' }
    Get-Item -LiteralPath (Join-Path $ProjectRoot 'ASG.exe') | Select-Object FullName, Length
} finally { Pop-Location }
