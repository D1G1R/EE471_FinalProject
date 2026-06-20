# api/intent_parser.py
"""
Sesli komuttan intent (niyet) çıkarır.

Desteklenen intent'ler:
  - play          → müziği başlat
  - pause         → müziği duraklat
  - next          → sonraki şarkı
  - previous      → önceki şarkı
  - volume_up     → sesi artır
  - volume_down   → sesi azalt
  - volume_set    → sesi belirli bir seviyeye ayarla
  - current_track → şu an ne çalıyor
  - unknown       → anlaşılamadı
"""

import re

# Anahtar kelime → intent eşleştirmesi
INTENT_KEYWORDS = {
    "play": [
        "çal", "oynat", "başlat", "devam", "play", "resume", "start",
        "müziği aç", "müzik aç", "şarkıyı aç",
    ],
    "pause": [
        "durdur", "duraklat", "kapat", "pause", "stop", "sus",
        "müziği kapat", "müzik kapat",
    ],
    "next": [
        "sonraki", "geç", "atla", "ileri", "next", "skip",
        "sonraki şarkı", "şarkı geç", "şarkıyı geç", "bu şarkıyı geç",
    ],
    "previous": [
        "önceki", "geri", "previous", "back", "geri al",
        "önceki şarkı", "bir önceki",
    ],
    "volume_up": [
        "sesi aç", "sesi artır", "daha yüksek", "ses yükselt",
        "volume up", "louder", "sesi yükselt",
    ],
    "volume_down": [
        "sesi kıs", "sesi azalt", "daha kısık", "ses azalt",
        "volume down", "quieter", "softer", "sesi düşür",
    ],
    "current_track": [
        "ne çalıyor", "hangi şarkı", "bu şarkı ne", "şarkı adı",
        "what's playing", "current song", "bu ne", "şu an ne çalıyor",
    ],
}


def parse_intent(text: str) -> dict:
    """
    Metin komutundan intent ve parametreleri çıkarır.

    Dönüş: {"intent": str, "params": dict}
    """
    text_lower = text.lower().strip()

    # Önce volume_set kontrolü (sayı içeren komutlar)
    volume_match = re.search(
        r"ses(?:i|)\s*(?:yüzde\s*)?(\d+)", text_lower
    ) or re.search(
        r"volume\s*(\d+)", text_lower
    ) or re.search(
        r"yüzde\s*(\d+)", text_lower
    )

    if volume_match:
        vol = int(volume_match.group(1))
        return {"intent": "volume_set", "params": {"volume": min(100, max(0, vol))}}

    # Çok kelimeli ifadeleri önce kontrol et (uzun → kısa sıralama)
    for intent, keywords in INTENT_KEYWORDS.items():
        sorted_keywords = sorted(keywords, key=len, reverse=True)
        for keyword in sorted_keywords:
            if keyword in text_lower:
                return {"intent": intent, "params": {}}

    return {"intent": "unknown", "params": {"original_text": text}}