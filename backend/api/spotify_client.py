# api/spotify_client.py
import os
import requests
from urllib.parse import urlencode


SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1"

SCOPES = "user-modify-playback-state user-read-playback-state user-read-currently-playing"

MUSIC_GENRES = {
    "rock", "pop", "jazz", "classical", "hip hop", "rap", "metal",
    "electronic", "dance", "country", "blues", "reggae", "soul",
    "r&b", "indie", "alternative", "folk", "punk", "funk",
    # Türkçe
    "türkçe pop", "türkçe rock", "arabesk", "halk müziği",
}


class SpotifyClient:
    """Spotify Web API ile etkileşim kuran istemci sınıfı."""

    def __init__(self, access_token: str, refresh_token: str = None, on_token_refresh=None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.on_token_refresh = on_token_refresh  # yeni token gelince çağrılır: fn(access_token)
        self._build_headers()

    def _build_headers(self):
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _try_refresh(self) -> bool:
        """Token'ı yenile; başarılıysa True döner."""
        if not self.refresh_token:
            return False
        data = refresh_access_token(self.refresh_token)
        new_token = data.get("access_token")
        if not new_token:
            return False
        self.access_token = new_token
        self._build_headers()
        if self.on_token_refresh:
            self.on_token_refresh(new_token)
        return True

    # ---------- Playback kontrol ----------

    def _request(self, method: str, url: str, **kwargs):
        """İstek gönderir; 401'de bir kez token yenileyip tekrar dener."""
        resp = requests.request(method, url, headers=self.headers, **kwargs)
        if resp.status_code == 401 and self._try_refresh():
            resp = requests.request(method, url, headers=self.headers, **kwargs)
        return resp

    def play(self):
        """Çalmaya devam et."""
        resp = self._request("PUT", f"{SPOTIFY_API_URL}/me/player/play")
        return self._handle(resp)

    def pause(self):
        """Duraklat."""
        resp = self._request("PUT", f"{SPOTIFY_API_URL}/me/player/pause")
        return self._handle(resp)

    def next_track(self):
        """Sonraki şarkıya geç."""
        resp = self._request("POST", f"{SPOTIFY_API_URL}/me/player/next")
        return self._handle(resp)

    def previous_track(self):
        """Önceki şarkıya dön."""
        resp = self._request("POST", f"{SPOTIFY_API_URL}/me/player/previous")
        return self._handle(resp)

    def set_volume(self, volume_percent: int):
        """Ses seviyesini ayarla (0-100)."""
        volume_percent = max(0, min(100, volume_percent))
        resp = self._request(
            "PUT",
            f"{SPOTIFY_API_URL}/me/player/volume",
            params={"volume_percent": volume_percent},
        )
        return self._handle(resp)

    def current_track(self):
        """Şu an çalan şarkı bilgisini döndür."""
        resp = self._request("GET", f"{SPOTIFY_API_URL}/me/player/currently-playing")
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
        resp = self._request("GET", f"{SPOTIFY_API_URL}/me/player")
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

    def search_and_play(self, query: str):
        """Önce sanatçı arar, bulamazsa şarkı arar."""
        query_lower = query.lower().strip()

        # Tür mü kontrol et
        if query_lower in MUSIC_GENRES:
            return self._play_genre(query_lower)

        # 1. Önce sanatçı ara
        artist_result = self._search_artist(query)
        if artist_result["success"]:
            return artist_result

        # 2. Sanatçı bulunamadıysa şarkı ara
        return self._search_track(query)

    def _search_artist(self, query: str):
        """Sanatçı arar ve bulursa sanatçının müziğini çalar."""
        resp = self._request(
            "GET",
            f"{SPOTIFY_API_URL}/search",
            params={"q": query, "type": "artist", "limit": 3},
        )

        if resp.status_code != 200:
            return {"success": False, "message": f"Arama hatası: {resp.status_code}"}

        items = resp.json().get("artists", {}).get("items", [])
        if not items:
            return {"success": False, "message": "Sanatçı bulunamadı."}

        # En alakalı sanatçıyı bul — isim benzerliği kontrol et
        best_match = None
        for artist in items:
            if artist["name"].lower() == query.lower():
                best_match = artist
                break
        if not best_match:
            # Tam eşleşme yoksa ilk sonucu al ama popülerlik kontrolü yap
            if items[0].get("popularity", 0) > 20:
                best_match = items[0]

        if not best_match:
            return {"success": False, "message": "Sanatçı bulunamadı."}

        artist_uri = best_match["uri"]
        artist_name = best_match["name"]

        # Sanatçının müziğini çal (context olarak)
        play_resp = self._request(
            "PUT",
            f"{SPOTIFY_API_URL}/me/player/play",
            json={"context_uri": artist_uri},
        )

        if play_resp.status_code in (200, 204):
            return {
                "success": True,
                "message": f"Çalınıyor: {artist_name}",
                "data": {"artist": artist_name},
            }
        return {"success": False, "message": f"Sanatçı bulundu ama çalınamadı: {play_resp.status_code}"}

    def _search_track(self, query: str):
        """Şarkı arar ve ilk sonucu çalar."""
        resp = self._request(
            "GET",
            f"{SPOTIFY_API_URL}/search",
            params={"q": query, "type": "track", "limit": 1},
        )

        if resp.status_code != 200:
            return {"success": False, "message": f"Arama hatası: {resp.status_code}"}

        items = resp.json().get("tracks", {}).get("items", [])
        if not items:
            return {"success": False, "message": f"'{query}' bulunamadı."}

        track = items[0]
        track_uri = track["uri"]
        track_name = track["name"]
        artist_name = ", ".join(a["name"] for a in track["artists"])

        play_resp = self._request(
            "PUT",
            f"{SPOTIFY_API_URL}/me/player/play",
            json={"uris": [track_uri]},
        )

        if play_resp.status_code in (200, 204):
            return {
                "success": True,
                "message": f"Çalınıyor: {track_name} - {artist_name}",
                "data": {"name": track_name, "artist": artist_name},
            }
        return {"success": False, "message": f"Şarkı bulundu ama çalınamadı: {play_resp.status_code}"}

    def _play_genre(self, genre: str):
        """Tür bazlı öneri çalar."""
        resp = self._request(
            "GET",
            f"{SPOTIFY_API_URL}/recommendations",
            params={"seed_genres": genre.replace(" ", "-"), "limit": 1},
        )

        if resp.status_code == 200:
            tracks = resp.json().get("tracks", [])
            if tracks:
                track = tracks[0]
                play_resp = self._request(
                    "PUT",
                    f"{SPOTIFY_API_URL}/me/player/play",
                    json={"uris": [track["uri"]]},
                )
                if play_resp.status_code in (200, 204):
                    artist_name = ", ".join(a["name"] for a in track["artists"])
                    return {
                        "success": True,
                        "message": f"Çalınıyor ({genre}): {track['name']} - {artist_name}",
                        "data": {"name": track["name"], "artist": artist_name},
                    }

        return self._search_track(genre)

    # ---------- Yardımcı ----------

    def _handle(self, resp):
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
