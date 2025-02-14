#! /usr/bin/env bash
set -x

source "${USHgfs}/preamble.sh"
export GDASsorc=/scratch1/NCEPDEV/nems/David.Burrows/feb4_mark_updates/gw_jedi_soca_uwtools_update/sorc/gdas.cd
export GENEXPsorc=/scratch1/NCEPDEV/nems/David.Burrows/feb4_mark_updates
export JEDIIN=/scratch1/NCEPDEV/nems/David.Burrows/jedi_input

echo "$PYTHONPATH"
module list
unset PYTHONPATH

source ${GDASsorc}/bundle/venv/uwtools/bin/activate

cp -r ${JEDIIN}/gen-exp ${DATA}
chmod 766 ${DATA}/gen-exp
cd ${DATA}/gen-exp

mv Data Data_broken_links
cp -Lr ${JEDIIN}/Data .
cp -r ${JEDIIN}/2.3.0/* Data/crtm/

cp -r ${JEDIIN}/AerosolCoeff.bin Data/crtm/AerosolCoeff.bin

## to run 12Z restarts
cd ${DATA}/gen-exp/c48_input_data/INPUT/
mkdir hold
mv coupler* fv_* gfs_* phy_* sfc_* hold/.
cp /scratch1/NCEPDEV/global/glopara/data/ICSDIR/C48/20241120/gdas.20210323/06/model/atmos/restart/* .
for file in *; do
  mv "${file}" "${file#20210323.120000.}"
done
cd ${DATA}/gen-exp

python ${HOMEgfs}/scripts/exjedi_inline.py
export err=$?;
if [ ${err} -ne 0 ]; then exit 1; fi

deactivate

cp ${JEDIIN}/forecast_c48_001_12Z.yaml testinput/forecast_c48_001.yaml
cp ${JEDIIN}/forecast_c48_002_12Z.yaml testinput/forecast_c48_002.yaml
cp ${JEDIIN}/letkf-c48-exp_12Z.yaml testinput/letkf-c48-exp.yaml

unlink ModelRunDirs/c48_001/model_configure
unlink ModelRunDirs/c48_002/model_configure
cp /home/David.Burrows/model_configure_cheat ModelRunDirs/c48_001/model_configure
cp /home/David.Burrows/model_configure_cheat ModelRunDirs/c48_002/model_configure

cp /home/David.Burrows/coupler_cheat.res ModelRunDirs/c48_001/INPUT/coupler.res
cp /home/David.Burrows/coupler_cheat.res ModelRunDirs/c48_002/INPUT/coupler.res

cp ${JEDIIN}/fv3jedi_letkf.x ${DATA}
srun --export=ALL -n 12 ${GDASsorc}/build/bin/fv3jedi_letkf.x testinput/letkf-c48-exp.yaml

exit 0
