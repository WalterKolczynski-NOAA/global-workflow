#!/bin/bash
LD_LIBRARY_PATH=$(dirname "/scratch3/NCEPDEV/nems/role.epic/containers/ubuntu22.04-intel-ufs-env-v1.9.2.img")
export LD_LIBRARY_PATH

singularity exec \
    -B /scratch3 -B /scratch4 \
    "/scratch3/NCEPDEV/nems/role.epic/containers/ubuntu22.04-intel-ufs-env-v1.9.2.img" \
    "/scratch4/NAGAPE/epic/Wei.Huang/demo/global-workflow-cloud/dev/container/env/python-env.sh" "$@"
