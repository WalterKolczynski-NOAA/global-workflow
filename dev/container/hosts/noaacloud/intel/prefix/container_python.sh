#!/bin/bash
set -x
LD_LIBRARY_PATH=$(dirname "${CONTAINER_SIF}")
export LD_LIBRARY_PATH

singularity exec \
    ${CONTAINER_BINDINGS} \
    "${CONTAINER_SIF}" \
    "${HOMEgfs}/dev/container/env/python-env.sh" "$@"
