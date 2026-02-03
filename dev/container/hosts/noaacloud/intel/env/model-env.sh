#!/bin/bash

source /usr/lmod/lmod/init/bash
module use "${HOMEgfs}/sorc/ufs_model.fd/modulefiles"
module load ufs_container.intel

if [[ $# -gt 0 ]]; then
    "$@"
fi

