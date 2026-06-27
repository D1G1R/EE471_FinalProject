// lib/screens/home_screen.dart
import 'dart:io';
import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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

class _HomeScreenState extends State<HomeScreen> with TickerProviderStateMixin {
  final ApiService _api = ApiService();
  final AudioRecorder _recorder = AudioRecorder();

  bool _isListening = false;
  bool _isProcessing = false;
  bool _isConnected = false;
  bool _isButtonPressed = false;

  String _statusText = "Spotify'a bağlanın ve dinlemeyi başlatın";
  String _recognizedText = '';
  String _currentTrack = '';
  String _currentArtist = '';
  String _lastIntent = '';

  // Animasyon controller'ları
  late AnimationController _pulseController;
  late AnimationController _waveController;
  late AnimationController _buttonScaleController;
  late AnimationController _successController;

  late Animation<double> _buttonScaleAnimation;
  late Animation<double> _successAnimation;

  @override
  void initState() {
    super.initState();

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );

    _waveController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    );

    _buttonScaleController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 150),
    );
    _buttonScaleAnimation = Tween<double>(begin: 1.0, end: 0.88).animate(
      CurvedAnimation(parent: _buttonScaleController, curve: Curves.easeInOut),
    );

    _successController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );
    _successAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _successController, curve: Curves.elasticOut),
    );

    _checkStatus();
  }

  @override
  void dispose() {
    _isListening = false;
    _pulseController.dispose();
    _waveController.dispose();
    _buttonScaleController.dispose();
    _successController.dispose();
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
    // Buton basma animasyonu
    _buttonScaleController.forward().then((_) {
      _buttonScaleController.reverse();
    });
    HapticFeedback.mediumImpact();

    if (_isListening) {
      setState(() {
        _isListening = false;
        _statusText = 'Dinleme durduruldu';
      });
      _pulseController.stop();
      _pulseController.reset();
      _waveController.stop();
      _waveController.reset();
      if (await _recorder.isRecording()) {
        await _recorder.stop();
      }
    } else {
      final micStatus = await Permission.microphone.request();
      if (!micStatus.isGranted) {
        _showSnackBar('Mikrofon izni gerekli!');
        return;
      }
      setState(() {
        _isListening = true;
        _statusText = 'Dinleniyor...';
        _recognizedText = '';
        _lastIntent = '';
      });
      _pulseController.repeat(reverse: true);
      _waveController.repeat();
      _listenLoop();
    }
  }

  Future<void> _listenLoop() async {
    while (_isListening) {
      try {
        // 1. ADIM: Sessizce dinle, ses gelene kadar bekle
        setState(() => _statusText = 'Dinleniyor... (komut bekleniyor)');

        final dir = await getTemporaryDirectory();
        final filePath = '${dir.path}/voice_${DateTime.now().millisecondsSinceEpoch}.wav';

        // Kaydı başlat
        await _recorder.start(
          RecordConfig(
            encoder: AudioEncoder.wav,
            sampleRate: 16000,
            numChannels: 1,
            bitRate: 256000,
          ),
          path: filePath,
        );

        // Ses seviyesini izle — konuşma başlayana kadar bekle
        bool speechStarted = false;
        int consecutiveSpeechFrames = 0;
        int silenceAfterSpeech = 0;
        const double speechThreshold = -20.0; // dB, bunun üstü konuşma (daha az hassas)
        const int speechConfirmFrames = 3;     // 3 ardışık frame gerekli (sahte tetiklenmeyi önler)
        const int silenceLimit = 6;            // 6 × 300ms = ~1.8 saniye sessizlik

        while (_isListening) {
          final amp = await _recorder.getAmplitude();
          final double dbLevel = amp.current;

          if (!speechStarted) {
            // Henüz konuşma başlamadı — ses gelene kadar bekle
            if (dbLevel > speechThreshold) {
              consecutiveSpeechFrames++;
              if (consecutiveSpeechFrames >= speechConfirmFrames) {
                speechStarted = true;
                silenceAfterSpeech = 0;
                setState(() => _statusText = 'Konuşma algılandı...');
              }
            } else {
              consecutiveSpeechFrames = 0; // ardışıklığı sıfırla
            }
          } else {
            // Konuşma başlamış — sessizlik sayacı
            if (dbLevel > speechThreshold) {
              silenceAfterSpeech = 0; // hâlâ konuşuyor, sıfırla
            } else {
              silenceAfterSpeech++;
              if (silenceAfterSpeech >= silenceLimit) {
                // Yeterince sessizlik oldu, konuşma bitti
                break;
              }
            }
          }

          // 30 saniye boyunca hiç konuşma yoksa döngüyü yenile
          await Future.delayed(const Duration(milliseconds: 300));
        }

        if (!_isListening) {
          if (await _recorder.isRecording()) await _recorder.stop();
          break;
        }

        final path = await _recorder.stop();
        if (path == null) continue;

        // Konuşma algılanmadıysa dosyayı atla
        if (!speechStarted) continue;

        // Dosya boyutu kontrolü
        final file = File(path);
        final fileSize = await file.length();
        if (fileSize < 30000) continue;

        // Backend'e gönder
        setState(() {
          _isProcessing = true;
          _statusText = 'İşleniyor...';
        });

        final result = await _api.sendVoiceCommand(path);

        final recognizedText = result['recognized_text'] ?? '';
        final intent = result['intent'] ?? '';
        final success = result['result']?['success'] ?? false;

        if (recognizedText.isNotEmpty && intent != 'unknown') {
          setState(() {
            _recognizedText = recognizedText;
            _lastIntent = intent;
            _statusText = success
                ? 'Komut çalıştırıldı!'
                : (result['result']?['message'] ?? 'Hata');
          });

          if (success) {
            _successController.forward(from: 0);
            HapticFeedback.lightImpact();
          }

          _checkStatus();
        }

        setState(() => _isProcessing = false);

      } catch (e) {
        setState(() {
          _isProcessing = false;
          _statusText = 'Dinleniyor...';
        });
        await Future.delayed(const Duration(milliseconds: 500));
      }
    }
  }

  void _showSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );
  }

  String _intentToTurkish(String intent) {
    const map = {
      'play': '▶ Çal',
      'pause': '⏸ Duraklat',
      'next': '⏭ Sonraki',
      'previous': '⏮ Önceki',
      'volume_up': '🔊 Sesi Aç',
      'volume_down': '🔉 Sesi Kıs',
      'volume_set': '🔈 Ses Ayarla',
      'current_track': '🎵 Şarkı Bilgisi',
      'search_and_play': '🔍 Şarkı Ara & Çal',
      'unknown': '❓ Anlaşılamadı',
    };
    return map[intent] ?? intent;
  }

  @override
  Widget build(BuildContext context) {
    const green = Color(0xFF1DB954);

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Spotify Voice Controller',
          style: TextStyle(fontWeight: FontWeight.w600, letterSpacing: 0.5),
        ),
        centerTitle: true,
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
        child: Center(
          child: Column(
            children: [
              const SizedBox(height: 24),

              // Şu an çalan şarkı
              if (_currentTrack.isNotEmpty)
                _buildNowPlaying(green),

              // Durum mesajı
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 8),
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 300),
                  child: Text(
                    _statusText,
                    key: ValueKey(_statusText),
                    style: TextStyle(fontSize: 15, color: Colors.grey[400]),
                    textAlign: TextAlign.center,
                  ),
                ),
              ),

              // İşleniyor göstergesi
              AnimatedOpacity(
                opacity: _isProcessing ? 1.0 : 0.0,
                duration: const Duration(milliseconds: 200),
                child: Padding(
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
              ),

              // Son komut bilgisi
              if (_recognizedText.isNotEmpty)
                _buildLastCommand(green),

              const Spacer(),

              // Ses dalgası animasyonu
              if (_isListening)
                _buildSoundWaves(green),

              const SizedBox(height: 20),

              // Mikrofon butonu
              _buildMicButton(green),

              const SizedBox(height: 16),

              // Alt yazı
              Text(
                _isListening
                    ? 'Durdurmak için dokunun'
                    : _isConnected
                        ? 'Dinlemeyi başlatmak için dokunun'
                        : "Önce Spotify'a bağlanın",
                style: TextStyle(color: Colors.grey[600], fontSize: 13),
              ),

              // Spotify'a bağlan butonu
              if (!_isConnected) ...[
                const SizedBox(height: 20),
                _buildConnectButton(green),
              ],

              const SizedBox(height: 40),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildNowPlaying(Color green) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 400),
      margin: const EdgeInsets.symmetric(horizontal: 32, vertical: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            green.withValues(alpha: 0.15),
            green.withValues(alpha: 0.05),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: green.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: green.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(Icons.music_note, color: green, size: 28),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _currentTrack,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Text(
                  _currentArtist,
                  style: TextStyle(fontSize: 13, color: Colors.grey[400]),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLastCommand(Color green) {
    return ScaleTransition(
      scale: _successAnimation.drive(Tween(begin: 0.95, end: 1.0)),
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 32, vertical: 8),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        ),
        child: Column(
          children: [
            Text(
              '"$_recognizedText"',
              style: const TextStyle(
                fontSize: 15,
                fontStyle: FontStyle.italic,
                color: Colors.white70,
              ),
              textAlign: TextAlign.center,
            ),
            if (_lastIntent.isNotEmpty) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                decoration: BoxDecoration(
                  color: green.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  _intentToTurkish(_lastIntent),
                  style: TextStyle(color: green, fontSize: 13, fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSoundWaves(Color green) {
    return AnimatedBuilder(
      animation: _waveController,
      builder: (context, child) {
        return SizedBox(
          height: 40,
          width: 200,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(9, (index) {
              final offset = index * 0.12;
              final value = sin((_waveController.value + offset) * 2 * pi);
              final height = 8.0 + (value.abs() * 28);
              return AnimatedContainer(
                duration: const Duration(milliseconds: 100),
                margin: const EdgeInsets.symmetric(horizontal: 2.5),
                width: 4,
                height: height,
                decoration: BoxDecoration(
                  color: green.withValues(alpha: 0.4 + (value.abs() * 0.6)),
                  borderRadius: BorderRadius.circular(4),
                ),
              );
            }),
          ),
        );
      },
    );
  }

  Widget _buildMicButton(Color green) {
    return GestureDetector(
      onTapDown: _isConnected ? (_) {
        setState(() => _isButtonPressed = true);
        _buttonScaleController.forward();
      } : null,
      onTapUp: _isConnected ? (_) {
        setState(() => _isButtonPressed = false);
        _buttonScaleController.reverse();
        _toggleListening();
      } : null,
      onTapCancel: () {
        setState(() => _isButtonPressed = false);
        _buttonScaleController.reverse();
      },
      child: AnimatedBuilder(
        animation: Listenable.merge([_pulseController, _buttonScaleController]),
        builder: (context, child) {
          final pulseScale = _isListening ? 1.0 + (_pulseController.value * 0.08) : 1.0;
          final pressScale = _buttonScaleAnimation.value;
          final totalScale = pulseScale * pressScale;

          return Transform.scale(
            scale: totalScale,
            child: Stack(
              alignment: Alignment.center,
              children: [
                // Dış halka (pulse efekti)
                if (_isListening)
                  AnimatedBuilder(
                    animation: _pulseController,
                    builder: (context, child) {
                      return Container(
                        width: 160 + (_pulseController.value * 20),
                        height: 160 + (_pulseController.value * 20),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: Colors.red.withValues(alpha: 0.3 - (_pulseController.value * 0.3)),
                            width: 2,
                          ),
                        ),
                      );
                    },
                  ),

                // İkinci halka
                if (_isListening)
                  AnimatedBuilder(
                    animation: _pulseController,
                    builder: (context, child) {
                      return Container(
                        width: 140 + (_pulseController.value * 10),
                        height: 140 + (_pulseController.value * 10),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: Colors.red.withValues(alpha: 0.05),
                        ),
                      );
                    },
                  ),

                // Ana buton
                AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  width: 120,
                  height: 120,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: _isListening
                        ? Colors.red
                        : _isConnected
                            ? green
                            : Colors.grey[800],
                    boxShadow: [
                      BoxShadow(
                        color: (_isListening ? Colors.red : green).withValues(
                          alpha: _isButtonPressed ? 0.1 : _isListening ? 0.5 : 0.3,
                        ),
                        blurRadius: _isButtonPressed ? 10 : _isListening ? 30 : 20,
                        spreadRadius: _isButtonPressed ? 0 : _isListening ? 5 : 2,
                      ),
                    ],
                  ),
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 200),
                    transitionBuilder: (child, animation) {
                      return ScaleTransition(scale: animation, child: child);
                    },
                    child: Icon(
                      _isListening ? Icons.stop_rounded : Icons.mic_rounded,
                      key: ValueKey(_isListening),
                      size: 48,
                      color: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildConnectButton(Color green) {
    return ElevatedButton.icon(
      onPressed: _connectSpotify,
      icon: const Icon(Icons.login_rounded),
      label: const Text("Spotify'a Bağlan"),
      style: ElevatedButton.styleFrom(
        backgroundColor: green,
        foregroundColor: Colors.black,
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
        elevation: 4,
        shadowColor: green.withValues(alpha: 0.4),
      ),
    );
  }
}
