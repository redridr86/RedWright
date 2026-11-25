@echo off
setlocal
cd /d "%~dp0"

py -3.12 -c "import sys,struct; raise SystemExit(0 if struct.calcsize('P')==8 else 1)" >nul 2>&1
if errorlevel 1 (
  echo RedWright needs 64-bit Python 3.12 for PyTorch ROCm 7.14.
  echo Install Python 3.12 from python.org and check "Add python.exe to PATH".
  pause
  exit /b 1
)

if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if sys.version_info[:2]==(3,12) else 1)"
  if errorlevel 1 (
    echo Removing .venv so it can be rebuilt with Python 3.12.
    rmdir /s /q .venv
  )
)
if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv
  if errorlevel 1 (
    echo Could not create the virtual environment.
    pause
    exit /b 1
  )
)

call .venv\Scripts\activate
python -c "import torch; raise SystemExit(0 if 'rocm7.14' in torch.__version__ else 1)" >nul 2>&1
if errorlevel 1 (
  echo Installing PyTorch 2.12 for ROCm 7.14. This replaces DirectML and can take several minutes.
  python -m pip uninstall -y torch torchvision torchaudio torch-directml >nul 2>&1
  python -m pip install --upgrade pip
  python -m pip install --extra-index-url https://repo.amd.com/rocm/whl-multi-arch/ "torch[device-all]==2.12.0+rocm7.14.0" "torchvision[device-all]==0.27.0+rocm7.14.0"
  if errorlevel 1 (
    echo ROCm PyTorch did not install.
    echo Delete the .venv folder and run this again with Python 3.12.
    pause
    exit /b 1
  )
)
python -c "import diffusers, PIL, peft" >nul 2>&1
if errorlevel 1 (
  echo Installing the picture and LoRA libraries.
  python -m pip install "diffusers==0.32.2" "transformers==4.46.3" "accelerate==1.1.1" "peft==0.13.2" safetensors pillow numpy
  if errorlevel 1 (
    echo Could not finish the library install.
    pause
    exit /b 1
  )
)
echo Starting "%CD%\redgen.py"
findstr /C:"stamp: RedWright build 62." redgen.py >nul
if errorlevel 1 (
  echo.
  echo This folder does not look like RedWright build 62.
  pause
  exit /b 1
)
if exist __pycache__ rmdir /s /q __pycache__
python -B redgen.py
if errorlevel 1 pause
