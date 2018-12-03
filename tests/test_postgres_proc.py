import socket


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
    assert can_connect_to_tcp_port('localhost', proc.port) == is_running


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

