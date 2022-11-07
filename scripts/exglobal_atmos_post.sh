#! /usr/bin/env bash

source "${HOMEgfs}/ush/preamble.sh"

# Determine which yaml file to use
case ${fhr} in
	anl) yaml_cat='anl' ;;
	000) yaml_cat='f000';;
	*)   yaml_cat='fhr' ;;
esac
post_settings="${PARMpost}/atm_post_${CDUMP}_${yaml_cat}.yaml"

# Run post
"${HOMEgfs}/ush/atm_post.py" "${post_settings}"
err=$?

exit ${err}
