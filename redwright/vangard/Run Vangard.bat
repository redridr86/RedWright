@echo off
cd /d "%~dp0"
where node >nul 2>&1
if errorlevel 1 (
  echo Install Node.js 18 or newer, then open Vangard Studio again.
  echo https://nodejs.org/
  pause
  exit /b 1
)
if not exist node_modules (
  echo Installing Vangard Studio. This happens once and can take several minutes.
  call npm install
  if errorlevel 1 (
    echo npm install failed.
    pause
    exit /b 1
  )
)
if not exist "node_modules\electron\cli.js" (
  echo Electron did not install. Delete the node_modules folder and open Vangard Studio again.
  pause
  exit /b 1
)
echo Building Vangard Studio...
call npm run build
if errorlevel 1 (
  echo The build failed.
  pause
  exit /b 1
)
echo Opening Vangard Studio...
if "%~1"=="" (
  node "node_modules\electron\cli.js" .
) else (
  node "node_modules\electron\cli.js" . --project "%~1"
)
if errorlevel 1 pause
