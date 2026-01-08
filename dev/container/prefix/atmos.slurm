#! /bin/sh
#SBATCH --job-name=C48_S2SW_gfs_atmos_prod_f000-f002_12
#SBATCH --account=epic
#SBATCH --qos=batch
#SBATCH --partition=u1-compute
#SBATCH -t 00:45:00
#SBATCH --ntasks=24
#SBATCH -o /scratch3/NAGAPE/epic/Wei.Huang/run/prefix/COMROOT/C48_S2SW/logs/2021032312/gfs_atmos_prod_f000-f002.log
#SBATCH --exclusive
#SBATCH --comment=2954d0947bdd0b7f9c2fbe20561c3dd9
export RUN_ENVIR='emc'
export HOMEgfs='/scratch4/NAGAPE/epic/Wei.Huang/demo/global-workflow-cloud'
export EXPDIR='/scratch3/NAGAPE/epic/Wei.Huang/run/prefix/EXPDIR/C48_S2SW'
export NET='gfs'
export RUN='gfs'
export CDATE='2021032312'
export PDY='20210323'
export cyc='12'
export COMROOT='/scratch3/NAGAPE/epic/Wei.Huang/run/prefix/COMROOT'
export DATAROOT='/scratch3/NAGAPE/epic/Wei.Huang/stmp/prefix/RUNDIRS/C48_S2SW/gfs.2021032312'
export FHR_LIST='0,1,2'
export COMPONENT='atmos'
/scratch4/NAGAPE/epic/Wei.Huang/demo/global-workflow-cloud/dev/job_cards/rocoto/atmos_products.sh

