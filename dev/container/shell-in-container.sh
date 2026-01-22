#!/bin/bash

set -x

HOMEgfs="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." > /dev/null 2>&1 && pwd)"
source "${HOMEgfs}/ush/detect_machine.sh"

ln -sf ${MACHINE_ID}.env env
ln -sf ${MACHINE_ID}.prefix prefix
cp ${HOMEgfs}/env/CONTAINER4${MACHINE_ID} ${HOMEgfs}/env/CONTAINER.env
source ${HOMEgfs}/env/CONTAINER.env

# shellcheck disable=SC2086
singularity shell -e ${CONTAINER_BINDINGS} "${CONTAINER_SIF}"
