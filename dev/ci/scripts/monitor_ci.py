#!/usr/bin/env python3

from argparse import ArgumentParser
import os
import sys
from time import sleep
from wxflow import which, Logger, CommandNotFoundError, ProcessError
import utils.rocotostat as rs
from datetime import datetime, timedelta

SLEEP_DURATION = 120  # Sleep duration (seconds) between rocoto runs
MAX_RUN_TIME = timedelta(hours=24)
MAX_CONSECUTIVE_UNAVAILABLE = 3

# This scrpit is a utility with unix style pipe-able side effects so
# stdout True only if LOGGING_LEVEL is DEBUG, else False
_log_level = os.environ.get("LOGGING_LEVEL", "INFO").upper()
_stdout = _log_level == "DEBUG"
logger = Logger(
    level=_log_level,
    colored_log=False,
    stdout=_stdout,
    logfile_path=os.environ.get("ROCOTOSTAT_LOG_FILE")
)


def input_args():
    """
    Parse command-line arguments for rocotostat workflow analysis.

    This function configures and parses command-line arguments used to specify the Rocoto workflow XML document and database
    file, along with optional flags for verbose output and bash declare functionality. The function validates input files and
    returns a namespace object containing all parsed arguments for use throughout the rocotostat analysis process.

    Returns
    -------
    args : Namespace
        The parsed command-line arguments containing workflow document path, database file path, and output format options.
    """

    description = """
        Using rocotostat to get the status of all jobs this scripts
        determines rocoto_state: if all cycles are done, then rocoto_state
        is Done. Assuming rocotorun had just been run, and the rocoto_state
        is not Done, then rocoto_state is Stalled if there are no jobs that
        are RUNNING, SUBMITTING, or QUEUED.
        """

    parser = ArgumentParser(description=description)

    parser.add_argument('expdir', help='Path to the experiment directory containing Rocoto workflow XML and database files')
    parser.add_argument('--verbose', action='store_true', help='List the states and the number of jobs that are in each', required=False)
    parser.add_argument('-v', dest='verbose')

    args = parser.parse_args()

    return args


def print_status(rocoto_status):
    """
    Print the status of the Rocoto workflow for each experiment.

    This function takes a dictionary containing the status of each experiment's Rocoto workflow and prints a summary of the
    overall status, including whether all experiments are done or if any have failed jobs. It also provides detailed information
    about each experiment's status, including the number of cycles completed and the total number of cycles.

    Parameters
    ----------
    rocoto_status : dict
        A dictionary where keys are experiment names and values are dictionaries containing the status information for each
        experiment's Rocoto workflow.
    """

    if not rocoto_status:
        print("No experiment status available.")
        return

    headers = ["Experiment", "State", "Cyc Done", "Running", "Queued", "Duration"]
    rows = []
    for experiment, status in rocoto_status.items():
        rows.append([
            experiment,
            status['ROCOTO_STATE'],
            f"{status['CYCLES_DONE']}/{status['CYCLES_TOTAL']}",
            str(status.get('RUNNING', '0')),
            str(status.get('QUEUED', '0')),
            str(status['DURATION']) if status.get('DURATION') is not None else 'N/A',
        ])

    column_widths = [len(header) for header in headers]
    for row in rows:
        for i, value in enumerate(row):
            column_widths[i] = max(column_widths[i], len(value))

    header_line = " | ".join(header.rjust(column_widths[i]) for i, header in enumerate(headers))
    separator_line = "-+-".join("-" * column_widths[i] for i in range(len(headers)))

    print(f'  Status at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  '.center(len(header_line), '='))
    print(header_line)
    print(separator_line)
    for row in rows:
        print(" | ".join(value.rjust(column_widths[i]) for i, value in enumerate(row)))
    print()


def check_end_states(rocoto_status, consecutive_unavailable_count):
    """
    Check the end states of the Rocoto workflow and handle exit conditions.

    This function evaluates the status of each experiment's Rocoto workflow to determine if all experiments are done, if any have failed jobs, or if the status is unavailable or unknown. It increments a counter for consecutive unavailable or unknown states and exits the script with appropriate exit codes based on the conditions met.

    Parameters
    ----------
    rocoto_status : dict
        A dictionary where keys are experiment names and values are dictionaries containing the status information for each experiment's Rocoto workflow.
    consecutive_unavailable_count : int
        The current count of consecutive checks where the Rocoto status was unavailable or unknown.

    Returns
    -------
    consecutive_unavailable_count : int
        The updated count of consecutive checks where the Rocoto status was unavailable or unknown.

    """

    if all(status['ROCOTO_STATE'] == 'DONE' for status in rocoto_status.values()):
        logger.info("All experiments are done.")
        sys.exit(rs.EXIT_CODE['DONE'])

    for status in ['FAIL', 'ERROR', 'STALLED']:
        if any(status['ROCOTO_STATE'] == status for status in rocoto_status.values()):
            logger.error(f"One or more experiments have {status.lower()} jobs.")
            sys.exit(rs.EXIT_CODE[status])

    if any(status['ROCOTO_STATE'] in ['UNAVAILABLE', 'UNKNOWN'] for status in rocoto_status.values()):
        consecutive_unavailable_count += 1
        logger.warning(f"Rocoto status is unavailable or unknown for {consecutive_unavailable_count} consecutive checks.")
        if consecutive_unavailable_count >= MAX_CONSECUTIVE_UNAVAILABLE:
            logger.error("Maximum consecutive unavailable or unknown checks reached. Exiting.")
            sys.exit(rs.EXIT_CODE['UNAVAILABLE'])
    else:
        consecutive_unavailable_count = 0

    return consecutive_unavailable_count


if __name__ == '__main__':
    """
    main Execute the script.

    main() parses the input arguments, checks if the rocotostat command is available,
    adds default arguments to the rocotostat command, and runs it and reports
    out to stdout spcific information of rocoto workflow.
    """

    args = input_args()

    try:
        rocotorun = which("rocotorun")
    except CommandNotFoundError:
        logger.exception("rocotorun not found in PATH")
        raise CommandNotFoundError("rocotorun not found in PATH")

    try:
        rocotostat = which("rocotostat")
    except CommandNotFoundError:
        logger.exception("rocotostat not found in PATH")
        raise CommandNotFoundError("rocotostat not found in PATH")

    experiments = [dir for dir in os.listdir(args.expdir) if os.path.isdir(os.path.join(args.expdir, dir))]

    consecutive_unavailable_count = 0

    logger.info(f'Experiments found: {experiments}')

    start_time = datetime.now()
    logger.info(f'Monitoring started at: {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
    while datetime.now() - start_time < MAX_RUN_TIME:

        rocoto_status = {}
        for experiment in experiments:
            logger.info(f'Updating {experiment}')
            experiment_path = os.path.join(args.expdir, experiment)
            workflow_file = os.path.join(experiment_path, f'{experiment}.xml')
            database_file = os.path.join(experiment_path, f'{experiment}.db')

            if not os.path.isfile(workflow_file):
                logger.warning(f"Workflow file not found: {workflow_file}")
                continue

            rocotorun_args = ['-w', workflow_file, '-d', database_file]
            rocotostat_args = ['-w', workflow_file, '-d', database_file]

            if args.verbose:
                rocotorun_args.append('--verbose')
                rocotostat_args.append('--verbose')

            rocotorun.add_default_arg(rocotorun_args)
            rocotostat.add_default_arg(rocotostat_args)

            try:
                rs.run_rocoto(rocotorun)
                rocoto_status[experiment] = rs.rocoto_status(rocotostat)
            except ProcessError as e:
                logger.error(f"Error running rocoto for experiment {experiment}: {e}")

        print_status(rocoto_status)

        # Check for end states and remember how many times in a row the status was unavailable or unknown
        consecutive_unavailable_count = check_end_states(rocoto_status, consecutive_unavailable_count)

        logger.info(f'Sleeping for {SLEEP_DURATION} seconds before next check...')
        sleep(SLEEP_DURATION)

    sys.exit(rs.EXIT_CODE['MAX_TIME_EXCEEDED'])
