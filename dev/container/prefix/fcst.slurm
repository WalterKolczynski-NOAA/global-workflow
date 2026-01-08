#! /bin/sh
#SBATCH --job-name=C48_S2SW_gfs_fcst_seg0_12
#SBATCH --account=epic
#SBATCH --qos=batch
#SBATCH --partition=u1-compute
#SBATCH -t 00:30:00
#SBATCH --ntasks=192
#SBATCH -o /scratch3/NAGAPE/epic/Wei.Huang/run/prefix/COMROOT/C48_S2SW/logs/2021032312/gfs_fcst_seg0.log
#SBATCH --exclusive
#SBATCH --comment=75aadbd40d3692eb46dd634e22b39058
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
export FCST_SEGMENT='0'
/scratch4/NAGAPE/epic/Wei.Huang/demo/global-workflow-cloud/dev/job_cards/rocoto/fcst.sh

