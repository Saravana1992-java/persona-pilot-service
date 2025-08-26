from enum import Enum


class EsIndexPrefix(Enum):
    """
        Enum class for different Elastic search (ES) indices allowed

        This class defines 2 types of Elastic search indices: insights, ai_summary_cache.
        Each index prefix is associated with an integer value.

        Attributes:
        insights (int): Represents the insights (insights_dev, insights_qa & insights_prod).
        ai_summary_cache (int): Represents the ai_summary_cache (ai_summary_cache_dev,
        ai_summary_cache_qa & ai_summary_cache_prod).
        """
    insights = 1
    ai_summary_cache = 2
