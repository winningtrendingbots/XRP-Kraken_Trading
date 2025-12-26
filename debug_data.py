"""
Script de diagnóstico para verificar datos de Kraken
"""

import os
import sys
from kraken_trader import KrakenTrader
import pandas as pd


def diagnose_data():
    """Diagnosticar datos de Kraken"""
    
    print("\n" + "="*70)
    print("DIAGNÓSTICO DE DATOS DE KRAKEN")
    print("="*70)
    
    # Cargar credenciales
    api_key = os.getenv('KRAKEN_API_KEY')
    api_secret = os.getenv('KRAKEN_API_SECRET')
    
    if not api_key or not api_secret:
        print("\n❌ Variables de entorno no configuradas")
        print("   Ejecuta: export $(cat .env | xargs)")
        sys.exit(1)
    
    try:
        # Inicializar trader
        print("\n🔍 Conectando a Kraken...")
        trader = KrakenTrader(api_key, api_secret)
        print("✅ Conectado")
        
        # Test diferentes pares e intervalos
        test_configs = [
            ('XETHZUSD', 15, 'ETH/USD 15min'),
            ('XXRPZUSD', 15, 'XRP/USD 15min'),
            ('XBTUSDT', 15, 'BTC/USDT 15min'),
        ]
        
        for pair, interval, description in test_configs:
            print(f"\n{'─'*70}")
            print(f"Probando: {description} ({pair})")
            print('─'*70)
            
            try:
                # Descargar datos
                df = trader.get_ohlc_data(pair, interval)
                
                if df is None:
                    print(f"❌ No se pudieron obtener datos para {pair}")
                    continue
                
                print(f"✅ Datos descargados: {len(df)} velas")
                print(f"\nColumnas disponibles:")
                for col in df.columns:
                    print(f"  • {col}")
                
                print(f"\nRango de fechas:")
                print(f"  Desde: {df.index[0]}")
                print(f"  Hasta: {df.index[-1]}")
                
                print(f"\nÚltimas 5 velas:")
                print(df[['open', 'high', 'low', 'close', 'volume']].tail(5))
                
                print(f"\nEstadísticas:")
                print(f"  Precio actual: ${df['close'].iloc[-1]:,.2f}")
                print(f"  Máximo: ${df['high'].max():,.2f}")
                print(f"  Mínimo: ${df['low'].min():,.2f}")
                print(f"  Volumen total: {df['volume'].sum():,.0f}")
                print(f"  Volumen promedio: {df['volume'].mean():,.2f}")
                
                print(f"\nCalidad de datos:")
                null_counts = df.isnull().sum()
                if null_counts.sum() == 0:
                    print("  ✅ No hay valores nulos")
                else:
                    print("  ⚠️  Valores nulos encontrados:")
                    for col, count in null_counts[null_counts > 0].items():
                        print(f"     {col}: {count} nulos")
                
                # Verificar tipos de datos
                print(f"\nTipos de datos:")
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    dtype = df[col].dtype
                    has_none = df[col].isnull().any()
                    print(f"  {col}: {dtype} {'(contiene NaN)' if has_none else ''}")
                
                # Test de cálculo de indicadores
                print(f"\n🧪 Probando cálculo de indicadores...")
                try:
                    import ta
                    
                    # Test ADX
                    adx = ta.trend.adx(df['high'], df['low'], df['close'], window=14)
                    print(f"  ✅ ADX calculado: último valor = {adx.iloc[-1]:.2f}")
                    
                    # Test RSI
                    rsi = ta.momentum.rsi(df['close'], window=14)
                    print(f"  ✅ RSI calculado: último valor = {rsi.iloc[-1]:.2f}")
                    
                    # Test ATR
                    atr = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
                    print(f"  ✅ ATR calculado: último valor = {atr.iloc[-1]:.2f}")
                    
                    print(f"\n✅ Todos los indicadores funcionan correctamente")
                    
                except Exception as e:
                    print(f"\n❌ Error calculando indicadores: {e}")
                    import traceback
                    traceback.print_exc()
                
            except Exception as e:
                print(f"❌ Error con {pair}: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n" + "="*70)
        print("✅ DIAGNÓSTICO COMPLETADO")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error general: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    diagnose_data()
