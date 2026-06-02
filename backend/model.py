import os
from joblib import load
from sklearn.pipeline import Pipeline

class FactModel:
    def __init__(self, model_path: str):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modelo não encontrado: {model_path}")
        self.pipeline: Pipeline = load(model_path)

    def predict(self, claim: str) -> str:
        prediction = self.pipeline.predict([claim])[0]
        if prediction == "true":
            return "VERDADEIRO"
        if prediction == "false":
            return "FALSO"
        return "INCONCLUSIVO"

    def predict_proba(self, claim: str) -> float:
        if hasattr(self.pipeline, "predict_proba"):
            proba = self.pipeline.predict_proba([claim])[0]
            return max(proba)
        return 0.0
