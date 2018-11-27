from queue import Queue
from threading import Thread
import logging


class Worker(Thread):
    def __init__(self, queue, result_queue):
        super(Worker, self).__init__()
        self._q = queue
        self.result_queue = result_queue
        self.daemon = True
        self.start()

    def run(self):
        while True:
            f, args, kwargs = self._q.get()
            result = f(*args, **kwargs)
            if result:
                self.result_queue.put(result)
            self._q.task_done()


class ThreadPool(object):
    def __init__(self, num_t):
        self._q = Queue(num_t)
        self.results_q = Queue()
        # Create Worker Thread
        for _ in range(num_t):
            Worker(self._q, self.results_q)

    def add_task(self, f, *args, **kwargs):
        self._q.put((f, args, kwargs))

    def wait_complete(self):
        _result = []
        self._q.join()
        while not self.results_q.empty():
            _result.append(self.results_q.get())
        return _result
