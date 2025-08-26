class Insight:
    def __init__(self, index, key, score):
        self.index = index
        self.key = key
        self.score = score

    def to_dict(self):
        return {
            'index': self.index,
            'key': self.key,
            'score': self.score
        }
