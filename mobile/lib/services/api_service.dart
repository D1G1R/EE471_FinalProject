// lib/services/api_service.dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  // Emülatör kullanıyorsan 10.0.2.2, fiziksel cihaz için PC'nin local IP adresini yaz
  static const String baseUrl = 'http://192.168.1.101:8000/api';

  /// Ses dosyasını backend'e gönder, komutu çalıştır
  Future<Map<String, dynamic>> sendVoiceCommand(String filePath) async {
    final uri = Uri.parse('$baseUrl/voice-command/');
    final request = http.MultipartRequest('POST', uri);

    request.files.add(
      await http.MultipartFile.fromPath('audio', filePath),
    );

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Hata: ${response.statusCode} - ${response.body}');
    }
  }

  /// Metin komutu gönder (test amaçlı)
  Future<Map<String, dynamic>> sendTextCommand(String text) async {
    final uri = Uri.parse('$baseUrl/text-command/');
    final response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'text': text}),
    );

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Hata: ${response.statusCode} - ${response.body}');
    }
  }

  /// Spotify login URL'ini al
  Future<String> getSpotifyLoginUrl() async {
    final uri = Uri.parse('$baseUrl/spotify/login/');
    final response = await http.get(uri);

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return data['auth_url'];
    } else {
      throw Exception('Login URL alınamadı.');
    }
  }

  /// Mevcut çalan şarkı bilgisi
  Future<Map<String, dynamic>> getCurrentStatus() async {
    final uri = Uri.parse('$baseUrl/status/');
    final response = await http.get(uri);

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Durum alınamadı: ${response.statusCode}');
    }
  }
}
