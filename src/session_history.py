from datetime import datetime

import pandas as pd


class SessionHistory:
    """Store fixed mode recommendations in the current Streamlit session."""

    def __init__(self, records):
        self.records = records

    def save_history(self, round_num, strategy, numbers, memo=""):
        if isinstance(numbers, list):
            numbers = ", ".join(map(str, sorted(numbers)))
        self.records.append({
            "round": round_num,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "strategy": strategy,
            "numbers": str(numbers),
            "memo": memo,
        })
        return True

    def load_history(self):
        return pd.DataFrame(
            self.records, columns=["round", "date", "strategy", "numbers", "memo"],
        ).iloc[::-1]

    def delete_history(self, index):
        if 0 <= index < len(self.records):
            del self.records[index]
            return True
        return False
