#!/bin/bash

 LD_LIBRARY_PATH=$(dirname "${CONTAINER_SIF}"
 export LD_LIBRARY_PATH

 singularity exec \
        "${CONTAINER_BINDINGS}" \
        "${CONTAINER_SIF}" \
        "${HOMEgfs}/dev/container/env/model-env.sh" \
        "$@"
