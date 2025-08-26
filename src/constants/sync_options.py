from enum import Enum


class SyncOptions(Enum):
    """
    Enum for representing the status of a job.

    This enumeration defines the possible synchronization options.

    Attributes:
        insert (Enum): Indicates that the job is currently being processed.
        upsert (Enum): Indicates that the job has finished processing successfully.
        bulk_insert (Enum): Indicates that the job has encountered an error during processing and did not complete
        successfully.
    """
    insert = 1
    upsert = 2
    bulk_insert = 3