#!/bin/bash
# Poetry Environment Setup Script for Autonomous AI Architect
# Usage: bash setup_poetry_env.sh [--check] [--install]

set -e

function check_poetry() {
    if command -v poetry &> /dev/null; then
        echo "Poetry is installed: $(poetry --version)"
    else
        echo "Poetry is NOT installed."
        return 1
    fi
}

function install_poetry() {
    if command -v poetry &> /dev/null; then
        echo "Poetry already installed."
    else
        echo "Installing Poetry..."
        curl -sSL https://install.python-poetry.org | python3 -
        export PATH="$HOME/.local/bin:$PATH"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
        echo "Poetry installed: $(poetry --version)"
    fi
}

function setup_env() {
    check_poetry || install_poetry
    echo "Setting up Poetry environment..."
    poetry install
    echo "Poetry environment setup complete."

    # Create necessary directories
    mkdir -p backend/outputs/code_executions
    mkdir -p backend/vectorstore_data
    mkdir -p secrets

    # Test if the environment works
    echo "Testing environment setup..."
    poetry run python -c "import fastapi, google_generativeai, crewai, qdrant_client; print('Environment setup successful!')"

    echo ""
    echo "=== Environment Setup Complete ==="
    echo "To activate the environment, run: poetry shell"
    echo "To run the application, use: ./start_autonomous_ai_architect.sh"
    echo ""
}

if [[ "$1" == "--check" ]]; then
    check_poetry
    exit $?
fi

if [[ "$1" == "--install" ]]; then
    install_poetry
    exit $?
fi

setup_env
