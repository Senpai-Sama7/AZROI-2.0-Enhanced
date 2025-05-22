@echo off
REM Autonomous AI Architect - Windows Setup Script
REM This script provides an easy setup process for Windows users

echo.
echo ===============================================================
echo            AUTONOMOUS AI ARCHITECT WINDOWS INSTALLER           
echo ===============================================================
echo.

REM Check for prerequisites
echo Checking prerequisites...
echo.

REM Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Please install Python 3.9 or newer.
    echo Visit: https://www.python.org/downloads/
    echo.
    goto :error
) else (
    for /f "tokens=2" %%I in ('python --version 2^>^&1') do set PYTHON_VERSION=%%I
    echo [OK] Python %PYTHON_VERSION% found.
)

REM Check Docker
docker --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker not found. Please install Docker Desktop.
    echo Visit: https://www.docker.com/products/docker-desktop/
    echo.
    goto :error
) else (
    for /f "tokens=3" %%I in ('docker --version') do set DOCKER_VERSION=%%I
    echo [OK] Docker %DOCKER_VERSION% found.
)

REM Check if Docker is running
docker ps >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker is installed but not running.
    echo Please start Docker Desktop and run this script again.
    echo.
    goto :error
) else (
    echo [OK] Docker is running.
)

REM Check Google Cloud SDK
gcloud --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Google Cloud SDK not found. Please install it.
    echo Visit: https://cloud.google.com/sdk/docs/install
    echo.
    goto :error
) else (
    for /f "tokens=4" %%I in ('gcloud --version 2^>^&1 ^| findstr /C:"Google Cloud SDK"') do set GCLOUD_VERSION=%%I
    echo [OK] Google Cloud SDK %GCLOUD_VERSION% found.
)

echo.
echo All prerequisites are met!
echo.
echo ---------------------------------------------------------------
echo.
echo This script will help you set up the Autonomous AI Architect on Windows.
echo.
echo The full setup requires manual steps for Google Cloud Platform.
echo Due to the complexity of GCP setup on Windows, we'll guide you through
echo those steps, but some parts need to be done manually.
echo.
echo Press any key to continue with the setup...
pause >nul

REM Provide billing information
echo.
echo ===============================================================
echo                    GCP BILLING INFORMATION
echo ===============================================================
echo.
echo This system uses Google Cloud Platform services which will incur
echo charges to your GCP account. Before proceeding, please be aware:
echo.
echo Estimated monthly costs for typical usage: $5-$20 USD
echo depending on:
echo - The number of applications you deploy
echo - The compute resources you use
echo - The storage requirements of your applications
echo.
echo Services that incur charges include:
echo - Google Cloud Storage (for storing your code)
echo - Google Artifact Registry (for storing Docker images) 
echo - Google Cloud Build (for building your applications)
echo - Google Cloud Run (for running your deployed applications)
echo.
echo You can monitor costs in the GCP Console Billing section:
echo https://console.cloud.google.com/billing
echo.
echo Do you understand and accept these potential charges? (Y/N)
set /p BILLING_CONFIRMED=

if /I not "%BILLING_CONFIRMED%"=="Y" (
    echo.
    echo Setup canceled. You must acknowledge the billing information to continue.
    goto :error
)

REM Create folder structure if needed
if not exist "secrets" (
    mkdir secrets
    echo Created 'secrets' directory.
)

REM Instructions for GCP setup
echo.
echo ===============================================================
echo                   GOOGLE CLOUD PLATFORM SETUP                  
echo ===============================================================
echo.
echo Please follow these steps to set up your GCP project:
echo.
echo 1. Open the Google Cloud Console in your browser:
echo    https://console.cloud.google.com/
echo.
echo 2. Create a new project or select an existing one.
echo.
echo 3. Enable the following APIs:
echo    - IAM API (iam.googleapis.com)
echo    - Cloud Resource Manager API (cloudresourcemanager.googleapis.com)
echo    - Cloud Storage API (storage.googleapis.com)
echo    - Artifact Registry API (artifactregistry.googleapis.com)
echo    - Cloud Build API (cloudbuild.googleapis.com)
echo    - Cloud Run Admin API (run.googleapis.com)
echo    - Service Usage API (serviceusage.googleapis.com)
echo.
echo 4. Create a service account with the following roles:
echo    - Storage Admin (roles/storage.admin)
echo    - Cloud Build Editor (roles/cloudbuild.builds.editor)
echo    - Artifact Registry Administrator (roles/artifactregistry.admin)
echo    - Cloud Run Admin (roles/run.admin)
echo    - Service Account User (roles/iam.serviceAccountUser)
echo    - Logs Writer (roles/logging.logWriter)
echo    - Monitoring Metric Writer (roles/monitoring.metricWriter)
echo.
echo 5. Create and download a JSON key for the service account.
echo.
echo 6. Save the key file to: secrets\architect-super-sa-key.json
echo.
echo Have you completed these steps? (Y/N)
set /p GCP_SETUP_DONE=

if /I not "%GCP_SETUP_DONE%"=="Y" (
    echo.
    echo Please complete the GCP setup before continuing.
    echo You can run this script again after completing the setup.
    goto :error
)

REM Check if the key file exists
if not exist "secrets\architect-super-sa-key.json" (
    echo.
    echo [ERROR] Service account key file not found at secrets\architect-super-sa-key.json
    echo Please download your service account key and save it to this location.
    goto :error
)

REM Setup backend
echo.
echo ===============================================================
echo                        BACKEND SETUP                          
echo ===============================================================
echo.

cd backend

REM Create virtual environment
echo Creating Python virtual environment...
python -m venv .venv
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to create virtual environment.
    goto :error
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install dependencies
echo Installing Python dependencies (this may take several minutes)...
python -m pip install --upgrade pip
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Some dependencies might not have installed correctly.
    echo You can try manually installing them later if you encounter issues.
)

REM Create .env file
echo.
echo Creating .env file...
echo.
echo Please enter the following information:
echo.

set /p PROJECT_ID=Enter your GCP project ID: 
set /p REGION=Enter your GCP region (default: us-central1): 
if "%REGION%"=="" set REGION=us-central1

set /p GEMINI_API_KEY=Enter your Google Gemini API key (or press Enter to skip): 

echo Use Azure OpenAI? (Y/N)
set /p USE_AZURE=
if /I "%USE_AZURE%"=="Y" (
    set /p AZURE_KEY=Enter your Azure OpenAI API key: 
    set /p AZURE_BASE=Enter your Azure OpenAI API base URL (default: https://azroi.openai.azure.com/): 
    if "%AZURE_BASE%"=="" set AZURE_BASE=https://azroi.openai.azure.com/
    set /p AZURE_VERSION=Enter your Azure OpenAI API version (default: 2023-03-15-preview): 
    if "%AZURE_VERSION%"=="" set AZURE_VERSION=2023-03-15-preview
    set /p AZURE_DEPLOYMENT=Enter your Azure OpenAI deployment ID (default: gpt-4o-mini): 
    if "%AZURE_DEPLOYMENT%"=="" set AZURE_DEPLOYMENT=gpt-4o-mini
) else (
    set /p OPENAI_KEY=Enter your OpenAI API key (or press Enter to skip): 
    set /p OPENAI_MODEL=Enter the OpenAI model to use (default: gpt-4-turbo): 
    if "%OPENAI_MODEL%"=="" set OPENAI_MODEL=gpt-4-turbo
)

echo # Autonomous AI Architect Environment Configuration>.env
echo # Generated by windows_setup.bat>>.env
echo.>>.env
echo # Backend API Keys>>.env
echo BACKEND_GEMINI_API_KEY=%GEMINI_API_KEY%>>.env
echo.>>.env
echo # GCP Configuration>>.env
echo GCP_PROJECT_ID=%PROJECT_ID%>>.env
echo GCP_REGION=%REGION%>>.env
echo GCS_BUCKET_NAME=azroi_bucket>>.env
echo ARTIFACT_REGISTRY_DOCKER_REPO=ai-architect-apps>>.env
echo CLOUD_RUN_SERVICE_NAME_PREFIX=ai-arch-svc>>.env
echo.>>.env
echo # ChromaDB Configuration>>.env
echo CHROMA_DB_PATH=./vectorstore_data>>.env
echo CHROMA_DB_COLLECTION_NAME=architect_memory>>.env

if /I "%USE_AZURE%"=="Y" (
    echo.>>.env
    echo # Azure OpenAI Configuration (for Open Interpreter)>>.env
    echo AZURE_OPENAI_API_KEY=%AZURE_KEY%>>.env
    echo AZURE_OPENAI_API_BASE=%AZURE_BASE%>>.env
    echo AZURE_OPENAI_API_VERSION=%AZURE_VERSION%>>.env
    echo AZURE_OPENAI_DEPLOYMENT_ID=%AZURE_DEPLOYMENT%>>.env
) else (
    echo.>>.env
    echo # OpenAI Configuration (for Open Interpreter)>>.env
    echo OPENAI_API_KEY=%OPENAI_KEY%>>.env
    echo OPEN_INTERPRETER_MODEL_STRING=%OPENAI_MODEL%>>.env
)

echo.>>.env
echo # This enables direct use of credentials file from env>>.env
echo GOOGLE_APPLICATION_CREDENTIALS=../secrets/architect-super-sa-key.json>>.env

REM Deactivate virtual environment and return to root
echo.
call .venv\Scripts\deactivate.bat
cd ..

echo.
echo ===============================================================
echo                 VERIFYING INSTALLATION
echo ===============================================================
echo.

REM Check service account key file
echo Checking service account key file...
if exist "secrets\architect-super-sa-key.json" (
    echo [OK] Service account key file exists.
) else (
    echo [ERROR] Service account key file not found.
    echo Please download your service account key and save it to secrets\architect-super-sa-key.json
    goto :error
)

REM Check backend environment
echo Checking backend environment...
if exist "backend\.venv" (
    echo [OK] Backend virtual environment exists.
) else (
    echo [ERROR] Backend virtual environment not found.
    echo Please check the installation log for errors.
    goto :error
)

REM Check backend configuration
echo Checking backend configuration...
if exist "backend\.env" (
    echo [OK] Backend configuration file exists.
) else (
    echo [ERROR] Backend configuration file not found.
    echo Please check the installation log for errors.
    goto :error
)

REM Check for frontend directory
echo Checking frontend directory...
if exist "frontend" (
    echo [OK] Frontend directory exists.
) else (
    echo [WARNING] Frontend directory not found. This is normal for pre-built versions.
)

echo.
echo Installation verification passed!
echo Your Autonomous AI Architect system is correctly installed.
echo.

REM Create a Windows start script
echo @echo off> start_architect_windows.bat
echo REM Set Google Application Credentials>> start_architect_windows.bat
echo set GOOGLE_APPLICATION_CREDENTIALS=%%CD%%\secrets\architect-super-sa-key.json>> start_architect_windows.bat
echo.>> start_architect_windows.bat
echo echo Starting Autonomous AI Architect...>> start_architect_windows.bat
echo echo.>> start_architect_windows.bat
echo cd backend>> start_architect_windows.bat
echo call .venv\Scripts\activate.bat>> start_architect_windows.bat
echo echo Starting backend server on http://localhost:8001>> start_architect_windows.bat
echo start "AI Architect Backend" cmd /c "uvicorn main:app --host 0.0.0.0 --port 8001">> start_architect_windows.bat
echo cd ..>> start_architect_windows.bat
echo.>> start_architect_windows.bat
echo echo Waiting for backend to initialize...>> start_architect_windows.bat
echo timeout /t 3 /nobreak>> start_architect_windows.bat
echo.>> start_architect_windows.bat
echo cd frontend\public ^|^| cd frontend ^|^| cd .>> start_architect_windows.bat
echo echo Starting frontend server on http://localhost:8000>> start_architect_windows.bat
echo start "AI Architect Frontend" cmd /c "python -m http.server 8000">> start_architect_windows.bat
echo cd ..>> start_architect_windows.bat
echo.>> start_architect_windows.bat
echo echo Opening in browser...>> start_architect_windows.bat
echo start http://localhost:8000>> start_architect_windows.bat
echo.>> start_architect_windows.bat
echo echo Autonomous AI Architect is now running!>> start_architect_windows.bat
echo echo Frontend: http://localhost:8000>> start_architect_windows.bat
echo echo Backend:  http://localhost:8001>> start_architect_windows.bat
echo echo.>> start_architect_windows.bat
echo echo The system is running in separate windows. To stop the servers,>> start_architect_windows.bat
echo echo close those windows or press Ctrl+C in each one.>> start_architect_windows.bat
echo echo.>> start_architect_windows.bat
echo pause>> start_architect_windows.bat

echo.
echo ===============================================================
echo                    INSTALLATION COMPLETE!                     
echo ===============================================================
echo.
echo The Autonomous AI Architect has been successfully set up on your
echo Windows system. You can now start the application by running:
echo.
echo   start_architect_windows.bat
echo.
echo Do you want to start the Autonomous AI Architect now? (Y/N)
set /p START_NOW=

if /I "%START_NOW%"=="Y" (
    call start_architect_windows.bat
) else (
    echo.
    echo You can start the application later by running start_architect_windows.bat
)

echo.
echo Thanks for installing the Autonomous AI Architect!
echo.
goto :end

:error
echo.
echo Setup encountered errors. Please fix the issues and try again.
echo.

:end
pause
