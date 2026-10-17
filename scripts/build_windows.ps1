$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$icon = Join-Path $projectRoot 'src\f1widget\assets\app.ico'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Create .venv and install the project with its build extra first. See README.'
}
Push-Location $projectRoot
$originalPath = $env:PATH
try {
    # Prevent unrelated applications' runtime DLLs from entering the bundle.
    $env:PATH = "$projectRoot\.venv\Scripts;$env:SystemRoot\System32;$env:SystemRoot"
    & $python -m PyInstaller --clean --noconfirm --onefile --windowed --noupx --icon $icon `
        --add-data "${icon}:f1widget/assets" `
        --name F1Standings --paths src --specpath build --distpath dist `
        --workpath build\pyinstaller packaging\launcher.py
    if ($LASTEXITCODE -ne 0) { throw 'Windows build failed.' }
    Write-Host 'Ready: dist\F1Standings.exe'
} finally {
    $env:PATH = $originalPath
    Pop-Location
}
