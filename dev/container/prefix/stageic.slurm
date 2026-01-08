#! /bin/sh
#SBATCH --job-name=C48_S2SW_gfs_stage_ic_12
#SBATCH --account=epic
#SBATCH --qos=batch
#SBATCH --partition=u1-service
#SBATCH -t 00:15:00
#SBATCH --ntasks=1
#SBATCH --mem=4096
#SBATCH -o /scratch3/NAGAPE/epic/Wei.Huang/run/prefix/COMROOT/C48_S2SW/logs/2021032312/gfs_stage_ic.log
#SBATCH --export=NONE
#SBATCH --comment=d57f47d320af16f2bed476db01a4b73b
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
/scratch4/NAGAPE/epic/Wei.Huang/demo/global-workflow-cloud/dev/job_cards/rocoto/stage_ic.sh

