#!/bin/bash

source /usr/lmod/lmod/init/bash
module use "${HOMEgfs}/sorc/gfs_utils.fd/modulefiles"
module load gfsutils_container.intel
module load wgrib2
module load gettext
module load prod_util
export UTILROOT=${prod_util_ROOT}

if [[ $# -gt 0 ]]; then
    "$@"
fi
