import signal
import multiprocessing as mp
from loguru import logger
from queue import Empty
from typing import Any, Callable, Dict

class Worker(mp.Process):
    def __init__(self, id: str, processor: "Processor"):
        super().__init__()
        self.id = id
        self.task_queue = processor.queue
        self.processor = processor

    def run(self):
        self.started = True
        logger.debug(f"Worker {self.id} started")

        def signal_handler(sig, frame):
            logger.warning(f"Worker {self.id} received signal {signal.strsignal(sig)}")
            self.task_queue.put(None)

        signal.signal(signal.SIGINT, signal_handler)

        while True:
            try:
                next_task = self.task_queue.get(timeout=1)
            except Empty:
                continue
            if next_task is None:
                logger.warning(f"Worker {self.id}/{len(self.processor.workers)} stopped")
                # self.task_queue.task_done()
                break
            workname, data = next_task
            self._dispatch(workname, data)
            # self.task_queue.task_done()
        return

    def _dispatch(self, workname: str, data: Any):
        if workname in self.processor.handlers:
            try:
                self.processor.handlers[workname](data)
            except Exception as e:
                logger.error(f"{workname}: {e}")
        else:
            logger.error(f"No handler function for task `{workname}`")

class Processor:
    handlers: Dict[str, Callable[[dict], None]]
    def __init__(self, num_workers: int = 4):
        self.queue = mp.Queue()
        self.workers: list["Worker"] = []
        self.handlers = {}

        for i in range(num_workers):
            w = Worker(i+1, self)
            w.daemon = True
            self.workers.append(w)

    def add_work(self, workname: str, data: Any = None):
        self.queue.put((workname, data))

    def handler(self, workname: str):
        def decorator(func):
            self.handlers[workname] = func
            return func
        return decorator

    def register_handlers(self, handlers: Dict[str, Callable[[dict], None]]):
        self.handlers.update(handlers)

    def run(self):
        for w in self.workers:
            w.start()
        for w in self.workers:
            try:
                w.join()
            except KeyboardInterrupt:
                logger.warning("Stopping workers, tasks remaining in queue: ", self.queue.qsize() or 'N/A')
                
