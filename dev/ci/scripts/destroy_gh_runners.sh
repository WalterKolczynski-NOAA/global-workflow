#!/usr/bin/env bash

set -eu

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
HOMEglobal="$(cd "${script_dir}" && git rev-parse --show-toplevel)"

source "${HOMEglobal}/ush/detect_machine.sh"
export machine="${MACHINE_ID}"
echo "${machine} detected. Will destroy runners for ${machine}."

echo "Where are your GitHub runners located?"
location="/foo"
while [[ ! -d "${location}" ]]; do
    read -r location
    if [[ ! -d "${location}" ]]; then
        echo "${location} does not exist!"
    fi
done
echo

num_existing=$(find "${location}" -maxdepth 1 -type d -regextype posix-extended -regex "${location}/${machine}_[0-9]{3}" -printf '.' | wc -c)
if [[ "${num_existing}" -eq 0 ]]; then
    echo "No runners found in ${location} matching the pattern ${machine}_###:"
    ls "${location}"
    exit 1
else
    echo "${num_existing} existing runners found in ${location}"
fi

num_destroy=""
while [[ ! "${num_destroy}" =~ ^[0-9]+$ || ${num_destroy} -lt 0 ]]; do
    echo "How many runners would you like to destroy?"
    read -r num_destroy
    if [[ "${num_destroy}" =~ ^[0-9]+$ ]]; then
        if [[ "${num_destroy}" -lt 0 ]]; then
            echo "Please enter a non-negative interger"
        elif [[ "${num_destroy}" -eq 0 ]]; then
            echo "Zero runners chosen, exiting"
            exit 0
        elif [[ "${num_destroy}" -gt "${num_existing}" ]]; then
            echo "Number to destroy larger than the number that exist, will destroy them all"
            num_destroy="${num_existing}"
        fi
    else
        if [[ "${num_destroy}" == "all" ]]; then
            num_destroy="${num_existing}"
        else
            echo "Please enter a non-negative interger"
        fi
    fi
done
echo

last_runner_num=$((num_existing - 1))
last_runner_num_padded=$(printf '%03d' "${last_runner_num}")
repo=$(grep -oP '(?<="gitHubUrl": ")(.*)(?=",)' "${location}/${machine}_${last_runner_num_padded}/.runner")

echo "Please enter GitHub token to destroy ${num_destroy} runners"
echo "(found in code shown at ${repo}/settings/actions/runners/new?arch=x64&os=linux)"
read -r token
echo

new_total=$((num_existing - num_destroy))

cd "${location}"
for ((runner_num = num_existing - 1; runner_num >= new_total; runner_num--)); do
    runner_num_padded=$(printf '%03d' "${runner_num}")
    dir_name="${machine}_${runner_num_padded}"
    ./stop_runners.sh "${dir_name}"
    cd "${dir_name}"
    ./config.sh remove --token "${token}"
    cd ..
    rm -Rf "${dir_name}"
done

echo "${num_destroy} runners have been destoyed"
