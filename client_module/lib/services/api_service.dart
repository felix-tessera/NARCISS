import 'package:dio/dio.dart';

final dio = Dio();

Future<String> getBalance() async {
  final response = await dio.get('http://192.168.167.226:8000/api/balance');
  print("Баланс:" + response.data);
  return response.data;
}
