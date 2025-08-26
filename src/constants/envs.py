from enum import Enum


class Env(Enum):
    """
        This class defines four types of GCP environments: LOCAL, DEV, QA, and PROD.
        Each environment type is associated with an integer value.

        Attributes:
        LOCAL (int): Represents the local environment.
        DEV (int): Represents the development environment.
        QA (int): Represents the quality assurance environment.
        PROD (int): Represents the production environment.
        """
    LOCAL = 1
    DEV = 2
    QA = 3
    PROD = 4
