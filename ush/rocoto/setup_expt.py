#!/usr/bin/env python3

'''
Entry point for setting up an experiment in the global-workflow
'''

import os
import glob
import shutil
from datetime import datetime
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, FileType
import workflow_utils as wfu
import yaml
from pprint import pprint
from textwrap import dedent

def makedirs_if_missing(dirname):
    '''
    Creates a directory if not already present
    '''
    if not os.path.exists(dirname):
        os.makedirs(dirname)


def fill_COMROT(host, inputs):
    '''
    Method to populate the COMROT for supported modes.
    INPUTS:
        host: host specific object from class HostInfo in workflow_utils.py
        inputs: user inputs to setup_expt.py
    '''

    fill_modes = {
        'cycled': fill_COMROT_cycled,
        'forecast-only': fill_COMROT_forecasts
    }

    try:
        fill_modes[inputs['mode']](host, inputs)
    except KeyError:
        raise NotImplementedError(f'{inputs["mode"]} is not a supported mode.\n' +
                                  'Currently supported modes are:\n' +
                                  f'{" | ".join(fill_modes.keys())}')

    return


def fill_COMROT_cycled(host, inputs):
    '''
    Implementation of 'fill_COMROT' for cycled mode
    '''

    idatestr = inputs['idate'].strftime('%Y%m%d%H')
    comrot = os.path.join(inputs['comrot'], inputs['pslot'])

    if inputs['icsdir'] is not None:
        # Link ensemble member initial conditions
        enkfdir = f'enkf{inputs["cdump"]}.{idatestr[:8]}/{idatestr[8:]}'
        makedirs_if_missing(os.path.join(comrot, enkfdir))
        for ii in range(1, inputs['nens'] + 1):
            makedirs_if_missing(os.path.join(comrot, enkfdir, f'mem{ii:03d}'))
            os.symlink(os.path.join(inputs['icsdir'], idatestr, f'C{inputs["resens"]}', f'mem{ii:03d}', 'RESTART'),
                       os.path.join(comrot, enkfdir, f'mem{ii:03d}', 'RESTART'))

        # Link deterministic initial conditions
        detdir = f'{inputs["cdump"]}.{idatestr[:8]}/{idatestr[8:]}'
        makedirs_if_missing(os.path.join(comrot, detdir))
        os.symlink(os.path.join(inputs["icsdir"], idatestr, f'C{inputs["resdet"]}', 'control', 'RESTART'),
                   os.path.join(comrot, detdir, 'RESTART'))

        # Link bias correction and radiance diagnostics files
        for fname in ['abias', 'abias_pc', 'abias_air', 'radstat']:
            os.symlink(os.path.join(inputs["icsdir"], idatestr, f'{inputs["cdump"]}.t{idatestr[8:]}z.{fname}'),
                       os.path.join(comrot, detdir, f'{inputs["cdump"]}.t{idatestr[8:]}z.{fname}'))

    return


def fill_COMROT_forecasts(host, inputs):
    '''
    Implementation of 'fill_COMROT' for forecast-only mode
    '''
    return


def fill_EXPDIR(inputs):
    '''
    Method to copy config files from workflow to experiment directory
    INPUTS:
        inputs: user inputs to `setup_expt.py`
    '''
    configdir = inputs['configdir']
    expdir = os.path.join(inputs['expdir'], inputs['pslot'])

    configs = glob.glob(f'{configdir}/config.*')
    if len(configs) == 0:
        raise IOError(f'no config files found in {configdir}')
    for config in configs:
        shutil.copy(config, expdir)

    if 'settings' in inputs.keys():
        write_case_config(os.path.join(expdir, 'config.case'), inputs['settings'])

    return


def edit_baseconfig(host, inputs):
    '''
    Parses and populates the templated `config.base.emc.dyn` to `config.base`
    '''

    base_config = f'{inputs["expdir"]}/{inputs["pslot"]}/config.base'

    here = os.path.dirname(__file__)
    top = os.path.abspath(os.path.join(
        os.path.abspath(here), '../..'))

    if os.path.exists(base_config):
        os.unlink(base_config)

    tmpl_dict = {
        "@MACHINE@": host.machine.upper(),
        "@PSLOT@": inputs['pslot'],
        "@SDATE@": inputs['idate'].strftime('%Y%m%d%H'),
        "@EDATE@": inputs['edate'].strftime('%Y%m%d%H'),
        "@CASECTL@": f'C{inputs["resdet"]}',
        "@HOMEgfs@": top,
        "@BASE_GIT@": host.info["base_git"],
        "@DMPDIR@": host.info["dmpdir"],
        "@NWPROD@": host.info["nwprod"],
        "@COMROOT@": host.info["comroot"],
        "@HOMEDIR@": host.info["homedir"],
        "@EXPDIR@": inputs['expdir'],
        "@ROTDIR@": inputs['comrot'],
        "@ICSDIR@": inputs['icsdir'],
        "@STMP@": host.info["stmp"],
        "@PTMP@": host.info["ptmp"],
        "@NOSCRUB@": host.info["noscrub"],
        "@ACCOUNT@": host.info["account"],
        "@QUEUE@": host.info["queue"],
        "@QUEUE_SERVICE@": host.info["queue_service"],
        "@PARTITION_BATCH@": host.info["partition_batch"],
        "@EXP_WARM_START@": inputs['warm_start'],
        "@MODE@": inputs['mode'],
        "@CHGRP_RSTPROD@": host.info["chgrp_rstprod"],
        "@CHGRP_CMD@": host.info["chgrp_cmd"],
        "@HPSSARCH@": host.info["hpssarch"],
        "@LOCALARCH@": host.info["localarch"],
        "@ATARDIR@": host.info["atardir"],
        "@gfs_cyc@": inputs['gfs_cyc'],
        "@APP@": inputs['app'],
    }

    if inputs['mode'] in ['cycled']:
        extend_dict = {
            "@CASEENS@": f'C{inputs["resens"]}',
            "@NMEM_ENKF@": inputs['nens'],
        }
        tmpl_dict = dict(tmpl_dict, **extend_dict)

    with open(base_config + '.emc.dyn', 'rt') as fi:
        basestr = fi.read()

    for key, val in tmpl_dict.items():
        basestr = basestr.replace(key, str(val))

    with open(base_config, 'wt') as fo:
        fo.write(basestr)

    print('')
    print(f'EDITED:  {base_config} as per user input.')
    print(f'DEFAULT: {base_config}.emc.dyn is for reference only.')
    print('Please verify and delete the default file before proceeding.')
    print('')

    return


def input_args():
    '''
    Method to collect user arguments for `setup_expt.py`
    '''

    here = os.path.dirname(__file__)
    top = os.path.abspath(os.path.join(
        os.path.abspath(here), '../..'))

    description = """
        Setup files and directories to start a GFS parallel.\n
        Create EXPDIR, copy config files.\n
        Create COMROT experiment directory structure,
        link initial condition files from $ICSDIR to $COMROT
        """

    parser = ArgumentParser(description=description,
                            formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('--user_file', help='YAML containing user paths', required=False, default=None, type=FileType(mode='r'))
    parser.add_argument('--case_file', help='YAML containing experiment settings', required=True, default=None, type=FileType(mode='r'))
    parser.add_argument('--pslot', help='parallel experiment name', type=str, required=False, default='test')
    parser.add_argument('--comrot', help='full path to COMROT', type=str, required=False, default=os.getenv('HOME'))
    parser.add_argument('--expdir', help='full path to EXPDIR', type=str, required=False, default=os.getenv('HOME'))
    defaults = {
        'pslot': 'test',
        'resdet': 384,
        'app': 'ATM',
        'configdir': os.path.join(top, 'parm/config'),
        'cdump': 'gdas',
        'gfs_cyc': 1,
        'start': 'cold',
        'resens': 192,
        'nens': 20,
    }

    # # Set up sub-parsers for various modes of experimentation
    # subparser = parser.add_subparsers(dest='mode')
    # cycled = subparser.add_parser(
    #     'cycled', help='arguments for cycled mode')
    # forecasts = subparser.add_parser(
    #     'forecast-only', help='arguments for forecast-only mode')

    # # Common arguments across all modes
    # for subp in [cycled, forecasts]:
    #     subp.add_argument('--pslot', help='parallel experiment name',
    #                       type=str, required=False, default='test')
    #     subp.add_argument('--resdet', help='resolution of the deterministic model forecast',
    #                       type=int, required=False, default=384)
    #     subp.add_argument('--comrot', help='full path to COMROT',
    #                       type=str, required=False, default=os.getenv('HOME'))
    #     subp.add_argument('--expdir', help='full path to EXPDIR',
    #                       type=str, required=False, default=os.getenv('HOME'))
    #     subp.add_argument('--idate', help='starting date of experiment, initial conditions must exist!', required=False, type=lambda dd: datetime.strptime(dd, '%Y%m%d%H'))
    #     subp.add_argument('--edate', help='end date experiment', required=False, type=lambda dd: datetime.strptime(dd, '%Y%m%d%H'))
    #     subp.add_argument('--icsdir', help='full path to initial condition directory', type=str, required=False, default=None)
    #     subp.add_argument('--configdir', help='full path to directory containing the config files',
    #                       type=str, required=False, default=os.path.join(top, 'parm/config'))
    #     subp.add_argument('--cdump', help='CDUMP to start the experiment',
    #                       type=str, required=False, default='gdas')
    #     subp.add_argument('--gfs_cyc', help='GFS cycles to run', type=int,
    #                       choices=[0, 1, 2, 4], default=1, required=False)
    #     subp.add_argument('--start', help='restart mode: warm or cold', type=str,
    #                       choices=['warm', 'cold'], required=False, default='cold')
    #     subp.add_argument('--case_file', help='case file', required=False, default=None, type=FileType(mode='r'))

    # # cycled mode additional arguments
    # cycled.add_argument('--resens', help='resolution of the ensemble model forecast',
    #                     type=int, required=False, default=192)
    # cycled.add_argument('--nens', help='number of ensemble members',
    #                     type=int, required=False, default=20)
    # cycled.add_argument('--app', help='UFS application', type=str,
    #                     choices=['ATM', 'ATMW'], required=False, default='ATM')

    # # forecast only mode additional arguments
    # forecasts.add_argument('--app', help='UFS application', type=str, choices=[
    #     'ATM', 'ATMW', 'S2S', 'S2SW'], required=False, default='ATM')
    # forecasts.add_argument('--aerosols', help="Run with coupled aerosols", required=False,
    #                        action='store_const', const="YES", default="NO")

    settings = defaults

    args = parser.parse_args()

    if args.user_file is not None:
        settings.update(yaml.load(args.user_file))

    if args.case_file is not None:
        settings.update(process_yaml(yaml.load(args.case_file)))

    settings.update({key: value for key, value in args.__dict__.items() if value is not None})

    validate_settings(settings)

    # Add an entry for warm_start = .true. or .false.
    if settings['start'] == "warm":
        settings['warm_start'] = ".true."
    else:
        settings['warm_start'] = ".false."
    return settings


def query_and_clean(dirname):
    '''
    Method to query if a directory exists and gather user input for further action
    '''

    create_dir = True
    if os.path.exists(dirname):
        print()
        print(f'directory already exists in {dirname}')
        print()
        overwrite = input('Do you wish to over-write [y/N]: ')
        create_dir = True if overwrite in [
            'y', 'yes', 'Y', 'YES'] else False
        if create_dir:
            shutil.rmtree(dirname)

    return create_dir


def write_case_config(filename: str, settings: dict) -> None:
    '''
    Writes a bash file with variable exports determined by a given dictionary.

    Parameters
    ----------
    filename: str
        File name to write to (usually expdir/config.case)

    settings: dict
        Dictionary containing variable/value pairs of variables to be written in bash form

    Returns
    ----------
    None

    '''

    case_config = open(filename, "w")

    write_string = dedent(
    f'''    #! /usr/bin/env bash

    #
    # Auto-generated by setup_expt.py
    #

    echo "BEGIN: {filename}"

    # 
    # Settings in this file will overwrite defaults in other config files
    #

    {os.linesep.join([f'export {key}="{settings[key]}"' for key in settings.keys()])}

    echo "END: {filename}"

    ''')
    
    case_config.write(write_string)
    case_config.close()

    return None


def process_yaml(case_data: dict) -> dict:
    '''
    Conducts any necessary processing to convert variables from the case file
     into the appropriate types

    Parameters
    ----------
    case_data: dict
        Dictionary containing the data from the provided case file

    Returns
    ----------
    dict
        Modified dictionary with variables converted to the correct types

    '''
    for var in ['idate', 'edate']:
        if case_data[var] is not None:
            case_data[var] = datetime.strptime(str(case_data[var]), '%Y%m%d%H')

    return case_data


def validate_settings(settings: dict) -> None:
    '''
    Validates that all needed settings are present and in the correct form

    Parameters
    ----------
    settings: dict
        Dictionary containing all of the settings

    Returns
    ----------
    None

    Raises
    ----------
    SyntaxError
        If any of the necessary settings are missing or invalid

    '''
    # This is probably more properly done with schema, but schema is not part of the standard 
    #   installation on Hera

    mandatory_settings = ['mode', 'idate', 'edate']
    if not all ([var in settings.keys() for var in mandatory_settings]):
        raise SyntaxError(f'The following settings must be specified in either the case file or as an argument:{os.linesep}{os.linesep.join(mandatory_settings)}')

    mode_allowed = ['cycled', 'forecast-only']
    if settings['mode'] not in mode_allowed:
        raise SyntaxError(f'mode must be one of {mode_allowed}')

    start_allowed = ['cold', 'warm']
    if settings['start'] not in start_allowed:
        raise SyntaxError(f'start must be one of {start_allowed}')


    app_allowed = ['ATM', 'ATMA', 'ATAW', 'ATMAW', 'S2S', 'S2SA', 'S2SW', 'S2SAW']
    if settings['app'] not in app_allowed:
        raise SyntaxError(f'app must be one of {app_allowed}')

    if settings['app'][0:3] in ['S2S'] and 'icsdir' not in settings.keys():
        raise SyntaxError("icsdir must be specified in either the case file or as an argument when running an S2S app")


if __name__ == '__main__':

    user_inputs = input_args()
    host=wfu.HostInfo(wfu.detectMachine())

    comrot = os.path.join(user_inputs['comrot'], user_inputs['pslot'])
    expdir = os.path.join(user_inputs['expdir'], user_inputs['pslot'])

    create_comrot = query_and_clean(comrot)
    create_expdir = query_and_clean(expdir)

    if create_comrot:
        makedirs_if_missing(comrot)
        fill_COMROT(host, user_inputs)

    if create_expdir:
        makedirs_if_missing(expdir)
        fill_EXPDIR(user_inputs)
        edit_baseconfig(host, user_inputs)
