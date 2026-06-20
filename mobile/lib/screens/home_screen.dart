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

  bool _isRecording = false;
  bool _isProcessing = false;
  bool _isConnected = false;

  String _statusText = 'Spotify\'a bağlanın ve konuşmaya başlayın';
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
          _statusText = 'Bağlandı — komut vermek için basılı tutun';
        } else {
          _statusText = 'Bağlandı — Spotify\'da bir şarkı açın';
        }
      });
    } catch (e) {
      setState(() {
        _isConnected = false;
        _statusText = 'Spotify\'a bağlanın';
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

  Future<void> _startRecording() async {
    final micStatus = await Permission.microphone.request();
    if (!micStatus.isGranted) {
      _showSnackBar('Mikrofon izni gerekli!');
      return;
    }

    final dir = await getTemporaryDirectory();
    final filePath = '${dir.path}/voice_command.wav';

    await _recorder.start(
      const RecordConfig(
        encoder: AudioEncoder.wav,
        sampleRate: 16000,
        numChannels: 1,
        bitRate: 256000,
      ),
      path: filePath,
    );

    setState(() {
      _isRecording = true;
      _statusText = 'Dinliyorum...';
      _recognizedText = '';
      _lastIntent = '';
    });
    _pulseController.repeat(reverse: true);
  }

  Future<void> _stopRecordingAndProcess() async {
    final path = await _recorder.stop();
    _pulseController.stop();
    _pulseController.reset();

    if (path == null) {
      setState(() {
        _isRecording = false;
        _statusText = 'Kayıt alınamadı.';
      });
      return;
    }

    setState(() {
      _isRecording = false;
      _isProcessing = true;
      _statusText = 'İşleniyor...';
    });

    try {
      final result = await _api.sendVoiceCommand(path);

      setState(() {
        _isProcessing = false;
        _recognizedText = result['recognized_text'] ?? '';
        _lastIntent = result['intent'] ?? '';
        final success = result['result']?['success'] ?? false;
        _statusText = success
            ? 'Komut çalıştırıldı!'
            : result['result']?['message'] ?? 'Bir hata oluştu.';
      });

      // Şarkı bilgisini güncelle
      _checkStatus();
    } catch (e) {
      setState(() {
        _isProcessing = false;
        _statusText = 'Hata: $e';
      });
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
            tooltip: _isConnected ? 'Durumu güncelle' : 'Spotify\'a bağlan',
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

            // Tanınan metin ve intent
            if (_recognizedText.isNotEmpty) ...[
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 32),
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.05),
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
                        backgroundColor: green.withOpacity(0.2),
                        labelStyle: TextStyle(color: green),
                      ),
                    ],
                  ],
                ),
              ),
            ],

            const Spacer(),

            // Büyük mikrofon butonu
            GestureDetector(
              onLongPressStart: _isConnected && !_isProcessing
                  ? (_) => _startRecording()
                  : null,
              onLongPressEnd: _isRecording ? (_) => _stopRecordingAndProcess() : null,
              child: AnimatedBuilder(
                animation: _pulseController,
                builder: (context, child) {
                  final scale = _isRecording ? 1.0 + (_pulseController.value * 0.15) : 1.0;
                  return Transform.scale(
                    scale: scale,
                    child: Container(
                      width: 120,
                      height: 120,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: _isRecording
                            ? green
                            : _isProcessing
                                ? Colors.orange
                                : _isConnected
                                    ? green.withOpacity(0.2)
                                    : Colors.grey[800],
                        boxShadow: _isRecording
                            ? [
                                BoxShadow(
                                  color: green.withOpacity(0.4),
                                  blurRadius: 30,
                                  spreadRadius: 5,
                                ),
                              ]
                            : null,
                      ),
                      child: Icon(
                        _isRecording
                            ? Icons.mic
                            : _isProcessing
                                ? Icons.hourglass_top
                                : Icons.mic_none,
                        size: 48,
                        color: _isRecording ? Colors.black : Colors.white,
                      ),
                    ),
                  );
                },
              ),
            ),

            const SizedBox(height: 16),
            Text(
              _isConnected
                  ? 'Basılı tutarak komut verin'
                  : 'Önce Spotify\'a bağlanın →',
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