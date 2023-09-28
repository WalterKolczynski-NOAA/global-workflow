#! /usr/bin/env bash

source "${HOMEgfs}/ush/preamble.sh"

# Locally scoped variables and functions
# shellcheck disable=SC2153
GDATE=$(date -d "${PDY} ${cyc} - ${assim_freq} hours" +%Y%m%d%H)
gPDY="${GDATE:0:8}"
gcyc="${GDATE:8:2}"


member_dirs=()

if [[ "${RUN}" == "gefs" ]]; then
# Populate the member_dirs array based on the value of NMEM_ENS
  for ((i = 0; i < "${NMEM_ENS}"; i++)); do
    member_dirs+=("mem$(printf "%03d" "${i}")")
  done
else
member_dirs+=("")
fi

# Initialize return code
err=0

error_message(){
    echo "FATAL ERROR: Unable to copy ${1} to ${2} (Error code ${3})"
}

###############################################################
# Start staging gefs and gfs here
# Stage the FV3 initial conditions to ROTDIR (cold start)

for MEMDIR in ${memdir[@]}; do

member_dir=""
NMEM_ENS=0
YMD=${PDY} HH=${cyc} generate_com -r COM_ATMOS_INPUT
[[ ! -d "${COM_ATMOS_INPUT}" ]] && mkdir -p "${COM_ATMOS_INPUT}"
  for member_dir in $(seq -w 0 $((NMEM_ENS - 1))); do
    source="${BASE_CPLIC}/${CPL_ATMIC}/${YMD}${HH}/${member_dir}/atmos/gfs_ctrl.nc"
    target="${COM_ATMOS_INPUT}/gfs_ctrl.nc"
    ${NCP} "${source}" "${target}"
    rc=$?
    (( rc != 0 )) && error_message "${source}" "${target}" "${rc}"
    err=$((err + rc))
    for ftype in gfs_data sfc_data; do
      for tt in $(seq 1 6); do
        source="${BASE_CPLIC}/${CPL_ATMIC}/${YMD}${HH}/${member_dir}/atmos/${ftype}.tile${tt}.nc"
        target="${COM_ATMOS_INPUT}/${ftype}.tile${tt}.nc"
        rc=$?
        (( rc != 0 )) && error_message "${source}" "${target}" "${rc}"
        err=$((err + rc))
      done
    done
  done

# Stage ocean initial conditions to ROTDIR (warm start)
if [[ "${DO_OCN:-}" = "YES" ]]; then
member_dir=""
NMEM_ENS=0
  YMD=${gPDY} HH=${gcyc} generate_com -r COM_OCEAN_RESTART
  [[ ! -d "${COM_OCEAN_RESTART}" ]] && mkdir -p "${COM_OCEAN_RESTART}"
    for member_dir in $(seq -w 0 $((NMEM_ENS - 1))); do
    source="${BASE_CPLIC}/${CPL_ATMIC}/${YMD}${HH}/${member_dir}/ocean/${PDY}.${cyc}0000.MOM.res.nc"
    target="${COM_OCEAN_RESTART}/${PDY}.${cyc}0000.MOM.res.nc"
    ${NCP} "${source}" "${target}"
    rc=$?
    (( rc != 0 )) && error_message "${source}" "${target}" "${rc}"
    err=$((err + rc))
    done
      echo "FATAL ERROR: Unsupported ocean resolution ${OCNRES}"
      rc=1
      err=$((err + rc))
fi

# Stage ice initial conditions to ROTDIR (warm start)
if [[ "${DO_ICE:-}" = "YES" ]]; then
  member_dir=""
  NMEM_ENS=0
  YMD=${gPDY} HH=${gcyc} generate_com -r COM_ICE_RESTART
  [[ ! -d "${COM_ICE_RESTART}" ]] && mkdir -p "${COM_ICE_RESTART}"
    for member_dir in $(seq -w 0 $((NMEM_ENS - 1))); do
    source="${BASE_CPLIC}/${CPL_ATMIC}/${YMD}${HH}/${member_dir}/ice/${PDY}.${cyc}0000.cice_model.res.nc"
    target="${COM_OCEAN_RESTART}/${PDY}.${cyc}0000.cice_model.res.nc"
    ${NCP} "${source}" "${target}"
    rc=$?
    (( rc != 0 )) && error_message "${source}" "${target}" "${rc}"
    err=$((err + rc))
    done
      echo "FATAL ERROR: Unsupported ocean resolution ${OCNRES}"
      rc=1
      err=$((err + rc))
fi

# Stage the WW3 initial conditions to ROTDIR (warm start; TODO: these should be placed in $RUN.$gPDY/$gcyc)
if [[ "${DO_WAVE:-}" = "YES" ]]; then
  member_dir=""
  NMEM_ENS=0
  YMD=${PDY} HH=${cyc} generate_com -r COM_WAVE_RESTART
  [[ ! -d "${COM_WAVE_RESTART}" ]] && mkdir -p "${COM_WAVE_RESTART}"
  for grdID in ${waveGRD}; do  # TODO: check if this is a bash array; if so adjust
    source="${BASE_CPLIC}/${CPL_WAVIC}/${PDY}${cyc}/wav/${grdID}/${PDY}.${cyc}0000.restart.${grdID}"
    target="${COM_WAVE_RESTART}/${PDY}.${cyc}0000.restart.${grdID}"
    ${NCP} "${source}" "${target}"
    rc=$?
    (( rc != 0 )) && error_message "${source}" "${target}" "${rc}"
    err=$((err + rc))
  done
elif [[ "${DO_WAVE:-}" = "YES" && "${RUN}" = "gefs" ]]; then
  YMD=${gPDY} HH=${gcyc} generate_com -r COM_WAVE_RESTART
  [[ ! -d "${COM_WAVE_RESTART}" ]] && mkdir -p "${COM_WAVE_RESTART}"
    for member_dir in $(seq -w 0 $((NMEM_ENS - 1))); do
    source="${BASE_CPLIC}/${CPL_ATMIC}/${YMD}${HH}/${member_dir}/ice/${PDY}.${cyc}0000.restart.${waveGRD}"
    target="${COM_OCEAN_RESTART}/${PDY}.${cyc}0000.restart.${waveGRD}"
    ${NCP} "${source}" "${target}"
    rc=$?
    (( rc != 0 )) && error_message "${source}" "${target}" "${rc}"
    err=$((err + rc))
    done
      echo "FATAL ERROR: Unsupported ocean resolution ${OCNRES}"
      rc=1
      err=$((err + rc))
fi
done
###############################################################
# Check for errors and exit if any of the above failed
if  [[ "${err}" -ne 0 ]] ; then
  echo "FATAL ERROR: Unable to copy ICs from ${BASE_CPLIC} to ${ROTDIR}; ABORT!"
  exit "${err}"
fi

##############################################################
# Exit cleanly
exit "${err}"
