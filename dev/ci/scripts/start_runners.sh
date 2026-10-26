#!/usr/bin/env bash

set -eu

RUNNER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" > /dev/null 2>&1 && pwd)
cd "${RUNNER_DIR}" || exit

runners=("$@")

if [[ ${runners[0]} == "all" ]]; then
    readarray -d '' runners < <(find . -maxdepth 1 -mindepth 1 -type d -print0)
fi

for runner in "${runners[@]}"; do
    stop_file="stop"
    rm "${runner}/${stop_file}"
done

./runner_watchdog.sh
