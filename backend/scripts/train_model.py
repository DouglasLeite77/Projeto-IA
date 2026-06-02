import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report
from joblib import dump
from backend.text_preprocessing import load_pt_stopwords, TextPreprocessor

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "initial_dataset.csv")
MODEL_DIR = os.path.join(BASE_DIR, "model")
MODEL_PATH = os.path.join(MODEL_DIR, "model.joblib")


def build_pipeline(pt_stopwords=None):
    return Pipeline([
        ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 3), preprocessor=TextPreprocessor(pt_stopwords))),
        ("clf", LogisticRegression(max_iter=2000, class_weight='balanced'))
    ])


if __name__ == "__main__":
    df = pd.read_csv(DATA_PATH)
    if df.empty:
        raise SystemExit("Dataset vazio. Preencha backend/data/initial_dataset.csv com registros.")

    df["label"] = df["label"].astype(str).str.strip().str.lower()
    df = df[df["label"].isin(["true", "false"])]
    if df.empty:
        raise SystemExit("Dataset não contém registros válidos com label true/false.")

    X = df["claim"].astype(str)
    y = df["label"].astype(str)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    pt_stopwords = load_pt_stopwords()
    pipeline = build_pipeline(pt_stopwords)

    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    report = classification_report(y_test, y_pred, digits=4)
    print("=== Relatório de classificação ===")
    print(report)

    os.makedirs(MODEL_DIR, exist_ok=True)
    dump(pipeline, MODEL_PATH)
    print(f"Modelo salvo em: {MODEL_PATH}")
