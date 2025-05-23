#!/bin/bash
# Terraform Check & Utility Script for Autonomous AI Architect
# Usage: bash check_terraform.sh [--check] [--version]

set -e

function check_terraform() {
    if command -v terraform &> /dev/null; then
        echo "Terraform is installed: $(terraform version | head -n 1)"
    else
        echo "Terraform is NOT installed."
        return 1
    fi
}

function show_version() {
    if command -v terraform &> /dev/null; then
        terraform version
    else
        echo "Terraform is NOT installed."
        return 1
    fi
}

if [[ "$1" == "--check" ]]; then
    check_terraform
    exit $?
fi

if [[ "$1" == "--version" ]]; then
    show_version
    exit $?
fi

check_terraform
