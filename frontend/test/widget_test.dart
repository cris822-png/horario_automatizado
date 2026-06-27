import 'package:flutter_test/flutter_test.dart';
import 'package:turnodeportivo/main.dart';

void main() {
  testWidgets('App builds without crashing', (WidgetTester tester) async {
    await tester.pumpWidget(const TurnoDeportivoApp());
    expect(find.byType(TurnoDeportivoApp), findsOneWidget);
  });
}
