# Autonomous AI Architect - Easy Installation Guide

This guide provides a simplified approach to installing and setting up the Autonomous AI Architect system. Follow these steps to get started quickly.

## One-Click Installation

We've created a simple installation script that automates most of the setup process. This is the recommended approach for users without technical experience.

### Step 1: Download the System

Make sure you have the entire Autonomous AI Architect system downloaded and extracted to a directory on your computer.

### Step 2: Run the Installation Script

1. Open a terminal/command prompt
2. Navigate to the directory containing the Autonomous AI Architect files
3. Run the following commands:

```bash
# Make the installation script executable
chmod +x easy_install.sh

# Run the installation script
./easy_install.sh
```

4. Follow the prompts in the script to complete the installation

The script will:
- Check for required prerequisites (Python, Docker, Google Cloud SDK)
- Guide you through setting up your Google Cloud Platform account
- Configure the backend environment
- Set up everything needed to run the system

### Step 3: Start Using the System

Once installation is complete, you can access the Autonomous AI Architect by opening a web browser and navigating to:

```
http://localhost:8000
```

## What You'll Need

Before running the installation script, make sure you have:

1. **A computer** with Linux, macOS, or Windows with WSL
2. **Python 3.9 or newer** installed
3. **Docker Desktop** (or Docker Engine for Linux) installed and running
4. **Google Cloud SDK** installed
5. **A Google Cloud Platform account** with billing enabled
6. **API Keys** (recommended but not required during installation):
   - Google Gemini API key (for the Planner Agent)
   - Azure OpenAI API key or standard OpenAI API key (for the Code Execution Agent)

The installation script will check for these requirements and guide you through setting up any missing components.

## Important: Google Cloud Platform Billing Information

This system uses Google Cloud Platform services which will incur charges to your GCP account. Before proceeding with installation, please be aware of the following:

- **Estimated monthly costs** for typical usage are between $5-$20 USD depending on:
  - The number of applications you deploy
  - The compute resources you use
  - The storage requirements of your applications

- **Services that incur charges include**:
  - Google Cloud Storage (for storing your code)
  - Google Artifact Registry (for storing Docker images)
  - Google Cloud Build (for building your applications)
  - Google Cloud Run (for running your deployed applications)

- **Cost Management**:
  - You can monitor your costs in the [GCP Console Billing section](https://console.cloud.google.com/billing)
  - Set up [budget alerts](https://cloud.google.com/billing/docs/how-to/budgets) to avoid unexpected charges
  - Deployed applications can be stopped or deleted when not in use to minimize costs

The installation script will ask you to confirm that you understand these potential charges before proceeding with the Google Cloud Platform setup.

## Manual Installation

If you prefer to follow the manual installation steps, or if you encounter issues with the automatic script, please refer to the comprehensive [HOW_TO_USE.md](HOW_TO_USE.md) guide, which provides detailed instructions for each step of the installation process.

## Troubleshooting

If you encounter issues during installation:

### Prerequisites Issues

1. **Python not found or wrong version**
   - Install Python 3.9+ from [python.org](https://www.python.org/downloads/)
   - On Linux: `sudo apt install python3.9 python3.9-venv`
   - On macOS with Homebrew: `brew install python@3.9`

2. **Docker issues**
   - Ensure Docker Desktop is installed and running
   - On Linux, check if the Docker daemon is running: `sudo systemctl status docker`
   - Try running `docker ps` to verify Docker works correctly

3. **Google Cloud SDK issues**
   - Install from [cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)
   - Make sure it's in your PATH: `echo $PATH`
   - Run `gcloud init` to authenticate

### GCP Setup Issues

1. **Failed to create GCP project**
   - Check you have sufficient permissions
   - Create a project manually through the [GCP Console](https://console.cloud.google.com/)
   - Ensure you have a valid billing account linked

2. **Failed to enable APIs**
   - Enable them manually in the [API Library](https://console.cloud.google.com/apis/library)
   - Check for any billing issues with your GCP account

3. **Service account issues**
   - Create a service account manually in the [IAM Console](https://console.cloud.google.com/iam-admin/serviceaccounts)
   - Grant the required roles manually
   - Download the key file and place it in `secrets/architect-super-sa-key.json`

### Backend Setup Issues

1. **Virtual environment creation fails**
   - Install the venv module: `python3 -m pip install virtualenv`
   - Try manually creating it: `python3 -m venv backend/.venv`

2. **Dependency installation fails**
   - Update pip: `python3 -m pip install --upgrade pip`
   - Check your internet connection
   - Install dependencies one by one to identify problematic packages

3. **Configuration issues**
   - Check if .env file exists in the backend directory
   - Make sure all required environment variables are set

### System Startup Issues

1. **Backend server won't start**
   - Check if port 8001 is already in use: `lsof -i :8001` or `netstat -tuln | grep 8001`
   - Check backend logs for specific error messages
   - Try starting manually: `cd backend && source .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8001`

2. **Frontend server won't start**
   - Check if port 8000 is already in use: `lsof -i :8000` or `netstat -tuln | grep 8000`
   - Verify frontend directory structure
   - Try starting manually: `cd frontend/public && python3 -m http.server 8000`

3. **Browser doesn't open automatically**
   - Open your browser manually and navigate to `http://localhost:8000`

### Windows-Specific Issues

1. **Windows Subsystem for Linux (WSL) issues**
   - Ensure WSL is installed: Run `wsl --install` in PowerShell as administrator
   - Make sure you're using WSL 2: Run `wsl --set-default-version 2`
   - For command line tools, use a WSL terminal or Command Prompt, not PowerShell

2. **Docker Desktop on Windows issues**
   - Ensure WSL 2 integration is enabled in Docker Desktop settings
   - Restart Docker Desktop after installation
   - Make sure Hyper-V and WSL 2 features are enabled in Windows

3. **Windows path issues**
   - Check for spaces in directory paths (these can cause problems)
   - Use forward slashes (/) instead of backslashes (\\) in paths when running commands in WSL
   - Add Python and other tools to your system PATH environment variable

4. **Windows-specific error messages**
   - "Access denied" errors: Run Command Prompt as administrator
   - "The system cannot find the path specified": Check current directory and paths
   - "Windows Defender prevented this action": Add exclusions for development folders

If issues persist, refer to the detailed [HOW_TO_USE.md](HOW_TO_USE.md) document for more information or seek help from the support team.

## After Installation

Once your system is installed and running, you can start creating amazing applications right away! Check out the [10 Powerful Project Examples](HOW_TO_USE.md#10-powerful-project-examples) in the HOW_TO_USE.md guide for inspiration on what you can build.
