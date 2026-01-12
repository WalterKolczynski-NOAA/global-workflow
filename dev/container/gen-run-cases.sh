#!/bin/bash

set -x

HOMEgfs="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." > /dev/null 2>&1 && pwd)"
source "${HOMEgfs}/ush/detect_machine.sh"

run_with_container="YES"
#run_with_container="NO"

casetype="pr"
#yamllist="C48_ATM"
yamllist="C48_S2SW"
#yamllist="C48_S2SWA_gefs"
#yamllist="C96mx100_S2S"

#casetype=hires
#yamllist="C768_S2SW"

HOMEDIR=${HOMEgfs}
img=ubuntu22.04-intel-ufs-env-v1.9.2.img
if [[ ${MACHINE_ID} = ursa* ]]; then
    rundir="/scratch3/NAGAPE/epic/${USER}/run/prefix"
    HPC_ACCOUNT=epic

    module load rocoto/1.3.7
    rocotocmd=$(command -v rocotorun)
elif [[ ${MACHINE_ID} = gaea* ]]; then
    rundir="/gpfs/f6/scratch/${USER}/run/prefix"
    HPC_ACCOUNT=bil-fire8

    rocotocmd=/autofs/ncrc-svm1_home2/Christopher.W.Harrop/rocoto-1.3.7/bin/rocotorun
elif [[ ${MACHINE_ID} = noaacloud* ]]; then
    rundir="/lustre/${USER}/run"
    HPC_ACCOUNT="${USER}"

    module load rocoto/1.3.7
    rocotocmd=$(command -v rocotorun)
fi

set -x

mkdir -p "${rundir}"

cd "${HOMEDIR}/dev/workflow" || exit 1

if [[ "${run_with_container}" == "YES" ]]; then
    CONTAINER_OPTIONS="-R -r \"${rocotocmd}\""
else
    CONTAINER_OPTIONS=""
fi

RUNTESTS="${rundir}" \
./generate_workflows.sh \
        -H "${HOMEDIR}" \
        -y "${yamllist}" \
        -Y "${HOMEDIR}/dev/ci/cases/${casetype}" \
        -A "${HPC_ACCOUNT}" \
        -e "${USER}@noaa.gov" \
        ${CONTAINER_OPTIONS} \
        -v
