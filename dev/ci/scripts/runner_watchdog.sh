#!/usr/bin/env bash

set -eu

runner_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" > /dev/null 2>&1 && pwd)
cd "${runner_dir}" || exit

for runner in */; do
    cd "${runner}"
    lock_file="./lock"
    log_file="./runner.log"
    stop_file="./stop"

    if [[ ! -f "${stop_file}" ]]; then
        # Check if the runner process is already running via a lock file
        if [[ -f "${lock_file}" ]]; then
            # Optional: check if the PID in the lock file is still valid
            if ps -p "$(cat "${lock_file}")" > /dev/null; then
                echo "Runner is already running with PID $(cat "${lock_file}"). Exiting."
                exit
            else
                echo "Stale lock file found. Removing."
                rm "${lock_file}"
            fi
        fi

        # Start the runner in the background and save its PID to the lock file
        echo "Starting runner ${runner}..."
        nohup ./run.sh > "${log_file}" 2>&1 &
        echo $! > "${lock_file}"
        echo "Runner started with PID $!."
    else
        echo "Runner ${runner} marked as stopped, skipping."
    fi

    cd ..
done
