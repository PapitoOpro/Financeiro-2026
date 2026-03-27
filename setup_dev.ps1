<#
setup_dev.ps1
PowerShell helper to create a virtualenv and install Python dependencies for the Financeiro-2026 project.

Usage (run from repo root):
  PowerShell (normal user):
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    .\setup_dev.ps1

Options:
  -InstallBuildTools    Instala Visual Studio Build Tools via winget (requer admin e winget)
  -SkipRequirements     Cria o venv mas não instala `requirements.txt`
  -PythonVersion '3.11' Versão Python preferida para o venv (padrão 3.11)

#>

param(
    [switch]$InstallBuildTools = $false,
    [switch]$SkipRequirements = $false,
    [string]$PythonVersion = "3.11"
)

$ErrorActionPreference = 'Stop'

function Write-Ok([string]$m){ Write-Host $m -ForegroundColor Green }
function Write-Warn([string]$m){ Write-Host $m -ForegroundColor Yellow }
function Write-Err([string]$m){ Write-Host $m -ForegroundColor Red }

Write-Host "== Financeiro-2026: Setup de desenvolvimento =="

Write-Host "Procurando Python (recomendado: $PythonVersion) ..."

$usePyLauncher = $false
if (Get-Command py -ErrorAction SilentlyContinue) {
    try { & py -$PythonVersion -c "import sys" > $null 2>&1; if ($LASTEXITCODE -eq 0) { $usePyLauncher = $true } } catch {}
}

$useSystemPython = $false
if (-not $usePyLauncher -and (Get-Command python -ErrorAction SilentlyContinue)) {
    try {
        $verTuple = (& python -c "import sys; print('%d.%d' % (sys.version_info[0], sys.version_info[1]))" 2>&1).Trim()
        if ($verTuple) {
            $parts = $verTuple.Split('.')
            if ([int]$parts[0] -gt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge ([int]($PythonVersion.Split('.')[1])))) { $useSystemPython = $true }
        }
    } catch {}
}

if (-not $usePyLauncher -and -not $useSystemPython) {
    Write-Err "Python 3.11+ não foi encontrado. Instale Python 3.11 (https://www.python.org/downloads/windows/) ou use o launcher 'py'."
    exit 1
}

if ($InstallBuildTools) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Warn "Instalação do Visual Studio Build Tools via winget iniciada (requer confirmação/admin). Isso pode demorar."
        winget install --id Microsoft.VisualStudio.2022.BuildTools -e --accept-package-agreements --accept-source-agreements
    } else {
        Write-Warn "winget não encontrado: instale as Build Tools manualmente: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022"
    }
}

if (-not (Test-Path -Path ".venv")) {
    Write-Host "Criando virtualenv em .venv..."
    if ($usePyLauncher) { & py -$PythonVersion -m venv .venv } else { & python -m venv .venv }
    if ($LASTEXITCODE -ne 0) { Write-Err "Erro ao criar virtualenv."; exit 1 }
    Write-Ok "Virtualenv criado em .venv"
} else {
    Write-Warn ".venv já existe — pulando criação"
}

$venvPy = Join-Path (Resolve-Path .venv).Path "Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Err "Python dentro do venv não encontrado: $venvPy"; exit 1 }

Write-Host "Atualizando pip, setuptools e wheel no venv..."
& $venvPy -m pip install --upgrade pip setuptools wheel

if (-not $SkipRequirements) {
    if (Test-Path "requirements.txt") {
        Write-Host "Instalando dependências do requirements.txt (pode demorar)..."
        & $venvPy -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { Write-Warn "Algumas dependências falharam na instalação. Veja mensagens acima. Tente usar Python 3.11 ou instale Build Tools." }
    } else {
        Write-Warn "Arquivo requirements.txt não encontrado — pulando instalação de dependências." 
    }
} else {
    Write-Warn "Flag -SkipRequirements ativada — pulando instalação de requirements.txt"
}

Write-Host "\nVerificando módulos importantes..."
try {
    & $venvPy -c "import cv2; print(cv2.__version__)" > $null 2>&1
    if ($LASTEXITCODE -eq 0) { Write-Ok "cv2 (OpenCV) disponível no venv." } else { Write-Warn "cv2 não disponível no venv." }
} catch { Write-Warn "cv2 import falhou." }

if (Get-Command tesseract -ErrorAction SilentlyContinue) { Write-Ok "Tesseract (binário) disponível." } else { Write-Warn "Tesseract não encontrado. Instale Tesseract OCR (ex: UB-Mannheim build) e adicione ao PATH." }

if (Get-Command pdftoppm -ErrorAction SilentlyContinue) { Write-Ok "Poppler (pdftoppm) disponível." } else { Write-Warn "Poppler não encontrado. Para extração melhor de PDFs instale Poppler e adicione ao PATH." }

Write-Host "\nSetup concluído." 
Write-Host "Ative o venv com: .\\.venv\\Scripts\\Activate.ps1"
Write-Host "Rode a aplicação com: python -m streamlit run app.py"
Write-Host "Ou, usando o python do venv: .\\.venv\\Scripts\\python.exe -m streamlit run app.py"

Write-Ok "Boas práticas: use Python 3.11, e instale Tesseract/Poppler se for usar OCR ou conversão de PDF."
