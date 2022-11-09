#! /usr/bin/env bash

source "${HOMEgfs}/ush/preamble.sh"

for type in "atm" "sflux"; do
	# Determine which yaml file to use
	case ${fhr} in
		anl) yaml_cat='anl' ;;
		000) yaml_cat='f000';;
		*)   yaml_cat='fhr' ;;
	esac
	post_settings="${PARMpost}/${type}_post_${yaml_cat}.yaml"

	# Run post
	"${HOMEgfs}/ush/atm_post.py" "${post_settings}"
	err=$?

	if ((err > 0)); then
		exit "${err}"
	fi
done

exit
