from enum import Enum


class SummaryReactions(Enum):
    """
        Enum class for different user reactions allowed for AI summary

        This class defines 3 types of reactions: Like, Dislike & Reload.
        Each reaction is associated with an integer value.

        Attributes:
        like (int): Liked AI Summary.
        dislike (int): Disliked AI summary,
        reload (int): Reload AI summary,
        """
    like = 1
    dislike = 2
    reload = 3
