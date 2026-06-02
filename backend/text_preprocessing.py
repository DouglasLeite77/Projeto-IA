import os
import re
from unidecode import unidecode

try:
    from nltk.stem.snowball import SnowballStemmer
    _HAS_NLTK = True
except Exception:
    _HAS_NLTK = False


def load_pt_stopwords():
    base_dir = os.path.dirname(__file__)
    path = os.path.join(base_dir, "data", "pt_stopwords.txt")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return [w.strip() for w in f if w.strip()]
    return None


class TextPreprocessor:
    def __init__(self, pt_stopwords=None):
        self.pt_stopwords = pt_stopwords

    def __call__(self, text: str) -> str:
        return normalize_text(text, self.pt_stopwords)


def normalize_text(text: str, pt_stopwords=None) -> str:
    text = str(text).lower()
    text = re.sub(r'http\\S+', ' ', text)
    text = unidecode(text)
    text = re.sub(r'[^a-z0-9\\s]', ' ', text)
    tokens = text.split()
    if pt_stopwords:
        tokens = [t for t in tokens if t not in pt_stopwords]
    if _HAS_NLTK:
        stemmer = SnowballStemmer("portuguese")
        tokens = [stemmer.stem(t) for t in tokens]
    return ' '.join(tokens)
