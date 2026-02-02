#!/bin/bash
module load singularity
LD_LIBRARY_PATH=$(dirname "/scratch3/NCEPDEV/nems/role.epic/containers/ubuntu22.04-intel-ufs-env-v1.9.2.img")
export LD_LIBRARY_PATH

singularity exec \
    ${CONTAINER_BINDINGS} \
    "${CONTAINER_SIF}" \
    "${HOMEgfs}/dev/container/env/python-env.sh" "$@"
