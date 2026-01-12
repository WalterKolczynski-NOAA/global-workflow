#!/bin/bash

 export I_MPI_PMI_LIBRARY=/opt/cray/pe/lib64/libpmi2.so
 export I_MPI_FABRICS=shm:ofi
 export I_MPI_OFI_PROVIDER=tcp
 export FI_PROVIDER=tcp
 export FI_TCP_IFACE=eth0

 LD_LIBRARY_PATH=$(dirname "${CONTAINER_SIF}")
 export LD_LIBRARY_PATH

 singularity exec \
        -B ${I_MPI_PMI_LIBRARY} \
        ${CONTAINER_BINDINGS} \
        "${CONTAINER_SIF}" \
        "${HOMEgfs}/dev/container/env/model-env.sh" \
        "$@"
