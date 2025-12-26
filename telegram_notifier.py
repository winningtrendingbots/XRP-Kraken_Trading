"""
Telegram Notification Module
Envío de notificaciones de trading a Telegram
"""

import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Gestor de notificaciones a Telegram"""
    
    def __init__(self, bot_token, chat_id):
        """
        Inicializar notificador
        
        Args:
            bot_token: Token del bot de Telegram
            chat_id: ID del chat donde enviar mensajes
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
    def send_message(self, text, parse_mode='HTML'):
        """
        Enviar mensaje a Telegram
        
        Args:
            text: Texto del mensaje
            parse_mode: 'HTML' o 'Markdown'
        """
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Error enviando mensaje a Telegram: {response.text}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error enviando notificación: {e}")
            return False
    
    def notify_startup(self, config):
        """Notificar inicio del bot"""
        message = f"""
🚀 <b>BOT DE TRADING INICIADO</b>

📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
💱 Par: {config.SYMBOL}
⏱ Intervalo: {config.INTERVAL}

⚙️ <b>Configuración:</b>
• Capital inicial: ${config.INITIAL_CAPITAL:,.2f}
• Riesgo por trade: {config.RISK_PER_TRADE*100}%
• Apalancamiento: {config.LEVERAGE_MIN}-{config.LEVERAGE_MAX}x
• Trailing stop: {'✅' if config.USE_TRAILING_STOP else '❌'}
• Pérdida diaria máx: ${config.MAX_DAILY_LOSS}

✅ Sistema listo para operar
        """
        self.send_message(message.strip())
    
    def notify_signal(self, signal_type, price, indicators):
        """Notificar señal detectada"""
        emoji = "🟢" if signal_type == "BUY" else "🔴"
        
        message = f"""
{emoji} <b>SEÑAL DETECTADA: {signal_type}</b>

💰 Precio: ${price:,.2f}
📊 Aceleración: {indicators.get('accel', 0):.1f}
📈 ADX: {indicators.get('adx', 0):.1f}
📉 RSI: {indicators.get('rsi', 0):.1f}

⏳ Esperando confirmación...
        """
        self.send_message(message.strip())
    
    def notify_order_placed(self, order_details):
        """Notificar orden colocada"""
        direction = "COMPRA" if order_details['side'] == 'buy' else "VENTA"
        emoji = "🟢" if order_details['side'] == 'buy' else "🔴"
        
        message = f"""
{emoji} <b>ORDEN EJECUTADA: {direction}</b>

📝 ID: <code>{order_details['txid']}</code>
💰 Precio entrada: ${order_details['price']:,.2f}
📊 Tamaño: {order_details['size']:.4f}
💵 Costo: ${order_details['cost']:,.2f}
⚡ Apalancamiento: {order_details['leverage']}x
💼 Margen requerido: ${order_details['margin']:,.2f}

🎯 Take Profit: ${order_details.get('tp', 0):,.2f}
🛑 Stop Loss: ${order_details.get('sl', 0):,.2f}

✅ Posición abierta
        """
        self.send_message(message.strip())
    
    def notify_order_closed(self, close_details):
        """Notificar cierre de orden"""
        pnl = close_details['pnl']
        emoji = "✅" if pnl > 0 else "❌"
        pnl_emoji = "💰" if pnl > 0 else "💸"
        
        message = f"""
{emoji} <b>POSICIÓN CERRADA</b>

📝 ID: <code>{close_details['txid']}</code>
📊 Dirección: {close_details['direction'].upper()}

💰 Precio entrada: ${close_details['entry_price']:,.2f}
💰 Precio salida: ${close_details['exit_price']:,.2f}
⏱ Duración: {close_details['duration']}

{pnl_emoji} <b>P&L: ${pnl:+,.2f}</b>
📈 Retorno: {close_details['return_pct']:+.2f}%
🎯 Razón: {close_details['reason']}

💼 Balance actual: ${close_details['balance']:,.2f}
        """
        self.send_message(message.strip())
    
    def notify_trailing_stop_update(self, position_id, new_stop, profit):
        """Notificar actualización de trailing stop"""
        message = f"""
📊 <b>TRAILING STOP ACTUALIZADO</b>

📝 Posición: <code>{position_id}</code>
🛑 Nuevo stop: ${new_stop:,.2f}
💰 Profit actual: ${profit:,.2f}

✅ Stop ajustado
        """
        self.send_message(message.strip())
    
    def notify_daily_loss_limit(self, daily_loss, limit):
        """Notificar límite de pérdida diaria alcanzado"""
        message = f"""
⚠️ <b>LÍMITE DE PÉRDIDA DIARIA ALCANZADO</b>

💸 Pérdida del día: ${daily_loss:,.2f}
🚫 Límite: ${limit:,.2f}

🛑 Trading detenido por hoy
🔄 Reinicio: mañana 00:00 UTC

❌ Todas las posiciones cerradas
        """
        self.send_message(message.strip())
    
    def notify_error(self, error_msg):
        """Notificar error crítico"""
        message = f"""
❌ <b>ERROR CRÍTICO</b>

🐛 {error_msg}

⚠️ Revisar logs inmediatamente
        """
        self.send_message(message.strip())
    
    def notify_daily_summary(self, summary):
        """Enviar resumen diario"""
        emoji_pnl = "💰" if summary['pnl'] >= 0 else "💸"
        
        message = f"""
📊 <b>RESUMEN DIARIO</b>

📅 Fecha: {summary['date']}

📈 Trades totales: {summary['total_trades']}
✅ Ganadores: {summary['winning_trades']}
❌ Perdedores: {summary['losing_trades']}
📊 Win rate: {summary['win_rate']:.1f}%

{emoji_pnl} <b>P&L del día: ${summary['pnl']:+,.2f}</b>
💼 Balance: ${summary['balance']:,.2f}
📉 Drawdown máx: {summary['max_dd']:.2f}%

🎯 Mejor trade: ${summary['best_trade']:+,.2f}
💸 Peor trade: ${summary['worst_trade']:+,.2f}

{'🟢 Día positivo' if summary['pnl'] >= 0 else '🔴 Día negativo'}
        """
        self.send_message(message.strip())
    
    def notify_position_update(self, position_info):
        """Notificar actualización de posición"""
        pnl = position_info['pnl']
        emoji = "💰" if pnl >= 0 else "💸"
        
        message = f"""
📊 <b>ACTUALIZACIÓN DE POSICIÓN</b>

📝 ID: <code>{position_info['id']}</code>
💰 Precio actual: ${position_info['current_price']:,.2f}
💰 Precio entrada: ${position_info['entry_price']:,.2f}

{emoji} P&L: ${pnl:+,.2f} ({position_info['pnl_pct']:+.2f}%)
⏱ Tiempo en trade: {position_info['time_in_trade']}

🎯 TP: ${position_info['tp']:,.2f}
🛑 SL: ${position_info['sl']:,.2f}
        """
        self.send_message(message.strip())
