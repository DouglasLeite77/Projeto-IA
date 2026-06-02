import os
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from .dataset import DatasetManager
from .model import FactModel

BASE_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.dirname(BASE_DIR)
load_dotenv(os.path.join(ROOT_DIR, ".env"))
DATA_PATH = os.path.join(BASE_DIR, "data", "initial_dataset.csv")
MODEL_PATH = os.path.join(BASE_DIR, "model", "model.joblib")

app = FastAPI(title="Verificador de Fatos")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ClaimRequest(BaseModel):
    claim: str

class ClaimResponse(BaseModel):
    claim: str
    source: str
    verdict: str
    probability: float
    detail: str
    url: Optional[str] = None

dataset = DatasetManager(DATA_PATH)
model = None
try:
    model = FactModel(MODEL_PATH)
except FileNotFoundError:
    model = None

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
FACTCHECK_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": model is not None}

@app.post("/analyze", response_model=ClaimResponse)
async def analyze(request: ClaimRequest):
    claim_text = request.claim.strip()
    if not claim_text:
        raise HTTPException(status_code=400, detail="A afirmação é obrigatória")

    existing = dataset.find_claim(claim_text)
    if existing:
        return ClaimResponse(
            claim=existing["claim"],
            source=existing.get("source", "Fonte local"),
            verdict=existing.get("label", "VERIFICADO").upper(),
            probability=1.0,
            detail=existing.get("notes", "Resultado obtido do dataset local"),
            url=existing.get("url", "")
        )

    factcheck_data = None
    if GOOGLE_API_KEY:
        params = {
            "query": claim_text,
            "key": GOOGLE_API_KEY,
            "languageCode": "pt"
        }
        response = requests.get(FACTCHECK_URL, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            claims = data.get("claims", [])
            if claims:
                claim_item = claims[0]
                claim_review = claim_item.get("claimReview", [{}])[0]
                verdict = claim_item.get("textualRating", {}).get("rating", "VERIFICADO")
                source = claim_review.get("publisher", {}).get("name", "Google Fact Check")
                detail = claim_review.get("title", "")
                url = claim_review.get("url", "")
                factcheck_data = {
                    "claim": claim_text,
                    "label": verdict.upper(),
                    "source": source,
                    "date": claim_review.get("publishDate", ""),
                    "notes": detail,
                    "verdict": verdict.upper(),
                    "detail": detail,
                    "url": url,
                }

    if factcheck_data:
        dataset.append_record({
            "claim": factcheck_data["claim"],
            "label": factcheck_data["verdict"],
            "source": factcheck_data["source"],
            "date": factcheck_data["date"],
            "notes": factcheck_data["detail"],
        })
        return ClaimResponse(
            claim=claim_text,
            source=factcheck_data["source"],
            verdict=factcheck_data["verdict"],
            probability=1.0,
            detail=factcheck_data["detail"] or "Verificação encontrada na API de fact-check",
            url=factcheck_data.get("url", "")
        )

    if model is None:
        raise HTTPException(status_code=503, detail="Modelo de ML não carregado. Execute o treinamento primeiro.")

    verdict = model.predict(claim_text)
    probability = model.predict_proba(claim_text)
    record = {
        "claim": claim_text,
        "label": verdict,
        "source": "ML Model",
        "date": "",
        "notes": "Estimativa do modelo",
        "url": ""
    }
    dataset.append_record(record)

    return ClaimResponse(
        claim=claim_text,
        source="Modelo de Machine Learning",
        verdict=verdict,
        probability=round(probability, 3),
        detail="Resultado estimado pelo modelo de ML"
    )

# Training control/state
train_status = {"running": False, "last_msg": "idle"}

from threading import Thread
import subprocess

def _run_training_in_background():
    try:
        train_status['running'] = True
        train_status['last_msg'] = 'training started'
        # run the training script as a subprocess so environment is isolated
        proc = subprocess.run(["python", "-m", "backend.scripts.train_model"], capture_output=True, text=True)
        train_status['last_msg'] = proc.stdout + '\n' + proc.stderr
    except Exception as e:
        train_status['last_msg'] = f'error: {e}'
    finally:
        train_status['running'] = False

@app.post('/retrain')
async def retrain():
    if train_status['running']:
        raise HTTPException(status_code=409, detail='Training already running')
    # start background thread
    t = Thread(target=_run_training_in_background, daemon=True)
    t.start()
    return {"status": "started"}

@app.get('/train-status')
async def get_train_status():
    return train_status
