<#
Setup script for Financeiro-2026 (Windows PowerShell)
Usage:
  Open PowerShell in the repo root and run:
    powershell -ExecutionPolicy Bypass -File .\scripts\setup_venv.ps1
  To also install optional binaries (Tesseract/Poppler via Chocolatey):
    powershell -ExecutionPolicy Bypass -File .\scripts\setup_venv.ps1 -InstallOptionalBinaries

This script will:
 - locate Python (preferring py -3.11),
 - create a virtual environment in `.venv` (if missing),
 - upgrade pip/setuptools/wheel,
 - install packages from `requirements.txt`.

Note: installing Tesseract/Poppler requires Chocolatey and admin privileges.
#>

param(
    [switch]$InstallOptionalBinaries
)

function Write-Info($m) { Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Write-Warn($m) { Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Write-Err($m) { Write-Host "[ERROR] $m" -ForegroundColor Red }

Write-Info "Procurando Python 3.11 (prefere 'py -3.11' quando disponível)..."

$pythonCaller = $null
$pythonFlag = $null

# Prefer 'py -3.11' if available
try {
    & py -3.11 -c "import sys; print(sys.executable)" > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        $pythonCaller = 'py'
        $pythonFlag = '-3.11'
    }
} catch {}

# Fallback to 'python' in PATH
if (-not $pythonCaller) {
    try {
        $v = & python -c "import sys; print(sys.version)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $pythonCaller = 'python'
            $pythonFlag = $null
        }
    } catch {}
}

if (-not $pythonCaller) {
    Write-Err "Python não encontrado. Instale Python 3.11 e execute novamente."
    exit 1
}

Write-Info "Usando: $pythonCaller $($pythonFlag -join ' ')"

# Create venv if missing
$venvPath = Join-Path $PSScriptRoot ".." | Resolve-Path -Relative | ForEach-Object { Join-Path $_ ".venv" }
$venvPath = Join-Path (Get-Location) ".venv"

if (-not (Test-Path $venvPath)) {
    Write-Info "Criando virtualenv em $venvPath..."
    if ($pythonFlag) {
        & $pythonCaller $pythonFlag -m venv $venvPath
    } else {
        & $pythonCaller -m venv $venvPath
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Falha ao criar virtualenv. Saindo."
        exit 1
    }
} else {
    Write-Info ".venv já existe — pulando criação."
}

$venvPython = Join-Path $venvPath "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Err "Python dentro do venv não encontrado em $venvPython"
    exit 1
}

# Upgrade pip
Write-Info "Atualizando pip, setuptools e wheel..."
& $venvPython -m pip install --upgrade pip setuptools wheel

# Install requirements
if (Test-Path "requirements.txt") {
    Write-Info "Instalando dependências de requirements.txt..."
    & $venvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "pip retornou código de erro — verifique o output acima."
    }
} else {
    Write-Warn "requirements.txt não encontrado — pulando instalação de pacotes."
}

if ($InstallOptionalBinaries) {
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Info "Instalando Tesseract e Poppler via Chocolatey (requer privilégios admin)..."
        choco install -y tesseract poppler
    } else {
        Write-Warn "Chocolatey não encontrado. Instale Chocolatey ou instale Tesseract/Poppler manualmente."
    }
}

Write-Host ""
Write-Info "Concluído. Para ativar o venv (PowerShell):"
Write-Host "  .\\.venv\\Scripts\\Activate.ps1"
Write-Info "Ou (CMD):"
Write-Host "  .\\.venv\\Scripts\\activate.bat"
Write-Info "Para rodar a app:"
Write-Host "  streamlit run app.py"
Write-Host ""
Write-Info "Dica: crie .streamlit/secrets.toml com suas configurações de BD antes de rodar, se necessário."
