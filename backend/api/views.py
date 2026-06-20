# api/views.py
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status


from .speech_service import transcribe_audio
from .intent_parser import parse_intent
from .spotify_client import (
    SpotifyClient,
    get_auth_url,
    exchange_code_for_token,
)

# Basitlik için token'ları bellekte tutuyoruz.
# Production'da veritabanı veya Redis kullanılmalı.
_tokens = {}


@api_view(["GET"])
def spotify_login(request):
    """Spotify OAuth akışını başlatır."""
    return Response({"auth_url": get_auth_url()})


@api_view(["GET"])
def spotify_callback(request):
    """Spotify OAuth callback — code'u token ile değiştirir."""
    code = request.GET.get("code")
    error = request.GET.get("error")

    if error:
        return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

    if not code:
        return Response(
            {"error": "Code parametresi eksik."}, status=status.HTTP_400_BAD_REQUEST
        )

    token_data = exchange_code_for_token(code)

    if "access_token" in token_data:
        _tokens["access_token"] = token_data["access_token"]
        _tokens["refresh_token"] = token_data.get("refresh_token")
        return Response({
            "success": True,
            "message": "Spotify bağlantısı başarılı!",
        })

    return Response(
        {"error": "Token alınamadı.", "details": token_data},
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["POST"])
@parser_classes([MultiPartParser])
def voice_command(request):
    """
    Ana endpoint: Ses dosyası alır, metne çevirir, komutu çalıştırır.

    Beklenen: multipart/form-data ile 'audio' dosyası
    """
    audio_file = request.FILES.get("audio")
    if not audio_file:
        return Response(
            {"error": "Ses dosyası gönderilmedi."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Token kontrolü
    access_token = _tokens.get("access_token")
    if not access_token:
        return Response(
            {"error": "Spotify bağlantısı yok. Önce /api/spotify/login/ ile giriş yapın."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # 1. Ses → Metin (Azure STT)
    audio_bytes = audio_file.read()
    stt_result = transcribe_audio(audio_bytes)

    if not stt_result["success"]:
        return Response({
            "step": "speech_to_text",
            "error": stt_result.get("error", "STT başarısız."),
        }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    recognized_text = stt_result["text"]

    # 2. Metin → Intent (NLP)
    intent_result = parse_intent(recognized_text)
    intent = intent_result["intent"]
    params = intent_result["params"]

    # 3. Intent → Spotify API çağrısı
    spotify = SpotifyClient(access_token)
    action_result = execute_intent(spotify, intent, params)

    return Response({
        "recognized_text": recognized_text,
        "language": stt_result.get("language"),
        "intent": intent,
        "params": params,
        "result": action_result,
    })


@api_view(["POST"])
def text_command(request):
    """
    Test endpoint: Doğrudan metin komutu gönder (ses kaydı olmadan test için).
    """
    text = request.data.get("text", "")
    if not text:
        return Response(
            {"error": "Metin gönderilmedi."}, status=status.HTTP_400_BAD_REQUEST
        )

    access_token = _tokens.get("access_token")
    if not access_token:
        return Response(
            {"error": "Spotify bağlantısı yok."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    intent_result = parse_intent(text)
    spotify = SpotifyClient(access_token)
    action_result = execute_intent(spotify, intent_result["intent"], intent_result["params"])

    return Response({
        "recognized_text": text,
        "intent": intent_result["intent"],
        "params": intent_result["params"],
        "result": action_result,
    })


@api_view(["GET"])
def current_status(request):
    """Spotify'daki mevcut durumu döndürür."""
    access_token = _tokens.get("access_token")
    if not access_token:
        return Response(
            {"error": "Spotify bağlantısı yok."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    spotify = SpotifyClient(access_token)
    track = spotify.current_track()
    playback = spotify.get_playback_state()

    return Response({"track": track, "playback": playback})


# ---------- Yardımcı ----------

def execute_intent(spotify: SpotifyClient, intent: str, params: dict) -> dict:
    """Intent'e göre Spotify API çağrısı yapar."""
    actions = {
        "play": spotify.play,
        "pause": spotify.pause,
        "next": spotify.next_track,
        "previous": spotify.previous_track,
        "volume_up": lambda: _adjust_volume(spotify, +15),
        "volume_down": lambda: _adjust_volume(spotify, -15),
        "volume_set": lambda: spotify.set_volume(params.get("volume", 50)),
        "current_track": spotify.current_track,
    }

    action = actions.get(intent)
    if action:
        return action()

    return {"success": False, "message": f"Anlaşılamayan komut: {params.get('original_text', '')}"}


def _adjust_volume(spotify: SpotifyClient, delta: int) -> dict:
    """Mevcut sese göre artırma/azaltma yapar."""
    state = spotify.get_playback_state()
    if state["success"] and state["data"]:
        current = state["data"].get("volume", 50)
        new_vol = max(0, min(100, current + delta))
        return spotify.set_volume(new_vol)
    return {"success": False, "message": "Ses seviyesi alınamadı."}
