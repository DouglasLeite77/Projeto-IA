import os
import csv
import time
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / 'backend'
DATA_DIR = BACKEND_DIR / 'data'

GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')
if not GNEWS_API_KEY:
    env_path = ROOT / '.env'
    if env_path.exists():
        with env_path.open(encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('GNEWS_API_KEY='):
                    _, val = line.split('=', 1)
                    GNEWS_API_KEY = val.strip().strip('"').strip("\'")
                    break

API_URL = 'https://gnews.io/api/v4/search'
DATA_PATH = DATA_DIR / 'gnews_articles.csv'
KEYWORDS = [
    'eleição', 'bolsonaro', 'lula', 'pt', 'campanha', 'urna', 'voto', 'fraude'
]


def fetch_news(query: str, max_results: int = 10):
    params = {
        'q': query,
        'token': GNEWS_API_KEY,
        'lang': 'pt',
        'max': max_results,
        'sortby': 'publishedAt'
    }
    resp = requests.get(API_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def save_articles(path: Path, articles):
    path.parent.mkdir(parents=True, exist_ok=True)
    header = ['query', 'title', 'description', 'content', 'source', 'publishedAt', 'url']
    exists = path.exists()
    with path.open('a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not exists:
            writer.writeheader()
        for article in articles:
            writer.writerow(article)


def normalize_article(article, query):
    source_name = ''
    source = article.get('source')
    if isinstance(source, dict):
        source_name = source.get('name', '')
    return {
        'query': query,
        'title': article.get('title', '').strip(),
        'description': article.get('description', '').strip(),
        'content': article.get('content', '').strip(),
        'source': source_name,
        'publishedAt': article.get('publishedAt', ''),
        'url': article.get('url', '')
    }


def load_existing_urls(path: Path):
    if not path.exists():
        return set()
    urls = set()
    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get('url', '').strip()
            if url:
                urls.add(url)
    return urls


def main():
    if not GNEWS_API_KEY:
        print('GNEWS_API_KEY não definido. Defina em .env ou na variável de ambiente.')
        raise SystemExit(1)

    existing_urls = load_existing_urls(DATA_PATH)
    collected = []

    for query in KEYWORDS:
        print(f'Consultando GNews: {query}')
        try:
            data = fetch_news(query, max_results=10)
        except requests.RequestException as exc:
            print(f'Erro ao consultar GNews para {query}:', exc)
            time.sleep(3)
            continue

        for item in data.get('articles', []):
            article = normalize_article(item, query)
            if not article['url'] or article['url'] in existing_urls:
                continue
            collected.append(article)
            existing_urls.add(article['url'])

        time.sleep(1)

    if collected:
        print(f'Gravando {len(collected)} artigos GNews em {DATA_PATH}')
        save_articles(DATA_PATH, collected)
    else:
        print('Nenhum artigo novo encontrado ou todos já estavam salvos.')


if __name__ == '__main__':
    main()
