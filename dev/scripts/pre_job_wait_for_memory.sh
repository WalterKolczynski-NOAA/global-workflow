#!/usr/bin/env bash
set -euo pipefail

# Wait until enough memory is available before starting a GitHub runner job.
# This is useful on self-hosted runners where other processes may be consuming RAM.
#
# Example:
#   ./scripts/pre_job_wait_for_memory.sh --min-mem-gb 8 --check-interval 30 --max-wait-min 30

MIN_MEM_GB="${MIN_MEM_GB:-4}"
CHECK_INTERVAL="${CHECK_INTERVAL:-30}"
MAX_WAIT_MINUTES="${MAX_WAIT_MINUTES:-0}"

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --min-mem-gb N          Minimum available memory in GB before continuing (default: 4)
  --check-interval N      Seconds between checks (default: 30)
  --max-wait-min N       Maximum wait time in minutes before exiting non-zero (default: 0 = no limit)
  -h, --help              Show this help message

Environment variables:
  MIN_MEM_GB             Override default minimum memory threshold
  CHECK_INTERVAL         Override default check interval in seconds
  MAX_WAIT_MINUTES       Override default max wait time in minutes
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --min-mem-gb)
      MIN_MEM_GB="${2:-}"
      shift 2
      ;;
    --check-interval)
      CHECK_INTERVAL="${2:-}"
      shift 2
      ;;
    --max-wait-min)
      MAX_WAIT_MINUTES="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if ! [[ "$MIN_MEM_GB" =~ ^[0-9]+$ ]]; then
  echo "Error: --min-mem-gb must be a non-negative integer" >&2
  exit 1
fi

if ! [[ "$CHECK_INTERVAL" =~ ^[0-9]+$ ]]; then
  echo "Error: --check-interval must be a non-negative integer" >&2
  exit 1
fi

if ! [[ "$MAX_WAIT_MINUTES" =~ ^[0-9]+$ ]]; then
  echo "Error: --max-wait-min must be a non-negative integer" >&2
  exit 1
fi

MIN_MEM_MB=$((MIN_MEM_GB * 1024))
WAIT_START=$(date +%s)

while true; do
  # Use the Linux 'free' output's 'available' memory column, which is the most accurate.
  # This avoids false positives from memory that is still cached or reclaimable.
  if ! MEM_INFO=$(free -m 2>/dev/null); then
    echo "Unable to read memory stats from 'free -m'." >&2
    exit 1
  fi

  AVAILABLE_MB=$(echo "$MEM_INFO" | awk '/^Mem:/{print $7}')

  if [[ -z "$AVAILABLE_MB" || ! "$AVAILABLE_MB" =~ ^[0-9]+$ ]]; then
    echo "Unable to parse available memory from: $MEM_INFO" >&2
    exit 1
  fi

  if (( AVAILABLE_MB >= MIN_MEM_MB )); then
    echo "Enough memory available: ${AVAILABLE_MB} MB free / required ${MIN_MEM_MB} MB"
    exit 0
  fi

  NOW=$(date +%s)
  ELAPSED_MINUTES=$(( (NOW - WAIT_START) / 60 ))

  if (( MAX_WAIT_MINUTES > 0 && ELAPSED_MINUTES >= MAX_WAIT_MINUTES )); then
    echo "Timed out after ${MAX_WAIT_MINUTES} minutes waiting for memory. Available: ${AVAILABLE_MB} MB / required: ${MIN_MEM_MB} MB" >&2
    exit 1
  fi

  echo "Waiting for more memory: ${AVAILABLE_MB} MB available, need at least ${MIN_MEM_MB} MB. Sleeping ${CHECK_INTERVAL}s."
  sleep "$CHECK_INTERVAL"
done
