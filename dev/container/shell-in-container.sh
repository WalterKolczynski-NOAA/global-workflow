#!/bin/bash

set -x

HOMEgfs="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." > /dev/null 2>&1 && pwd)"
source "${HOMEgfs}/ush/detect_machine.sh"

if [[ ${MACHINE_ID} = ursa* ]]; then
    source ${HOMEgfs}/env/CONTAINER4ursa
elif [[ ${MACHINE_ID} = gaea* ]]; then
    source ${HOMEgfs}/env/CONTAINER4gaeac6
elif [[ ${MACHINE_ID} = noaacloud* ]]; then
    CONTAINER_SIF="/contrib/containers/${sif}"
    CONTAINER_BINDINGS="-B /contrib -B /lustre -B /bucket"
fi

# shellcheck disable=SC2086
singularity shell -e ${CONTAINER_BINDINGS} "${CONTAINER_SIF}"
