import time
from multiprocessing import Process

from golem.core.processmonitor import ProcessMonitor
from golem.tools.assertlogs import LogTestCase


class MockProcess(object):
    def __init__(self, timeout=10, raise_exc=True):
        self.timeout = timeout
        self.working = True
        self.raise_exc = raise_exc

    def run(self):
        started = time.time()

        while self.working:
            time.sleep(1)
            if time.time() - started >= self.timeout:
                if self.raise_exc:
                    raise Exception("Mock process running for over {}s".format(
                        self.timeout))
                else:
                    self.working = False


def wait_for_processes(timeout=10, *processes):
    started = time.time()
    timeout = max(timeout, 5)

    while time.time() - started < timeout:

        all_stopped = True
        for process in processes:
            if ProcessMonitor.is_process_alive(process):
                all_stopped = False
                break

        if all_stopped:
            return
        time.sleep(0.5)


def run_exit():
    return


class TestProcessMonitor(LogTestCase):

    def test_monitor(self):

        mp = MockProcess()
        p1 = Process(target=run_exit)
        p2 = Process(target=mp.run)

        p1.start()
        p2.start()

        pm = ProcessMonitor(p1, p2)
        pm.start()

        wait_for_processes(10, p1, p2)

        self.assertFalse(pm.is_process_alive(p1))
        self.assertFalse(pm.is_process_alive(p2))

    def test_monitor_2(self):
        mp1, mp2 = MockProcess(), MockProcess(timeout=0)

        p1 = Process(target=mp1.run)
        p2 = Process(target=mp2.run)

        p1.start()
        p2.start()

        pm = ProcessMonitor(p1, p2)
        pm.start()

        wait_for_processes(10, p1, p2)

        if pm.is_process_alive(p1) or pm.is_process_alive(p2):
            pm.exit()
            self.fail("Processes not killed after timeout")

    def test_exit(self):
        import logging
        logger = logging.getLogger("golem.core")
        mp1, mp2 = MockProcess(), MockProcess()
        p1 = Process(target=mp1.run)
        p2 = Process(target=mp2.run)

        p1.start()
        p2.start()

        pm = ProcessMonitor(p1, p2)

        def callback():
            logger.warning("Shutting down...")

        pm.add_shutdown_callback(callback=callback)

        pm.start()
        with self.assertLogs(logger, level="WARNING"):
            pm.exit()

        wait_for_processes(10, p1, p2)

        self.assertFalse(pm.is_process_alive(p1))
        self.assertFalse(pm.is_process_alive(p2))
