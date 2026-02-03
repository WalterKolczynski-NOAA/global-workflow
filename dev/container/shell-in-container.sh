#!/bin/bash

set -x

HOMEgfs="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." > /dev/null 2>&1 && pwd)"
source "${HOMEgfs}/ush/detect_machine.sh"

ln -sf ${HOMEgfs}/dev/container/hosts/${MACHINE_ID}/intel/env ${HOMEgfs}/dev/container/env
ln -sf ${HOMEgfs}/dev/container/hosts/${MACHINE_ID}/intel/prefix ${HOMEgfs}/dev/container/prefix
cp ${HOMEgfs}/dev/container/hosts/${MACHINE_ID}/intel/env/CONTAINER.env ${HOMEgfs}/env/CONTAINER.env
UMID="${MACHINE_ID^^}"
if [[ -f ${HOMEgfs}/dev/container/hosts/${MACHINE_ID}/intel/env/${UMID}.env ]]; then
    cp ${HOMEgfs}/dev/container/hosts/${MACHINE_ID}/intel/env/${UMID}.env ${HOMEgfs}/env/${UMID}.env
fi
source ${HOMEgfs}/env/CONTAINER.env

# shellcheck disable=SC2086
singularity shell -e ${CONTAINER_BINDINGS} "${CONTAINER_SIF}"
