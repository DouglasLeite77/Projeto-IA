import csv
import os
from typing import Optional, Dict

class DatasetManager:
    def __init__(self, path: str):
        self.path = path
        self.headers = ["claim", "label", "source", "date", "notes", "url"]
        self.records = []
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.headers)
                writer.writeheader()
            self.records = []
            return

        with open(self.path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.records = [row for row in reader]
            if reader.fieldnames and "url" not in reader.fieldnames:
                for row in self.records:
                    row["url"] = ""
                with open(self.path, "w", newline="", encoding="utf-8") as rewrite:
                    writer = csv.DictWriter(rewrite, fieldnames=self.headers)
                    writer.writeheader()
                    writer.writerows(self.records)

    def find_claim(self, claim: str) -> Optional[Dict[str, str]]:
        text = claim.strip().lower()
        for row in self.records:
            if row["claim"].strip().lower() == text:
                return row
        return None

    def append_record(self, record: Dict[str, str]):
        normalized = {field: record.get(field, "") for field in self.headers}
        self.records.append(normalized)
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.headers)
            writer.writerow(normalized)
