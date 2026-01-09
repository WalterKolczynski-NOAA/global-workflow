#!/bin/bash

source /usr/lmod/lmod/init/bash
module use "${HOMEgfs}/sorc/ufs_utils.fd/modulefiles"
module load build.container.intel

if [[ $# -gt 0 ]]; then
    "$@"
fi
