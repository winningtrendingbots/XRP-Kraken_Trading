"""
Script de test para verificar conexiones y configuración
Ejecutar antes de activar el bot en producción
"""

import os
import sys
from kraken_trader import KrakenTrader
from telegram_notifier import TelegramNotifier
from state_manager import StateManager


def test_environment_variables():
    """Test 1: Verificar variables de entorno"""
    print("\n" + "="*60)
    print("TEST 1: VARIABLES DE ENTORNO")
    print("="*60)
    
    required = [
        'KRAKEN_API_KEY',
        'KRAKEN_API_SECRET',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID'
    ]
    
    all_ok = True
    for var in required:
        value = os.getenv(var)
        if value:
            masked = value[:8] + "..." if len(value) > 8 else "***"
            print(f"✅ {var}: {masked}")
        else:
            print(f"❌ {var}: NO ENCONTRADA")
            all_ok = False
    
    return all_ok


def test_kraken_connection():
    """Test 2: Verificar conexión con Kraken"""
    print("\n" + "="*60)
    print("TEST 2: CONEXIÓN KRAKEN")
    print("="*60)
    
    try:
        api_key = os.getenv('KRAKEN_API_KEY')
        api_secret = os.getenv('KRAKEN_API_SECRET')
        
        if not api_key or not api_secret:
            print("❌ No hay credenciales de Kraken")
            return False
        
        trader = KrakenTrader(api_key, api_secret)
        
        # Test 1: Obtener balance
        print("\n🔍 Obteniendo balance...")
        balance = trader.get_balance()
        if balance is not None:
            print("✅ Balance obtenido correctamente")
            print(f"   Cuentas disponibles: {list(balance.index)}")
        else:
            print("❌ Error obteniendo balance")
            return False
        
        # Test 2: Obtener balance tradeable
        print("\n🔍 Obteniendo balance tradeable...")
        tradeable = trader.get_tradable_balance()
        print(f"✅ Balance disponible para trading: ${tradeable:.2f}")
        
        if tradeable < 100:
            print("⚠️  ADVERTENCIA: Balance muy bajo para operar")
        
        # Test 3: Obtener ticker
        print("\n🔍 Obteniendo precio actual de ETH...")
        ticker = trader.get_ticker('XETHZUSD')
        if ticker:
            print(f"✅ Precio ETH/USD:")
            print(f"   Ask: ${ticker['ask']:,.2f}")
            print(f"   Bid: ${ticker['bid']:,.2f}")
            print(f"   Last: ${ticker['last']:,.2f}")
        else:
            print("❌ Error obteniendo ticker")
            return False
        
        # Test 4: Obtener datos OHLC
        print("\n🔍 Descargando datos OHLC (15min)...")
        ohlc = trader.get_ohlc_data('XETHZUSD', interval=15)
        if ohlc is not None and len(ohlc) > 0:
            print(f"✅ Datos OHLC descargados: {len(ohlc)} velas")
            print(f"   Desde: {ohlc.index[0]}")
            print(f"   Hasta: {ohlc.index[-1]}")
            print(f"   Columnas: {ohlc.columns.tolist()}")
            print(f"   Último close: ${ohlc['close'].iloc[-1]:,.2f}")
            
            # Verificar calidad de datos
            null_counts = ohlc[['open', 'high', 'low', 'close', 'volume']].isnull().sum()
            if null_counts.sum() == 0:
                print(f"   ✅ No hay valores nulos")
            else:
                print(f"   ⚠️  Valores nulos: {null_counts.to_dict()}")
                
            # Test de cálculo de indicadores
            print("\n🔍 Probando cálculo de indicadores...")
            try:
                import ta
                adx = ta.trend.adx(ohlc['high'], ohlc['low'], ohlc['close'], window=14)
                rsi = ta.momentum.rsi(ohlc['close'], window=14)
                print(f"   ✅ ADX: {adx.iloc[-1]:.2f}")
                print(f"   ✅ RSI: {rsi.iloc[-1]:.2f}")
            except Exception as e:
                print(f"   ❌ Error calculando indicadores: {e}")
                return False
        else:
            print("❌ Error descargando datos OHLC")
            return False
        
        # Test 5: Calcular tamaño de posición
        print("\n🔍 Calculando tamaño de posición de prueba...")
        current_price = ticker['last']
        position_calc = trader.calculate_position_size(
            balance=tradeable,
            risk_percent=0.05,
            stop_loss_points=200,
            current_price=current_price,
            pair='XETHZUSD'
        )
        
        if position_calc:
            print(f"✅ Cálculo de posición:")
            print(f"   Tamaño: {position_calc['size']:.4f} ETH")
            print(f"   Apalancamiento sugerido: {position_calc['leverage']}x")
            print(f"   Costo: ${position_calc['cost']:,.2f}")
            print(f"   Margen requerido: ${position_calc['margin_required']:,.2f}")
        else:
            print("❌ Error calculando posición")
            return False
        
        print("\n✅ Todos los tests de Kraken pasaron correctamente")
        return True
        
    except Exception as e:
        print(f"\n❌ Error en test de Kraken: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_telegram():
    """Test 3: Verificar notificaciones de Telegram"""
    print("\n" + "="*60)
    print("TEST 3: NOTIFICACIONES TELEGRAM")
    print("="*60)
    
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not bot_token or not chat_id:
            print("❌ No hay credenciales de Telegram")
            return False
        
        telegram = TelegramNotifier(bot_token, chat_id)
        
        print("\n📱 Enviando mensaje de prueba...")
        success = telegram.send_message(
            "🧪 <b>MENSAJE DE PRUEBA</b>\n\n"
            "Este es un mensaje de prueba del bot de trading.\n"
            "Si recibes este mensaje, la configuración es correcta.\n\n"
            "✅ Sistema listo para operar"
        )
        
        if success:
            print("✅ Mensaje enviado correctamente")
            print("   Verifica tu Telegram para confirmar recepción")
            return True
        else:
            print("❌ Error enviando mensaje")
            return False
        
    except Exception as e:
        print(f"\n❌ Error en test de Telegram: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_manager():
    """Test 4: Verificar gestión de estado"""
    print("\n" + "="*60)
    print("TEST 4: GESTIÓN DE ESTADO")
    print("="*60)
    
    try:
        print("\n🔍 Inicializando gestor de estado...")
        state = StateManager('test_state.json')
        
        print("✅ Gestor inicializado")
        
        # Test escritura
        print("\n🔍 Probando escritura de estado...")
        state.set_capital(10000)
        state.save_state()
        print("✅ Estado guardado")
        
        # Test lectura
        print("\n🔍 Probando lectura de estado...")
        capital = state.get_capital()
        print(f"✅ Capital leído: ${capital:.2f}")
        
        # Test posiciones
        print("\n🔍 Probando gestión de posiciones...")
        test_position = {
            'entry_price': 3500,
            'size': 0.1,
            'direction': 'long',
            'stop_loss': 3400,
            'take_profit': 3600,
            'leverage': 2
        }
        state.add_position('TEST_001', test_position)
        positions = state.get_all_positions()
        print(f"✅ Posición de prueba creada: {len(positions)} posiciones")
        
        # Limpiar
        state.remove_position('TEST_001')
        print("✅ Posición de prueba eliminada")
        
        # Limpiar archivo de prueba
        import os
        if os.path.exists('test_state.json'):
            os.remove('test_state.json')
        
        print("\n✅ Todos los tests de estado pasaron correctamente")
        return True
        
    except Exception as e:
        print(f"\n❌ Error en test de estado: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_final_summary(results):
    """Imprimir resumen final"""
    print("\n" + "="*60)
    print("RESUMEN DE TESTS")
    print("="*60)
    
    tests = [
        ("Variables de entorno", results[0]),
        ("Conexión Kraken", results[1]),
        ("Notificaciones Telegram", results[2]),
        ("Gestión de estado", results[3])
    ]
    
    all_passed = all(r for r in results)
    
    for test_name, passed in tests:
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        print(f"{status} - {test_name}")
    
    print("\n" + "="*60)
    
    if all_passed:
        print("✅ TODOS LOS TESTS PASARON")
        print("\n🚀 El bot está listo para operar en producción")
        print("\nPróximos pasos:")
        print("1. Revisa la configuración en live_trading.py")
        print("2. Ajusta los parámetros de riesgo según tu estrategia")
        print("3. Sube el código a GitHub")
        print("4. Configura los Secrets en GitHub")
        print("5. Habilita el workflow de GitHub Actions")
        print("\n⚠️  IMPORTANTE: Empieza con cantidades pequeñas")
    else:
        print("❌ ALGUNOS TESTS FALLARON")
        print("\n🔧 Soluciona los errores antes de continuar:")
        print("1. Verifica todas las credenciales")
        print("2. Comprueba los permisos de las API keys")
        print("3. Asegúrate de tener balance suficiente")
        print("4. Revisa los errores específicos arriba")
    
    print("="*60 + "\n")
    
    return all_passed


def main():
    """Ejecutar todos los tests"""
    print("\n" + "🧪" * 30)
    print("BOT DE TRADING - SUITE DE TESTS")
    print("🧪" * 30)
    
    results = [
        test_environment_variables(),
        test_kraken_connection(),
        test_telegram(),
        test_state_manager()
    ]
    
    success = print_final_summary(results)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
