# actionQueue class
import logging
import queue
import threading
from time import sleep

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(threadName)s - %(message)s"
)


class ActionQueue:
    def __init__(self):
        self.action_queue = queue.Queue()

        self.worker_thread = threading.Thread(
            target=self._worker, name="ActionQueueWorker"
        )
        self.worker_thread.daemon = (
            True  # Allows main program to exit even if queue is not empty
        )
        self.worker_thread.start()

    def add(self, action):
        self.action_queue.put(action)
        logging.info(
            f"Action '{action.__name__}' added to the queue. Current queue size: {self.action_queue.qsize()}"
        )

    def get_queue_size(self):
        """
        Returns the current size of the action queue.
        """
        return self.action_queue.qsize()

    def _worker(self):
        logging.info("Worker thread started.")

        # 4. An infinite loop to continuously check the queue
        while True:
            # The get() method blocks until an item is available
            action = self.action_queue.get()

            try:
                # 6. Robust error handling for each action
                logging.info(f"Executing action '{action.__name__}'.")
                action()
            except Exception as e:
                logging.error(
                    f"Error executing action '{action.__name__}': {e}", exc_info=True
                )
            finally:
                # Signal that the task from the queue is done
                self.action_queue.task_done()
