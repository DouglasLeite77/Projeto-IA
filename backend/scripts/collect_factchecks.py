import os
import csv
import time
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / 'backend'
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
                        API_KEY = val.strip().strip('"').strip("\'")
                        break
                    except Exception:
                        pass

DATA_PATH = BACKEND_DIR / 'data' / 'initial_dataset.csv'

KEYWORDS = [
    # Principais atores e partidos
    'lula', 'luiz inacio lula da silva', 'jair bolsonaro', 'bolsonaro', 'ciro gomes',
    'sergio moro', 'haddad', 'fernando haddad', 'marina silva', 'geraldo alckmin',
    'joao doria', 'aecio neves', 'eduardo bolsonaro', 'flavio bolsonaro',
    'pt', 'psdb', 'pl', 'psol', 'pmdb', 'pmn', 'pps', 'pcdo', 'psb', 'rede', 'psl',

    # Instituições e tribunais
    'stf', 'tse', 'tribunal superior eleitoral', 'tribunal superior federal',
    'congresso', 'senado', 'camara dos deputados', 'camara federal', 'cpi',

    # Temas centrais e termos eleitorais
    'eleicao', 'eleicoes', 'eleitoral', 'voto', 'urna', 'urna eletronica',
    'fraude', 'fraude eleitoral', 'contagem de votos', 'resultado eleitoral',
    'primeiro turno', 'segundo turno', 'campanha', 'propaganda eleitoral',

    # Políticas públicas e programas
    'auxilio emergencial', 'bolsa familia', 'bolsa familia 2022', 'fundo eleitoral',
    'reforma da previdencia', 'reforma administrativa', 'pec', 'pl', 'decreto',

    # Corrupcao e operações de investigação
    'corrupcao', 'lava jato', 'mensalao', 'denuncia', 'operacao policial', 'investigacao',

    # Mídia, redes sociais e desinformação
    'fake news', 'desinformacao', 'checagem', 'fact-check', 'whatsapp', 'telegram',
    'facebook', 'instagram', 'youtube', 'redes sociais', 'midia', 'portais',

    # Institutos e pesquisas
    'datafolha', 'ibope', 'pesquisa eleitoral', 'instituto de pesquisa',

    # Governos e cargos
    'presidente', 'presidencia', 'governador', 'prefeito', 'deputado', 'senador',

    # Termos gerais usados em checagens
    'afirmacao', 'veracidade', 'veredito', 'falso', 'verdadeiro', 'enganoso',

    # Assuntos recorrentes na política brasileira
    'corrupcao politica', 'impeachment', 'auxilio', 'beneficio', 'inflacao', 'desemprego',
    'saude publica', 'vacina', 'covid', 'educacao', 'seguranca publica', 'impostos',
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


def fetch_claims_for_query(query: str, page_size: int = 10, page_token: str | None = None, max_retries: int = 5):
    params = {
        'query': query,
        'key': API_KEY,
        'languageCode': 'pt',
        'pageSize': page_size
    }
    if page_token:
        params['pageToken'] = page_token

    attempt = 0
    while True:
        attempt += 1
        try:
            resp = requests.get(FACTCHECK_URL, params=params, timeout=10)
            if resp.status_code in (429, 503):
                if attempt >= max_retries:
                    resp.raise_for_status()
                delay = min(5 * attempt, 30)
                print(f'API retornou {resp.status_code}; retry {attempt}/{max_retries} em {delay}s')
                time.sleep(delay)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            if attempt >= max_retries:
                raise
            delay = min(5 * attempt, 30)
            print(f'Erro de rede/servidor ({exc}); retry {attempt}/{max_retries} em {delay}s')
            time.sleep(delay)


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
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    for kw in KEYWORDS:
        page_token = None
        page_index = 0
        while True:
            try:
                page_index += 1
                print(f'Consultando: {kw} (page {page_index})')
                data = fetch_claims_for_query(kw, page_size=20, page_token=page_token)
                claims = data.get('claims', [])
                for c in claims:
                    claim_text = c.get('text') or c.get('claim') or ''
                    claim_text = claim_text.strip()
                    if not claim_text:
                        continue
                    key = claim_text.lower()
                    if key in existing:
                        continue
                    verdict = None
                    if isinstance(c.get('textualRating'), dict):
                        verdict = c.get('textualRating', {}).get('rating')
                    claim_review = c.get('claimReview', [])
                    source = ''
                    date = ''
                    notes = ''
                    url = ''
                    if claim_review:
                        first = claim_review[0]
                        source = first.get('publisher', {}).get('name', '')
                        date = first.get('publishDate', '')
                        url = first.get('url', '')
                        notes = first.get('title', '') or first.get('textualRating', '')
                        tr = first.get('textualRating')
                        if isinstance(tr, dict):
                            trv = tr.get('rating')
                            if trv:
                                verdict = trv
                    label = map_rating_to_label(verdict)
                    if label is None:
                        continue
                    rec = {
                        'claim': claim_text,
                        'label': label,
                        'source': source or 'Google Fact Check',
                        'date': date,
                        'notes': notes,
                        'url': url
                    }
                    new_records.append(rec)
                    existing[key] = rec
                page_token = data.get('nextPageToken')
                if not page_token or page_index >= 3:
                    break
            except Exception as e:
                print(f'Erro ao consultar {kw}:', e)
                break
    if new_records:
        print(f'Adicionando {len(new_records)} novos registros ao dataset')
        append_records(DATA_PATH, new_records)
    else:
        print('Nenhum novo registro encontrado.')
