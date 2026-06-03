import os
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from .dataset import DatasetManager
from .gnews import GNewsManager
from .model import FactModel

BASE_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.dirname(BASE_DIR)
load_dotenv(os.path.join(ROOT_DIR, ".env"))
DATA_PATH = os.path.join(BASE_DIR, "data", "initial_dataset.csv")
MODEL_PATH = os.path.join(BASE_DIR, "model", "model.joblib")


def normalize_verdict(value: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "FALSO"
    false_tokens = ["false", "falso", "nao", "não", "errado", "mentira", "mito", "conjectura", "inconclusivo", "questionable", "not true", "mostly false"]
    true_tokens = ["true", "verdade", "verdadeiro", "verificado", "correto", "confirmado"]
    if any(tok in text for tok in false_tokens):
        return "FALSO"
    if any(tok in text for tok in true_tokens):
        return "VERDADEIRO"
    return "FALSO"

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
    gnews_score: Optional[float] = None

dataset = DatasetManager(DATA_PATH)
model = None
try:
    model = FactModel(MODEL_PATH)
except FileNotFoundError:
    model = None

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
FACTCHECK_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
GNEWS_CSV_PATH = os.path.join(BASE_DIR, "data", "gnews_articles.csv")

gnews_manager = GNewsManager(GNEWS_CSV_PATH)


def extract_factcheck_rating(claim_item: dict) -> str:
    if not isinstance(claim_item, dict):
        return ""

    textual = claim_item.get("textualRating")
    if isinstance(textual, dict):
        rating = textual.get("rating", "")
        if isinstance(rating, str) and rating.strip():
            return rating
    elif isinstance(textual, str) and textual.strip():
        return textual

    claim_review = claim_item.get("claimReview", [])
    if claim_review and isinstance(claim_review, list):
        first = claim_review[0]
        if isinstance(first, dict):
            review_textual = first.get("textualRating")
            if isinstance(review_textual, dict):
                rating = review_textual.get("rating", "")
                if isinstance(rating, str) and rating.strip():
                    return rating
            elif isinstance(review_textual, str) and review_textual.strip():
                return review_textual
    return ""


def extract_factcheck_detail(claim_item: dict) -> str:
    if not isinstance(claim_item, dict):
        return ""

    claim_review = claim_item.get("claimReview", [])
    title = ""
    if claim_review and isinstance(claim_review, list):
        first = claim_review[0]
        if isinstance(first, dict):
            title = first.get("title", "") or ""

    claim_text = claim_item.get("text") or claim_item.get("claim") or ""
    if title and ("..." in title or "…" in title):
        if claim_text and claim_text.lower() not in title.lower():
            return f"{claim_text} | {title}"
    return title or claim_text or ""


def expand_detail_text(detail: str, claim_text: str) -> str:
    if not detail:
        return claim_text or ""
    if "..." in detail or "…" in detail:
        claim_text = (claim_text or "").strip()
        if claim_text and claim_text.lower() not in detail.lower():
            return f"{claim_text} | {detail}"
    return detail

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
        # Não substituir a afirmação original enviada pelo usuário.
        # Exibir a claim original em `claim` e incluir a claim encontrada no dataset em `detail`.
        matched_claim = existing.get("claim", "")
        detail_text = expand_detail_text(existing.get("notes", "Resultado obtido do dataset local"), matched_claim)
        # prefixar informação sobre correspondência local
        # Não prefixar; usar apenas o texto de detalhe já construído
        detail_text = detail_text
        return ClaimResponse(
            claim=claim_text,
            source=existing.get("source", "Fonte local"),
            verdict=normalize_verdict(existing.get("label", "FALSO")),
            probability=1.0,
            detail=detail_text,
            url=existing.get("url", "")
        )

    gnews_article = gnews_manager.search_claim(claim_text)

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
                verdict = extract_factcheck_rating(claim_item)
                if not verdict:
                    verdict = claim_review.get("title", "")
                source = claim_review.get("publisher", {}).get("name", "Google Fact Check")
                detail = extract_factcheck_detail(claim_item) or claim_review.get("textualRating", "")
                url = claim_review.get("url", "")
                normalized_verdict = normalize_verdict(verdict)
                factcheck_data = {
                    "claim": claim_text,
                    "label": normalized_verdict,
                    "source": source,
                    "date": claim_review.get("publishDate", ""),
                    "notes": detail,
                    "verdict": normalized_verdict,
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
        source = factcheck_data["source"]
        detail = factcheck_data["detail"] or "Verificação encontrada na API de fact-check"
        url = factcheck_data.get("url", "")
        gnews_score = None
        if gnews_article:
            source = f"{source} + GNews ({gnews_article.get('source', 'GNews')})"
            detail = f"{detail} | Artigo GNews relacionado: {gnews_article.get('title', '').strip()}"
            if not url:
                url = gnews_article.get('url', "")
            gnews_score = gnews_article.get('gnews_score')
        return ClaimResponse(
            claim=claim_text,
            source=source,
            verdict=factcheck_data["verdict"],
            probability=1.0,
            detail=detail,
            url=url,
            gnews_score=gnews_score,
        )

    if gnews_article:
        if model:
            verdict = model.predict(claim_text)
            probability = model.predict_proba(claim_text)
            source = f"Modelo de Machine Learning / GNews ({gnews_article.get('source', 'GNews')})"
        else:
            verdict = "VERDADEIRO"
            probability = 0.0
            source = f"GNews ({gnews_article.get('source', 'GNews')})"
        detail = f"Artigo GNews relacionado: {gnews_article.get('title', '').strip()}"
        url = gnews_article.get('url', "")
        gnews_score = gnews_article.get('gnews_score')
    else:
        if model:
            verdict = model.predict(claim_text)
            probability = model.predict_proba(claim_text)
        else:
            verdict = "FALSO"
            probability = 0.0
        source = "Modelo de Machine Learning"
        detail = "Resultado estimado pelo modelo de ML"
        url = ""
        gnews_score = None

    return ClaimResponse(
        claim=claim_text,
        source=source,
        verdict=verdict,
        probability=round(probability, 3),
        detail=detail,
        url=url,
        gnews_score=gnews_score,
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
