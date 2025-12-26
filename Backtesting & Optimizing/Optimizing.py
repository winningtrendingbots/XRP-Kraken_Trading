#!pip install yfinance>=0.2.28 pandas>=2.0.0 numpy>=1.24.0 matplotlib>=3.7.0 seaborn>=0.12.0 scikit-learn>=1.3.0 tensorflow>=2.13.0 ta>=0.11.0
"""
SISTEMA DE OPTIMIZACIÓN AUTOMÁTICA DE ESTRATEGIA
Prueba múltiples configuraciones y guarda las mejores por Sharpe ratio
"""

import warnings
warnings.filterwarnings('ignore')

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta, time
from sklearn.preprocessing import StandardScaler
import ta
from itertools import product
import json
from tqdm import tqdm
import os

plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# ============================================================================
# CONFIGURACIÓN DE OPTIMIZACIÓN
# ============================================================================

class OptimizationConfig:
    """
    Define los parámetros a optimizar con sus rangos
    """

    # Parámetros a optimizar (define rangos con [min, max, step])
    PARAMS_TO_OPTIMIZE = {
        'VOLUME_SMOOTH_PERIODS': [3, 4, 1],           # min=2, max=8, step=2
        'ACCEL_BARS_REQUIRED': [2, 4, 1],             # min=2, max=5, step=1
        'ADX_THRESHOLD': [25, 25, 5],                 # min=20, max=30, step=5
        'RISK_PER_TRADE': [0.05, 0.05, 0.01],         # min=1%, max=5%, step=1%
        'ATR_STOP_MULTIPLIER': [1.0, 2.0, 0.5],       # min=1.0, max=2.5, step=0.5
        'TP_POINTS': [100, 200, 100],                  # min=100, max=300, step=50
        'TRAILING_START': [25, 25, 10],               # min=10, max=30, step=10
        'TRAILING_STEP': [15, 15, 5],                  # min=5, max=15, step=5
        'MIN_CONFIRMATIONS_RATIO': [0.25, 0.75, 0.25],  # min=0%, max=50%, step=25%
    }

    # Parámetros booleanos (True/False)
    BOOLEAN_PARAMS = {
        'USE_ADX': [True, False],
        'USE_OBV': [True, False],
        'USE_TRAILING_STOP': [True, True],
        'OBV_USE_TREND': [False, False],
    }

    # Parámetros fijos (no se optimizan)
    FIXED_PARAMS = {
        'INITIAL_CAPITAL': 10000,
        'SYMBOL': 'XRP-USD',
        'PERIOD': '2y',
        'INTERVAL': '1h',
        'COMMISSION': 0.0002,
        'USE_PRICE_MA': False,
        'USE_RSI_FILTER': False,
        'USE_BB_FILTER': False,
        'PROFIT_CLOSE': 30,
        'MAX_DAILY_LOSS': -50,
        'MAX_POSITIONS': 1,
        'SAME_DIRECTION_ONLY': False,
        'MAX_BARS_IN_TRADE': 2,
        'USE_TRADING_HOURS': True,
        'TRADE_ASIAN_SESSION': False,
        'TRADE_EUROPEAN_SESSION': True,
        'TRADE_AMERICAN_SESSION': True,
        'USE_CUSTOM_HOURS': False,
        'TRADE_MONDAY': True,
        'TRADE_TUESDAY': True,
        'TRADE_WEDNESDAY': True,
        'TRADE_THURSDAY': True,
        'TRADE_FRIDAY': True,
    }

    # Configuración de la optimización
    TOP_N_RESULTS = 10                    # Cuántas mejores configuraciones guardar
    MIN_TRADES_REQUIRED = 10              # Mínimo de trades para considerar válida una config
    OUTPUT_FILE = 'optimization_results.csv'
    BEST_CONFIGS_FILE = 'best_configs.json'

# ============================================================================
# [CÓDIGO DEL BACKTESTER ORIGINAL - SE MANTIENE IGUAL]
# ============================================================================

class StrategyConfig:
    """Configuración base de la estrategia"""
    pass

def download_forex_data(symbol=None, period=None, interval=None):
    """Download and synthesize forex data"""
    symbol = symbol or 'GBPJPY=X'
    period = period or '2y'
    interval = interval or '1h'

    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)

    if df.empty:
        raise ValueError(f"No data downloaded for {symbol}")

    # Synthesize volume for Forex
    if df['Volume'].sum() == 0 or df['Volume'].mean() < 1:
        price_range = df['High'] - df['Low']
        price_change = abs(df['Close'].diff())

        price_range_norm = (price_range - price_range.min()) / (price_range.max() - price_range.min() + 1e-10)
        price_change_norm = (price_change - price_change.min()) / (price_change.max() - price_change.min() + 1e-10)

        base_volume = (price_range_norm + price_change_norm) / 2

        hour_of_day = df.index.hour
        time_factor = np.ones(len(df))
        time_factor[(hour_of_day >= 8) & (hour_of_day < 12)] = 1.5
        time_factor[(hour_of_day >= 13) & (hour_of_day < 17)] = 2.0
        time_factor[(hour_of_day >= 17) & (hour_of_day < 22)] = 1.3

        noise = np.random.normal(1, 0.2, len(df))
        noise = np.clip(noise, 0.5, 1.5)

        synthetic_volume = base_volume * time_factor * noise * 100000
        df['Volume'] = synthetic_volume

    return df

def calculate_volume_derivatives(df, config):
    """Calculate volume derivatives"""
    df = df.copy()

    df['Volume_Smoothed'] = df['Volume'].rolling(
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

    df['Consecutive_Accel'] = 0
    consec = 0
    for i in range(1, len(df)):
        if df['Accel_Positive'].iloc[i]:
            consec = max(0, consec) + 1
        elif df['Accel_Negative'].iloc[i]:
            consec = min(0, consec) - 1
        else:
            consec = 0
        df.loc[df.index[i], 'Consecutive_Accel'] = consec

    return df

def add_technical_indicators(df):
    """Add technical indicators"""
    df = df.copy()

    df['ADX'] = ta.trend.adx(df['High'], df['Low'], df['Close'], window=14)
    df['ADX_pos'] = ta.trend.adx_pos(df['High'], df['Low'], df['Close'], window=14)
    df['ADX_neg'] = ta.trend.adx_neg(df['High'], df['Low'], df['Close'], window=14)

    df['OBV'] = ta.volume.on_balance_volume(df['Close'], df['Volume'])
    df['OBV_MA'] = df['OBV'].rolling(window=3).mean()

    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()

    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)

    bb = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
    df['BB_upper'] = bb.bollinger_hband()
    df['BB_lower'] = bb.bollinger_lband()
    df['BB_mid'] = bb.bollinger_mavg()

    df['Price_Momentum'] = df['Close'].diff(5)

    return df

def generate_signals(df, config):
    """Generate trading signals"""
    df = df.copy()

    df['Signal_Volume'] = 0
    df['Signal_ADX'] = 0
    df['Signal_OBV'] = 0
    df['Signal_Price'] = 0
    df['Signal_RSI'] = 0
    df['Signal_BB'] = 0
    df['Signal_Final'] = 0

    # Volume signals
    df.loc[df['Consecutive_Accel'] >= config.ACCEL_BARS_REQUIRED, 'Signal_Volume'] = 1
    df.loc[df['Consecutive_Accel'] <= -config.ACCEL_BARS_REQUIRED, 'Signal_Volume'] = -1

    # ADX
    if config.USE_ADX:
        df.loc[
            (df['ADX'] > config.ADX_THRESHOLD) &
            (df['ADX_pos'] > df['ADX_neg']),
            'Signal_ADX'
        ] = 1
        df.loc[
            (df['ADX'] > config.ADX_THRESHOLD) &
            (df['ADX_neg'] > df['ADX_pos']),
            'Signal_ADX'
        ] = -1

    # OBV
    if config.USE_OBV:
        if config.OBV_USE_TREND:
            df.loc[
                (df['OBV'] > df['OBV_MA']) &
                (df['OBV'] > df['OBV'].shift(1)),
                'Signal_OBV'
            ] = 1
            df.loc[
                (df['OBV'] < df['OBV_MA']) &
                (df['OBV'] < df['OBV'].shift(1)),
                'Signal_OBV'
            ] = -1
        else:
            df.loc[df['OBV'] > df['OBV'].shift(1), 'Signal_OBV'] = 1
            df.loc[df['OBV'] < df['OBV'].shift(1), 'Signal_OBV'] = -1

    # Price MA
    if config.USE_PRICE_MA:
        df.loc[
            (df['Close'] > df['SMA_20']) &
            (df['Price_Momentum'] > 0),
            'Signal_Price'
        ] = 1
        df.loc[
            (df['Close'] < df['SMA_20']) &
            (df['Price_Momentum'] < 0),
            'Signal_Price'
        ] = -1

    # RSI filter
    if config.USE_RSI_FILTER:
        df.loc[df['RSI'] < config.RSI_OVERSOLD, 'Signal_RSI'] = 1
        df.loc[df['RSI'] > config.RSI_OVERBOUGHT, 'Signal_RSI'] = -1

    # BB filter
    if config.USE_BB_FILTER:
        df.loc[df['Close'] < df['BB_lower'], 'Signal_BB'] = 1
        df.loc[df['Close'] > df['BB_upper'], 'Signal_BB'] = -1

    # Combine signals
    for i in range(len(df)):
        vol_signal = df['Signal_Volume'].iloc[i]

        if vol_signal == 0:
            continue

        confirmations = 0
        required_confirmations = 0

        if config.USE_ADX:
            required_confirmations += 1
            if df['Signal_ADX'].iloc[i] == vol_signal:
                confirmations += 1

        if config.USE_OBV:
            required_confirmations += 1
            if df['Signal_OBV'].iloc[i] == vol_signal:
                confirmations += 1

        if config.USE_PRICE_MA:
            required_confirmations += 1
            if df['Signal_Price'].iloc[i] == vol_signal:
                confirmations += 1

        if config.USE_BB_FILTER:
            required_confirmations += 1
            if df['Signal_BB'].iloc[i] == vol_signal:
                confirmations += 1

        # RSI filter
        if config.USE_RSI_FILTER:
            rsi_signal = df['Signal_RSI'].iloc[i]
            if vol_signal == 1 and rsi_signal == -1:
                continue
            if vol_signal == -1 and rsi_signal == 1:
                continue
            if rsi_signal == vol_signal:
                confirmations += 0.5

        if required_confirmations == 0:
            df.loc[df.index[i], 'Signal_Final'] = vol_signal
        elif confirmations >= required_confirmations * config.MIN_CONFIRMATIONS_RATIO:
            df.loc[df.index[i], 'Signal_Final'] = vol_signal

    return df

def can_trade(timestamp, config):
    """Check if trading is allowed at this timestamp"""
    if not config.USE_TRADING_HOURS:
        return True

    hour = timestamp.hour
    minute = timestamp.minute
    day_of_week = timestamp.weekday()

    day_allowed = [
        config.TRADE_MONDAY,
        config.TRADE_TUESDAY,
        config.TRADE_WEDNESDAY,
        config.TRADE_THURSDAY,
        config.TRADE_FRIDAY,
        False,
        False
    ]

    if not day_allowed[day_of_week]:
        return False

    if config.USE_CUSTOM_HOURS:
        current_minutes = hour * 60 + minute
        start_minutes = config.START_HOUR * 60 + config.START_MINUTE
        end_minutes = config.END_HOUR * 60 + config.END_MINUTE
        return start_minutes <= current_minutes <= end_minutes
    else:
        time_in_minutes = hour * 60 + minute

        if config.TRADE_ASIAN_SESSION:
            if 0 <= time_in_minutes <= (8 * 60):
                return True

        if config.TRADE_EUROPEAN_SESSION:
            if (7 * 60) <= time_in_minutes <= (16 * 60):
                return True

        if config.TRADE_AMERICAN_SESSION:
            if (13 * 60) <= time_in_minutes <= (22 * 60):
                return True

        return False

class Backtester:
    """Complete backtesting engine"""

    def __init__(self, config):
        self.config = config
        self.initial_capital = config.INITIAL_CAPITAL
        self.capital = config.INITIAL_CAPITAL
        self.positions = []
        self.trades = []
        self.equity_curve = []
        self.max_drawdown = 0
        self.peak_capital = config.INITIAL_CAPITAL
        self.current_day = None
        self.daily_profit = 0
        self.daily_loss_hit = False

    def run(self, df):
        """Run backtest"""
        for i in range(100, len(df)):
            timestamp = df.index[i]
            current_price = df['Close'].iloc[i]
            high = df['High'].iloc[i]
            low = df['Low'].iloc[i]
            atr = df['ATR'].iloc[i]
            signal = df['Signal_Final'].iloc[i]

            current_day = timestamp.date()
            if self.current_day != current_day:
                self.current_day = current_day
                self.daily_profit = 0
                self.daily_loss_hit = False

            if self.daily_profit <= self.config.MAX_DAILY_LOSS and not self.daily_loss_hit:
                self._close_all_positions(timestamp, current_price, 'daily_loss')
                self.daily_loss_hit = True

            if self.daily_loss_hit:
                continue

            if not can_trade(timestamp, self.config):
                continue

            self._update_positions(timestamp, current_price, high, low, atr)

            if signal != 0 and len(self.positions) < self.config.MAX_POSITIONS:
                if self.config.SAME_DIRECTION_ONLY and len(self.positions) > 0:
                    existing_direction = self.positions[0]['direction']
                    new_direction = 'long' if signal > 0 else 'short'
                    if existing_direction != new_direction:
                        continue

                self._open_position(timestamp, current_price, signal, atr)

            floating_pnl = sum([
                (current_price - p['entry_price']) * p['size'] if p['direction'] == 'long'
                else (p['entry_price'] - current_price) * p['size']
                for p in self.positions
            ])

            current_equity = self.capital + floating_pnl
            self.equity_curve.append({'timestamp': timestamp, 'equity': current_equity})

            if current_equity > self.peak_capital:
                self.peak_capital = current_equity

            drawdown = (self.peak_capital - current_equity) / self.peak_capital
            self.max_drawdown = max(self.max_drawdown, drawdown)

        self._close_all_positions(df.index[-1], df['Close'].iloc[-1], 'end')

        return self._get_results()

    def _open_position(self, timestamp, price, signal, atr):
        """Open position"""
        risk_amount = self.capital * self.config.RISK_PER_TRADE
        position_size = risk_amount / (self.config.ATR_STOP_MULTIPLIER * atr)
        position_size = min(position_size, 0.1 * 100000)

        position = {
            'id': len(self.trades) + len(self.positions),
            'timestamp': timestamp,
            'entry_price': price,
            'direction': 'long' if signal > 0 else 'short',
            'size': position_size,
            'bars_open': 0,
            'stop_loss': price - self.config.ATR_STOP_MULTIPLIER * atr if signal > 0
                        else price + self.config.ATR_STOP_MULTIPLIER * atr,
            'take_profit': price + self.config.TP_POINTS * 0.0001 if signal > 0
                          else price - self.config.TP_POINTS * 0.0001,
            'trailing_activated': False,
            'highest_profit': 0
        }

        commission = position_size * price * self.config.COMMISSION
        self.capital -= commission
        self.positions.append(position)

    def _close_position(self, position, timestamp, price, reason):
        """Close position"""
        if position not in self.positions:
            return

        if position['direction'] == 'long':
            pnl = (price - position['entry_price']) * position['size']
        else:
            pnl = (position['entry_price'] - price) * position['size']

        commission = position['size'] * price * self.config.COMMISSION
        net_pnl = pnl - commission

        self.capital += net_pnl
        self.daily_profit += net_pnl

        self.trades.append({
            'entry_time': position['timestamp'],
            'exit_time': timestamp,
            'entry_price': position['entry_price'],
            'exit_price': price,
            'direction': position['direction'],
            'pnl': net_pnl,
            'bars_held': position['bars_open'],
            'exit_reason': reason
        })

        try:
            self.positions.remove(position)
        except ValueError:
            pass

    def _close_all_positions(self, timestamp, price, reason):
        """Close all positions"""
        for position in list(self.positions):
            self._close_position(position, timestamp, price, reason)

    def _update_positions(self, timestamp, current_price, high, low, atr):
        """Update all positions"""
        point = 0.0001

        for position in list(self.positions):
            if position not in self.positions:
                continue

            position['bars_open'] += 1

            if position['direction'] == 'long':
                profit_points = (current_price - position['entry_price']) / point
            else:
                profit_points = (position['entry_price'] - current_price) / point

            if profit_points >= self.config.PROFIT_CLOSE:
                self._close_position(position, timestamp, current_price, 'profit_target')
                continue

            if self.config.USE_TRAILING_STOP:
                if profit_points >= self.config.TRAILING_START:
                    if not position['trailing_activated']:
                        position['trailing_activated'] = True
                        position['highest_profit'] = profit_points
                    else:
                        if profit_points > position['highest_profit']:
                            position['highest_profit'] = profit_points

                            trail_level = position['highest_profit'] - self.config.TRAILING_STEP

                            if position['direction'] == 'long':
                                new_sl = position['entry_price'] + trail_level * point
                                if new_sl > position['stop_loss']:
                                    position['stop_loss'] = new_sl
                            else:
                                new_sl = position['entry_price'] - trail_level * point
                                if new_sl < position['stop_loss']:
                                    position['stop_loss'] = new_sl

            if position['direction'] == 'long':
                if low <= position['stop_loss']:
                    self._close_position(position, timestamp, position['stop_loss'], 'stop_loss')
                    continue
                elif high >= position['take_profit']:
                    self._close_position(position, timestamp, position['take_profit'], 'take_profit')
                    continue
            else:
                if high >= position['stop_loss']:
                    self._close_position(position, timestamp, position['stop_loss'], 'stop_loss')
                    continue
                elif low <= position['take_profit']:
                    self._close_position(position, timestamp, position['take_profit'], 'take_profit')
                    continue

            if position['bars_open'] >= self.config.MAX_BARS_IN_TRADE:
                self._close_position(position, timestamp, current_price, 'time_limit')
                continue

    def _get_results(self):
        """Calculate results"""
        equity_df = pd.DataFrame(self.equity_curve) if self.equity_curve else pd.DataFrame({
            'timestamp': [datetime.now()],
            'equity': [self.initial_capital]
        })

        if len(self.trades) == 0:
            return {
                'total_return': 0,
                'total_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'max_drawdown': self.max_drawdown * 100,
                'sharpe_ratio': 0,
                'final_capital': self.capital,
                'trades_df': pd.DataFrame(),
                'equity_df': equity_df
            }

        trades_df = pd.DataFrame(self.trades)
        winning = trades_df[trades_df['pnl'] > 0]
        losing = trades_df[trades_df['pnl'] <= 0]

        gross_profit = winning['pnl'].sum() if len(winning) > 0 else 0
        gross_loss = abs(losing['pnl'].sum()) if len(losing) > 0 else 1

        equity_returns = equity_df['equity'].pct_change().dropna()
        sharpe = (equity_returns.mean() / equity_returns.std()) * np.sqrt(252) if len(equity_returns) > 1 and equity_returns.std() > 0 else 0

        return {
            'total_return': ((self.capital - self.initial_capital) / self.initial_capital) * 100,
            'total_trades': len(trades_df),
            'win_rate': (len(winning) / len(trades_df)) * 100,
            'avg_win': winning['pnl'].mean() if len(winning) > 0 else 0,
            'avg_loss': losing['pnl'].mean() if len(losing) > 0 else 0,
            'profit_factor': gross_profit / gross_loss,
            'max_drawdown': self.max_drawdown * 100,
            'sharpe_ratio': sharpe,
            'final_capital': self.capital,
            'trades_df': trades_df,
            'equity_df': equity_df
        }

# ============================================================================
# SISTEMA DE OPTIMIZACIÓN
# ============================================================================

class StrategyOptimizer:
    """Sistema de optimización de estrategia"""

    def __init__(self, opt_config=None):
        self.opt_config = opt_config or OptimizationConfig()
        self.results = []
        self.data = None

    def generate_param_combinations(self):
        """Genera todas las combinaciones de parámetros"""
        # Parámetros numéricos
        param_ranges = {}
        for param, (min_val, max_val, step) in self.opt_config.PARAMS_TO_OPTIMIZE.items():
            if step == 0:
                param_ranges[param] = [min_val]
            else:
                # Asegurar que incluimos el valor máximo
                values = []
                current = min_val
                while current <= max_val:
                    values.append(current)
                    current += step
                param_ranges[param] = values

        # Parámetros booleanos
        bool_ranges = {}
        for param, values in self.opt_config.BOOLEAN_PARAMS.items():
            bool_ranges[param] = values

        # Combinar todos
        all_param_names = list(param_ranges.keys()) + list(bool_ranges.keys())
        all_param_values = list(param_ranges.values()) + list(bool_ranges.values())

        # Generar combinaciones
        combinations = list(product(*all_param_values))

        print(f"\n🔬 Generando combinaciones de parámetros...")
        print(f"   Parámetros numéricos: {len(param_ranges)}")
        print(f"   Parámetros booleanos: {len(bool_ranges)}")
        print(f"   Total combinaciones: {len(combinations):,}")

        # Convertir a lista de diccionarios
        param_dicts = []
        for combo in combinations:
            param_dict = dict(zip(all_param_names, combo))
            param_dicts.append(param_dict)

        return param_dicts

    def create_config_from_params(self, params):
        """Crea un objeto de configuración desde parámetros"""
        config = StrategyConfig()

        # Parámetros fijos
        for param, value in self.opt_config.FIXED_PARAMS.items():
            setattr(config, param, value)

        # Parámetros optimizados
        for param, value in params.items():
            setattr(config, param, value)

        return config

    def run_single_backtest(self, params, df):
        """Ejecuta un backtest con una configuración específica"""
        try:
            # Crear configuración
            config = self.create_config_from_params(params)

            # Procesar datos
            df_processed = calculate_volume_derivatives(df.copy(), config)
            df_processed = add_technical_indicators(df_processed)
            df_processed = generate_signals(df_processed, config)

            # Ejecutar backtest
            backtester = Backtester(config)
            results = backtester.run(df_processed)

            # Filtrar por número mínimo de trades
            if results['total_trades'] < self.opt_config.MIN_TRADES_REQUIRED:
                return None

            # Añadir parámetros a resultados
            result = {**params, **results}

            return result

        except Exception as e:
            print(f"   ⚠️ Error en backtest: {str(e)}")
            return None

    def optimize(self):
        """Ejecuta la optimización completa"""
        print("\n" + "="*80)
        print("  OPTIMIZACIÓN AUTOMÁTICA DE ESTRATEGIA")
        print("="*80)

        # Descargar datos una sola vez
        print("\n📥 Descargando datos...")
        self.data = download_forex_data(
            self.opt_config.FIXED_PARAMS['SYMBOL'],
            self.opt_config.FIXED_PARAMS['PERIOD'],
            self.opt_config.FIXED_PARAMS['INTERVAL']
        )

        # Procesar indicadores base
        self.data = add_technical_indicators(self.data)

        # Generar combinaciones
        param_combinations = self.generate_param_combinations()

        # Ejecutar backtests
        print(f"\n🚀 Ejecutando {len(param_combinations):,} backtests...")
        print("   (Esto puede tomar varios minutos)")

        valid_results = []

        for i, params in enumerate(tqdm(param_combinations, desc="Progreso")):
            result = self.run_single_backtest(params, self.data)

            if result is not None:
                valid_results.append(result)

            # Mostrar progreso cada 100 iteraciones
            if (i + 1) % 100 == 0:
                print(f"\n   Completados: {i+1}/{len(param_combinations)} | Válidos: {len(valid_results)}")

        self.results = valid_results

        print(f"\n✅ Optimización completada!")
        print(f"   Total configuraciones probadas: {len(param_combinations):,}")
        print(f"   Configuraciones válidas (>{self.opt_config.MIN_TRADES_REQUIRED} trades): {len(valid_results)}")

        return self.results

    def get_top_configs(self, metric='sharpe_ratio', top_n=None):
        """Obtiene las mejores configuraciones por métrica"""
        if not self.results:
            print("⚠️ No hay resultados. Ejecuta optimize() primero.")
            return pd.DataFrame()

        top_n = top_n or self.opt_config.TOP_N_RESULTS

        # Convertir a DataFrame
        results_df = pd.DataFrame(self.results)

        # Ordenar por métrica
        results_df = results_df.sort_values(metric, ascending=False)

        # Tomar top N
        top_results = results_df.head(top_n)

        return top_results

    def save_results(self, filename=None):
        """Guarda todos los resultados a CSV"""
        if not self.results:
            print("⚠️ No hay resultados para guardar.")
            return

        filename = filename or self.opt_config.OUTPUT_FILE

        results_df = pd.DataFrame(self.results)
        results_df = results_df.sort_values('sharpe_ratio', ascending=False)

        results_df.to_csv(filename, index=False)
        print(f"\n💾 Resultados guardados en: {filename}")

    def save_best_configs(self, filename=None, top_n=None):
        """Guarda las mejores configuraciones en JSON"""
        filename = filename or self.opt_config.BEST_CONFIGS_FILE
        top_n = top_n or self.opt_config.TOP_N_RESULTS

        top_configs = self.get_top_configs(top_n=top_n)

        if top_configs.empty:
            print("⚠️ No hay configuraciones para guardar.")
            return

        # Convertir a lista de diccionarios
        configs_list = top_configs.to_dict('records')

        # Guardar en JSON
        with open(filename, 'w') as f:
            json.dump(configs_list, f, indent=4, default=str)

        print(f"💾 Top {top_n} configuraciones guardadas en: {filename}")

    def print_top_configs(self, top_n=None, metric='sharpe_ratio'):
        """Imprime las mejores configuraciones"""
        top_n = top_n or self.opt_config.TOP_N_RESULTS

        top_configs = self.get_top_configs(metric=metric, top_n=top_n)

        if top_configs.empty:
            print("⚠️ No hay configuraciones para mostrar.")
            return

        print(f"\n" + "="*80)
        print(f"  TOP {top_n} CONFIGURACIONES (ordenadas por {metric.upper()})")
        print("="*80)

        for idx, (i, row) in enumerate(top_configs.iterrows(), 1):
            print(f"\n🏆 RANK #{idx}")
            print(f"   {'━'*70}")

            # Métricas principales
            print(f"   📊 RENDIMIENTO:")
            print(f"      Sharpe Ratio:       {row['sharpe_ratio']:>8.3f}")
            print(f"      Total Return:       {row['total_return']:>8.2f}%")
            print(f"      Win Rate:           {row['win_rate']:>8.2f}%")
            print(f"      Profit Factor:      {row['profit_factor']:>8.2f}")
            print(f"      Max Drawdown:       {row['max_drawdown']:>8.2f}%")
            print(f"      Total Trades:       {row['total_trades']:>8.0f}")

            # Parámetros
            print(f"\n   ⚙️  PARÁMETROS:")
            for param in self.opt_config.PARAMS_TO_OPTIMIZE.keys():
                if param in row:
                    print(f"      {param:.<30} {row[param]:>10}")

            for param in self.opt_config.BOOLEAN_PARAMS.keys():
                if param in row:
                    print(f"      {param:.<30} {str(row[param]):>10}")

        print("\n" + "="*80)

    def plot_optimization_results(self):
        """Visualiza los resultados de la optimización"""
        if not self.results:
            print("⚠️ No hay resultados para visualizar.")
            return

        results_df = pd.DataFrame(self.results)

        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle('Resultados de Optimización', fontsize=16, fontweight='bold')

        # 1. Sharpe Ratio distribution
        ax = axes[0, 0]
        ax.hist(results_df['sharpe_ratio'], bins=50, alpha=0.7, edgecolor='black')
        ax.axvline(results_df['sharpe_ratio'].median(), color='red', linestyle='--', label='Mediana')
        ax.set_xlabel('Sharpe Ratio')
        ax.set_ylabel('Frecuencia')
        ax.set_title('Distribución de Sharpe Ratio')
        ax.legend()
        ax.grid(alpha=0.3)

        # 2. Return vs Drawdown
        ax = axes[0, 1]
        scatter = ax.scatter(results_df['max_drawdown'], results_df['total_return'],
                            c=results_df['sharpe_ratio'], cmap='RdYlGn', alpha=0.6)
        ax.set_xlabel('Max Drawdown (%)')
        ax.set_ylabel('Total Return (%)')
        ax.set_title('Return vs Drawdown')
        plt.colorbar(scatter, ax=ax, label='Sharpe Ratio')
        ax.grid(alpha=0.3)

        # 3. Win Rate vs Profit Factor
        ax = axes[0, 2]
        scatter = ax.scatter(results_df['win_rate'], results_df['profit_factor'],
                            c=results_df['sharpe_ratio'], cmap='RdYlGn', alpha=0.6)
        ax.set_xlabel('Win Rate (%)')
        ax.set_ylabel('Profit Factor')
        ax.set_title('Win Rate vs Profit Factor')
        plt.colorbar(scatter, ax=ax, label='Sharpe Ratio')
        ax.grid(alpha=0.3)

        # 4. Total Return distribution
        ax = axes[1, 0]
        ax.hist(results_df['total_return'], bins=50, alpha=0.7, edgecolor='black', color='green')
        ax.axvline(0, color='red', linestyle='--', linewidth=2)
        ax.set_xlabel('Total Return (%)')
        ax.set_ylabel('Frecuencia')
        ax.set_title('Distribución de Retornos')
        ax.grid(alpha=0.3)

        # 5. Trades vs Sharpe
        ax = axes[1, 1]
        scatter = ax.scatter(results_df['total_trades'], results_df['sharpe_ratio'],
                            alpha=0.6, c=results_df['total_return'], cmap='RdYlGn')
        ax.set_xlabel('Total Trades')
        ax.set_ylabel('Sharpe Ratio')
        ax.set_title('Número de Trades vs Sharpe')
        plt.colorbar(scatter, ax=ax, label='Return (%)')
        ax.grid(alpha=0.3)

        # 6. Top 10 configs
        ax = axes[1, 2]
        top_10 = results_df.nlargest(10, 'sharpe_ratio')
        y_pos = np.arange(len(top_10))
        ax.barh(y_pos, top_10['sharpe_ratio'].values, color='steelblue', alpha=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels([f"Config {i+1}" for i in range(len(top_10))])
        ax.set_xlabel('Sharpe Ratio')
        ax.set_title('Top 10 Configuraciones')
        ax.grid(alpha=0.3, axis='x')

        plt.tight_layout()
        plt.savefig('optimization_results.png', dpi=300, bbox_inches='tight')
        print("\n📊 Gráfico guardado como: optimization_results.png")
        plt.show()

# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================

if __name__ == "__main__":

    # Configurar optimización
    opt_config = OptimizationConfig()

    # Crear optimizador
    optimizer = StrategyOptimizer(opt_config)

    # Ejecutar optimización
    results = optimizer.optimize()

    # Mostrar mejores configuraciones
    optimizer.print_top_configs(top_n=10)

    # Guardar resultados
    optimizer.save_results()
    optimizer.save_best_configs()

    # Visualizar
    optimizer.plot_optimization_results()

    print("\n✅ Proceso completado!")
    print(f"   📄 Todos los resultados: {opt_config.OUTPUT_FILE}")
    print(f"   🏆 Mejores configs: {opt_config.BEST_CONFIGS_FILE}")
    print(f"   📊 Gráficos: optimization_results.png")
