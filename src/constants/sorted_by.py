from enum import Enum


class SortedBy(Enum):
    """
    Enum for representing the sort options.

    This enumeration defines the possible sort options.

    Attributes:
        lastUpdatedAsc (Enum): Indicates that the result set will be sorted by lastUpdatedTime in descending order.
        lastUpdatedDesc (Enum): Indicates that the result set will be sorted by lastUpdatedTime in ascending order.
        relevance (Enum): Indicates that the result set will be sorted by relevancy ranking in descending order.
        mostAccessed (Enum): Indicates that the result set will be sorted by views in descending order.
    """
    lastUpdatedAsc = 1
    lastUpdatedDesc = 2
    relevance = 3
    mostAccessed = 4
