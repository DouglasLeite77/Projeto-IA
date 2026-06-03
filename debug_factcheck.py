import os
import requests
from pathlib import Path
ROOT = Path('c:/Users/Douglas/Desktop/Projeto-IA')
API_KEY = os.getenv('GOOGLE_API_KEY')
if not API_KEY:
    env_path = ROOT / '.env'
    if env_path.exists():
        with open(env_path, encoding='utf-8') as f:
            for line in f:
                if 'GOOGLE_API_KEY' in line:
                    API_KEY = line.split('=', 1)[1].strip().strip('"').strip("'")
                    break
print('API_KEY', bool(API_KEY))
url = 'https://factchecktools.googleapis.com/v1alpha1/claims:search'
params = {'query': 'bolsonaro', 'key': API_KEY, 'languageCode': 'pt', 'pageSize': 20}
resp = requests.get(url, params=params, timeout=15)
print('status', resp.status_code)
data = resp.json()
print('keys', list(data.keys()))
claims = data.get('claims', [])
print('claims', len(claims))
for i, c in enumerate(claims[:5], 1):
    print('---', i)
    print('text', c.get('text'))
    print('claim', c.get('claim'))
    print('textualRating', c.get('textualRating'))
    print('claimReview', c.get('claimReview'))
