import csv
import os
import re
from pathlib import Path
from unidecode import unidecode

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / 'backend' / 'data' / 'initial_dataset.csv'
CLEAN_PATH = ROOT / 'backend' / 'data' / 'cleaned_dataset.csv'


def normalize(text: str) -> str:
    if text is None:
        return ''
    t = str(text).lower()
    t = unidecode(t)
    t = re.sub(r'http\S+', ' ', t)
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def clean():
    records = []
    seen = set()
    if not DATA_PATH.exists():
        print('Dataset não encontrado:', DATA_PATH)
        return
    with DATA_PATH.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            claim = row.get('claim', '')
            label = str(row.get('label', '')).strip().lower()
            if label not in ('true', 'false'):
                continue
            norm = normalize(claim)
            if not norm:
                continue
            if norm in seen:
                continue
            seen.add(norm)
            records.append({'claim': claim.strip(), 'label': label, 'source': row.get('source',''), 'date': row.get('date',''), 'notes': row.get('notes',''), 'url': row.get('url','')})

    if not records:
        print('Nenhum registro válido após limpeza.')
        return

    os.makedirs(CLEAN_PATH.parent, exist_ok=True)
    with CLEAN_PATH.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['claim','label','source','date','notes','url'])
        writer.writeheader()
        for r in records:
            writer.writerow(r)
    print(f'Cleaned dataset salvo em: {CLEAN_PATH} ({len(records)} registros)')


if __name__ == '__main__':
    clean()
