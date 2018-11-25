from queue import Queue
from threading import Thread


class ThreadPool:
    def __init__(self, number_of_workers, signal):
        self.tasks_queue = Queue(number_of_workers)
        self.result_queue = Queue()
        for _ in range(number_of_workers):
            ThreadWorker(self.tasks_queue, self.result_queue, signal)

    def add_task(self, func, *args, **kwargs):
        self.tasks_queue.put((func, args, kwargs))

    def wait_completion(self):
        self.tasks_queue.join()
        _result = []
        while not self.result_queue.empty():
            _result.append(self.result_queue.get())
        return _result


class ThreadWorker(Thread):
    def __init__(self, tasks_queue, result_queue, signal):
        Thread.__init__(self)
        self.tasks_queue = tasks_queue
        self.result_queue = result_queue
        self.signal = signal
        self.daemon = True
        self.start()

    def run(self):
        while True:
            func, args, kwargs = self.tasks_queue.get()
            try:
                r = func(*args, **kwargs)
                self.result_queue.put(r)
            except Exception as e:
                self.result_queue.put(e)
            finally:
                self.signal.updateProgress.emit()
                self.tasks_queue.task_done()
