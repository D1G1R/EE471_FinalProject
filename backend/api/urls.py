# api/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("spotify/login/", views.spotify_login, name="spotify-login"),
    path("spotify/callback/", views.spotify_callback, name="spotify-callback"),
    path("voice-command/", views.voice_command, name="voice-command"),
    path("text-command/", views.text_command, name="text-command"),
    path("status/", views.current_status, name="current-status"),
]
