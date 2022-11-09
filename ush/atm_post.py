#! /usr/bin/env python3

import os
import shutil
import subprocess
import time
from datetime import timedelta
from argparse import ArgumentParser
from python.pygw.src.pygw import timetools
from python.pygw.src.pygw.template import Template, TemplateConstants
from python.pygw.src.pygw.fsutils import mkdir
from python.pygw.src.pygw.yaml_file import YAMLFile
from pprint import pprint
from functools import partial

# Make sure print is flushed immediately
print = partial(print, flush=True)


def run_post(settings: dict) -> None:
    '''
    Runs UPP as an MPI job, then creates an index file.

    Parameters
    ----------
    settings : dict
               Dictionary of settings needed to run post. Dictionary must include
               the following keys/value pairs:
                   mpi_run      : str
                                  Command to execute an mpi job
                   grib_idx_exe : str
                                  Path to program that creates a grib index file
                   exe_log_file : str
                                  Path to log file for executables

    Returns
    -------
    None

    Input files
    -----------
    The following must be in the current directory:
    upp.x : Post executable
    itag  : Post namelist

    Output files
    ------------
    pgbfile : GRiB2 file for input data on gaussian grid
    pgifile : GRiB2 index of pgbfile

    '''
    with open('itag', 'r') as file:
        print(f'''
                Executing {settings['post_exe']} (copied as upp.x) with the
                following namelist:
                    {file.read()}

                Output will be written to {settings['exe_log_file']}

                '''
              )
    os.environ['PGBOUT'] = 'pgbfile'
    subprocess.run(f"{settings['mpi_run']} upp.x >> {settings['exe_log_file']}", shell=True, check=True)
    subprocess.run(f"{settings['grib_idx_exe']} pgbfile pgifile >> {settings['exe_log_file']}",
                   shell=True, check=True)


def make_namelist(settings: dict) -> str:
    '''
    Takes a namelist template and substitutes in variables and the verification time.

    Parameters
    ----------
    settings : dict
               Dictionary contaning the name of the template file, the initial time and
               forecast hour, and the variables to substitute. At a minimum, the
               dictionary must have the following key/value pairs:
                   tmpl_file : str
                               Path to the template
                   cdate     : str
                               Initial time in YYYYMMDDHH format
                   fhr       : str
                               Forecast hour (parsable to int) or anl

    Returns
    -------
    str
        String representation of the template file, with substitutions for all of the
        variables in the template that are present in settings, and for all strftime
        format codes (%Y, %m, etc.).

    '''
    with open(settings['tmpl_file'], 'r') as file:
        tmpl = file.read()

    tmpl = Template.substitute_structure(tmpl, TemplateConstants.DOUBLE_CURLY_BRACES, settings.get)
    delta = 0 if settings['fhr'] in ['anl'] else int(settings['fhr'])
    when = timetools.strptime(settings['cdate'], "%Y%m%d%H") + timedelta(hours=delta)
    tmpl = timetools.strftime(when, tmpl)

    return(tmpl)


def wait_for_model_output(settings: dict) -> None:
    '''
    Repeatedly sleeps while waiting for trigger file to be available. Will return
    once the file is present. If the file does not exist after the maximum wait
    time, an exception will be thrown.

    Parameters
    ----------
    settings : dict
               Dictionary containing the needed settings. The dictional must specify
               the following key/value pairs:
                   trigger_file   : str
                                    Path to file we are waiting for
                   sleep_interval : int
                                    Time to sleep between checks (in seconds)
                   sleep_max      : int
                                    Maximum number of seconds to wait

    Returns
    -------
    None

    Raises
    ------
    RuntimeException
        If trigger_file still does not exist after sleep_max seconds

    '''

    sleep_max = settings['sleep_max']
    sleep_interval = settings['sleep_interval']
    trigger_file = settings['trigger_file']

    for timer in range(0, sleep_max // sleep_interval):
        if os.path.isfile(trigger_file):
            # File exists, job can proceed
            return

        time.sleep(sleep_interval)

    raise RuntimeError(f"File {trigger_file} does not exist after waiting {sleep_max}s")


def test_make_namelist() -> None:
    settings = {
        "cdate": '2021061512',
        "fhr": '012',
        "atm_file": "dummy_atm_file",
        "flux_file": "dummy_flux_file",
        "out_form": "netcdfpara",
        "grib_version": "2",
        "post_variables": "test list of post vars",
        "tmpl_file": "../parm/post/post.nml.j2"
    }
    print(make_namelist(settings))


def stage_post(settings: dict, nml_filename: str = 'itag') -> None:
    '''
    Stages all the necessary files and executables to run post.

    Parameters
    ----------
    settings     : dict
                   Dictionary containing all the needed settings to stage. Dictionary must
                   contain the following key/value pairs:
                       work_dir   : str
                                    The temporary working directory to use
                       atm_file   : str
                                    Raw atmosphere model output in NetCDF format. Will be linked
                                    to work_dir as atm_file.
                       sfc_file   : str
                                    Raw atmosphere flux output in NetCDF format. Will be linked
                                    to work_dir as sfc_file.
                       flat_file  : str
                                    Post 'flat' file. Will be linked to work_dir as
                                    postxconfig-NT.txt.
                       grib_table : str
                                    Grib2 table. Will be linked to work_dir.
                       mp_file    : str
                                    Microphysics .dat file. Will be linked to work_dir as
                                    eta_micro_lookup.dat.
                       post_exe   : str
                                    Path to the post executable. Will be linked to work_dir as
                                    upp.x

                   Additionally, the following key/value pair may be defined:
                       is_ens     : bool
                                    Whether data is an ensemble member (default is False)

    nml_filename : str
                   File name for the namelist file. UPP currently expects this to be 'itag'.
                   [Default: 'itag']

    '''
    work_dir = settings['work_dir']
    mkdir(work_dir)
    os.chdir(work_dir)

    namelist = make_namelist(settings)
    with open(nml_filename, 'w') as file:
        file.write(namelist)

    os.symlink(settings['flat_file'], 'postxconfig-NT.txt')
    os.symlink(settings['grib_table'], os.path.basename(settings['grib_table']))
    os.symlink(settings['mp_file'], 'eta_micro_lookup.dat')
    os.symlink(settings['atm_file'], 'atm_file')
    os.symlink(settings['sfc_file'], 'sfc_file')
    os.symlink(settings['post_exe'], 'upp.x')

    if settings.get('is_ens', False):
        # TODO replace negatively_post_fcst with ${ens_pert_type} in postxconfig-NT.txt
        # sed < "${PostFlatFile}" -e "s#negatively_pert_fcst#${ens_pert_type}#" > ./postxconfig-NT.txt
        pass


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
    shutil.copyfile('pgbfile', settings['grib_out'])
    shutil.copyfile('pgifile', settings['grib_idx_out'])


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
                             signalling (values)

    '''
    for signal in settings.get('dbn_signals', []):
        signal_file = settings['dbn_signals'][signal]
        subprocess.run(f"{settings['dbn_alert']} {signal} {signal_file}", shell=True, check=True)


if __name__ == '__main__':
    '''
    Runs post using a given settings file.

    Parameters
    ----------
    settings_file : YAML file containing the settings to use for post

    Returns
    -------
    None

    '''
    parser = ArgumentParser()
    parser.add_argument('settings_file', help='Path to the YAML file containing the post settings')

    args = parser.parse_args()
    settings = YAMLFile(path=args.settings_file)
    # Move all settings that are defined under include to the top level
    # TODO make this recursive
    for inc in settings.pop('include', []):
        settings.update(inc)

    print("Running post using the following settings:")
    pprint(settings)

    stage_post(settings=settings)
    wait_for_model_output(settings=settings)
    run_post(settings=settings)

    if settings['send_com'] in ["YES"]:
        send_com(settings)

    if settings['send_dbn'] in ["YES"]:
        send_dbn(settings)
