"""
Script para enviar resumen diario de trading
Se ejecuta automáticamente al final del día
"""

import os
import sys
from datetime import datetime, date
from state_manager import StateManager
from telegram_notifier import TelegramNotifier
from kraken_trader import KrakenTrader


def generate_daily_summary():
    """Generar resumen del día"""
    
    # Cargar estado
    state = StateManager()
    
    # Obtener estadísticas del día
    stats = state.get_daily_stats()
    
    # Obtener balance actual de Kraken
    api_key = os.getenv('KRAKEN_API_KEY')
    api_secret = os.getenv('KRAKEN_API_SECRET')
    
    current_balance = 0
    if api_key and api_secret:
        try:
            trader = KrakenTrader(api_key, api_secret)
            current_balance = trader.get_tradable_balance()
        except Exception as e:
            print(f"Error obteniendo balance: {e}")
    
    # Calcular métricas adicionales
    total_trades = stats['trades']
    winning_trades = stats['winning_trades']
    losing_trades = stats['losing_trades']
    daily_pnl = stats['profit']
    
    # Simular best/worst trade (necesitarías guardar esto en el state)
    # Por ahora usamos valores placeholder
    best_trade = 0
    worst_trade = 0
    
    summary = {
        'date': str(date.today()),
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': stats['win_rate'],
        'pnl': daily_pnl,
        'balance': current_balance,
        'max_dd': 0,  # Calcularías esto con más datos históricos
        'best_trade': best_trade,
        'worst_trade': worst_trade
    }
    
    return summary


def send_daily_summary():
    """Enviar resumen diario a Telegram"""
    
    # Inicializar Telegram
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("❌ Credenciales de Telegram no encontradas")
        sys.exit(1)
    
    telegram = TelegramNotifier(bot_token, chat_id)
    
    # Generar resumen
    summary = generate_daily_summary()
    
    # Enviar
    telegram.notify_daily_summary(summary)
    
    print(f"✅ Resumen diario enviado para {summary['date']}")
    print(f"   Trades: {summary['total_trades']}")
    print(f"   P&L: ${summary['pnl']:.2f}")
    print(f"   Win Rate: {summary['win_rate']:.1f}%")


def main():
    """Función principal"""
    print("\n📊 Generando resumen diario...")
    send_daily_summary()


if __name__ == "__main__":
    main()
