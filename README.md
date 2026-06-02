# Projeto IA - Verificação de Fatos

Arquitetura proposta:
- Frontend web responsivo com HTML/CSS/JavaScript (PWA-friendly)
- Backend Python com FastAPI
- Integração com API Google Fact Check
- Dataset local para consultas e treinamento de modelo
- Modelo de ML para estimar veracidade quando não houver verificação externa

## Como usar

1. Instale dependências do backend:
   ```powershell
   cd "c:\Users\User\Documents\Nova pasta\Projeto IA\backend"
   python -m pip install -r requirements.txt
   ```

2. Coletar verificações usando a Google Fact Check API (usa a chave em `.env`):
   ```powershell
   cd "c:\Users\User\Documents\Nova pasta\Projeto IA"
   python backend/scripts/collect_factchecks.py
   ```

3. Limpar e deduplicar o dataset:
   ```powershell
   python backend/scripts/clean_dataset.py
   ```

4. Treinar o modelo (ou use o endpoint `/retrain`):
   ```powershell
   python -m backend.scripts.train_model
   # ou iniciar o backend e chamar /retrain
   uvicorn backend.app:app --reload --port 8000
   # então POST http://127.0.0.1:8000/retrain
   ```

5. Execute o backend (se não estiver rodando):
   ```powershell
   uvicorn backend.app:app --reload --port 8000
   ```

6. Abra o frontend em `frontend/index.html` ou sirva via servidor estático.

## Observações
- A API de fact-check exige chave de API Google em `GOOGLE_API_KEY`.
- Você pode definir a chave em um arquivo `.env` na raiz do projeto ou como variável de ambiente.
- Um exemplo de arquivo está em `.env.example`.
- O dataset inicial está em `backend/data/initial_dataset.csv` e o dataset limpo em `backend/data/cleaned_dataset.csv`.
- O modelo salvo é gerenciado em `backend/model/model.joblib`.
