import os
import csv
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Prefer environment variable, otherwise try to read .env manually
API_KEY = os.getenv('GOOGLE_API_KEY')
if not API_KEY:
    env_path = ROOT / '.env'
    if env_path.exists():
        with env_path.open(encoding='utf-8') as f:
            for line in f:
                if 'GOOGLE_API_KEY' in line:
                    try:
                        _, val = line.split('=', 1)
                        API_KEY = val.strip().strip('\"').strip("\'")
                        break
                    except Exception:
                        pass

DATA_PATH = ROOT / 'data' / 'initial_dataset.csv'

KEYWORDS = [
    'eleição', 'eleicoes', 'bolsonaro', 'lula', 'pt', 'pl', 'psdb', 'campanha',
    'urna', 'voto', 'fraude', 'fraudes eleitorais', 'falsidade', 'eleitoral'
]

FACTCHECK_URL = 'https://factchecktools.googleapis.com/v1alpha1/claims:search'


def map_rating_to_label(rating: str):
    if not rating:
        return None
    r = rating.strip().lower()
    # common positive indicators
    if 'true' in r or 'verdade' in r or 'verdadeiro' in r:
        return 'true'
    if 'mostly true' in r or 'muito' in r and 'verdade' in r:
        return 'true'
    # common negative indicators
    if 'false' in r or 'falso' in r or 'not true' in r:
        return 'false'
    if 'mostly false' in r or 'principalmente falso' in r:
        return 'false'
    return None


def fetch_claims_for_query(query: str, page_size: int = 10):
    params = {
        'query': query,
        'key': API_KEY,
        'languageCode': 'pt',
        'pageSize': page_size
    }
    resp = requests.get(FACTCHECK_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def load_existing_claims(path: Path):
    existing = {}
    if not path.exists():
        return existing
    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing[row['claim'].strip().lower()] = row
    return existing


def append_records(path: Path, records):
    header = ['claim', 'label', 'source', 'date', 'notes', 'url']
    exists = path.exists()
    with path.open('a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not exists:
            writer.writeheader()
        for r in records:
            writer.writerow(r)


if __name__ == '__main__':
    if not API_KEY:
        print('GOOGLE_API_KEY não definido no .env')
        raise SystemExit(1)

    existing = load_existing_claims(DATA_PATH)
    new_records = []
    for kw in KEYWORDS:
        try:
            print(f'Consultando: {kw}')
            data = fetch_claims_for_query(kw, page_size=20)
            claims = data.get('claims', [])
            for c in claims:
                claim_text = c.get('text') or c.get('claim') or ''
                claim_text = claim_text.strip()
                if not claim_text:
                    continue
                key = claim_text.lower()
                if key in existing:
                    continue
                # try to extract rating and source
                verdict = None
                # try claim-level textualRating
                if isinstance(c.get('textualRating'), dict):
                    verdict = c.get('textualRating', {}).get('rating')
                # try claimReview
                claim_review = c.get('claimReview', [])
                source = ''
                date = ''
                notes = ''
                if claim_review:
                    first = claim_review[0]
                    source = first.get('publisher', {}).get('name', '')
                    date = first.get('publishDate', '')
                    notes = first.get('title', '') or first.get('textualRating', '')
                    # textualRating may be nested in claimReview
                    tr = first.get('textualRating')
                    if isinstance(tr, dict):
                        trv = tr.get('rating')
                        if trv:
                            verdict = trv
                label = map_rating_to_label(verdict)
                if label is None:
                    # ignore inconclusive for training, but still store if wanted
                    continue
                rec = {
                    'claim': claim_text,
                    'label': label,
                    'source': source or 'Google Fact Check',
                    'date': date,
                    'notes': notes,
                    'url': first.get('url', '')
                }
                new_records.append(rec)
                existing[key] = rec
        except Exception as e:
            print(f'Erro ao consultar {kw}:', e)
    if new_records:
        print(f'Adicionando {len(new_records)} novos registros ao dataset')
        append_records(DATA_PATH, new_records)
    else:
        print('Nenhum novo registro encontrado.')
