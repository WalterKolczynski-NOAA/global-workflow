#! /usr/bin/env bash

#
# Script name:         exgfs_pmgr.sh.sms
#
#  This script monitors the progress of the gfs_fcst job
#

PREAMBLE_SCRIPT="${PREAMBLE_SCRIPT:-$HOMEgfs/ush/preamble.sh}"
if [ -f "${PREAMBLE_SCRIPT}" ]; then
  source $PREAMBLE_SCRIPT
fi

hour=00
TEND=384
TCP=385

if [ -e pgrb2_hours ]; then
   rm -f pgrb2_hours
fi

while [ $hour -lt $TCP ]; 
do
  hour=$(printf "%02d" $hour)
  echo $hour >>pgrb2_hours
  if [ 10#$hour -lt 240 ]
  then
     if [ 10#$hour -lt 120 ]
     then
       let "hour=hour+1"
     else
       let "hour=hour+3"
     fi
  else
     let "hour=hour+12"
  fi
done
pgrb2_jobs=$(cat pgrb2_hours)

#
# Wait for all fcst hours to finish 
#
icnt=1
while [ $icnt -lt 1000 ]
do
  for fhr in ${pgrb2_jobs}
  do    
    if [ -s ${COMIN}/gfs.${cycle}.master.grb2if${fhr} ]
    then
#      if [ $fhr -eq 0 ]
#      then 
#        ecflow_client --event release_pgrb2_anl
#      fi    
      ecflow_client --event release_pgrb2_${fhr}
      # Remove current fhr from list
      pgrb2_jobs=$(echo ${pgrb2_jobs} | sed "s/${fhr}//")
    fi
  done
  
  result_check=$(echo ${pgrb2_jobs} | wc -w)
  if [ $result_check -eq 0 ]
  then
     break
  fi

  sleep 10
  icnt=$((icnt + 1))
  if [ $icnt -ge 720 ]
  then
    msg="ABORTING after 2 hours of waiting for GFS POST hours ${pgrb2_jobs}."
    err_exit $msg
  fi

done


exit
