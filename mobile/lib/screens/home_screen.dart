// lib/screens/home_screen.dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:record/record.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:path_provider/path_provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../services/api_service.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with SingleTickerProviderStateMixin {
  final ApiService _api = ApiService();
  final AudioRecorder _recorder = AudioRecorder();

  bool _isListening = false;
  bool _isProcessing = false;
  bool _isConnected = false;

  String _statusText = "Spotify'a bağlanın ve dinlemeyi başlatın";
  String _recognizedText = '';
  String _currentTrack = '';
  String _currentArtist = '';
  String _lastIntent = '';

  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    _checkStatus();
  }

  @override
  void dispose() {
    _isListening = false;
    _pulseController.dispose();
    _recorder.dispose();
    super.dispose();
  }

  Future<void> _checkStatus() async {
    try {
      final status = await _api.getCurrentStatus();
      setState(() {
        _isConnected = true;
        final track = status['track']?['data'];
        if (track != null) {
          _currentTrack = track['name'] ?? '';
          _currentArtist = track['artist'] ?? '';
          _statusText = 'Bağlandı — dinlemeyi başlatın';
        } else {
          _statusText = "Bağlandı — Spotify'da bir şarkı açın";
        }
      });
    } catch (e) {
      setState(() {
        _isConnected = false;
        _statusText = "Spotify'a bağlanın";
      });
    }
  }

  Future<void> _connectSpotify() async {
    try {
      final authUrl = await _api.getSpotifyLoginUrl();
      if (await canLaunchUrl(Uri.parse(authUrl))) {
        await launchUrl(Uri.parse(authUrl), mode: LaunchMode.externalApplication);
      }
    } catch (e) {
      _showSnackBar('Bağlantı hatası: $e');
    }
  }

  Future<void> _toggleListening() async {
    if (_isListening) {
      // Dinlemeyi durdur
      setState(() {
        _isListening = false;
        _statusText = 'Dinleme durduruldu';
      });
      _pulseController.stop();
      _pulseController.reset();
      // Kayıt devam ediyorsa durdur
      if (await _recorder.isRecording()) {
        await _recorder.stop();
      }
    } else {
      // Dinlemeye başla
      final micStatus = await Permission.microphone.request();
      if (!micStatus.isGranted) {
        _showSnackBar('Mikrofon izni gerekli!');
        return;
      }
      setState(() {
        _isListening = true;
        _statusText = 'Dinleniyor...';
      });
      _pulseController.repeat(reverse: true);
      _listenLoop();
    }
  }

  Future<void> _listenLoop() async {
    while (_isListening) {
      try {
        final dir = await getTemporaryDirectory();
        final filePath = '${dir.path}/voice_command_${DateTime.now().millisecondsSinceEpoch}.wav';

        // 3 saniye kaydet
        await _recorder.start(
          RecordConfig(
            encoder: AudioEncoder.wav,
            sampleRate: 16000,
            numChannels: 1,
            bitRate: 256000,
          ),
          path: filePath,
        );

        await Future.delayed(const Duration(seconds: 3));

        // Dinleme kapatıldıysa çık
        if (!_isListening) {
          if (await _recorder.isRecording()) {
            await _recorder.stop();
          }
          break;
        }

        final path = await _recorder.stop();
        if (path == null) continue;

        // İşleniyor göster ama dinlemeye devam et
        setState(() {
          _isProcessing = true;
        });

        final result = await _api.sendVoiceCommand(path);

        final recognizedText = result['recognized_text'] ?? '';
        final intent = result['intent'] ?? '';
        final success = result['result']?['success'] ?? false;

        // Boş veya anlaşılamayan komutları atla
        if (recognizedText.isNotEmpty && intent != 'unknown') {
          setState(() {
            _recognizedText = recognizedText;
            _lastIntent = intent;
            _statusText = success ? 'Komut çalıştırıldı!' : (result['result']?['message'] ?? 'Hata');
          });
          _checkStatus(); // Şarkı bilgisini güncelle
        }

        setState(() {
          _isProcessing = false;
        });

      } catch (e) {
        setState(() {
          _isProcessing = false;
          _statusText = 'Dinleniyor...';
        });
        // Kısa bekle ve tekrar dene
        await Future.delayed(const Duration(milliseconds: 500));
      }
    }
  }

  void _showSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  String _intentToTurkish(String intent) {
    const map = {
      'play': 'Çal',
      'pause': 'Duraklat',
      'next': 'Sonraki',
      'previous': 'Önceki',
      'volume_up': 'Sesi Aç',
      'volume_down': 'Sesi Kıs',
      'volume_set': 'Ses Ayarla',
      'current_track': 'Şarkı Bilgisi',
      'unknown': 'Anlaşılamadı',
    };
    return map[intent] ?? intent;
  }

  @override
  Widget build(BuildContext context) {
    final green = Theme.of(context).colorScheme.primary;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Spotify Voice Controller'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          IconButton(
            icon: Icon(
              _isConnected ? Icons.link : Icons.link_off,
              color: _isConnected ? green : Colors.grey,
            ),
            onPressed: _isConnected ? _checkStatus : _connectSpotify,
            tooltip: _isConnected ? 'Durumu güncelle' : "Spotify'a bağlan",
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 20),

            // Şu an çalan şarkı
            if (_currentTrack.isNotEmpty) ...[
              Icon(Icons.music_note, color: green, size: 32),
              const SizedBox(height: 8),
              Text(
                _currentTrack,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
                textAlign: TextAlign.center,
              ),
              Text(
                _currentArtist,
                style: TextStyle(fontSize: 16, color: Colors.grey[400]),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 20),
            ],

            // Durum mesajı
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Text(
                _statusText,
                style: TextStyle(fontSize: 16, color: Colors.grey[300]),
                textAlign: TextAlign.center,
              ),
            ),

            const SizedBox(height: 12),

            // İşleniyor göstergesi
            if (_isProcessing)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: SizedBox(
                  width: 24,
                  height: 24,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: green,
                  ),
                ),
              ),

            // Tanınan metin ve intent
            if (_recognizedText.isNotEmpty) ...[
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 32),
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.05),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  children: [
                    Text(
                      '"$_recognizedText"',
                      style: const TextStyle(
                        fontSize: 16,
                        fontStyle: FontStyle.italic,
                        color: Colors.white70,
                      ),
                    ),
                    if (_lastIntent.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Chip(
                        label: Text(_intentToTurkish(_lastIntent)),
                        backgroundColor: green.withValues(alpha: 0.2),
                        labelStyle: TextStyle(color: green),
                      ),
                    ],
                  ],
                ),
              ),
            ],

            const Spacer(),

            // Büyük Start/Stop butonu
            GestureDetector(
              onTap: _isConnected ? _toggleListening : null,
              child: AnimatedBuilder(
                animation: _pulseController,
                builder: (context, child) {
                  final scale = _isListening ? 1.0 + (_pulseController.value * 0.15) : 1.0;
                  return Transform.scale(
                    scale: scale,
                    child: Container(
                      width: 120,
                      height: 120,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: _isListening
                            ? Colors.red
                            : _isConnected
                                ? green.withValues(alpha: 0.2)
                                : Colors.grey[800],
                        boxShadow: _isListening
                            ? [
                                BoxShadow(
                                  color: Colors.red.withValues(alpha: 0.4),
                                  blurRadius: 30,
                                  spreadRadius: 5,
                                ),
                              ]
                            : null,
                      ),
                      child: Icon(
                        _isListening ? Icons.stop : Icons.mic,
                        size: 48,
                        color: Colors.white,
                      ),
                    ),
                  );
                },
              ),
            ),

            const SizedBox(height: 16),
            Text(
              _isListening
                  ? 'Durdurmak için dokunun'
                  : _isConnected
                      ? 'Dinlemeyi başlatmak için dokunun'
                      : "Önce Spotify'a bağlanın →",
              style: TextStyle(color: Colors.grey[500], fontSize: 14),
            ),

            // Spotify'a bağlan butonu
            if (!_isConnected) ...[
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: _connectSpotify,
                icon: const Icon(Icons.login),
                label: const Text("Spotify'a Bağlan"),
                style: ElevatedButton.styleFrom(
                  backgroundColor: green,
                  foregroundColor: Colors.black,
                  padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 14),
                ),
              ),
            ],

            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }
}
