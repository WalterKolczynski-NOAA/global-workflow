#!/usr/bin/env python3

from datetime import datetime
import sys
import os
from time import sleep, time

from wxflow import which, Logger, CommandNotFoundError, ProcessError
from argparse import ArgumentParser, FileType

from collections import Counter

# ============================================================================
# RETRY AND TIMING CONSTANTS
# ============================================================================

# Rocoto command retry configuration
ROCOTO_RUN_MAX_ATTEMPTS = 3        # Maximum attempts for rocotorun
ROCOTO_RUN_SLEEP_DURATION = 120    # Sleep duration (seconds) between rocotorun attempts

ROCOTO_SUMMARY_MAX_ATTEMPTS = 3        # Maximum attempts for rocotostat --summary
ROCOTO_SUMMARY_SLEEP_DURATION = 120    # Sleep duration (seconds) between summary attempts

ROCOTO_STATCOUNT_MAX_ATTEMPTS = 4      # Maximum attempts for rocotostat --all
ROCOTO_STATCOUNT_SLEEP_DURATION = 120  # Sleep duration (seconds) between statcount attempts

ROCOTO_RETRY_MAX_ATTEMPTS = 2          # Maximum retry attempts for status checks
ROCOTO_RETRY_SLEEP_DURATION = 120      # Sleep duration (seconds) between retry attempts

# Telescoping delay configuration
TELESCOPING_MAX_DELAY_SECONDS = 600    # Maximum delay cap for telescoping retries
TELESCOPING_DELAY_MULTIPLIER = 2       # Base multiplier for exponential backoff

# Exit codes
EXIT_CODE = {
    'DONE': 0,          # Exit code when workflow is done
    'FAIL': 1,          # Exit code when workflow has failed jobs
    'RUNNING': 2,       # Exit code when workflow is still running
    'STALLED': 3,       # Exit code when workflow is stalled
    'UNAVAILABLE': 4,   # Exit code when workflow has unavailable jobs
    'UNKNOWN': 5,        # Exit code when workflow has unknown job states
    'MAX_TIME_EXCEEDED': 6   # Exit code when maximum time exceeded
}

# ============================================================================

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


def get_user_thread_count():
    """
    Get the current user thread count for monitoring against ulimit -u.

    Returns
    -------
    dict
        Dictionary containing thread count and limit information
    """

    try:
        current_user = os.getenv('USER', 'unknown')

        ps = which('ps')
        try:
            result = ps("-u", current_user, "-L", output=str)
            user_threads = len(result.strip().split('\n')) - 1 if result.strip() else 0
        except ProcessError:
            user_threads = -1

        bash = which('bash')
        try:
            result = bash("-c", "ulimit -u", output=str)
            process_limit = int(result.strip())
        except (ProcessError, ValueError):
            process_limit = -1

        return {
            'user': current_user,
            'thread_count': user_threads,
            'process_limit': process_limit,
            'utilization_pct': round((user_threads / process_limit * 100), 2) if process_limit > 0 else -1
        }

    except (OSError, ProcessError) as e:
        logger.warning(f"Error getting user thread count: {e}")
        return {
            'user': 'unknown',
            'thread_count': -1,
            'process_limit': -1,
            'utilization_pct': -1
        }


def log_thread_count(stage="", enabled=False):
    """
    Log the current user thread count with optional stage identifier.

    Parameters
    ----------
    stage : str
        Optional stage identifier (e.g., "START", "END")
    enabled : bool
        Whether thread logging is enabled (default: False)
    """
    if not enabled:
        return

    thread_info = get_user_thread_count()
    stage_prefix = f"[{stage}] " if stage else ""

    logger.info(f"{stage_prefix}USER_THREAD_COUNT: {thread_info['user']} has "
                f"{thread_info['thread_count']}/{thread_info['process_limit']} threads "
                f"({thread_info['utilization_pct']}% utilization)")


def attempt_multiple_times(expression, max_attempts, sleep_duration=0,
                           exception_class=Exception, use_telescoping_delay=True, thread_logging_enabled=False):
    """
    Retries a function multiple times with optional telescoping delays.

    Try to execute the function expression up to max_attempts times ignoring
    any exceptions of the type exception_class. It waits for sleep_duration
    seconds between attempts. If use_telescoping_delay is True, the sleep
    duration increases with each attempt.

    Parameters
    ----------
    expression : callable
        The function to be executed.
    max_attempts : int
        The maximum number of attempts to execute the function.
    sleep_duration : int, optional
        The base number of seconds to wait between attempts. Default is 0.
    exception_class : Exception, optional
        The type of exception to catch. Default is the base Exception class,
        catching all exceptions.
    use_telescoping_delay : bool, optional
        If True, use increasing delays between attempts. Default is True.
    thread_logging_enabled : bool, optional
        If True, enable thread count logging during retry attempts. Default is False.

    Returns
    -------
    The return value of the function expression.

    Raises
    ------
    exception_class
        If the function expression raises an exception of type exception_class
        in all max_attempts attempts.

    """

    attempt = 0
    last_exception = None
    total_start_time = time()

    while attempt < max_attempts:
        call_start_time = time()
        try:
            result = expression()
            call_end_time = time()

            # Log performance metrics
            call_duration = call_end_time - call_start_time
            total_duration = call_end_time - total_start_time

            # Log thread count after successful call
            log_thread_count(f"ROCOTO_SUCCESS_ATTEMPT_{attempt + 1}", thread_logging_enabled)

            logger.info(f"Rocoto call successful on attempt {attempt + 1}: "
                        f"call_time={call_duration:.2f}s, "
                        f"total_time={total_duration:.2f}s")

            return result

        except exception_class as e:
            last_exception = e
            attempt += 1
            call_end_time = time()
            call_duration = call_end_time - call_start_time

            # Log thread count after failed call
            log_thread_count(f"ROCOTO_FAILED_ATTEMPT_{attempt}", thread_logging_enabled)

            logger.warning(f"Rocoto call failed on attempt {attempt}: "
                           f"call_time={call_duration:.2f}s, "
                           f"error={str(last_exception)}")

            if attempt < max_attempts:
                if use_telescoping_delay:
                    current_delay = min(sleep_duration * (TELESCOPING_DELAY_MULTIPLIER ** (attempt - 1)), TELESCOPING_MAX_DELAY_SECONDS)
                else:
                    current_delay = sleep_duration

                if current_delay > 0:
                    logger.info(f"Waiting {current_delay}s before retry "
                                f"attempt {attempt + 1}")
                    sleep(current_delay)

    # Log final failure
    total_duration = time() - total_start_time
    logger.error(f"All {max_attempts} attempts failed after {total_duration:.2f}s total")
    raise last_exception


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

    parser.add_argument('-w', help='workflow_document', type=FileType('r'), required=True)
    parser.add_argument('-d', help='database_file', metavar='Database File', type=FileType('r'), required=True)
    parser.add_argument('--verbose', action='store_true', help='List the states and the number of jobs that are in each', required=False)
    parser.add_argument('-v', action='store_true', help='List the states and the number of jobs that are in each', required=False)
    parser.add_argument('--declare', action='store_true', help='create and declare list of the status values for bash', required=False)
    parser.add_argument('--thread-logging', action='store_true',
                        help='Enable thread count performance logging for monitoring system resource usage', required=False)

    args = parser.parse_args()

    return args


def run_rocoto(rocotorun, thread_logging_enabled=False):
    """
    Execute rocotostat with summary flag and analyze workflow cycle completion status.

    This function invokes the rocotorun command to run the Rocoto workflow,
    handling retries if the scheduler infrastructure is temporarily unavailable.

    Parameters
    ----------
    rocotorun : callable
    thread_logging_enabled : bool, optional
        Whether to enable thread count logging during rocotostat execution. Default is False.

    Returns
    -------
    None

    """

    attempt_multiple_times(lambda: rocotorun(),
                           ROCOTO_RUN_MAX_ATTEMPTS,
                           ROCOTO_RUN_SLEEP_DURATION,
                           ProcessError,
                           thread_logging_enabled=thread_logging_enabled)


def rocotostat_summary(rocotostat, thread_logging_enabled=False):
    """
    Execute rocotostat with summary flag and analyze workflow cycle completion status.

    This function invokes the rocotostat command with the '--summary' argument to retrieve high-level workflow information,
    then processes the output to extract cycle completion statistics. It parses the summary output to determine the total
    number of workflow cycles and counts how many cycles have reached the 'Done' state, providing essential metrics for
    workflow progress monitoring and completion assessment.

    Parameters
    ----------
    rocotostat : callable
        The rocotostat command object configured with workflow and database file paths for execution.
    thread_logging_enabled : bool, optional
        Whether to enable thread count logging during rocotostat execution. Default is False.

    Returns
    -------
    rocoto_status : dict
        Dictionary containing 'CYCLES_TOTAL' (total cycles) and 'CYCLES_DONE' (completed cycles) for status tracking.
    """

    rocotostat_output_raw = attempt_multiple_times(lambda: rocotostat("--summary", output=str),
                                                   ROCOTO_SUMMARY_MAX_ATTEMPTS,
                                                   ROCOTO_SUMMARY_SLEEP_DURATION,
                                                   ProcessError,
                                                   thread_logging_enabled=thread_logging_enabled)
    rocotostat_output_raw = rocotostat_output_raw.splitlines()[1:]

    rocotostat_output = []
    for line in rocotostat_output_raw:
        cycle = line[0:12].strip()
        state = line[16:24].strip()
        activated_str = line[28:48].strip()
        deactivated_str = line[52:72].strip()

        activated = None
        if activated_str and activated_str != '-':
            try:
                activated = datetime.strptime(activated_str, "%b %d %Y %H:%M:%S")
            except ValueError:
                activated = None

        deactivated = None
        if deactivated_str and deactivated_str != '-':
            try:
                deactivated = datetime.strptime(deactivated_str, "%b %d %Y %H:%M:%S")
            except ValueError:
                deactivated = None

        rocotostat_output.append({
            'cycle': cycle,
            'state': state,
            'activated': activated,
            'deactivated': deactivated
        })

    if _log_level == "DEBUG":
        logger.debug(rocotostat_output)

    duration = (
        max(entry['deactivated'] for entry in rocotostat_output) - min(entry['activated'] for entry in rocotostat_output)
        if (
            rocotostat_output and
            all(entry['activated'] for entry in rocotostat_output) and
            all(entry['deactivated'] for entry in rocotostat_output)
        )
        else None
    )

    rocoto_status = {
        'CYCLES_TOTAL': len(rocotostat_output),
        'CYCLES_DONE': sum(1 for entry in rocotostat_output if entry['state'] == 'Done'),
        'DURATION': duration
    }
    return rocoto_status


def rocoto_statcount(rocotostat, thread_logging_enabled=False):
    """
    Execute rocotostat with all jobs flag and analyze detailed job status distribution across workflow cycles.

    This function runs the rocotostat command with the '--all' argument to retrieve comprehensive job status information
    for all workflow cycles and tasks. It processes the detailed output to count jobs in each status category including
    SUCCEEDED, FAIL, DEAD, RUNNING, SUBMITTING, QUEUED, UNAVAILABLE, and UNKNOWN states, providing granular insight into
    workflow execution progress and identifying potential issues or bottlenecks in the job execution pipeline.

    Parameters
    ----------
    rocotostat : callable
        The rocotostat command object configured with workflow and database file paths for comprehensive job analysis.
    thread_logging_enabled : bool, optional
        Whether to enable thread count logging during rocotostat execution. Default is False.

    Returns
    -------
    rocoto_status : dict
        Dictionary containing counts for each job status category (SUCCEEDED, FAIL, DEAD, RUNNING, etc.) for monitoring.
    """

    rocotostat_output = attempt_multiple_times(lambda: rocotostat('--all', output=str),
                                               ROCOTO_STATCOUNT_MAX_ATTEMPTS,
                                               ROCOTO_STATCOUNT_SLEEP_DURATION,
                                               ProcessError,
                                               thread_logging_enabled=thread_logging_enabled)
    rocotostat_output = rocotostat_output.splitlines()[1:]
    rocotostat_output = [line.split()[0:4] for line in rocotostat_output if "======" not in line]
    rocotostat_output = [line for line in rocotostat_output if len(line) != 1]

    status_cases = ['SUCCEEDED', 'FAIL', 'DEAD', 'RUNNING', 'SUBMITTING', 'QUEUED', 'UNAVAILABLE', 'UNKNOWN']

    rocoto_status = {}
    status_counts = Counter(case for sublist in rocotostat_output for case in sublist)
    for case in status_cases:
        rocoto_status[case] = status_counts[case]
    rocoto_status['JOBS_TOTAL'] = len(rocotostat_output)
    rocoto_status['JOBS_DONE'] = status_counts['SUCCEEDED']

    return rocoto_status


def rocoto_status(rocotostat, thread_logging_enabled=False):
    """
    Execute rocotostat to retrieve both summary and detailed job status information, combining results into a single status dictionary.
    """
    rocoto_status = rocoto_statcount(rocotostat, thread_logging_enabled=thread_logging_enabled)
    rocoto_status.update(rocotostat_summary(rocotostat, thread_logging_enabled=thread_logging_enabled))

    if is_done(rocoto_status):
        rocoto_state = 'DONE'
    elif rocoto_status['DEAD'] > 0:
        rocoto_state = 'FAIL'
    elif rocoto_status['UNAVAILABLE'] > 0 or rocoto_status['UNKNOWN'] > 0:
        rocoto_status = attempt_multiple_times(lambda: rocoto_statcount(rocotostat, thread_logging_enabled=thread_logging_enabled),
                                               ROCOTO_RETRY_MAX_ATTEMPTS,
                                               ROCOTO_RETRY_SLEEP_DURATION,
                                               ProcessError,
                                               thread_logging_enabled=thread_logging_enabled)
        rocoto_state = 'RUNNING'
        if rocoto_status['UNAVAILABLE'] > 0:
            rocoto_state = 'UNAVAILABLE'
        if rocoto_status['UNKNOWN'] > 0:
            rocoto_state = 'UNKNOWN'
    elif is_stalled(rocoto_status):
        rocoto_status = attempt_multiple_times(lambda: rocoto_statcount(rocotostat, thread_logging_enabled=thread_logging_enabled),
                                               ROCOTO_RETRY_MAX_ATTEMPTS,
                                               ROCOTO_RETRY_SLEEP_DURATION,
                                               ProcessError,
                                               thread_logging_enabled=thread_logging_enabled)
        if is_stalled(rocoto_status):
            rocoto_state = 'STALLED'
    else:
        rocoto_state = 'RUNNING'

    rocoto_status['ROCOTO_STATE'] = rocoto_state

    return rocoto_status


def is_done(rocoto_status):
    """
    is_done Check if all cycles are done.

    is_done(rocoto_status) checks if the total number of cycles equals the number of
    done cycles in the rocoto_status dictionary.

    Input:
    rocoto_status - A dictionary with the count of each status case.

    Output:
    boolean - True if all cycles are done, False otherwise.
    """

    if rocoto_status['CYCLES_TOTAL'] == rocoto_status['CYCLES_DONE']:
        return True
    else:
        return False


def is_stalled(rocoto_status):
    """
    is_stalled Check if all cycles are stalled.

    is_stalled(rocoto_status) checks if all cycles are stalled by verifying if
    there are no jobs that are RUNNING, SUBMITTING, or QUEUED.

    Input:
    rocoto_status - A dictionary with the count of each status case.

    Output:
    boolean - True if all cycles are stalled, False otherwise.
    """

    if rocoto_status['RUNNING'] + rocoto_status['SUBMITTING'] + rocoto_status['QUEUED'] == 0:
        return True
    else:
        return False


if __name__ == '__main__':
    """
    main Execute the script.

    main() parses the input arguments, checks if the rocotostat command is available,
    adds default arguments to the rocotostat command, and runs it and reports
    out to stdout spcific information of rocoto workflow.
    """

    args = input_args()

    # Log thread count at start
    log_thread_count("START", args.thread_logging)

    try:
        rocotostat = which("rocotostat")
    except CommandNotFoundError:
        logger.exception("rocotostat not found in PATH")
        log_thread_count("ERROR_EXIT", args.thread_logging)
        raise CommandNotFoundError("rocotostat not found in PATH")

    # Add the persistent default arguments
    rocotostat.add_default_arg(['-w', os.path.abspath(args.w.name), '-d', os.path.abspath(args.d.name)])

    # --- PATCH: Pass thread_logging_enabled from args.thread_logging ---
    rocoto_status = rocoto_status(rocotostat, thread_logging_enabled=args.thread_logging)

    if args.verbose or args.v:
        for status in rocoto_status:
            if args.v:
                print(f'{status}:{rocoto_status[status]}')
            else:
                print(f'Number of {status} : {rocoto_status[status]}')

    if args.declare:
        for status in rocoto_status:
            print(f'declare {status}={rocoto_status[status]}')
    else:
        print(rocoto_status['ROCOTO_STATE'])

    # Log thread count at end
    log_thread_count("END", args.thread_logging)
    sys.exit(EXIT_CODE[rocoto_status['ROCOTO_STATE']])
