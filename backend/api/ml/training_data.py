# api/ml/training_data.py
"""
Intent sınıflandırma için eğitim verisi.
Her intent için mümkün olduğunca çeşitli cümleler ekle.
Ne kadar çok ve çeşitli → model o kadar iyi.
"""

TRAINING_DATA = [
    # ---------- play ----------
    ("çal", "play"),
    ("müziği çal", "play"),
    ("müziği başlat", "play"),
    ("devam et", "play"),
    ("devam ettir", "play"),
    ("kaldığı yerden devam et", "play"),
    ("müziği aç", "play"),
    ("şarkıyı başlat", "play"),
    ("oynat", "play"),
    ("başlat hadi", "play"),
    ("play", "play"),
    ("resume", "play"),
    ("müzik çalsın", "play"),
    ("continue", "play"),
    ("play some music", "play"), 

    # ---------- pause ----------
    ("durdur", "pause"),
    ("müziği durdur", "pause"),
    ("duraklat", "pause"),
    ("dur", "pause"),
    ("bir saniye dur", "pause"),
    ("müziği kapat", "pause"),
    ("sustur", "pause"),
    ("biraz dur", "pause"),
    ("şarkıyı durdur", "pause"),
    ("pause", "pause"),
    ("stop", "pause"),
    ("kapat şunu", "pause"),
    ("wait", "pause"),
    ("wait a moment", "pause"),

    # ---------- next ----------
    ("sonraki", "next"),
    ("sonraki şarkı", "next"),
    ("sonraki şarkıya geç", "next"),
    ("bir sonrakine geç", "next"),
    ("sonrakine geçer misin", "next"),
    ("atla", "next"),
    ("atla bunu", "next"),
    ("bu şarkıyı atla", "next"),
    ("geç bunu", "next"),
    ("şarkıyı geç", "next"),
    ("yeter bu şarkı", "next"),
    ("ileri", "next"),
    ("skip", "next"),
    ("next", "next"),
    ("diğer şarkı", "next"),

    # ---------- previous ----------
    ("önceki", "previous"),
    ("önceki şarkı", "previous"),
    ("önceki şarkıya dön", "previous"),
    ("bir önceki", "previous"),
    ("geri al", "previous"),
    ("geri dön", "previous"),
    ("bir öncekine geç", "previous"),
    ("baştan başlat", "previous"),
    ("previous", "previous"),
    ("back", "previous"),

    # ---------- volume_up ----------
    ("sesi aç", "volume_up"),
    ("sesi artır", "volume_up"),
    ("sesi yükselt", "volume_up"),
    ("ses biraz daha açılsın", "volume_up"),
    ("daha yüksek", "volume_up"),
    ("biraz daha aç sesi", "volume_up"),
    ("sesi büyüt", "volume_up"),
    ("louder", "volume_up"),
    ("volume up", "volume_up"),

    # ---------- volume_down ----------
    ("sesi kıs", "volume_down"),
    ("sesi azalt", "volume_down"),
    ("sesi düşür", "volume_down"),
    ("daha kısık", "volume_down"),
    ("biraz kıs sesi", "volume_down"),
    ("ses çok yüksek kıs", "volume_down"),
    ("sesi alçalt", "volume_down"),
    ("quieter", "volume_down"),
    ("volume down", "volume_down"),

    # ---------- current_track ----------
    ("ne çalıyor", "current_track"),
    ("şu an ne çalıyor", "current_track"),
    ("hangi şarkı bu", "current_track"),
    ("bu şarkı ne", "current_track"),
    ("şarkının adı ne", "current_track"),
    ("bu ne", "current_track"),
    ("çalan şarkı ne", "current_track"),
    ("what's playing", "current_track"),

    # ---------- search_and_play ----------
    # NOT: Bu intent için cümleler "X çal" kalıbında.
    # Model bu kalıbı öğrenecek, şarkı adını sonra ayıklayacağız.
    ("tarkan çal", "search_and_play"),
    ("sezen aksu çal", "search_and_play"),
    ("bohemian rhapsody çal", "search_and_play"),
    ("şarkı çal", "search_and_play"),
    ("müzik çal bana", "search_and_play"),
    ("queen aç", "search_and_play"),
    ("dua lipa oynat", "search_and_play"),
    ("şu şarkıyı aç", "search_and_play"),
    ("imagine dragons çal", "search_and_play"),
    ("bir şarkı çal", "search_and_play"),
    ("müzik aç bana", "search_and_play"),
    ("pinhani çal", "search_and_play"),
    ("ezhel çal", "search_and_play"),
    ("şu sanatçıyı çal", "search_and_play"),
    ("gripin çal", "search_and_play"),        
    ("metallica çal", "search_and_play"),      
    ("pop çal", "search_and_play"),            
    ("rap çal", "search_and_play"),              
    ("rap müzik çal", "search_and_play"),        
    ("rock müzik çal", "search_and_play"),       
    ("play bohemian rhapsody", "search_and_play"), 
    ("play sezen aksu", "search_and_play"),      
    ("play metallica", "search_and_play"),       
    ("play some rock music", "search_and_play"), 
    ("play some pop music", "search_and_play"),  
    ("canım sıkıldı bir şarkı çal", "search_and_play"),  
    ("i feel bad play a song", "search_and_play"),
]

# Tüm intent sınıfları
INTENTS = [
    "play",
    "pause",
    "next",
    "previous",
    "volume_up",
    "volume_down",
    "current_track",
    "search_and_play",
]
