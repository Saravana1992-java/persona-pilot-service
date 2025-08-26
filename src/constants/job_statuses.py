from enum import Enum


class JobStatus(Enum):
    """
    Enum for representing the status of a job.

    This enumeration defines the possible states of a job within the system, allowing for clear and consistent
    tracking of job progress and outcomes.

    Attributes:
        IN_PROGRESS (Enum): Indicates that the job is currently being processed.
        COMPLETED (Enum): Indicates that the job has finished processing successfully.
        FAILED (Enum): Indicates that the job has encountered an error during processing and did not complete
        successfully.
    """
    IN_PROGRESS = 1
    COMPLETED = 2
    FAILED = 3
