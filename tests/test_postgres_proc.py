"""
    Copyright 2016 Inmanta

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: code@inmanta.com
"""

import socket

import pytest

from inmanta import postgresproc


@pytest.fixture
def postgres_proc(unused_tcp_port_factory):
    proc = postgresproc.PostgresProc(unused_tcp_port_factory())
    yield proc
    proc.stop()


def test_basic_case(postgres_proc):
    assert_proc_state(postgres_proc, False)
    assert postgres_proc.start()
    assert_proc_state(postgres_proc, True)
    postgres_proc.stop()
    assert_proc_state(postgres_proc, False)


def test_start_already_started_process(postgres_proc):
    assert_proc_state(postgres_proc, False)
    assert postgres_proc.start()
    assert_proc_state(postgres_proc, True)
    assert postgres_proc.start()
    assert_proc_state(postgres_proc, True)


def test_stop_already_stopped_process(postgres_proc):
    assert_proc_state(postgres_proc, False)
    postgres_proc.stop()
    assert_proc_state(postgres_proc, False)
    assert postgres_proc.start()
    assert_proc_state(postgres_proc, True)
    postgres_proc.stop()
    assert_proc_state(postgres_proc, False)
    postgres_proc.stop()
    assert_proc_state(postgres_proc, False)


def assert_proc_state(proc, is_running):
    assert proc.running() == is_running
    assert can_connect_to_tcp_port("localhost", proc.port) == is_running


def can_connect_to_tcp_port(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
        return True
    except OSError:
        pass
    finally:
        s.close()
    return False
