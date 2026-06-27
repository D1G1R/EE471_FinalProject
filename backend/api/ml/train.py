# api/ml/train.py
"""
Intent sınıflandırma modelini eğitir.

Çalıştırma:
    cd backend
    python -m api.ml.train

Çıktı: api/ml/intent_model.pt ve api/ml/vocab.json
"""

import json
import os
import re

import numpy as np
import torch
import torch.nn as nn

from api.ml.training_data import TRAINING_DATA, INTENTS

MODEL_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(MODEL_DIR, "intent_model.pt")
VOCAB_PATH = os.path.join(MODEL_DIR, "vocab.json")


# ---------- Metin işleme ----------

def tokenize(text: str):
    """Metni küçük harfe çevirip kelimelere ayırır."""
    text = text.lower()
    return re.findall(r"\w+", text)


def build_vocab(data):
    """Eğitim verisindeki tüm kelimelerden bir sözlük oluşturur."""
    vocab = {"<UNK>": 0}  # bilinmeyen kelimeler için
    for text, _ in data:
        for word in tokenize(text):
            if word not in vocab:
                vocab[word] = len(vocab)
    return vocab


def text_to_vector(text, vocab):
    """
    Bag-of-words: metni kelime frekans vektörüne çevirir.
    Vektör boyutu = sözlük boyutu.
    """
    vec = np.zeros(len(vocab), dtype=np.float32)
    for word in tokenize(text):
        idx = vocab.get(word, 0)  # bilinmeyen → <UNK>
        vec[idx] += 1.0
    return vec


# ---------- Model ----------

class IntentClassifier(nn.Module):
    """Basit 2 katmanlı sinir ağı."""

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


# ---------- Eğitim ----------

def train():
    vocab = build_vocab(TRAINING_DATA)
    intent_to_idx = {intent: i for i, intent in enumerate(INTENTS)}

    # Veriyi tensöre çevir
    X = np.array([text_to_vector(text, vocab) for text, _ in TRAINING_DATA])
    y = np.array([intent_to_idx[intent] for _, intent in TRAINING_DATA])

    X = torch.from_numpy(X)
    y = torch.from_numpy(y).long()

    model = IntentClassifier(
        input_size=len(vocab),
        hidden_size=64,
        num_classes=len(INTENTS),
    )

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    epochs = 300
    for epoch in range(epochs):
        optimizer.zero_grad()
        outputs = model(X)
        loss = criterion(outputs, y)
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 50 == 0:
            # Doğruluk hesapla
            with torch.no_grad():
                preds = torch.argmax(model(X), dim=1)
                acc = (preds == y).float().mean().item()
            print(f"Epoch {epoch+1}/{epochs} | Loss: {loss.item():.4f} | Acc: {acc:.2%}")

    # Kaydet
    torch.save({
        "model_state": model.state_dict(),
        "input_size": len(vocab),
        "hidden_size": 64,
        "num_classes": len(INTENTS),
    }, MODEL_PATH)

    with open(VOCAB_PATH, "w", encoding="utf-8") as f:
        json.dump({"vocab": vocab, "intents": INTENTS}, f, ensure_ascii=False, indent=2)

    print(f"\nModel kaydedildi: {MODEL_PATH}")
    print(f"Sözlük kaydedildi: {VOCAB_PATH}")


if __name__ == "__main__":
    train()
