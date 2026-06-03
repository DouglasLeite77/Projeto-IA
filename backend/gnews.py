import csv
import os
from typing import Dict, List, Optional
from .text_preprocessing import normalize_text


class GNewsManager:
    def __init__(self, path: str):
        self.path = path
        self.articles = self._load_articles()

    def _load_articles(self) -> List[Dict[str, str]]:
        if not os.path.exists(self.path):
            return []

        with open(self.path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            articles = []
            for row in reader:
                title = row.get("title", "") or ""
                description = row.get("description", "") or ""
                content = row.get("content", "") or ""
                if not (title or description or content):
                    continue
                row["title_norm"] = normalize_text(title)
                row["description_norm"] = normalize_text(description)
                row["content_norm"] = normalize_text(content)
                row["source"] = row.get("source", "GNews") or "GNews"
                articles.append(row)
            return articles

    def search_claim(self, claim_text: str) -> Optional[Dict[str, str]]:
        normalized_claim = normalize_text(claim_text)
        if not normalized_claim:
            return None

        claim_tokens = set(normalized_claim.split())
        if not claim_tokens:
            return None

        best_article: Optional[Dict[str, str]] = None
        best_score = 0.0

        for article in self.articles:
            title_text = article.get("title_norm", "")
            description_text = article.get("description_norm", "")
            content_text = article.get("content_norm", "")
            combined_text = " ".join([title_text, description_text, content_text]).strip()

            if not combined_text:
                continue

            title_match = normalized_claim in title_text
            description_match = normalized_claim in description_text
            content_match = normalized_claim in content_text

            if title_match or description_match:
                article["gnews_score"] = 1.0
                return article

            article_tokens = set(combined_text.split())
            overlap = len(claim_tokens & article_tokens)
            if overlap < 2:
                continue

            claim_ratio = overlap / len(claim_tokens)
            article_ratio = overlap / max(len(article_tokens), 1)
            score = claim_ratio * 0.7 + article_ratio * 0.3

            if title_text:
                title_overlap = len(claim_tokens & set(title_text.split()))
                score += (title_overlap / max(1, len(claim_tokens))) * 0.2

            if score > best_score:
                best_score = score
                best_article = article

        if best_article and best_score >= 0.35:
            best_article["gnews_score"] = round(best_score, 3)
            return best_article

        return None
