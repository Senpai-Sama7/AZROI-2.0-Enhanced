# Autonomous AI Architect - Full Stack & Functional

This project provides a user interface and a **functional backend** for an Autonomous AI Architect system. It enables users to input high-level goals, receive AI-powered analysis and planning, and oversee AI agents performing real architectural tasks including code generation, Dockerization, and deployment to Google Cloud Platform.

**Current Status: Core backend pipeline is functional.**
-   Planner Agent uses Gemini.
-   Code Execution Agent uses Open Interpreter (can be configured for Azure OpenAI or standard OpenAI/local models).
-   Cloud Agent uses GCP SDKs to interact with GCS, Artifact Registry, Cloud Build, and Cloud Run.
-   Frontend displays real-time logs and artifact links.
-   Comprehensive test suite for agent functionality.

## Project Vision

The goal is to create a system where a user can define a complex software or system architecture objective, and a team of specialized AI agents, orchestrated by a main Architect AI, will:
1.  Decompose the goal into a detailed, actionable plan.
2.  Generate application code using tools like Open Interpreter.
3.  Create `Dockerfile`s for containerization.
4.  Upload artifacts to Google Cloud Storage (GCS).
5.  Trigger Google Cloud Build to create Docker images and push them to Google Artifact Registry (GAR).
6.  Deploy these images as services on Google Cloud Run.
7.  Store all plans, code paths, artifact URIs, logs, and statuses in a persistent vector memory (ChromaDB).
8.  Stream real-time progress to the user via the frontend UI.

This UI serves as the "Mission Control" for such a system.

## Project Structure

```
autonomous-ai-architect-ui/
├── frontend/
│   ├── public/index.html       # Main HTML for the UI
│   └── src/                    # React/TypeScript source code for UI
│       ├── App.tsx
│       ├── components/
│       ├── services/
│       ├── constants.ts
│       ├── index.tsx
│       └── types.ts
│
├── backend/
│   ├── .env                  # (Gitignored) Backend API Keys, GCP Config, OI Config
│   ├── .env.example          # Example for backend .env
│   ├── main.py               # FastAPI app, WebSocket, API endpoints
│   ├── config.json           # Backend configurations (defaults, can be overridden by .env)
│   ├── requirements.txt      # Python dependencies for the backend
│   ├── agents/               # AI agent implementations (functional)
│   │   ├── architect_agent.py    # Main orchestrator
│   │   ├── planner_agent.py      # Goal decomposition using Gemini
│   │   ├── code_execution_agent.py # Code/Dockerfile generation via Open Interpreter
│   │   └── cloud_agent.py        # GCP interactions (GCS, AR, Build, Run)
│   ├── tools/                # Utility modules
│   │   ├── memory_manager.py   # ChromaDB interaction for persistent memory
│   │   └── gcp_setup_example.py # Reference for GCP SDK authentication
│   ├── outputs/              # (Gitignored) Base directory for Open Interpreter code generation
│   │   └── code_executions/    # Task-specific code will be saved here
│   └── vectorstore_data/     # (Gitignored) ChromaDB persistent data
│
├── secrets/
│   └── architect-super-sa-key.json # (Gitignored) Your GCP Service Account Key JSON file
│
├── .gitignore                    # Specifies intentionally untracked files
├── README.md (This file)         # Project overview, setup, and usage instructions
└── start_autonomous_ai_architect.sh # Script to start both frontend and backend
```

## CRITICAL SETUP INSTRUCTIONS

Follow these steps meticulously to set up and run the system.

### 1. Prerequisites:
   - **Python 3.9+**: Ensure Python 3.9 or newer is installed.
   - **Docker Desktop (or Docker Engine for Linux)**: **Must be installed and running.** Open Interpreter heavily relies on Docker for sandboxed code execution.
   - **`gcloud` CLI (Google Cloud SDK)**: Required for authenticating your service account key for application-default credentials, which the backend Python SDKs will use. Install from [Google Cloud SDK docs](https://cloud.google.com/sdk/docs/install).
   - **A Google Cloud Platform (GCP) Project**: With **Billing Enabled**.

### 2. GCP Project Configuration:
   **a. Project ID & Region:**
      - Your Project ID: `ai-agent-system-458618`
      - Your Region: `us-central1`
      These will be configured in `backend/.env`.

   **b. Enable APIs:** In your GCP project (`ai-agent-system-458618`), ensure the following APIs are **ENABLED**. You can do this via the GCP Console or `gcloud services enable [API_NAME]`.
      - IAM API (`iam.googleapis.com`)
      - Cloud Resource Manager API (`cloudresourcemanager.googleapis.com`)
      - Cloud Storage API (`storage.googleapis.com`)
      - Artifact Registry API (`artifactregistry.googleapis.com`)
      - Cloud Build API (`cloudbuild.googleapis.com`)
      - Cloud Run Admin API (`run.googleapis.com`)
      - Service Usage API (`serviceusage.googleapis.com`) (usually enabled by default)

   **c. Create GCP Service Account & Key:**
      1.  Navigate to "IAM & Admin" > "Service Accounts" in your GCP Console for project `ai-agent-system-458618`.
      2.  Click "CREATE SERVICE ACCOUNT".
      3.  Service account name: e.g., `ai-architect-backend-runner`
      4.  Service account ID: Will be auto-generated (e.g., `ai-architect-backend-runner`).
      5.  Description: e.g., "Service account for the Autonomous AI Architect backend system."
      6.  Click "CREATE AND CONTINUE".
      7.  **Grant IAM Roles (CRITICAL - Assign ALL of these to the service account):**
          -   `Storage Admin` (`roles/storage.admin`) - To create/manage GCS buckets and objects.
          -   `Cloud Build Editor` (`roles/cloudbuild.builds.editor`) - To trigger and manage Cloud Builds.
          -   `Artifact Registry Administrator` (`roles/artifactregistry.admin`) - To create Artifact Registry repositories and push/manage Docker images.
          -   `Cloud Run Admin` (`roles/run.admin`) - To deploy and manage Cloud Run services.
          -   `Service Account User` (`roles/iam.serviceAccountUser`) - Crucial for allowing Cloud Build and Cloud Run services to act *as this service account* if they need to perform further GCP operations (e.g., Cloud Build writing to Artifact Registry).
          -   `Logs Writer` (`roles/logging.logWriter`) - For agents to write logs to Google Cloud Logging (optional; primary logging is via WebSocket for UI).
          -   `Monitoring Metric Writer` (`roles/monitoring.metricWriter`) - For agents to write custom metrics (optional).
          -   **Important for Artifact Registry Setup:** If the Artifact Registry repository is created *by the CloudAgent*, this service account might need `Project IAM Admin` (`roles/resourcemanager.projectIamAdmin`) temporarily to set IAM policies on the new repository (to grant Cloud Build SA write access). **A safer alternative is to pre-create the Artifact Registry repository (Step 2.e) and manually grant permissions.**
      8.  Click "CONTINUE".
      9.  Click "DONE".
      10. Find your newly created service account in the list. Click the three dots (Actions) > "Manage keys".
      11. Click "ADD KEY" > "Create new key" > Select "JSON" > Click "CREATE".
      12. A JSON key file will download. **This is your service account key.**

   **d. Place Service Account Key:**
      1.  At the root of this project, create a directory named `secrets`.
      2.  Move the downloaded JSON key file into this `secrets/` directory.
      3.  Rename the key file to `architect-super-sa-key.json`.
      4.  **Path:** `secrets/architect-super-sa-key.json`
      5.  **SECURITY:** The `secrets/` directory and its contents are included in `.gitignore` and **MUST NOT be committed to version control.**

   **e. Create Artifact Registry Docker Repository (Recommended):**
      1.  In your GCP Console for project `ai-agent-system-458618`, go to "Artifact Registry".
      2.  Click "CREATE REPOSITORY".
      3.  Name: `ai-architect-apps` (This should match `ARTIFACT_REGISTRY_DOCKER_REPO` in `backend/.env`).
      4.  Format: `Docker`.
      5.  Mode: `Standard`.
      6.  Region: `us-central1` (This should match `GCP_REGION` in `backend/.env`).
      7.  Click "CREATE".
      8.  **Grant Cloud Build Service Account Permissions:**
          *   After the repository is created, select it, go to the "PERMISSIONS" tab.
          *   Click "ADD PRINCIPAL".
          *   New principals: `[YOUR_PROJECT_NUMBER]@cloudbuild.gserviceaccount.com`
              *   (Replace `[YOUR_PROJECT_NUMBER]` with your actual GCP project number. You can find this on the GCP Console Dashboard).
              *   Note: For newer projects (after April 29, 2024), the Cloud Build SA format is `service-[PROJECT_NUMBER]@gcp-sa-cloudbuild.iam.gserviceaccount.com`. Use the correct one for your project.
          *   Role: `Artifact Registry Writer` (`roles/artifactregistry.writer`).
          *   This allows Cloud Build to push images to this repository. The `CloudAgent` will also attempt to grant this if it creates the repo, but it requires broader SA permissions.

### 3. Python Backend Setup:
   1.  Navigate to the `backend/` directory: `cd backend`
   2.  Create a Python virtual environment: `python3 -m venv .venv`
   3.  Activate it: `source .venv/bin/activate` (On Windows: `.venv\Scripts\activate`)
   4.  Install dependencies: `pip install -r requirements.txt`
   5.  Copy the example environment file: `cp .env.example .env`
   6.  **Edit `backend/.env` and fill in ALL placeholder values:**
       *   `BACKEND_GEMINI_API_KEY`: Your Google Gemini API key (from Google AI Studio, for the PlannerAgent).
       *   `GCP_PROJECT_ID`: Should be `ai-agent-system-458618`.
       *   `GCP_REGION`: Should be `us-central1`.
       *   `GCS_BUCKET_NAME`: Should be `azroi_bucket`. The `CloudAgent` will attempt to create this bucket if it doesn't exist.
       *   `ARTIFACT_REGISTRY_DOCKER_REPO`: Should be `ai-architect-apps` (or whatever you named it).
       *   `CLOUD_RUN_SERVICE_NAME_PREFIX`: e.g., `ai-arch-svc`.
       *   **Azure OpenAI (for Open Interpreter - if you want to use it):**
           *   `AZURE_OPENAI_API_KEY`: Your Azure OpenAI key (`71BMy...`).
           *   `AZURE_OPENAI_API_BASE`: `https://azroi.openai.azure.com/`
           *   `AZURE_OPENAI_API_VERSION`: `2023-03-15-preview`
           *   `AZURE_OPENAI_DEPLOYMENT_ID`: `gpt-4o-mini` (This is your model deployment name on Azure).
       *   `OPENAI_API_KEY`: Your standard OpenAI API key (if you want Open Interpreter to use GPT models from OpenAI as a fallback or primary).
       *   `OPEN_INTERPRETER_MODEL_STRING`: If using Azure, this might be set by `CodeExecutionAgent` based on Azure vars. If using OpenAI, set like `gpt-4-turbo`. If local, like `ollama/mistral`.
       *   `CHROMA_DB_PATH`, `CHROMA_DB_COLLECTION_NAME`: Defaults are usually fine.

### 4. Open Interpreter Initial Setup:
   - `open-interpreter` is installed via `requirements.txt`.
   - **Docker must be running on your system.**
   - The `CodeExecutionAgent` will attempt to configure Open Interpreter based on your `backend/.env` settings (prioritizing Azure OpenAI if configured, then standard OpenAI, then the `OPEN_INTERPRETER_MODEL_STRING`).
   - For the very first time, or if Open Interpreter needs to download models or authenticate, it might interactively prompt if `safe_mode` is `ask`. The `config.json` sets `auto_run: true` and `safe_mode: "auto"` to try and make it autonomous.
   - You can test Open Interpreter standalone from your backend virtual environment: `source backend/.venv/bin/activate; interpreter` and try a simple command.

### 5. Frontend (No specific build step for this version):
   - The frontend is served as static files by a Python HTTP server, started by the main script.
   - Configure your **client-side Gemini API key** (for the "Analyze with Gemini (Client-Side)" button) via the UI: "Help & Settings" > "Client API Key". This is stored in browser `localStorage`.

### 6. Running the System:
   1.  Ensure you are in the **project root directory**.
   2.  Make the startup script executable: `chmod +x start_autonomous_ai_architect.sh`
   3.  Run the script: `./start_autonomous_ai_architect.sh`
   4.  This script will:
       *   Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable for the backend.
       *   Source `backend/.env` for the backend process.
       *   Start the Python FastAPI backend (default: `http://localhost:8001`) in the background.
       *   Start a Python HTTP server for the frontend from `frontend/public/` (default: `http://localhost:8000`) in the background.
       *   Attempt to open `http://localhost:8000` in your default web browser.
   5.  **To stop the servers:** The script will print PIDs. You can use `kill [PID]` or `pkill -f uvicorn` and `pkill -f http.server`.

## Expected Behavior & Outputs:

1.  The frontend UI loads with the "Deep Space Gemstone" theme.
2.  After submitting a goal (e.g., "Create a Python FastAPI app with a /ping endpoint that returns 'pong'. Dockerize it and deploy to Cloud Run."):
    *   The backend receives the goal. A `goal_id` is generated.
    *   A WebSocket connection is established.
    *   **PlannerAgent** generates a task plan. This plan appears in the "Plan" tab of the Dashboard.
    *   **CodeExecutionAgent** uses Open Interpreter to generate code (e.g., `main.py`, `requirements.txt`) and a `Dockerfile` in `backend/outputs/code_executions/{goal_id}/{task_id}/`. Logs from OI and file paths are streamed.
    *   **CloudAgent**:
        *   Creates GCS bucket `azroi_bucket` (if it doesn't exist).
        *   Uploads the generated code and Dockerfile (as a `.tar.gz` archive) to `gs://azroi_bucket/...`. The GCS URI is logged.
        *   Creates Artifact Registry repository `ai-architect-apps` in `us-central1` (if it doesn't exist). The AR path is logged.
        *   Triggers Cloud Build using the GCS source. The Cloud Build ID and Console Log URL are logged.
        *   (Waits for Cloud Build to complete)
        *   Pushes the built image to `us-central1-docker.pkg.dev/ai-agent-system-458618/ai-architect-apps/your-service-name:tag`. The image URI is logged.
        *   Deploys this image to a new Cloud Run service in `us-central1`. The public URL of the deployed service is logged and displayed.
3.  All these steps, logs, and artifact URLs are streamed to the frontend Dashboard in real-time.
4.  You can check your GCP Console for the created GCS bucket/objects, Artifact Registry repository/images, Cloud Build history, and deployed Cloud Run services.
5.  The `backend/vectorstore_data/` directory will contain ChromaDB's data.

## Troubleshooting Common Issues:
-   **GCP Permission Denied Errors:** This is the most common issue. **Meticulously verify every IAM role listed in Step 2.c is granted to your service account (`secrets/architect-super-sa-key.json`).** Check Cloud Build logs in GCP Console for specific permission errors during the build or push to Artifact Registry.
-   **GCP API Not Enabled:** Go to "APIs & Services" > "Enabled APIs & Services" in GCP Console and ensure all listed APIs are enabled.
-   **Open Interpreter Failures:**
    -   **Docker Not Running:** Ensure Docker Desktop or Docker Engine is active.
    -   **Model Configuration:** OI needs access to an LLM. Ensure your Azure OpenAI keys in `backend/.env` are correct and the deployment ID `gpt-4o-mini` is valid for your Azure endpoint. If not using Azure, ensure `OPENAI_API_KEY` and `OPEN_INTERPRETER_MODEL_STRING` are correctly set for OpenAI, or OI is configured for a local model. Check OI logs streamed to the UI.
    -   Try running `interpreter` from `backend/.venv/bin/activate` in your terminal to test its basic setup.
-   **Python Dependencies:** `pip install -r backend/requirements.txt` must complete without errors in the `backend/.venv`.
-   **`.env` Variables:** Double-check all paths, names, and keys in `backend/.env`. A typo can cause failures.
-   **Port Conflicts:** If `8000` or `8001` are used by other applications, modify `start_autonomous_ai_architect.sh` and, if necessary, the `fetch` URL in `frontend/src/App.tsx` and the WebSocket URL.
-   **File Paths:** The script uses relative paths. Ensure you run `start_autonomous_ai_architect.sh` from the project root directory.
-   **Cloud Resource Naming Conflicts:** If a GCS bucket or AR repo with the exact name already exists and your SA doesn't have rights to overwrite/manage it, issues can occur. The script tries to handle "already exists" gracefully.

This setup is complex. Patience and careful attention to logs (both frontend browser console and backend terminal output) will be key to debugging any initial issues. Good luck!

## Testing

For information about running tests and adding new tests, see [TESTING.md](TESTING.md).

## Enhanced UI Reliability

### Configuration Panel UI
The Configuration Panel now includes client-side validation for API key input fields. This ensures that users receive immediate feedback on any invalid API keys before attempting to save the configuration. This enhancement improves user experience by preventing malformed API keys from being submitted to the backend.

### Monitoring Panel Display
The Monitoring Panel has been updated to ensure that UI components dynamically reflect new metric data received via WebSocket. This means that all corresponding UI elements within the Monitoring Panel will update automatically and dynamically in near real-time, without requiring a manual page refresh.
