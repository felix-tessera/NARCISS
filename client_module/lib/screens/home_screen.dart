import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:client_module/screens/futute_grid_bot_create_screen.dart';
import 'package:client_module/services/api_service.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Column(
          children: [
            Container(
              decoration: const BoxDecoration(color: Color.fromARGB(255, 18, 18, 19),
              borderRadius: BorderRadiusDirectional.only(bottomEnd: Radius.circular(35),
              bottomStart: Radius.circular(35))),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Center(child: Text('NARCISS', style: GoogleFonts.montserrat(textStyle: const TextStyle(
                  fontSize: 36, 
                  fontWeight: FontWeight.bold,
                  color: Color.fromARGB(255, 215, 208, 255),
                  ),)
                  )),
                  Padding(
                    padding: EdgeInsets.only(left: 15, top: 20,),
                    child: Row(
                      children: [
                        Baseline(
                          baseline: 20.0,
                          baselineType: TextBaseline.alphabetic,
                          child: Text('1 412.42', style: GoogleFonts.montserrat(textStyle: 
                          const TextStyle(fontSize: 36, 
                          color: Colors.white, 
                          fontWeight: FontWeight.w600)),),
                        ),
                        const SizedBox(width: 10,),
                        Text('USDT', style: GoogleFonts.montserrat(textStyle: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w500
                        )),)
                      ],
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.only(left: 15, bottom: 15),
                    child: Row(
                      children: [
                        Text('P&L за неделю ', style: GoogleFonts.montserrat(textStyle: 
                        const TextStyle(color: Colors.white, fontSize: 20, 
                        fontWeight: FontWeight.w400)),),
                        Text('+ 123.41', style: GoogleFonts.montserrat(textStyle: 
                        const TextStyle(color: Color.fromARGB(255, 208, 255, 219), fontSize: 20,
                        fontWeight: FontWeight.w500)),),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            botBlockListWidget
          ],
        ),
      ),
    );
  }
}

Widget botBlockListWidget = Expanded(
  child: ListView(
    shrinkWrap: true,
    children: [
      BotBlockWidget(headerText: 'Лидер по доходам', botName: 'Фьючерсный grid-бот', textARP: '1 312.21',),
      BotBlockWidget(headerText: 'Высокая доходность со сделки', botName: 'ИИ бот', textARP: '523.42',),
      BotBlockWidget(headerText: 'Стабильность', botName: 'DCA бот', textARP: '724.31',),
      BotBlockWidget(headerText: 'Один раз, но навсегда', botName: 'Coin sniping', textARP: '∞',),
    ],
  ),
);

class BotBlockWidget extends StatelessWidget {
  BotBlockWidget({super.key, required this.headerText, required this.botName, required this.textARP});

  String headerText = '';
  String botName = '';
  String textARP = '';

  @override
  Widget build(BuildContext context) {
    return FutureBuilder(
      future: getBalance(),
      builder: (context, snapshot){
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const CircularProgressIndicator();
        } else if (snapshot.hasError) {
          return Text('Ошибка: ${snapshot.error}');
        } else {
          return Padding(
        padding: const EdgeInsets.only(top: 8),
        child: Container(
          width: double.infinity,
          color: const Color.fromARGB(255, 18, 18, 19),
          child: Padding(
            padding: const EdgeInsets.only(left: 15, top: 10, bottom: 15),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(headerText, style: GoogleFonts.montserrat(textStyle: const TextStyle(color: 
                Color.fromARGB(255, 215, 215, 215),)),),
                const SizedBox(height: 5,),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(botName, style: GoogleFonts.montserrat(textStyle: const TextStyle(
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.w600
                    )),),
                    TextButton(onPressed: (){
                      Navigator.push(context, MaterialPageRoute(builder: (context) => FututeGridBotCreateScreen()));
                    }, child: Container(
                      width: 50,
                      height: 30,
                      decoration: const BoxDecoration(color: Color.fromARGB(255, 208, 255, 219,),
                      borderRadius: BorderRadius.all(Radius.circular(10))),
                      child: const Icon(Icons.arrow_forward, color: Colors.black,)))
                  ],
                ),
                Text('APR + $textARP %', style:GoogleFonts.montserrat(textStyle: const TextStyle(
                  color: Color.fromARGB(255, 208, 255, 219),
                  fontWeight: FontWeight.w600
                )),)
              ],
            ),
          ),
        ),
      );
        }
      }
    );
  }
}