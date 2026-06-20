# api/speech_service.py
import os
import azure.cognitiveservices.speech as speechsdk
import tempfile
import wave


def transcribe_audio(audio_bytes: bytes, sample_rate: int = 16000) -> dict:
    """
    Gelen ses verisini Azure Speech-to-Text ile metne çevirir.

    audio_bytes: WAV formatında ses verisi
    Dönüş: {"success": bool, "text": str, "language": str}
    """
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    speech_region = os.getenv("AZURE_SPEECH_REGION")

    if not speech_key or not speech_region:
        return {"success": False, "text": "", "error": "Azure Speech ayarları eksik."}

    # Geçici WAV dosyası oluştur
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
        # Eğer gelen veri ham PCM ise WAV header ekle
        if not audio_bytes[:4] == b"RIFF":
            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes(audio_bytes)
        else:
            tmp.write(audio_bytes)

    try:
        speech_config = speechsdk.SpeechConfig(
            subscription=speech_key, region=speech_region
        )
        # Türkçe ve İngilizce otomatik algılama
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
            pass  # Windows'ta dosya meşgul olabilir, sorun değil
        