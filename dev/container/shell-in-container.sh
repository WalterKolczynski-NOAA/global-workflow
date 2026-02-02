#!/bin/bash

set -x

HOMEgfs="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." > /dev/null 2>&1 && pwd)"
source "${HOMEgfs}/ush/detect_machine.sh"

if [[ ${MACHINE_ID} = ursa* ]]; then
    source ${HOMEgfs}/env/CONTAINER4ursa
elif [[ ${MACHINE_ID} = gaea* ]]; then
    source ${HOMEgfs}/env/CONTAINER4gaeac6
elif [[ ${MACHINE_ID} = hercules* ]]; then
    module load singularity
    sif=ubuntu22.04-intel-ufs-env-v1.9.2.img
    CONTAINER_SIF="/work2/noaa/epic/weihuang/containers/${sif}"
    CONTAINER_BINDINGS="-B /work -B /work2"
elif [[ ${MACHINE_ID} = noaacloud* ]]; then
    sif=ubuntu22.04-intel-ufs-env-v1.9.2.img
    CONTAINER_SIF="/contrib/containers/${sif}"
    CONTAINER_BINDINGS="-B /contrib -B /lustre -B /bucket"
fi

# shellcheck disable=SC2086
singularity shell -e ${CONTAINER_BINDINGS} "${CONTAINER_SIF}"
