# api/spotify_client.py
import os
import requests
from urllib.parse import urlencode


SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1"

SCOPES = "user-modify-playback-state user-read-playback-state user-read-currently-playing"


class SpotifyClient:
    """Spotify Web API ile etkileşim kuran istemci sınıfı."""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    # ---------- Playback kontrol ----------

    def play(self):
        """Çalmaya devam et."""
        resp = requests.put(f"{SPOTIFY_API_URL}/me/player/play", headers=self.headers)
        return self._handle(resp)

    def pause(self):
        """Duraklat."""
        resp = requests.put(f"{SPOTIFY_API_URL}/me/player/pause", headers=self.headers)
        return self._handle(resp)

    def next_track(self):
        """Sonraki şarkıya geç."""
        resp = requests.post(f"{SPOTIFY_API_URL}/me/player/next", headers=self.headers)
        return self._handle(resp)

    def previous_track(self):
        """Önceki şarkıya dön."""
        resp = requests.post(f"{SPOTIFY_API_URL}/me/player/previous", headers=self.headers)
        return self._handle(resp)

    def set_volume(self, volume_percent: int):
        """Ses seviyesini ayarla (0-100)."""
        volume_percent = max(0, min(100, volume_percent))
        resp = requests.put(
            f"{SPOTIFY_API_URL}/me/player/volume",
            headers=self.headers,
            params={"volume_percent": volume_percent},
        )
        return self._handle(resp)

    def current_track(self):
        """Şu an çalan şarkı bilgisini döndür."""
        resp = requests.get(
            f"{SPOTIFY_API_URL}/me/player/currently-playing", headers=self.headers
        )
        if resp.status_code == 204:
            return {"success": True, "data": None, "message": "Şu an bir şey çalmıyor."}
        if resp.status_code == 200:
            data = resp.json()
            track = data.get("item", {})
            return {
                "success": True,
                "data": {
                    "name": track.get("name"),
                    "artist": ", ".join(
                        a["name"] for a in track.get("artists", [])
                    ),
                    "album": track.get("album", {}).get("name"),
                    "is_playing": data.get("is_playing"),
                },
            }
        return {"success": False, "message": f"Hata: {resp.status_code}"}

    def get_playback_state(self):
        """Mevcut playback durumunu döndür (volume dahil)."""
        resp = requests.get(f"{SPOTIFY_API_URL}/me/player", headers=self.headers)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "success": True,
                "data": {
                    "volume": data.get("device", {}).get("volume_percent"),
                    "is_playing": data.get("is_playing"),
                    "device_name": data.get("device", {}).get("name"),
                },
            }
        if resp.status_code == 204:
            return {"success": True, "data": None, "message": "Aktif cihaz yok."}
        return {"success": False, "message": f"Hata: {resp.status_code}"}

    # ---------- Yardımcı ----------

    @staticmethod
    def _handle(resp):
        if resp.status_code in (200, 204):
            return {"success": True}
        return {"success": False, "message": f"Spotify hatası: {resp.status_code} - {resp.text}"}


# ---------- OAuth yardımcıları ----------

def get_auth_url():
    """Kullanıcıyı yönlendireceğimiz Spotify OAuth URL'ini oluşturur."""
    params = {
        "client_id": os.getenv("SPOTIFY_CLIENT_ID"),
        "response_type": "code",
        "redirect_uri": os.getenv("SPOTIFY_REDIRECT_URI"),
        "scope": SCOPES,
        "show_dialog": "true",
    }
    return f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(code: str):
    """Authorization code'u access token ile değiştirir."""
    resp = requests.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": os.getenv("SPOTIFY_REDIRECT_URI"),
            "client_id": os.getenv("SPOTIFY_CLIENT_ID"),
            "client_secret": os.getenv("SPOTIFY_CLIENT_SECRET"),
        },
    )
    return resp.json()


def refresh_access_token(refresh_token: str):
    """Refresh token kullanarak yeni access token alır."""
    resp = requests.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": os.getenv("SPOTIFY_CLIENT_ID"),
            "client_secret": os.getenv("SPOTIFY_CLIENT_SECRET"),
        },
    )
    return resp.json()
