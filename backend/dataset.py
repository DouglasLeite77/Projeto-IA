import csv
import os
import unicodedata
import re
import difflib
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
            # Try DictReader first; if file has no proper header, fall back to positional parsing
            f.seek(0)
            reader = csv.DictReader(f)
            # If the file's fieldnames don't match expected headers, parse by position
            if not reader.fieldnames or set([h.strip().lower() for h in reader.fieldnames]) != set(self.headers):
                f.seek(0)
                raw = list(csv.reader(f))
                records = []
                for row in raw:
                    # skip empty rows
                    if not any(cell.strip() for cell in row):
                        continue
                    # map columns by position to headers
                    mapped = {self.headers[i]: (row[i].strip() if i < len(row) else "") for i in range(len(self.headers))}
                    records.append(mapped)
                self.records = records
                # rewrite file with proper header and normalized rows
                with open(self.path, "w", newline="", encoding="utf-8") as rewrite:
                    writer = csv.DictWriter(rewrite, fieldnames=self.headers)
                    writer.writeheader()
                    writer.writerows(self.records)
            else:
                f.seek(0)
                reader = csv.DictReader(f)
                self.records = [row for row in reader]
                if reader.fieldnames and "url" not in reader.fieldnames:
                    for row in self.records:
                        row["url"] = ""
                    with open(self.path, "w", newline="", encoding="utf-8") as rewrite:
                        writer = csv.DictWriter(rewrite, fieldnames=self.headers)
                        writer.writeheader()
                        writer.writerows(self.records)

        # build normalized map for fuzzy/normalized lookup
        self._build_normalized_map()

    def _normalize_text(self, s: str) -> str:
        if not s:
            return ""
        # remove accents
        s = unicodedata.normalize('NFKD', s)
        s = ''.join(ch for ch in s if not unicodedata.combining(ch))
        s = s.lower()
        # remove non-alphanumeric characters
        s = re.sub(r"[^a-z0-9\s]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _build_normalized_map(self):
        self.normalized_map = {}
        for row in self.records:
            key = self._normalize_text(row.get('claim', ''))
            if not key:
                continue
            self.normalized_map.setdefault(key, []).append(row)

    def find_claim(self, claim: str) -> Optional[Dict[str, str]]:
        text = self._normalize_text(claim)
        # exact normalized match
        if not text:
            return None

        # exact normalized match
        if text in getattr(self, 'normalized_map', {}):
            return self.normalized_map[text][0]

        # fallback: fuzzy match against normalized claims
        best_row = None
        best_score = 0.0
        for key, rows in getattr(self, 'normalized_map', {}).items():
            score = difflib.SequenceMatcher(None, key, text).ratio()
            if score > best_score:
                best_score = score
                best_row = rows[0]

        # threshold for accepting fuzzy match
        if best_score >= 0.80:
            return best_row

        return None

    def append_record(self, record: Dict[str, str]):
        normalized = {field: record.get(field, "") for field in self.headers}
        self.records.append(normalized)
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.headers)
            writer.writerow(normalized)
        # update normalized map
        key = self._normalize_text(normalized.get('claim', ''))
        if key:
            self.normalized_map.setdefault(key, []).append(normalized)
