# api/speech_service.py
import os
import struct
import wave
import io
import tempfile
import azure.cognitiveservices.speech as speechsdk


def is_silent(audio_bytes: bytes, threshold: float = 300.0) -> bool:
    """Ses verisinin sessiz olup olmadığını kontrol eder."""
    try:
        with wave.open(io.BytesIO(audio_bytes), 'rb') as wf:
            frames = wf.readframes(wf.getnframes())
            if len(frames) < 2:
                return True
            samples = struct.unpack(f"{len(frames)//2}h", frames)
            rms = (sum(s**2 for s in samples) / len(samples)) ** 0.5
            return rms < threshold
    except Exception:
        return False


def transcribe_audio(audio_bytes: bytes, sample_rate: int = 16000) -> dict:
    """
    Gelen ses verisini Azure Speech-to-Text ile metne çevirir.

    audio_bytes: WAV formatında ses verisi
    Dönüş: {"success": bool, "text": str, "language": str}
    """
    # Sessizlik kontrolü — Azure'a gönderme
    if is_silent(audio_bytes):
        return {"success": False, "text": "", "error": "Sessizlik algılandı."}

    speech_key = os.getenv("AZURE_SPEECH_KEY")
    speech_region = os.getenv("AZURE_SPEECH_REGION")

    if not speech_key or not speech_region:
        return {"success": False, "text": "", "error": "Azure Speech ayarları eksik."}

    # Ham PCM ise WAV başlığı ekle (tempfile hâlâ açıkken aynı yola yazma hatasından kaçın)
    if audio_bytes[:4] != b"RIFF":
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_bytes)
        wav_bytes = buf.getvalue()
    else:
        wav_bytes = audio_bytes

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name

    try:
        speech_config = speechsdk.SpeechConfig(
            subscription=speech_key, region=speech_region
        )
        auto_detect_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(
            languages=["tr-TR", "en-US"]
        )

        audio_config = speechsdk.audio.AudioConfig(filename=tmp_path)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            auto_detect_source_language_config=auto_detect_config,
            audio_config=audio_config,
        )

        result = recognizer.recognize_once()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            lang_result = speechsdk.AutoDetectSourceLanguageResult(result)
            return {
                "success": True,
                "text": result.text,
                "language": lang_result.language,
            }
        elif result.reason == speechsdk.ResultReason.NoMatch:
            return {"success": False, "text": "", "error": "Ses anlaşılamadı."}
        else:
            return {
                "success": False,
                "text": "",
                "error": f"Hata: {result.reason}",
            }
    finally:
        try:
            os.unlink(tmp_path)
        except PermissionError:
            pass
