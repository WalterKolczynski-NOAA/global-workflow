#!/usr/bin/env bash

set -eu

list_descendants() {
    local children
    children=$(ps -o pid= --ppid "${1}")

    for pid in ${children}; do
        list_descendants "${pid}"
    done

    echo "${children}"
}

RUNNER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" > /dev/null 2>&1 && pwd)
cd "${RUNNER_DIR}" || exit

runners=("$@")

if [[ ${runners[0]} == "all" ]]; then
    readarray -d '' runners < <(find . -maxdepth 1 -mindepth 1 -type d -print0)
fi

for runner in "${runners[@]}"; do
    echo "${runner}"

    cd "${runner}"
    lock_file="./lock"
    stop_file="./stop"

    # Create file to let watchdog know to keep this runner down
    touch "${stop_file}"

    # Check if the runner process is already running via a lock file
    if [[ -f "${lock_file}" ]]; then
        echo "Stopping runner with PID $(cat "${lock_file}")."
        pid="$(cat "${lock_file}")"
        # shellcheck disable=SC2046,SC2311
        kill -- "${pid}" $(list_descendants "${pid}")
        rm -f "${lock_file}"
    fi

    cd ..
done
