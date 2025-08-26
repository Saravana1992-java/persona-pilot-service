from typing import Optional

from src.config.singleton import SingletonMeta

capacity = 30


class AsyncJobHandler(metaclass=SingletonMeta):
    """
    Handles asynchronous job operations, maintaining a history of jobs with a fixed capacity.

    This class is designed to manage job operations asynchronously, including registration, updating, retrieval,
    and removal of jobs. It maintains a history of jobs up to a specified capacity, automatically removing the oldest
    job when the capacity is exceeded.

    Attributes:
        bean_id (str): An identifier for the instance of this class, typically used for logging or debugging purposes.
        job (Optional[dict]): The current job being processed (if any).
        job_history (dict): A dictionary maintaining a history of jobs. Each job is stored with its job ID as the key.

    Methods:
        register(job_id: int, name: str, status: str, data: Optional[dict] = None): Registers a new job or replaces
        the oldest job if the history is at capacity.
        get(job_id: int): Retrieves a job from the job history based on its job ID.
        update(job_id: int, status: str, data: dict): Updates the status and data of an existing job in the job history.
        cleanup(): Clears the job history.
        remove(job_id: int): Removes a specific job from the job history. If no job ID is provided, it calls the
        cleanup method to clear the job history.
    """

    def __init__(self, bean_id):
        self.bean_id = bean_id
        self.job = None
        self.job_history = {}

    async def register(self, job_id: int, name: str, status: str, data: Optional[dict] = None):
        size = len(self.job_history)
        if size >= capacity:
            # Get the keys of the dictionary and convert them to integers
            timestamps = list(map(int, self.job_history.keys()))
            # Find the minimum timestamp (i.e., the oldest record)
            oldest_timestamp = min(timestamps)
            # Delete the oldest record
            del self.job_history[oldest_timestamp]
            # If it exists, update the value
        self.job_history[job_id] = {"job_id": job_id, "name": name, "status": status, "data": data}

    async def get(self, job_id: int) -> dict:
        if job_id in self.job_history:
            return self.job_history[job_id]
        else:
            return {}

    async def update(self, job_id: int, status: str, data: dict):
        if job_id is not None and job_id in self.job_history:
            self.job_history[job_id]["status"] = status
            self.job_history[job_id]["data"] = data

    async def cleanup(self):
        self.job_history.clear()

    async def remove(self, job_id: int):
        if job_id:
            if job_id in self.job_history:
                del self.job_history[job_id]
        else:
            await self.cleanup()
