# api/ml/predict.py
import json
import os
import re

import numpy as np
import torch
import torch.nn as nn

MODEL_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(MODEL_DIR, "intent_model.pt")
VOCAB_PATH = os.path.join(MODEL_DIR, "vocab.json")

# Güven eşiği: bunun altındaki tahminler "unknown" sayılır
CONFIDENCE_THRESHOLD = 0.55


class IntentClassifier(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, num_classes),
        )

    def forward(self, x):
        return self.net(x)


# Modeli bir kez yükle (modül seviyesinde cache)
_model = None
_vocab = None
_intents = None


def _load_model():
    global _model, _vocab, _intents
    if _model is not None:
        return

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            "Model bulunamadı. Önce 'python -m api.ml.train' ile eğit."
        )

    checkpoint = torch.load(MODEL_PATH, map_location="cpu")
    _model = IntentClassifier(
        checkpoint["input_size"],
        checkpoint["hidden_size"],
        checkpoint["num_classes"],
    )
    _model.load_state_dict(checkpoint["model_state"])
    _model.eval()

    with open(VOCAB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        _vocab = data["vocab"]
        _intents = data["intents"]


def _tokenize(text):
    return re.findall(r"\w+", text.lower())


def _text_to_vector(text):
    vec = np.zeros(len(_vocab), dtype=np.float32)
    for word in _tokenize(text):
        idx = _vocab.get(word, 0)
        vec[idx] += 1.0
    return vec


def predict_intent(text: str) -> dict:
    """
    Metinden intent tahmin eder.

    Dönüş: {"intent": str, "confidence": float}
    """
    _load_model()

    vec = _text_to_vector(text)
    x = torch.from_numpy(vec).unsqueeze(0)  # batch boyutu ekle

    with torch.no_grad():
        logits = _model(x)
        probs = torch.softmax(logits, dim=1)
        confidence, idx = torch.max(probs, dim=1)

    confidence = confidence.item()
    intent = _intents[idx.item()]

    if confidence < CONFIDENCE_THRESHOLD:
        return {"intent": "unknown", "confidence": confidence}

    return {"intent": intent, "confidence": confidence}
