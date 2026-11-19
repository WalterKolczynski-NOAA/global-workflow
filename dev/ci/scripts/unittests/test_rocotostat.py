#!/usr/bin/env python3

import time
import sys
import os
from shutil import rmtree
import wget
from unittest.mock import Mock

# Add the utils directory to the path to import rocotostat
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'utils'))
script_dir = os.path.dirname(os.path.abspath(__file__))

from rocotostat import rocoto_statcount, rocotostat_summary, is_done, is_stalled
from rocotostat import attempt_multiple_times, logger
import rocotostat

from wxflow import which, CommandNotFoundError

test_data_url = 'https://noaa-nws-global-pds.s3.amazonaws.com/data/CI/'

testdata_path = 'testdata/rocotostat'
testdata_full_path = os.path.join(script_dir, testdata_path)


if not os.path.isfile(os.path.join(testdata_full_path, 'database.db')):
    os.makedirs(testdata_full_path, exist_ok=True)
    workflow_url = test_data_url + str(testdata_path) + '/workflow.xml'
    workflow_destination = os.path.join(testdata_full_path, 'workflow.xml')
    wget.download(workflow_url, workflow_destination)

    database_url = test_data_url + str(testdata_path) + '/database.db'
    database_destination = os.path.join(testdata_full_path, 'database.db')
    wget.download(database_url, database_destination)

rocotostat_cmd = which('rocotostat')
if not rocotostat_cmd:
    raise CommandNotFoundError("rocotostat not found in PATH")

rocotostat_cmd.add_default_arg(['-w', os.path.join(testdata_path, 'workflow.xml'), '-d', os.path.join(testdata_path, 'database.db')])


def test_rocoto_statcount():

    result = rocoto_statcount(rocotostat_cmd)

    assert result['SUCCEEDED'] == 20
    assert result['FAIL'] == 0
    assert result['DEAD'] == 0
    assert result['RUNNING'] == 0
    assert result['SUBMITTING'] == 0
    assert result['QUEUED'] == 0


def test_rocoto_summary():

    result = rocotostat_summary(rocotostat_cmd)

    assert result['CYCLES_TOTAL'] == 1
    assert result['CYCLES_DONE'] == 1


def test_rocoto_done():

    result = rocotostat_summary(rocotostat_cmd)

    assert is_done(result)

    rmtree(testdata_full_path)


def test_rocoto_stalled():
    testdata_path = 'testdata/rocotostat_stalled'
    testdata_full_path = os.path.join(script_dir, testdata_path)
    xml = os.path.join(testdata_full_path, 'stalled.xml')
    db = os.path.join(testdata_full_path, 'stalled.db')

    if not os.path.isfile(os.path.join(testdata_full_path, 'stalled.db')):
        os.makedirs(testdata_full_path, exist_ok=True)
        workflow_url = test_data_url + str(testdata_path) + '/stalled.xml'
        database_url = test_data_url + str(testdata_path) + '/stalled.db'

        workflow_destination = os.path.join(testdata_full_path, 'stalled.xml')
        wget.download(workflow_url, workflow_destination)

        database_destination = os.path.join(testdata_full_path, 'stalled.db')
        wget.download(database_url, database_destination)

    rocotostat_cmd = which('rocotostat')
    rocotostat_cmd.add_default_arg(['-w', xml, '-d', db])

    result = rocoto_statcount(rocotostat_cmd)

    assert result['SUCCEEDED'] == 11
    assert is_stalled(result)

    rmtree(testdata_full_path)


def test_attempt_multiple_times_success_first_try(mocker):

    """Test that attempt_multiple_times succeeds on first try"""
    mock_func = mocker.Mock(return_value="success")

    result = attempt_multiple_times(mock_func, max_attempts=3, sleep_duration=0.1)

    assert result == "success"
    mock_func.assert_called_once()


def test_attempt_multiple_times_success_after_retries(mocker):
    """Test that attempt_multiple_times succeeds after some failures"""
    mock_func = mocker.Mock(side_effect=[Exception("fail"), Exception("fail"), "success"])

    result = attempt_multiple_times(mock_func, max_attempts=3, sleep_duration=0.1)

    assert result == "success"
    assert mock_func.call_count == 3


def test_attempt_multiple_times_max_attempts_exceeded(mocker):
    """Test that attempt_multiple_times fails after max attempts"""
    mock_func = mocker.Mock(side_effect=Exception("always fail"))

    try:
        attempt_multiple_times(mock_func, max_attempts=2, sleep_duration=0.1)
        assert False, "Expected Exception to be raised"
    except Exception as e:
        assert str(e) == "always fail"

    assert mock_func.call_count == 2


def test_attempt_multiple_times_delay(mocker):
    """Test that attempt_multiple_times respects delay between attempts"""
    mock_func = mocker.Mock(side_effect=[Exception("fail"), "success"])

    start_time = time.time()
    result = attempt_multiple_times(mock_func, max_attempts=3, sleep_duration=0.2)
    end_time = time.time()

    assert result == "success"
    assert mock_func.call_count == 2
    # Should take at least 0.2 seconds due to the delay
    assert end_time - start_time >= 0.2  # Allow some tolerance


def test_attempt_multiple_times_logging(mocker):
    """Test that attempt_multiple_times logs retry attempts"""
    mock_logger = mocker.patch('rocotostat.logger')
    mock_func = mocker.Mock(side_effect=[Exception("fail"), "success"])

    result = attempt_multiple_times(mock_func, max_attempts=3, sleep_duration=0.1)

    assert result == "success"
    assert mock_func.call_count == 2
    # Should have logged the retry attempt with warning for failure and info for success
    mock_logger.warning.assert_called()
    mock_logger.info.assert_called()


def test_get_user_thread_count_success(monkeypatch):
    monkeypatch.setenv('USER', 'tester')

    def fake_ps(*args, **kwargs):
        return "PID\n111\n222\n"

    def fake_bash(*args, **kwargs):
        return "100\n"

    def fake_which(command):
        if command == 'ps':
            return fake_ps
        if command == 'bash':
            return fake_bash
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(rocotostat, 'which', fake_which)

    result = rocotostat.get_user_thread_count()

    assert result['user'] == 'tester'
    assert result['thread_count'] == 2
    assert result['process_limit'] == 100
    assert result['utilization_pct'] == 2.0


def test_get_user_thread_count_handles_process_errors(monkeypatch):
    fake_process_error = type('FakeProcessError', (Exception,), {})
    monkeypatch.setattr(rocotostat, 'ProcessError', fake_process_error)

    def fake_ps(*args, **kwargs):
        raise fake_process_error('ps failed')

    def fake_bash(*args, **kwargs):
        return "not-an-integer\n"

    def fake_which(command):
        return fake_ps if command == 'ps' else fake_bash

    monkeypatch.setattr(rocotostat, 'which', fake_which)

    result = rocotostat.get_user_thread_count()

    assert result['thread_count'] == -1
    assert result['process_limit'] == -1
    assert result['utilization_pct'] == -1


def test_get_user_thread_count_outer_exception_path(monkeypatch):
    logger_warning = Mock()
    monkeypatch.setattr(rocotostat.logger, 'warning', logger_warning)

    def fake_which(_command):
        raise OSError('system error')

    monkeypatch.setattr(rocotostat, 'which', fake_which)

    result = rocotostat.get_user_thread_count()

    assert result == {
        'user': 'unknown',
        'thread_count': -1,
        'process_limit': -1,
        'utilization_pct': -1,
    }
    logger_warning.assert_called_once()


def test_log_thread_count_disabled(monkeypatch):
    get_user_thread_count_mock = Mock()
    logger_info_mock = Mock()
    monkeypatch.setattr(rocotostat, 'get_user_thread_count', get_user_thread_count_mock)
    monkeypatch.setattr(rocotostat.logger, 'info', logger_info_mock)

    rocotostat.log_thread_count(stage='START', enabled=False)

    get_user_thread_count_mock.assert_not_called()
    logger_info_mock.assert_not_called()


def test_log_thread_count_enabled(monkeypatch):
    monkeypatch.setattr(rocotostat, 'get_user_thread_count', lambda: {
        'user': 'tester',
        'thread_count': 3,
        'process_limit': 200,
        'utilization_pct': 1.5,
    })
    logger_info_mock = Mock()
    monkeypatch.setattr(rocotostat.logger, 'info', logger_info_mock)

    rocotostat.log_thread_count(stage='START', enabled=True)

    logger_info_mock.assert_called_once()
    assert '[START] USER_THREAD_COUNT: tester has 3/200 threads (1.5% utilization)' in logger_info_mock.call_args[0][0]


def test_run_rocoto_uses_retry_wrapper(monkeypatch):
    attempt_mock = Mock()
    monkeypatch.setattr(rocotostat, 'attempt_multiple_times', attempt_mock)

    rocotostat.run_rocoto(lambda: None, thread_logging_enabled=True)

    assert attempt_mock.call_count == 1
    call_args = attempt_mock.call_args
    assert callable(call_args[0][0])
    assert call_args[0][1] == rocotostat.ROCOTO_RUN_MAX_ATTEMPTS
    assert call_args[0][2] == rocotostat.ROCOTO_RUN_SLEEP_DURATION
    assert call_args[0][3] == rocotostat.ProcessError
    assert call_args[1]['thread_logging_enabled'] is True


def test_rocoto_status_done_path(monkeypatch):
    monkeypatch.setattr(rocotostat, 'rocoto_statcount', lambda *_args, **_kwargs: {
        'SUCCEEDED': 1,
        'FAIL': 0,
        'DEAD': 0,
        'RUNNING': 0,
        'SUBMITTING': 0,
        'QUEUED': 0,
        'UNAVAILABLE': 0,
        'UNKNOWN': 0,
        'JOBS_TOTAL': 1,
        'JOBS_DONE': 1,
    })
    monkeypatch.setattr(rocotostat, 'rocotostat_summary', lambda *_args, **_kwargs: {
        'CYCLES_TOTAL': 1,
        'CYCLES_DONE': 1,
        'DURATION': None,
    })
    monkeypatch.setattr(rocotostat, 'is_done', lambda _status: True)
    attempt_mock = Mock()
    monkeypatch.setattr(rocotostat, 'attempt_multiple_times', attempt_mock)

    result = rocotostat.rocoto_status(rocotostat=None)

    assert result['ROCOTO_STATE'] == 'DONE'
    attempt_mock.assert_not_called()


def test_rocoto_status_dead_path(monkeypatch):
    monkeypatch.setattr(rocotostat, 'rocoto_statcount', lambda *_args, **_kwargs: {
        'SUCCEEDED': 0,
        'FAIL': 0,
        'DEAD': 1,
        'RUNNING': 0,
        'SUBMITTING': 0,
        'QUEUED': 0,
        'UNAVAILABLE': 0,
        'UNKNOWN': 0,
        'JOBS_TOTAL': 1,
        'JOBS_DONE': 0,
    })
    monkeypatch.setattr(rocotostat, 'rocotostat_summary', lambda *_args, **_kwargs: {
        'CYCLES_TOTAL': 2,
        'CYCLES_DONE': 1,
        'DURATION': None,
    })
    monkeypatch.setattr(rocotostat, 'is_done', lambda _status: False)

    result = rocotostat.rocoto_status(rocotostat=None)

    assert result['ROCOTO_STATE'] == 'FAIL'


def test_rocoto_status_unavailable_retry_path(monkeypatch):
    monkeypatch.setattr(rocotostat, 'rocoto_statcount', lambda *_args, **_kwargs: {
        'SUCCEEDED': 0,
        'FAIL': 0,
        'DEAD': 0,
        'RUNNING': 1,
        'SUBMITTING': 0,
        'QUEUED': 0,
        'UNAVAILABLE': 1,
        'UNKNOWN': 0,
        'JOBS_TOTAL': 1,
        'JOBS_DONE': 0,
    })
    monkeypatch.setattr(rocotostat, 'rocotostat_summary', lambda *_args, **_kwargs: {
        'CYCLES_TOTAL': 2,
        'CYCLES_DONE': 1,
        'DURATION': None,
    })
    monkeypatch.setattr(rocotostat, 'is_done', lambda _status: False)
    attempt_mock = Mock(return_value={
        'SUCCEEDED': 0,
        'FAIL': 0,
        'DEAD': 0,
        'RUNNING': 1,
        'SUBMITTING': 0,
        'QUEUED': 0,
        'UNAVAILABLE': 1,
        'UNKNOWN': 0,
        'JOBS_TOTAL': 1,
        'JOBS_DONE': 0,
    })
    monkeypatch.setattr(rocotostat, 'attempt_multiple_times', attempt_mock)

    result = rocotostat.rocoto_status(rocotostat=None, thread_logging_enabled=True)

    assert result['ROCOTO_STATE'] == 'UNAVAILABLE'
    assert attempt_mock.call_count == 1
    assert attempt_mock.call_args[0][1] == rocotostat.ROCOTO_RETRY_MAX_ATTEMPTS
    assert attempt_mock.call_args[0][2] == rocotostat.ROCOTO_RETRY_SLEEP_DURATION
    assert attempt_mock.call_args[1]['thread_logging_enabled'] is True


def test_rocoto_status_stalled_retry_path(monkeypatch):
    monkeypatch.setattr(rocotostat, 'rocoto_statcount', lambda *_args, **_kwargs: {
        'SUCCEEDED': 0,
        'FAIL': 0,
        'DEAD': 0,
        'RUNNING': 0,
        'SUBMITTING': 0,
        'QUEUED': 0,
        'UNAVAILABLE': 0,
        'UNKNOWN': 0,
        'JOBS_TOTAL': 1,
        'JOBS_DONE': 0,
    })
    monkeypatch.setattr(rocotostat, 'rocotostat_summary', lambda *_args, **_kwargs: {
        'CYCLES_TOTAL': 2,
        'CYCLES_DONE': 1,
        'DURATION': None,
    })
    monkeypatch.setattr(rocotostat, 'is_done', lambda _status: False)
    stalled_check = Mock(side_effect=[True, True])
    monkeypatch.setattr(rocotostat, 'is_stalled', stalled_check)
    monkeypatch.setattr(rocotostat, 'attempt_multiple_times', Mock(return_value={
        'SUCCEEDED': 0,
        'FAIL': 0,
        'DEAD': 0,
        'RUNNING': 0,
        'SUBMITTING': 0,
        'QUEUED': 0,
        'UNAVAILABLE': 0,
        'UNKNOWN': 0,
        'JOBS_TOTAL': 1,
        'JOBS_DONE': 0,
    }))

    result = rocotostat.rocoto_status(rocotostat=None)

    assert result['ROCOTO_STATE'] == 'STALLED'
