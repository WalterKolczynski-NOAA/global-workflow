#!/bin/bash

module load singularity

export I_MPI_PMI_LIBRARY=/opt/slurm/lib64/libpmi2.so
export I_MPI_FABRICS=shm:ofi
export I_MPI_OFI_PROVIDER=tcp
export FI_PROVIDER=tcp
export FI_TCP_IFACE=eth0
export SLURM_MPI_TYPE=pmi2

LD_LIBRARY_PATH=$(dirname "${CONTAINER_SIF}")
export LD_LIBRARY_PATH

singularity exec \
        ${CONTAINER_BINDINGS} \
        "${CONTAINER_SIF}" \
        "${HOMEgfs}/dev/container/env/model-env.sh" \
        "$@"

