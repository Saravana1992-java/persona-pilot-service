class Insights:
    def __init__(self, insight_records, count):
        self.insight_records = insight_records
        self.total_records = count

    def to_dict(self):
        return {
            'insights': self.insight_records,
            'total_records': self.total_records
        }
