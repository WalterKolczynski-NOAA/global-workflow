#! /usr/bin/env bash
set -x

source "${USHgfs}/preamble.sh"
#export GDASsorc=/scratch1/NCEPDEV/nems/David.Burrows/feb4_mark_updates/gw_jedi_soca_uwtools_update/sorc/gdas.cd
#export JEDIIN=/scratch1/NCEPDEV/nems/David.Burrows/jedi_input
#
#unset PYTHONPATH
#source ${GDASsorc}/bundle/venv/uwtools/bin/activate
#
#cp -r ${JEDIIN}/gen-exp ${DATA}
#chmod 766 ${DATA}/gen-exp
#cd ${DATA}/gen-exp
#
##rm -f Data/crtm/*
##cp -r ${JEDIIN}/2.3.0/* Data/crtm/
#mv Data Data_broken_links
#cp -Lr ${JEDIIN}/Data .
#cp -r ${JEDIIN}/2.3.0/* Data/crtm/
#cp -r ${JEDIIN}/AerosolCoeff.bin Data/crtm/AerosolCoeff.bin
#
#python ${HOMEgfs}/scripts/exjedi_inline.py
#export err=$?;
#if [ ${err} -ne 0 ]; then exit 1; fi
#
#deactivate
#
srun --export=ALL -n 12 ${GDASsorc}/build/bin/fv3jedi_letkf.x testinput/letkf-c48-exp.yaml
export err=$?;
if [ ${err} -ne 0 ]; then exit 1; fi

mkdir -p ${ROTDIR}/jediinline.20230323/12
cp ${DATA}/gen-exp/ModelRunDirs/c48_001/RESTART/* ${ROTDIR}/jediinline.20230323/12/.
cp ${DATA}/gen-exp/ModelRunDirs/c48_002/RESTART/* ${ROTDIR}/jediinline.20230323/12/.
exit 0
