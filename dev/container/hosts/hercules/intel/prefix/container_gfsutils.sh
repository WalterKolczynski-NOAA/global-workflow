#!/bin/bash

module load singularity
LD_LIBRARY_PATH=$(dirname "CONTAINER_SIF}")
export LD_LIBRARY_PATH

# Create a temporary directory for MPI to use on the host
mkdir -p /work2/noaa/epic/weihuang/stmp/mpi_tmp

# Run with the redirection variables
export SINGULARITYENV_OMPI_MCA_orte_tmpdir_base=/work2/noaa/epic/weihuang/stmp/mpi_tmp
export SINGULARITYENV_TMPDIR=/work2/noaa/epic/weihuang/stmp/mpi_tmp

singularity exec \
        ${CONTAINER_BINDINGS} \
        "${CONTAINER_SIF}" \
        "${HOMEgfs}/dev/container/env/gfsutils-env.sh" \
        "$@"

# Clean up after the run
rm -rf /work2/noaa/epic/weihuang/stmp/mpi_tmp/*
