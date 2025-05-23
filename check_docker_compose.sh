#!/bin/bash
# Docker Compose Check & Utility Script for Autonomous AI Architect
# Usage: bash check_docker_compose.sh [--check] [--version]

set -e

function check_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose is installed: $(docker-compose --version)"
    elif docker compose version &> /dev/null; then
        echo "Docker Compose (plugin) is installed: $(docker compose version)"
    else
        echo "Docker Compose is NOT installed."
        return 1
    fi
}

function show_version() {
    if command -v docker-compose &> /dev/null; then
        docker-compose --version
    elif docker compose version &> /dev/null; then
        docker compose version
    else
        echo "Docker Compose is NOT installed."
        return 1
    fi
}

if [[ "$1" == "--check" ]]; then
    check_docker_compose
    exit $?
fi

if [[ "$1" == "--version" ]]; then
    show_version
    exit $?
fi

check_docker_compose
