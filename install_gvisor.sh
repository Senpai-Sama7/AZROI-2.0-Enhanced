#!/bin/bash
# gVisor Installation and Setup Script for Autonomous AI Architect
# This implements the PHASE 02 - Safety Sandbox (Open Interpreter Isolation)

set -e

# Logging function
log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting gVisor installation and configuration..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  log "Please run as root to install gVisor. Example: sudo ./install_gvisor.sh"
  exit 1
fi

# Check for Docker
if ! command -v docker &> /dev/null; then
  log "Docker not found. Please install Docker first."
  exit 1
fi

# Install gVisor runsc
log "Installing gVisor runsc runtime..."

# Get OS and architecture
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
  ARCH="amd64"
elif [ "$ARCH" = "aarch64" ]; then
  ARCH="arm64"
fi

# Download and install runsc
log "Downloading and installing runsc for $OS/$ARCH..."
curl -fsSL https://gvisor.dev/releases/release/latest/$OS/$ARCH/runsc > /usr/local/bin/runsc
chmod a+x /usr/local/bin/runsc

# Install containerd-shim
log "Installing containerd-shim-runsc-v1..."
curl -fsSL https://gvisor.dev/releases/release/latest/$OS/$ARCH/containerd-shim-runsc-v1 > /usr/local/bin/containerd-shim-runsc-v1
chmod a+x /usr/local/bin/containerd-shim-runsc-v1

# Configure Docker to use gVisor
log "Configuring Docker to use gVisor runsc runtime..."
cat <<EOF > /etc/docker/daemon.json
{
  "runtimes": {
    "runsc": {
      "path": "/usr/local/bin/runsc",
      "runtimeArgs": [
        "--platform=ptrace",
        "--network=host",
        "--log-file=/var/log/runsc.log",
        "--debug"
      ]
    }
  }
}
EOF

# Restart Docker to apply changes
log "Restarting Docker to apply changes..."
systemctl restart docker

# Create gVisor directory for configuration
log "Creating gVisor configuration directory..."
mkdir -p security/gvisor

# Create a seccomp profile directory
log "Creating seccomp profile directory..."
mkdir -p security/seccomp

# Create a basic seccomp profile for OI
log "Creating custom seccomp profile for Open Interpreter..."
cat <<EOF > security/seccomp/oi_seccomp.json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": [
    "SCMP_ARCH_X86_64",
    "SCMP_ARCH_X86",
    "SCMP_ARCH_AARCH64"
  ],
  "syscalls": [
    {
      "names": [
        "accept",
        "accept4",
        "access",
        "arch_prctl",
        "bind",
        "brk",
        "clock_getres",
        "clock_gettime",
        "clone",
        "close",
        "connect",
        "dup",
        "dup2",
        "dup3",
        "epoll_create",
        "epoll_create1",
        "epoll_ctl",
        "epoll_pwait",
        "epoll_wait",
        "exit",
        "exit_group",
        "faccessat",
        "fchdir",
        "fcntl",
        "fdatasync",
        "flock",
        "fsync",
        "ftruncate",
        "futex",
        "getcwd",
        "getdents",
        "getdents64",
        "getegid",
        "geteuid",
        "getgid",
        "getpeername",
        "getpgrp",
        "getpid",
        "getppid",
        "getrandom",
        "getrusage",
        "getsockname",
        "getsockopt",
        "gettid",
        "gettimeofday",
        "getuid",
        "io_setup",
        "ioctl",
        "listen",
        "lseek",
        "madvise",
        "memfd_create",
        "mkdir",
        "mmap",
        "mprotect",
        "mremap",
        "munmap",
        "nanosleep",
        "newfstatat",
        "open",
        "openat",
        "pipe",
        "pipe2",
        "poll",
        "ppoll",
        "prctl",
        "pread64",
        "prlimit64",
        "pwrite64",
        "read",
        "readlink",
        "readlinkat",
        "recvfrom",
        "recvmsg",
        "rename",
        "rt_sigaction",
        "rt_sigprocmask",
        "rt_sigreturn",
        "sched_getaffinity",
        "sched_yield",
        "sendfile",
        "sendmsg",
        "sendto",
        "set_robust_list",
        "set_tid_address",
        "setitimer",
        "setsockopt",
        "shutdown",
        "sigaltstack",
        "socket",
        "socketpair",
        "stat",
        "statfs",
        "statx",
        "tgkill",
        "time",
        "timer_create",
        "timer_delete",
        "timer_settime",
        "timerfd_create",
        "timerfd_settime",
        "truncate",
        "uname",
        "unlink",
        "unlinkat",
        "wait4",
        "waitid",
        "write",
        "writev"
      ],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
EOF

# Create Docker Compose file for Open Interpreter with gVisor
log "Creating Docker Compose file for Open Interpreter with gVisor..."
cat <<EOF > docker-compose.oi-sandbox.yml
version: '3.8'

services:
  open-interpreter:
    build:
      context: .
      dockerfile: Dockerfile.oi-sandbox
    container_name: oi-sandbox
    runtime: runsc
    security_opt:
      - seccomp:security/seccomp/oi_seccomp.json
      - no-new-privileges:true
    environment:
      - MODEL=\${OPEN_INTERPRETER_MODEL_STRING:-gpt-4}
      - AZURE_OPENAI_API_KEY=\${AZURE_OPENAI_API_KEY:-}
      - AZURE_OPENAI_API_BASE=\${AZURE_OPENAI_API_BASE:-}
      - AZURE_OPENAI_DEPLOYMENT_ID=\${AZURE_OPENAI_DEPLOYMENT_ID:-}
      - OPENAI_API_KEY=\${OPENAI_API_KEY:-}
    volumes:
      - ./backend/outputs:/app/outputs
    command: python -c "print('Open Interpreter sandbox ready')"
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
    networks:
      - ai-architect-net

networks:
  ai-architect-net:
    driver: bridge
EOF

# Create Dockerfile for OI Sandbox
log "Creating Dockerfile for Open Interpreter Sandbox..."
cat <<EOF > Dockerfile.oi-sandbox
FROM python:3.10-slim

WORKDIR /app

# Install essential packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Open Interpreter
RUN pip install --no-cache-dir "open-interpreter>=0.2.0" requests

# Create output directory for code generation
RUN mkdir -p /app/outputs

# Create a non-root user
RUN useradd -m -u 1000 aiuser
USER aiuser

# Set safe config for Open Interpreter
ENV INTERPRETER_CLI_AUTO_RUN=true
ENV INTERPRETER_CLI_SAFE_MODE=auto

# Set environment variables
ENV PYTHONUNBUFFERED=1

CMD ["python", "-c", "import interpreter; print('Open Interpreter sandbox ready')"]
EOF

# Create a script to run OI in the secure sandbox
log "Creating script to run Open Interpreter in the secure sandbox..."
cat <<EOF > run_oi_sandbox.sh
#!/bin/bash
# Run Open Interpreter in a secure gVisor sandbox

set -e

# Check Docker is running
if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Please start Docker first."
  exit 1
fi

# Load environment variables if .env exists
if [ -f backend/.env ]; then
  export \$(grep -v '^#' backend/.env | xargs)
fi

# Build and start the container
docker-compose -f docker-compose.oi-sandbox.yml up --build -d

echo "Open Interpreter secure sandbox is ready."
echo "To execute code in the sandbox, use the CodeExecutionAgent with sandbox_mode=gvisor"
EOF

chmod +x run_oi_sandbox.sh

log "gVisor installation and configuration completed."
log "To initialize the secure Open Interpreter sandbox, run: sudo ./run_oi_sandbox.sh"
log "The sandbox will use gVisor for enhanced security isolation."
