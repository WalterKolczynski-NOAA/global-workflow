#! /usr/bin/env bash
set -x

source "${USHgfs}/preamble.sh"

srun --export=ALL -n 12 ${GDASsorc}/build/bin/fv3jedi_letkf.x testinput/letkf-c48-exp.yaml
export err=$?;
if [ ${err} -ne 0 ]; then exit 1; fi

mkdir -p ${ROTDIR}/jediinline.20230323/12
cp ${DATA}/gen-exp/ModelRunDirs/c48_001/RESTART/* ${ROTDIR}/jediinline.20230323/12/.
cp ${DATA}/gen-exp/ModelRunDirs/c48_002/RESTART/* ${ROTDIR}/jediinline.20230323/12/.
exit 0
