#! /bin/sh
#SBATCH --job-name=fcst
#SBATCH --account=bil-fire8
#SBATCH --qos=normal
#SBATCH --partition=batch
#SBATCH -t 00:30:00
#SBATCH --ntasks=192
#SBATCH -o log.fcst
#SBATCH --exclusive --clusters=c6
#SBATCH --comment=ae72bfb6bb09054fd18586e3585beea4
export RUN_ENVIR='emc'
export HOMEgfs='/gpfs/f6/scratch/Wei.Huang/src/demo/global-workflow-cloud'
export EXPDIR='/gpfs/f6/scratch/Wei.Huang/run/prefix/EXPDIR/C48_S2SW'
export NET='gfs'
export RUN='gfs'
export CDATE='2021032312'
export PDY='20210323'
export cyc='12'
export COMROOT='/gpfs/f6/scratch/Wei.Huang/run/prefix/COMROOT'
export DATAROOT='/gpfs/f6/scratch/Wei.Huang/run/stmp/prefix/RUNDIRS/C48_S2SW/gfs.2021032312'
export FCST_SEGMENT='0'
/gpfs/f6/scratch/Wei.Huang/src/demo/global-workflow-cloud/dev/job_cards/rocoto/fcst.sh

