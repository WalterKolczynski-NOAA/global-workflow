#!/usr/bin/env python3

import os
import sys
import types
from datetime import timedelta

import pytest


# Add script directory to the python path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
sys.path.insert(0, SCRIPTS_DIR)

import monitor_ci  # noqa E402
import utils.rocotostat as rs  # noqa E402


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


_wxflow = types.ModuleType('wxflow')
_wxflow.which = lambda *args, **kwargs: None
_wxflow.Logger = _DummyLogger
_wxflow.CommandNotFoundError = Exception
_wxflow.ProcessError = Exception
sys.modules.setdefault('wxflow', _wxflow)


def _status(state, cycles_done=0, cycles_total=1, running=0, queued=0, duration=None):
    return {
        'ROCOTO_STATE': state,
        'CYCLES_DONE': cycles_done,
        'CYCLES_TOTAL': cycles_total,
        'RUNNING': running,
        'QUEUED': queued,
        'DURATION': duration,
    }


def test_input_args_parses_expdir_and_verbose(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['monitor_ci.py', '/tmp/expdir', '--verbose'])

    args = monitor_ci.input_args()

    assert args.expdir == '/tmp/expdir'
    assert args.verbose is True


def test_print_status_empty_output(capsys):
    monitor_ci.print_status({})

    captured = capsys.readouterr()
    assert 'No experiment status available.' in captured.out


def test_print_status_table_output(capsys):
    rocoto_status = {
        'exp_done': _status('DONE', cycles_done=2, cycles_total=2, running=0, queued=0, duration=timedelta(minutes=5)),
        'exp_running': _status('RUNNING', cycles_done=1, cycles_total=2, running=3, queued=1, duration=None),
    }

    monitor_ci.print_status(rocoto_status)

    captured = capsys.readouterr()
    assert 'Status at' in captured.out
    assert 'Experiment' in captured.out
    assert 'exp_done' in captured.out
    assert 'exp_running' in captured.out
    assert '2/2' in captured.out
    assert '1/2' in captured.out
    assert 'N/A' in captured.out


def test_check_end_states_exits_done():
    rocoto_status = {
        'exp1': _status('DONE', cycles_done=1, cycles_total=1),
        'exp2': _status('DONE', cycles_done=2, cycles_total=2),
    }

    with pytest.raises(SystemExit) as excinfo:
        monitor_ci.check_end_states(rocoto_status, consecutive_unavailable_count=0)

    assert excinfo.value.code == rs.EXIT_CODE['DONE']


@pytest.mark.parametrize('state', ['FAIL', 'STALLED'])
def test_check_end_states_exits_for_error_states(state):
    rocoto_status = {
        'exp1': _status('RUNNING', cycles_done=0, cycles_total=1, running=1),
        'exp2': _status(state, cycles_done=0, cycles_total=1),
    }

    with pytest.raises(SystemExit) as excinfo:
        monitor_ci.check_end_states(rocoto_status, consecutive_unavailable_count=0)

    assert excinfo.value.code == rs.EXIT_CODE[state]


def test_check_end_states_increments_unavailable_count_without_exit():
    rocoto_status = {
        'exp1': _status('UNAVAILABLE', cycles_done=0, cycles_total=1),
    }
    start_count = monitor_ci.MAX_CONSECUTIVE_UNAVAILABLE - 2

    result = monitor_ci.check_end_states(rocoto_status, consecutive_unavailable_count=start_count)

    assert result == start_count + 1


def test_check_end_states_exits_when_unavailable_limit_reached():
    rocoto_status = {
        'exp1': _status('UNKNOWN', cycles_done=0, cycles_total=1),
    }
    start_count = monitor_ci.MAX_CONSECUTIVE_UNAVAILABLE - 1

    with pytest.raises(SystemExit) as excinfo:
        monitor_ci.check_end_states(rocoto_status, consecutive_unavailable_count=start_count)

    assert excinfo.value.code == rs.EXIT_CODE['UNAVAILABLE']


def test_check_end_states_resets_unavailable_count():
    rocoto_status = {
        'exp1': _status('RUNNING', cycles_done=0, cycles_total=1, running=1),
    }

    result = monitor_ci.check_end_states(rocoto_status, consecutive_unavailable_count=2)

    assert result == 0
