from queue import Queue
import threading
from concurrent.futures import ThreadPoolExecutor

class DocumentQueue:
    def __init__(self, max_local_workers=2):
        self.queue = Queue()
        self.results = {}
        self.local_pool = ThreadPoolExecutor(max_workers=max_local_workers)
        self.colab_semaphore = threading.Semaphore(1)
        
    def add_document(self, doc_path: str, priority: int = 5):
        self.queue.put((priority, doc_path))
        
    def process_all(self, router_func):
        """
        Processes queue items using the provided routing function.
        """
        futures = []
        while not self.queue.empty():
            _, path = self.queue.get()
            futures.append(self.local_pool.submit(router_func, path))
            
        for f in futures:
            yield f.result()
