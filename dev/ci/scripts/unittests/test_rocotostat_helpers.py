#!/usr/bin/env python3

import os
import sys
import types
from unittest.mock import Mock

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
UTILS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'utils'))
sys.path.insert(0, UTILS_DIR)

try:
    import rocotostat
except ModuleNotFoundError as exc:
    if exc.name != 'wxflow':
        raise

    class _DummyLogger:
        def __init__(self, *args, **kwargs):
            pass

        def info(self, *args, **kwargs):
            pass

        def warning(self, *args, **kwargs):
            pass

        def error(self, *args, **kwargs):
            pass

        def exception(self, *args, **kwargs):
            pass

        def debug(self, *args, **kwargs):
            pass

    _wxflow = types.ModuleType('wxflow')
    _wxflow.which = lambda *args, **kwargs: None
    _wxflow.Logger = _DummyLogger
    _wxflow.CommandNotFoundError = Exception
    _wxflow.ProcessError = Exception
    sys.modules['wxflow'] = _wxflow
    import rocotostat


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
