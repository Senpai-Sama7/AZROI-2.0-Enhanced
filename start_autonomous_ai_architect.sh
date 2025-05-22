#!/bin/bash
# Autonomous AI Architect - Startup Script
# This script starts both the backend and frontend servers

# ANSI color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print banner
echo -e "${PURPLE}"
echo "┌──────────────────────────────────────────────────────────┐"
echo "│                                                          │"
echo "│               AUTONOMOUS AI ARCHITECT                    │"
echo "│                                                          │"
echo "│                Starting the System...                    │"
echo "│                                                          │"
echo "└──────────────────────────────────────────────────────────┘"
echo -e "${NC}"

# Set the Google Application Credentials env var
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/secrets/architect-super-sa-key.json"

echo -e "${BLUE}==== Checking Prerequisites ====${NC}"

# Check if key file exists
if [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
  echo -e "${RED}Error: GCP Service Account key file not found at $GOOGLE_APPLICATION_CREDENTIALS${NC}"
  echo "Please run the easy_install.sh script or follow the setup instructions in HOW_TO_USE.md"
  exit 1
fi

# Check if the backend directory exists
if [ ! -d "backend" ]; then
  echo -e "${RED}Error: 'backend' directory not found${NC}"
  echo "Please ensure you're running this script from the project root directory."
  exit 1
fi

# Check if Python virtual environment exists
if [ ! -d "backend/.venv" ]; then
  echo -e "${RED}Error: Python virtual environment not found in backend/.venv${NC}"
  echo "Please run the easy_install.sh script or follow the setup instructions in HOW_TO_USE.md"
  exit 1
fi

# Check if frontend directory exists
if [ ! -d "frontend" ]; then
  echo -e "${YELLOW}Warning: 'frontend' directory not found${NC}"
  echo "This is fine if you're using the pre-built version with static files."
fi

# Start the backend server
echo -e "${BLUE}==== Starting Backend Server ====${NC}"
cd backend

# Make sure the virtual environment exists
if [ ! -d ".venv" ]; then
  echo -e "${RED}Error: Python virtual environment not found in backend/.venv${NC}"
  echo "Please run the easy_install.sh script or follow the setup instructions in HOW_TO_USE.md"
  exit 1
fi

# Make sure the .env file exists
if [ ! -f ".env" ]; then
  echo -e "${RED}Error: Environment configuration file .env not found in backend directory${NC}"
  echo "Please run the easy_install.sh script or create the .env file manually"
  exit 1
fi

# Activate virtual environment
source .venv/bin/activate
if [ $? -ne 0 ]; then
  echo -e "${RED}Error: Failed to activate virtual environment${NC}"
  echo "Try running: cd backend && python3 -m venv .venv"
  exit 1
fi

# Start backend server in the background
echo "Starting FastAPI backend on http://localhost:8001"
uvicorn main:app --host 0.0.0.0 --port 8001 &
BACKEND_PID=$!

# Check if backend started successfully
sleep 2
if ! ps -p $BACKEND_PID > /dev/null; then
  echo -e "${RED}Error: Backend server failed to start${NC}"
  echo "Try running it manually: cd backend && source .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8001"
  exit 1
fi

cd ..
echo -e "${GREEN}Backend started with PID: $BACKEND_PID${NC}"

# Wait a moment for the backend to initialize
echo "Waiting for backend to initialize..."
sleep 3

# Check if backend is responding
if command -v curl >/dev/null 2>&1; then
  if ! curl -s http://localhost:8001/ping > /dev/null; then
    echo -e "${YELLOW}Warning: Backend server might not be responding. Continuing anyway...${NC}"
  else
    echo -e "${GREEN}Backend server is responding${NC}"
  fi
fi

# Start the frontend server
echo -e "${BLUE}==== Starting Frontend Server ====${NC}"

# Find the right directory for the frontend
if [ -d "frontend/public" ]; then
  FRONTEND_DIR="frontend/public"
elif [ -d "frontend" ]; then
  FRONTEND_DIR="frontend"
else
  FRONTEND_DIR="."
fi

cd $FRONTEND_DIR
echo "Starting frontend server on http://localhost:8000"

# Check if port 8000 is already in use
if command -v lsof >/dev/null 2>&1; then
  if lsof -i:8000 >/dev/null 2>&1; then
    echo -e "${YELLOW}Warning: Port 8000 is already in use.${NC}"
    echo "Please stop any other services using port 8000 or modify this script to use a different port."
    read -p "Do you want to continue anyway? (y/N): " continue_with_port
    if [[ ! $continue_with_port =~ ^[Yy]$ ]]; then
      echo -e "${YELLOW}Startup canceled. Stopping backend server...${NC}"
      kill $BACKEND_PID
      exit 1
    fi
  fi
fi

# Start the frontend server
python3 -m http.server 8000 &
FRONTEND_PID=$!

# Check if frontend started successfully
sleep 2
if ! ps -p $FRONTEND_PID > /dev/null; then
  echo -e "${RED}Error: Frontend server failed to start${NC}"
  echo "Try starting it manually: cd $FRONTEND_DIR && python3 -m http.server 8000"
  echo -e "${YELLOW}Stopping backend server...${NC}"
  kill $BACKEND_PID
  exit 1
fi

cd - > /dev/null # Return to original directory without output
echo -e "${GREEN}Frontend started with PID: $FRONTEND_PID${NC}"

# Save PIDs to file for later cleanup
echo "$BACKEND_PID $FRONTEND_PID" > .server_pids

# Open in browser
echo -e "${BLUE}==== Opening in Browser ====${NC}"

# Wait a moment for servers to be fully ready
sleep 2

# Check if the frontend is responding
if command -v curl >/dev/null 2>&1; then
  echo "Checking if frontend server is accessible..."
  if ! curl -s --head http://localhost:8000 > /dev/null; then
    echo -e "${YELLOW}Warning: Frontend server might not be responding correctly.${NC}"
  else
    echo -e "${GREEN}Frontend server is accessible${NC}"
  fi
fi

# Try to open the browser
BROWSER_OPENED=false
if command -v xdg-open >/dev/null 2>&1; then
  echo "Opening browser with xdg-open (Linux)..."
  xdg-open http://localhost:8000 && BROWSER_OPENED=true
elif command -v open >/dev/null 2>&1; then
  echo "Opening browser with open (macOS)..."
  open http://localhost:8000 && BROWSER_OPENED=true
elif command -v start >/dev/null 2>&1; then
  echo "Opening browser with start (Windows)..."
  start http://localhost:8000 && BROWSER_OPENED=true
fi

if [ "$BROWSER_OPENED" = true ]; then
  echo -e "${GREEN}Browser opened successfully${NC}"
else
  echo -e "${YELLOW}Could not open browser automatically.${NC}"
  echo "Please open your browser and navigate to http://localhost:8000"
fi

echo -e "${GREEN}Autonomous AI Architect is now running!${NC}"
echo -e "Frontend: ${CYAN}http://localhost:8000${NC}"
echo -e "Backend:  ${CYAN}http://localhost:8001${NC}"
echo ""
echo -e "${YELLOW}To stop the servers, press Ctrl+C or run:${NC}"
echo -e "${CYAN}kill $BACKEND_PID $FRONTEND_PID${NC}"
echo -e "${CYAN}# OR #${NC}"
echo -e "${CYAN}pkill -f uvicorn; pkill -f 'http.server'${NC}"

# Wait for user to press Ctrl+C
echo ""
echo "Press Ctrl+C to stop the servers"
wait