#!/usr/bin/env bash

set -eu

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
HOMEglobal="$(cd "${script_dir}" && git rev-parse --show-toplevel)"

runner_source_url='https://github.com/actions/runner/releases/download/v2.337.0/actions-runner-linux-x64-2.337.0.tar.gz'
runner_tarball=$(basename "${runner_source_url}")
runner_tarball_hash='70920811a4f8ad4328818682bca5c6469c1c942fab52448868071d0063816613'

source "${HOMEglobal}/ush/detect_machine.sh"
echo "${MACHINE_ID} detected. Will create runners for ${MACHINE_ID}."

echo "Where would you like to create more GitHub runners?"
read -r location
echo

num_existing=$(find "${location}" -maxdepth 1 -type d -regextype posix-extended -regex "${location}/${MACHINE_ID}_[0-9]{3}" -printf '.' | wc -c)
echo "${num_existing} existing runners found in ${location}"

num_new=""
while [[ ! "${num_new}" =~ ^[0-9]+$ || ${num_new} -lt 0 ]]; do
    echo "How many runners would you like to add?"
    read -r num_new
    if [[ "${num_new}" =~ ^[0-9]+$ ]]; then
        if [[ "${num_new}" -lt 0 ]]; then
            echo "Please enter a non-negative interger"
        elif [[ "${num_new}" -eq 0 ]]; then
            echo "Zero runners chosen, exiting"
            exit 0
        fi
    else
        echo "Please enter a non-negative interger"
    fi
done
echo

valid_repo=false
while ! ${valid_repo}; do
    echo "For which repository would you like to create runners? (<org>/<repo>)"
    read -r repo_short
    echo

    repo="https://github.com/${repo_short}"

    if wget -q "${repo}"; then
        valid_repo=true
    else
        echo "Could not connect to ${repo}, is it correct?"
    fi
    rm "${repo}"
done

echo "Please enter GitHub token for creating new runners"
echo "(found in code shown at ${repo}/settings/actions/runners/new?arch=x64&os=linux)"
read -r token
echo

new_total=$((num_existing + num_new))

mkdir -p "${location}"
cd "${location}"

rm -Rf .clean
mkdir .clean
cd .clean
curl -o "${runner_tarball}" -L "${runner_source_url}"
# Two spaces are required between the hash and the tarball
echo "${runner_tarball_hash}  ${runner_tarball}" | shasum -a 256 -c
echo "Extracting tarball"
tar -xzf "./${runner_tarball}"
rm "${runner_tarball}"
cd ..

for ((runner_num = num_existing; runner_num < new_total; runner_num++)); do
    runner_num_padded=$(printf '%03d' "${runner_num}")
    dir_name="${MACHINE_ID}_${runner_num_padded}"
    echo "Copying clean runner directory to ${dir_name}"
    rsync -a --stats .clean/ "${dir_name}"
    cd "${dir_name}"

    echo "Configuring GitHub runner ${dir_name}"
    ./config.sh --unattended --url "${repo}" --token "${token}" --name "${MACHINE_ID}_${runner_num_padded}" --labels "${MACHINE_ID}"

    cd ..
done

for script in create_gh_runners.sh destroy_gh_runners.sh runner_watchdog.sh stop_runners.sh start_runners.sh; do
    cp "${script_dir}/${script}" ./
    chmod "./${script}"
done

./runner_watchdog.sh

rm -Rf .clean
echo "Your new runners have been created"
echo "Add ${location}/runner_watchdog.sh to your crontab to keep your runners running"
