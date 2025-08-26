from enum import Enum


class EmbeddingModels(Enum):
    """
        Enum class for different types of embedding models.

        This class defines two types of embedding models: sentence_transformers.
        Each model type is associated with an integer value.

        Attributes:
        sentence_transformers (int): Represents the Sentence Transformers model.
        """
    sentence_transformers = 1
