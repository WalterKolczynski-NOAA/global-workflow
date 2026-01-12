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

export HOMEgfs=/gpfs/f6/scratch/Wei.Huang/src/demo/global-workflow-cloud
cd /gpfs/f6/scratch/Wei.Huang/run/stmp/prefix/RUNDIRS/C48_S2SW/gfs.2021032312/gfsfcst.2021032312/fcst.2649583
srun --mpi=pmi2 -l --export=ALL --distribution=block:block -n 192 \
/gpfs/f6/scratch/Wei.Huang/src/demo/global-workflow-cloud/dev/container/prefix/container_forecast.sh \
./gfs_model.x
