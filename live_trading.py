"""
LIVE TRADING BOT FOR KRAKEN
Ejecuta la estrategia de volumen + OHLC en producción
"""

import os
import sys
import logging
from datetime import datetime
import pandas as pd
import numpy as np
import ta

from kraken_trader import KrakenTrader
from telegram_notifier import TelegramNotifier
from state_manager import StateManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURACIÓN DE PRODUCCIÓN
# ============================================================================

class ProductionConfig:
    """Configuración para trading en vivo"""
    
    # API Kraken (se cargarán desde variables de entorno)
    KRAKEN_API_KEY = os.getenv('KRAKEN_API_KEY')
    KRAKEN_API_SECRET = os.getenv('KRAKEN_API_SECRET')
    
    # Telegram (se cargarán desde variables de entorno)
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    # Trading
    SYMBOL = 'XRP-USD'
    KRAKEN_PAIR = 'XXRPZUSD'  # Formato Kraken
    INTERVAL = 60  # minutos
    LOOKBACK_PERIODS = 200  # Cuántas velas históricas cargar
    
    # Estrategia (igual que backtest)
    VOLUME_SMOOTH_PERIODS = 4
    ACCEL_BARS_REQUIRED = 2
    
    # Confirmaciones
    USE_ADX = False
    ADX_THRESHOLD = 20
    USE_OBV = False
    USE_PRICE_MA = False
    USE_RSI_FILTER = False
    USE_BB_FILTER = False
    MIN_CONFIRMATIONS_RATIO = 0.25
    
    # Risk Management
    INITIAL_CAPITAL = 10000  # Solo para referencia
    RISK_PER_TRADE = 0.05
    TP_POINTS = 100
    ATR_STOP_MULTIPLIER = 1.0
    
    # Trailing Stop
    USE_TRAILING_STOP = True
    TRAILING_START = 25
    TRAILING_STEP = 15
    
    # Limits
    PROFIT_CLOSE = 50
    MAX_DAILY_LOSS = -20
    MAX_POSITIONS = 1
    SAME_DIRECTION_ONLY = False
    MAX_BARS_IN_TRADE = 2
    
    # Leverage
    LEVERAGE_MIN = 4
    LEVERAGE_MAX = 10
    
    # Trading Hours
    USE_TRADING_HOURS = True
    TRADE_EUROPEAN_SESSION = True
    TRADE_AMERICAN_SESSION = True
    TRADE_ASIAN_SESSION = False
    SESSION_BUFFER = 15
    
    # Días de trading
    TRADE_MONDAY = True
    TRADE_TUESDAY = True
    TRADE_WEDNESDAY = True
    TRADE_THURSDAY = True
    TRADE_FRIDAY = True


# ============================================================================
# FUNCIONES DE ANÁLISIS TÉCNICO
# ============================================================================

def calculate_volume_derivatives(df, config):
    """Calcular derivadas de volumen"""
    df = df.copy()
    
    df['Volume_Smoothed'] = df['volume'].rolling(
        window=config.VOLUME_SMOOTH_PERIODS, 
        min_periods=1
    ).mean()
    
    df['Vol_1st_Der'] = df['Volume_Smoothed'].diff()
    df['Vol_2nd_Der'] = df['Vol_1st_Der'].diff()
    
    df['Vol_1st_Der_Norm'] = (df['Vol_1st_Der'] - df['Vol_1st_Der'].mean()) / (df['Vol_1st_Der'].std() + 1e-10)
    df['Vol_2nd_Der_Norm'] = (df['Vol_2nd_Der'] - df['Vol_2nd_Der'].mean()) / (df['Vol_2nd_Der'].std() + 1e-10)
    
    df['Accel_Positive'] = (
        (df['Vol_1st_Der_Norm'] > 0.1) & 
        (df['Vol_2nd_Der_Norm'] > 0.1)
    ).astype(int)
    
    df['Accel_Negative'] = (
        (df['Vol_1st_Der_Norm'] < -0.1) & 
        (df['Vol_2nd_Der_Norm'] < -0.1)
    ).astype(int)
    
    # Calcular aceleración consecutiva
    df['Consecutive_Accel'] = 0
    consec = 0
    for i in range(1, len(df)):
        if df['Accel_Positive'].iloc[i]:
            consec = max(0, consec) + 1
        elif df['Accel_Negative'].iloc[i]:
            consec = min(0, consec) - 1
        else:
            consec = 0
        df.iloc[i, df.columns.get_loc('Consecutive_Accel')] = consec
    
    return df


def add_technical_indicators(df):
    """Agregar indicadores técnicos"""
    df = df.copy()
    
    df['ADX'] = ta.trend.adx(df['high'], df['low'], df['close'], window=14)
    df['ADX_pos'] = ta.trend.adx_pos(df['high'], df['low'], df['close'], window=14)
    df['ADX_neg'] = ta.trend.adx_neg(df['high'], df['low'], df['close'], window=14)
    
    df['OBV'] = ta.volume.on_balance_volume(df['close'], df['volume'])
    df['OBV_MA'] = df['OBV'].rolling(window=3).mean()
    
    df['SMA_20'] = df['close'].rolling(window=20).mean()
    df['SMA_50'] = df['close'].rolling(window=50).mean()
    
    df['RSI'] = ta.momentum.rsi(df['close'], window=14)
    df['ATR'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    
    bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
    df['BB_upper'] = bb.bollinger_hband()
    df['BB_lower'] = bb.bollinger_lband()
    df['BB_mid'] = bb.bollinger_mavg()
    
    df['Price_Momentum'] = df['close'].diff(5)
    
    return df


def generate_signal(df, config):
    """Generar señal de trading (última vela)"""
    
    # Señal de volumen
    last_accel = df['Consecutive_Accel'].iloc[-1]
    
    if last_accel >= config.ACCEL_BARS_REQUIRED:
        vol_signal = 1
    elif last_accel <= -config.ACCEL_BARS_REQUIRED:
        vol_signal = -1
    else:
        return 0, {}
    
    # Confirmaciones
    confirmations = 0
    required = 0
    
    if config.USE_ADX:
        required += 1
        if df['ADX'].iloc[-1] > config.ADX_THRESHOLD:
            if vol_signal == 1 and df['ADX_pos'].iloc[-1] > df['ADX_neg'].iloc[-1]:
                confirmations += 1
            elif vol_signal == -1 and df['ADX_neg'].iloc[-1] > df['ADX_pos'].iloc[-1]:
                confirmations += 1
    
    if config.USE_OBV:
        required += 1
        if vol_signal == 1 and df['OBV'].iloc[-1] > df['OBV'].iloc[-2]:
            confirmations += 1
        elif vol_signal == -1 and df['OBV'].iloc[-1] < df['OBV'].iloc[-2]:
            confirmations += 1
    
    if config.USE_PRICE_MA:
        required += 1
        if vol_signal == 1 and df['close'].iloc[-1] > df['SMA_20'].iloc[-1]:
            confirmations += 1
        elif vol_signal == -1 and df['close'].iloc[-1] < df['SMA_20'].iloc[-1]:
            confirmations += 1
    
    # Filtros
    if config.USE_RSI_FILTER:
        rsi = df['RSI'].iloc[-1]
        if vol_signal == 1 and rsi > 65:
            return 0, {}
        elif vol_signal == -1 and rsi < 35:
            return 0, {}
    
    # Decidir si hay señal final
    if required == 0 or confirmations >= required * config.MIN_CONFIRMATIONS_RATIO:
        indicators = {
            'accel': last_accel,
            'adx': df['ADX'].iloc[-1] if 'ADX' in df.columns else 0,
            'rsi': df['RSI'].iloc[-1] if 'RSI' in df.columns else 0,
            'obv': df['OBV'].iloc[-1] if 'OBV' in df.columns else 0
        }
        return vol_signal, indicators
    
    return 0, {}


def can_trade_now(config):
    """Verificar si podemos tradear según horario"""
    if not config.USE_TRADING_HOURS:
        return True
    
    now = datetime.utcnow()
    hour = now.hour
    minute = now.minute
    day_of_week = now.weekday()
    
    # Verificar día de la semana
    days_allowed = [
        config.TRADE_MONDAY,
        config.TRADE_TUESDAY,
        config.TRADE_WEDNESDAY,
        config.TRADE_THURSDAY,
        config.TRADE_FRIDAY,
        False, False
    ]
    
    if not days_allowed[day_of_week]:
        return False
    
    # Verificar sesiones
    time_minutes = hour * 60 + minute
    buffer = config.SESSION_BUFFER
    
    # Asian: 00:00-08:00
    if config.TRADE_ASIAN_SESSION:
        if buffer <= time_minutes <= (8 * 60 - buffer):
            return True
    
    # European: 07:00-16:00
    if config.TRADE_EUROPEAN_SESSION:
        if (7 * 60 + buffer) <= time_minutes <= (16 * 60 - buffer):
            return True
    
    # American: 13:00-22:00
    if config.TRADE_AMERICAN_SESSION:
        if (13 * 60 + buffer) <= time_minutes <= (22 * 60 - buffer):
            return True
    
    return False


# ============================================================================
# TRADING LOGIC
# ============================================================================

class LiveTrader:
    """Gestor principal de trading en vivo"""
    
    def __init__(self, config):
        self.config = config
        
        # Inicializar módulos
        self.kraken = KrakenTrader(
            config.KRAKEN_API_KEY,
            config.KRAKEN_API_SECRET,
            leverage_min=config.LEVERAGE_MIN,
            leverage_max=config.LEVERAGE_MAX
        )
        
        self.telegram = TelegramNotifier(
            config.TELEGRAM_BOT_TOKEN,
            config.TELEGRAM_CHAT_ID
        )
        
        self.state = StateManager()
        
        logger.info("LiveTrader inicializado")
    
    def run(self):
        """Ejecutar ciclo de trading"""
        try:
            logger.info("="*80)
            logger.info(f"Iniciando ciclo de trading: {datetime.now()}")
            logger.info("="*80)
            
            # Verificar si podemos tradear (pérdida diaria)
            if not self.state.can_trade():
                logger.warning("Trading deshabilitado por límite de pérdida diaria")
                return
            
            # Verificar horario
            if not can_trade_now(self.config):
                logger.info("Fuera de horario de trading")
                return
            
            # Obtener datos
            logger.info("Descargando datos de mercado...")
            df = self.kraken.get_ohlc_data(
                pair=self.config.KRAKEN_PAIR,
                interval=self.config.INTERVAL
            )
            
            if df is None or len(df) < 100:
                logger.error("No se pudieron obtener datos suficientes")
                self.telegram.notify_error("Error obteniendo datos de mercado")
                return
            
            # Calcular indicadores
            logger.info("Calculando indicadores...")
            df = calculate_volume_derivatives(df, self.config)
            df = add_technical_indicators(df)
            
            # Actualizar posiciones existentes
            self.update_open_positions(df)
            
            # Generar señal
            signal, indicators = generate_signal(df, self.config)
            current_price = df['close'].iloc[-1]
            atr = df['ATR'].iloc[-1]
            
            logger.info(f"Precio actual: ${current_price:.2f}")
            logger.info(f"Señal: {signal}")
            
            if signal != 0:
                signal_type = "BUY" if signal > 0 else "SELL"
                logger.info(f"🎯 Señal detectada: {signal_type}")
                self.telegram.notify_signal(signal_type, current_price, indicators)
                
                # Verificar si podemos abrir posición
                if self.can_open_position(signal):
                    self.open_position(signal, current_price, atr)
            
            # Incrementar contador de barras
            self.state.increment_bars_open()
            
            logger.info("Ciclo completado correctamente")
            
        except Exception as e:
            logger.error(f"Error en ciclo de trading: {e}", exc_info=True)
            self.telegram.notify_error(f"Error en ciclo: {str(e)}")
    
    def can_open_position(self, signal):
        """Verificar si podemos abrir una nueva posición"""
        positions = self.state.get_all_positions()
        
        # Verificar número máximo de posiciones
        if len(positions) >= self.config.MAX_POSITIONS:
            logger.info("Máximo de posiciones alcanzado")
            return False
        
        # Verificar misma dirección si está configurado
        if self.config.SAME_DIRECTION_ONLY and len(positions) > 0:
            first_direction = list(positions.values())[0]['direction']
            new_direction = 'long' if signal > 0 else 'short'
            
            if first_direction != new_direction:
                logger.info("Same direction only: dirección no permitida")
                return False
        
        return True
    
    def open_position(self, signal, current_price, atr):
        """Abrir nueva posición"""
        try:
            logger.info("Abriendo posición...")
            
            # Obtener balance
            balance = self.kraken.get_tradable_balance()
            logger.info(f"Balance disponible: ${balance:.2f}")
            
            if balance < 100:
                logger.warning("Balance insuficiente para operar")
                self.telegram.notify_error("Balance insuficiente")
                return
            
            # Calcular tamaño de posición
            stop_loss_points = self.config.ATR_STOP_MULTIPLIER * atr / 0.0001
            
            position_calc = self.kraken.calculate_position_size(
                balance=balance,
                risk_percent=self.config.RISK_PER_TRADE,
                stop_loss_points=stop_loss_points,
                current_price=current_price,
                pair=self.config.KRAKEN_PAIR
            )
            
            if position_calc is None:
                logger.error("No se pudo calcular tamaño de posición")
                return
            
            logger.info(f"Tamaño calculado: {position_calc['size']:.4f}")
            logger.info(f"Apalancamiento: {position_calc['leverage']}x")
            logger.info(f"Margen requerido: ${position_calc['margin_required']:.2f}")
            
            # Calcular stop loss y take profit
            direction = 'long' if signal > 0 else 'short'
            
            if direction == 'long':
                stop_loss = current_price - (self.config.ATR_STOP_MULTIPLIER * atr)
                take_profit = current_price + (self.config.TP_POINTS * 0.0001)
            else:
                stop_loss = current_price + (self.config.ATR_STOP_MULTIPLIER * atr)
                take_profit = current_price - (self.config.TP_POINTS * 0.0001)
            
            # Colocar orden en Kraken
            side = 'buy' if signal > 0 else 'sell'
            
            order_result = self.kraken.place_margin_order(
                pair=self.config.KRAKEN_PAIR,
                side=side,
                size=position_calc['size'],
                leverage=position_calc['leverage'],
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            if order_result is None:
                logger.error("Error colocando orden")
                self.telegram.notify_error("Error colocando orden en Kraken")
                return
            
            # Guardar en estado
            position_data = {
                'entry_price': current_price,
                'size': position_calc['size'],
                'direction': direction,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'leverage': position_calc['leverage'],
                'trailing_stop': None
            }
            
            self.state.add_position(order_result['txid'], position_data)
            
            # Notificar
            order_details = {
                'txid': order_result['txid'],
                'side': side,
                'price': current_price,
                'size': position_calc['size'],
                'cost': position_calc['cost'],
                'leverage': position_calc['leverage'],
                'margin': position_calc['margin_required'],
                'tp': take_profit,
                'sl': stop_loss
            }
            
            self.telegram.notify_order_placed(order_details)
            logger.info(f"✅ Posición abierta: {order_result['txid']}")
            
        except Exception as e:
            logger.error(f"Error abriendo posición: {e}", exc_info=True)
            self.telegram.notify_error(f"Error abriendo posición: {str(e)}")
    
    def update_open_positions(self, df):
        """Actualizar posiciones abiertas"""
        positions = self.state.get_all_positions()
        
        if len(positions) == 0:
            return
        
        current_price = df['close'].iloc[-1]
        high = df['high'].iloc[-1]
        low = df['low'].iloc[-1]
        atr = df['ATR'].iloc[-1]
        
        for position_id, position in list(positions.items()):
            try:
                self.update_single_position(position_id, position, current_price, high, low, atr)
            except Exception as e:
                logger.error(f"Error actualizando posición {position_id}: {e}")
    
    def update_single_position(self, position_id, position, current_price, high, low, atr):
        """Actualizar una posición individual"""
        
        # Calcular P&L actual
        if position['direction'] == 'long':
            pnl = (current_price - position['entry_price']) * position['size']
            profit_points = (current_price - position['entry_price']) / 0.0001
        else:
            pnl = (position['entry_price'] - current_price) * position['size']
            profit_points = (position['entry_price'] - current_price) / 0.0001
        
        # Actualizar extremos para trailing
        self.state.update_position_extremes(position_id, current_price)
        
        # Verificar profit close
        if profit_points >= self.config.PROFIT_CLOSE:
            logger.info(f"Profit target alcanzado para {position_id}")
            self.close_position(position_id, current_price, 'profit_target')
            return
        
        # Trailing stop
        if self.config.USE_TRAILING_STOP and profit_points >= self.config.TRAILING_START:
            self.handle_trailing_stop(position_id, position, profit_points, current_price)
        
        # Verificar SL/TP con high/low
        if position['direction'] == 'long':
            if low <= position['stop_loss']:
                self.close_position(position_id, position['stop_loss'], 'stop_loss')
                return
            elif high >= position['take_profit']:
                self.close_position(position_id, position['take_profit'], 'take_profit')
                return
        else:
            if high >= position['stop_loss']:
                self.close_position(position_id, position['stop_loss'], 'stop_loss')
                return
            elif low <= position['take_profit']:
                self.close_position(position_id, position['take_profit'], 'take_profit')
                return
        
        # Time limit
        if position['bars_open'] >= self.config.MAX_BARS_IN_TRADE:
            logger.info(f"Time limit alcanzado para {position_id}")
            self.close_position(position_id, current_price, 'time_limit')
            return
    
    def handle_trailing_stop(self, position_id, position, profit_points, current_price):
        """Manejar trailing stop"""
        
        if not position.get('trailing_activated'):
            position['trailing_activated'] = True
            position['highest_profit'] = profit_points
            self.state.update_position(position_id, position)
            logger.info(f"Trailing stop activado para {position_id}")
        else:
            if profit_points > position['highest_profit']:
                position['highest_profit'] = profit_points
                
                # Calcular nuevo stop
                trail_level = position['highest_profit'] - self.config.TRAILING_STEP
                
                if position['direction'] == 'long':
                    new_sl = position['entry_price'] + (trail_level * 0.0001)
                    if new_sl > position['stop_loss']:
                        position['stop_loss'] = new_sl
                        self.state.update_position(position_id, position)
                        
                        pnl = (current_price - position['entry_price']) * position['size']
                        self.telegram.notify_trailing_stop_update(position_id, new_sl, pnl)
                        logger.info(f"Trailing stop actualizado: ${new_sl:.2f}")
                else:
                    new_sl = position['entry_price'] - (trail_level * 0.0001)
                    if new_sl < position['stop_loss']:
                        position['stop_loss'] = new_sl
                        self.state.update_position(position_id, position)
                        
                        pnl = (position['entry_price'] - current_price) * position['size']
                        self.telegram.notify_trailing_stop_update(position_id, new_sl, pnl)
                        logger.info(f"Trailing stop actualizado: ${new_sl:.2f}")
    
    def close_position(self, position_id, exit_price, reason):
        """Cerrar posición"""
        try:
            position = self.state.get_position(position_id)
            
            if position is None:
                logger.warning(f"Posición {position_id} no encontrada en estado")
                return
            
            # Calcular P&L
            if position['direction'] == 'long':
                pnl = (exit_price - position['entry_price']) * position['size']
            else:
                pnl = (position['entry_price'] - exit_price) * position['size']
            
            return_pct = (pnl / (position['entry_price'] * position['size'])) * 100
            
            # Cerrar en Kraken
            success = self.kraken.close_position(
                pair=self.config.KRAKEN_PAIR,
                position_type=position['direction']
            )
            
            if not success:
                logger.error(f"Error cerrando posición en Kraken: {position_id}")
            
            # Actualizar estado
            self.state.add_trade(pnl)
            self.state.remove_position(position_id)
            
            # Verificar límite de pérdida diaria
            if self.state.is_daily_loss_limit_hit(self.config.MAX_DAILY_LOSS):
                self.telegram.notify_daily_loss_limit(
                    self.state.get_daily_profit(),
                    self.config.MAX_DAILY_LOSS
                )
            
            # Notificar
            entry_time = datetime.fromisoformat(position['entry_time'])
            duration = str(datetime.now() - entry_time).split('.')[0]
            
            close_details = {
                'txid': position_id,
                'direction': position['direction'],
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'pnl': pnl,
                'return_pct': return_pct,
                'reason': reason,
                'duration': duration,
                'balance': self.kraken.get_tradable_balance()
            }
            
            self.telegram.notify_order_closed(close_details)
            logger.info(f"✅ Posición cerrada: {position_id} | P&L: ${pnl:.2f}")
            
        except Exception as e:
            logger.error(f"Error cerrando posición: {e}", exc_info=True)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Función principal"""
    
    # Validar variables de entorno
    required_vars = [
        'KRAKEN_API_KEY',
        'KRAKEN_API_SECRET',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID'
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.error(f"Variables de entorno faltantes: {missing}")
        sys.exit(1)
    
    # Crear configuración
    config = ProductionConfig()
    
    # Inicializar trader
    trader = LiveTrader(config)
    
    # Ejecutar
    trader.run()


if __name__ == "__main__":
    main()
