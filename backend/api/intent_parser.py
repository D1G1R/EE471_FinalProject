# api/intent_parser.py
"""
Sesli komuttan intent çıkarır.
Artık PyTorch modeli kullanıyor, ama parametre ayıklama için regex de var.
"""

import re

from api.ml.predict import predict_intent


def extract_volume(text: str):
    """Metinden ses seviyesi sayısını ayıklar (varsa)."""
    text_lower = text.lower()
    match = (
        re.search(r"ses(?:i|)\s*(?:yüzde\s*)?(\d+)", text_lower)
        or re.search(r"volume\s*(\d+)", text_lower)
        or re.search(r"yüzde\s*(\d+)", text_lower)
    )
    if match:
        return min(100, max(0, int(match.group(1))))
    return None


def extract_search_query(text: str):
    text_lower = text.lower().strip()
    command_words = ["çal", "aç", "oynat", "başlat", "dinle"]
    query = text_lower
    for word in command_words:
        query = re.sub(rf"\b{word}\b", "", query)
    # Noktalama işaretlerini temizle
    query = re.sub(r"[^\w\s]", "", query).strip()
    return query if query else None


def parse_intent(text: str) -> dict:
    text = text.strip()
    text_lower = text.lower().strip()

    # Volume_set kontrolü
    volume = extract_volume(text)
    if volume is not None:
        return {"intent": "volume_set", "params": {"volume": volume}, "confidence": 1.0}

    # Türkçe kalıp: "X çal/aç/oynat"
    tr_pattern = re.search(
        r"^(.+?)\s+(çal|aç|oynat|dinle)$", text_lower
    )
    if tr_pattern:
        query = tr_pattern.group(1).strip()
        generic_words = {"müziği", "müzik", "şarkıyı", "şarkı", "bir", "bana"}
        if query not in generic_words:
            return {
                "intent": "search_and_play",
                "params": {"query": query},
                "confidence": 1.0,
            }

    # İngilizce kalıp: "play X" — başta play varsa ve tek kelime değilse
    en_pattern = re.match(r"^play\s+(.+)$", text_lower)
    if en_pattern:
        query = en_pattern.group(1).strip()
        # "play some music", "play music" gibi genel ifadeleri atla
        generic_en = {"music", "some music", "a song", "something", "anything"}
        if query not in generic_en:
            return {
                "intent": "search_and_play",
                "params": {"query": query},
                "confidence": 1.0,
            }

    # İngilizce kalıp: "X play" — sonda play varsa
    en_suffix = re.match(r"^(.+?)\s+play$", text_lower)
    if en_suffix:
        query = en_suffix.group(1).strip()
        generic_en_suffix = {"music", "song", "something"}
        if query not in generic_en_suffix:
            return {
                "intent": "search_and_play",
                "params": {"query": query},
                "confidence": 1.0,
            }

    # PyTorch modeli
    prediction = predict_intent(text)
    intent = prediction["intent"]
    confidence = prediction["confidence"]

    params = {}
    if intent == "search_and_play":
        query = extract_search_query(text)
        if query:
            params["query"] = query
        else:
            intent = "play"

    if intent == "unknown":
        params["original_text"] = text

    return {"intent": intent, "params": params, "confidence": confidence}
