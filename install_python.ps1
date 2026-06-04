# Emma Sarming Store - Automated Python & Environment Installer Script
# This script will install Python 3.12, set up a virtual environment, and install all dependencies.

$ErrorActionPreference = "Stop"

Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "           Emma Sarming Store - Setup & Installation          " -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan

# 1. Check if Python is already installed on the host
$pythonInstalled = $false
try {
    $ver = python --version 2>&1
    if ($ver -match "Python 3\.") {
        Write-Host "Found existing Python installation: $ver" -ForegroundColor Green
        $pythonInstalled = $true
    }
} catch {}

if (-not $pythonInstalled) {
    # 2. Download Python 3.12.8 Installer
    $installerPath = "$env:TEMP\python-3.12.8-amd64.exe"
    $downloadUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    
    Write-Host "Downloading Python 3.12.8 (64-bit)..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath
    
    # 3. Silent installation (User-level, no Admin rights needed!)
    Write-Host "Installing Python 3.12.8 silently..." -ForegroundColor Yellow
    $installArgs = "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_doc=0 Include_launcher=1"
    $process = Start-Process -FilePath $installerPath -ArgumentList $installArgs -PassThru -Wait
    
    # Check exit code
    if ($process.ExitCode -eq 0) {
        Write-Host "Python 3.12.8 installed successfully!" -ForegroundColor Green
    } else {
        Write-Host "Python installation failed with exit code: $($process.ExitCode)" -ForegroundColor Red
        Exit $process.ExitCode
    }
    
    # Cleanup
    Remove-Item -Path $installerPath -Force
    
    # Refresh PATH environment variable in current PowerShell session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "Machine")
}

# 4. Create Virtual Environment
Write-Host "Creating Python Virtual Environment (venv)..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "Virtual environment (venv) already exists. Skipping creation." -ForegroundColor Cyan
} else {
    python -m venv venv
    Write-Host "Virtual environment (venv) created successfully!" -ForegroundColor Green
}

# 5. Install Dependencies from requirements.txt
Write-Host "Installing project dependencies from requirements.txt..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe -m pip install --upgrade pip
& .\venv\Scripts\pip.exe install -r requirements.txt

Write-Host "=========================================================" -ForegroundColor Green
Write-Host " Emma Sarming Store is now fully set up and ready to run!     " -ForegroundColor Green
Write-Host " To run the application, use:                            " -ForegroundColor Green
Write-Host "   .\venv\Scripts\python.exe app.py                      " -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Green
