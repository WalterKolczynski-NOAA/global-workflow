#! /usr/bin/env bash

source "${HOMEgfs}/ush/preamble.sh"

###############################################################
# Source FV3GFS workflow modules
# TODO clean this up once ncdiag/1.1.2 is installed on WCOSS2
source "${HOMEgfs}/ush/detect_machine.sh"
if [[ "${MACHINE_ID}" == "wcoss2" ]]; then
   . ${HOMEgfs}/ush/load_ufswm_modules.sh
else
   . ${HOMEgfs}/ush/load_fv3gfs_modules.sh
fi
status=$?
[[ ${status} -ne 0 ]] && exit ${status}

module purge
module use ${HOMEgfs}/modulefiles
module load hera.jedi.intel
module list

export job="jediinline"
export jobid="${job}.$$"

# Execute the JJOB
"${HOMEgfs}/jobs/JJEDI_INLINE"
status=$?

exit ${status}
