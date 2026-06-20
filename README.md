# Spotify Voice Controller

Monorepo structure for a Spotify voice control project.

## Structure

```text
spotify-voice-controller/
├── backend/                  # Django project
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   ├── manage.py
│   └── voice_controller/
│       ├── settings.py
│       ├── urls.py
│       └── api/
│           ├── views.py
│           ├── urls.py
│           ├── spotify_client.py
│           ├── speech_service.py
│           └── intent_parser.py
├── mobile/                   # Flutter project placeholder
├── .github/
│   └── workflows/
│       └── ci.yml
└── README.md
```

## Backend

The backend is prepared as a Django skeleton with placeholder API modules for Spotify integration, speech processing, and intent parsing.

## Mobile

Run `flutter create mobile` inside the `mobile/` folder when you are ready to scaffold the Flutter app.
