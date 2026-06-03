import os
import numpy as np
from joblib import load
from sklearn.pipeline import Pipeline

class FactModel:
    def __init__(self, model_path: str):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modelo não encontrado: {model_path}")
        self.pipeline: Pipeline = load(model_path)

    def predict(self, claim: str) -> str:
        prediction = str(self.pipeline.predict([claim])[0]).strip().lower()
        if prediction == "false" or prediction == "falso":
            return "FALSO"
        return "VERDADEIRO"

    def predict_proba(self, claim: str) -> float:
        if not hasattr(self.pipeline, "predict_proba"):
            return 0.0

        proba = self.pipeline.predict_proba([claim])[0]
        prediction = str(self.pipeline.predict([claim])[0]).strip().lower()
        classes = [str(c).strip().lower() for c in self.pipeline.classes_]

        if prediction in classes:
            index = classes.index(prediction)
            return float(np.asarray(proba)[index])

        return float(np.max(np.asarray(proba)))

    def normalize_prediction(self, prediction: str) -> str:
        text = str(prediction or "").strip().lower()
        if "false" in text or "falso" in text:
            return "FALSO"
        return "VERDADEIRO"
