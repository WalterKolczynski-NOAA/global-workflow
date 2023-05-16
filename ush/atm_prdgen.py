#! /usr/bin/env python3

import os
import shutil
import subprocess
import time
from datetime import timedelta
from argparse import ArgumentParser
from python.pygw.src.pygw import timetools
from python.pygw.src.pygw.fsutils import mkdir
from python.pygw.src.pygw.yaml_file import YAMLFile
from pprint import pprint
from functools import partial

# Make sure print is flushed immediately
print = partial(print, flush=True)

def send_com(settings: dict) -> None:
    '''
    Copies post output from current directory to final destination. The current directory
    must have files names pgbfile and pgifile for the master grib file and its index,
    repsectively.

    Parameters
    ----------
    settings : dict
               Dictionary with paths for the final file names. The following key/value
               pairs must be defined:
               grib_out     : str
                              File name for the master grib file
               grib_idx_out : str
                              File naem for the master grib file index

    Returns
    -------
    None

    '''
    # shutil.copyfile('pgbfile', settings['grib_out'])
    # shutil.copyfile('pgifile', settings['grib_idx_out'])
    pass


def send_dbn(settings: dict) -> None:
    '''
    Sends specified alerts to the data broadcast network (DBN).

    Parameters
    ----------
    settings : dict
               Dictionary with paths for the final file names. The following key/value
               pairs must be defined:
               dbn_alert   : str
                             The command to send a DBN alert
               dbn_signals : dict
                             Sub-dictionary with a list of signals (keys) and the files they are
                             signaling (values)

    '''
    for signal in settings.get('dbn_signals', []):
        signal_file = settings['dbn_signals'][signal]
        subprocess.run(f"{settings['dbn_alert']} {signal} {signal_file}", shell=True, check=True)


if __name__ == '__main__':
    '''
    Runs post using a given settings file.

    Parameters
    ----------
    settings_file : YAML file containing the settings to use for prdgen

    Returns
    -------
    None

    '''
    parser = ArgumentParser()
    parser.add_argument('settings_file',
                        help='Path to the YAML file containing the product generation settings')

    args = parser.parse_args()
    settings = YAMLFile(path=args.settings_file)
    # Move all settings that are defined under include to the top level
    # TODO make this recursive
    for inc in settings.pop('include', []):
        settings.update(inc)

    print("Running prdgen using the following settings:")
    pprint(settings)

    if settings['send_com'] in ["YES"]:
        send_com(settings)

    if settings['send_dbn'] in ["YES"]:
        send_dbn(settings)