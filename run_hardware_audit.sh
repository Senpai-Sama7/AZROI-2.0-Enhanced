#!/bin/bash

# Run Hardware Audit System with metrics collection
# This script provides an easy way to run the enhanced hardware audit system

# Default parameters
OUTPUT_FILE="hw_report.json"
METRICS_FILE="metrics_history.json"
DURATION=30
INTERVAL=5
COLLECT_METRICS=false
DISABLE_GPU=false
DISABLE_DOCKER=false
SHOW_SUMMARY=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --output)
      OUTPUT_FILE="$2"
      shift 2
      ;;
    --metrics)
      METRICS_FILE="$2"
      COLLECT_METRICS=true
      shift 2
      ;;
    --duration)
      DURATION="$2"
      shift 2
      ;;
    --interval)
      INTERVAL="$2"
      shift 2
      ;;
    --no-gpu)
      DISABLE_GPU=true
      shift
      ;;
    --no-docker)
      DISABLE_DOCKER=true
      shift
      ;;
    --no-summary)
      SHOW_SUMMARY=false
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --output FILE       Output hardware report to FILE (default: hw_report.json)"
      echo "  --metrics FILE      Collect metrics and save to FILE (default: metrics_history.json)"
      echo "  --duration SECONDS  Duration for metrics collection in seconds (default: 30)"
      echo "  --interval SECONDS  Interval between metrics samples in seconds (default: 5)"
      echo "  --no-gpu            Disable GPU detection"
      echo "  --no-docker         Disable Docker metrics collection"
      echo "  --no-summary        Do not show summary on console"
      echo "  --help              Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help to see available options"
      exit 1
      ;;
  esac
done

# Build command
CMD="python3 backend/core_orchestration/hardware_audit.py --output $OUTPUT_FILE --interval $INTERVAL"

# Add flags if needed
if [[ "$DISABLE_GPU" == true ]]; then
  CMD="$CMD --no-gpu"
fi

if [[ "$DISABLE_DOCKER" == true ]]; then
  CMD="$CMD --no-docker"
fi

if [[ "$SHOW_SUMMARY" == true ]]; then
  CMD="$CMD --summary"
fi

if [[ "$COLLECT_METRICS" == true ]]; then
  CMD="$CMD --collect --duration $DURATION --export-metrics $METRICS_FILE"
fi

echo "Running hardware audit with command:"
echo "$CMD"
echo ""

# Execute command
eval "$CMD"

# Report file locations
echo ""
echo "Hardware report saved to: $OUTPUT_FILE"
if [[ "$COLLECT_METRICS" == true ]]; then
  echo "Metrics history saved to: $METRICS_FILE"
fi
