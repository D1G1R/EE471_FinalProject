# test_model.py
from api.ml.predict import predict_intent

tests = [
    "atla bunu",
    "yeter bu şarkı",
    "biraz kıs sesi",
    "tarkan çal",
    "ne çalıyor şu an",
    "devam ettir",
    "continue",
    "enough of this song",
    "turn it down",
    "play bohemian rhapsody",
    "play sezen aksu",
    "wait",
    "move on",
    "metallica çal",
    "pop çal",
    "rap çal",
    "rap müzik çal",
    "canım sıkıldı bir şarkı çal",
    "play some music",
    "play some rock music",
    "play some pop music",
    "gripin çal",
    "i feel bad, play a song",
    "play rock",
    "metal",
    "rock",
    "sago çal",
    "radiohead çal",
    "play funk",
    "rock çal",
    "play jazz",
    "play classical",

]

for t in tests:
    result = predict_intent(t)
    print(f"'{t}' → {result['intent']} ({result['confidence']:.0%})")
