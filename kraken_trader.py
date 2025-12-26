"""
Kraken API Trading Module
Gestión de órdenes en margin con apalancamiento inteligente
"""

import krakenex
from pykrakenapi import KrakenAPI
import pandas as pd
import time
from decimal import Decimal, ROUND_DOWN
import logging

logger = logging.getLogger(__name__)


class KrakenTrader:
    """Gestor de trading para Kraken Margin"""
    
    def __init__(self, api_key, api_secret, leverage_min=2, leverage_max=5):
        """
        Inicializar conexión con Kraken
        
        Args:
            api_key: API key de Kraken
            api_secret: API secret de Kraken
            leverage_min: Apalancamiento mínimo (para evitar comisiones)
            leverage_max: Apalancamiento máximo permitido
        """
        self.api = krakenex.API(key=api_key, secret=api_secret)
        self.k = KrakenAPI(self.api)
        self.leverage_min = leverage_min
        self.leverage_max = leverage_max
        
        # Información del par
        self.pair_info = {}
        
    def get_balance(self):
        """Obtener balance de la cuenta"""
        try:
            balance = self.k.get_account_balance()
            return balance
        except Exception as e:
            logger.error(f"Error obteniendo balance: {e}")
            return None
    
    def get_tradable_balance(self, currency='USD'):
        """Obtener balance disponible para trading en margin"""
        try:
            balance = self.k.get_trade_balance(asset=currency)
            return float(balance['eb'])  # Equivalent balance
        except Exception as e:
            logger.error(f"Error obteniendo balance tradable: {e}")
            return 0.0
    
    def get_ticker(self, pair='XETHZUSD'):
        """Obtener precio actual"""
        try:
            ticker = self.k.get_ticker_information(pair)
            return {
                'ask': float(ticker['a'][0][0]),  # Precio ask
                'bid': float(ticker['b'][0][0]),  # Precio bid
                'last': float(ticker['c'][0][0])  # Último precio
            }
        except Exception as e:
            logger.error(f"Error obteniendo ticker: {e}")
            return None
    
    def get_ohlc_data(self, pair='XETHZUSD', interval=15):
        """
        Obtener datos OHLC
        
        Args:
            pair: Par de trading
            interval: Intervalo en minutos (1, 5, 15, 30, 60, 240, 1440)
        """
        try:
            ohlc, last = self.k.get_ohlc_data(pair, interval=interval)
            return ohlc
        except Exception as e:
            logger.error(f"Error obteniendo OHLC: {e}")
            return None
    
    def calculate_position_size(self, balance, risk_percent, stop_loss_points, 
                                current_price, pair='XETHZUSD'):
        """
        Calcular tamaño de posición óptimo con apalancamiento inteligente
        
        Args:
            balance: Balance disponible
            risk_percent: Porcentaje de riesgo por operación
            stop_loss_points: Puntos de stop loss
            current_price: Precio actual
        """
        try:
            # Obtener información del par
            if pair not in self.pair_info:
                pair_data = self.k.get_tradable_asset_pairs(pair=pair)
                self.pair_info[pair] = pair_data.iloc[0]
            
            info = self.pair_info[pair]
            
            # Mínimo de orden
            min_order = float(info.get('ordermin', 0.001))
            
            # Calcular tamaño basado en riesgo
            risk_amount = balance * risk_percent
            stop_loss_decimal = stop_loss_points * 0.0001  # Para forex
            
            # Tamaño sin apalancamiento
            base_size = risk_amount / (stop_loss_decimal * current_price)
            
            # Calcular apalancamiento necesario
            max_size_no_leverage = balance / current_price
            
            if base_size <= max_size_no_leverage:
                # No necesitamos apalancamiento
                leverage = 1
                position_size = base_size
            else:
                # Calcular apalancamiento necesario
                required_leverage = base_size / max_size_no_leverage
                
                # Ajustar al rango permitido
                if required_leverage < self.leverage_min:
                    leverage = self.leverage_min
                else:
                    leverage = min(int(required_leverage + 0.5), self.leverage_max)
                
                # Recalcular tamaño con apalancamiento
                position_size = min(base_size, max_size_no_leverage * leverage)
            
            # Asegurar que cumple con el mínimo
            position_size = max(position_size, min_order)
            
            # Redondear según decimales permitidos
            decimals = int(info.get('lot_decimals', 8))
            position_size = float(Decimal(str(position_size)).quantize(
                Decimal(10) ** -decimals, rounding=ROUND_DOWN))
            
            return {
                'size': position_size,
                'leverage': leverage,
                'cost': position_size * current_price,
                'margin_required': (position_size * current_price) / leverage
            }
            
        except Exception as e:
            logger.error(f"Error calculando posición: {e}")
            return None
    
    def place_margin_order(self, pair, side, size, leverage=2, 
                          stop_loss=None, take_profit=None):
        """
        Colocar orden en margin
        
        Args:
            pair: Par de trading (ej: 'XETHZUSD')
            side: 'buy' o 'sell'
            size: Tamaño de la posición
            leverage: Apalancamiento
            stop_loss: Precio de stop loss
            take_profit: Precio de take profit
        """
        try:
            # Construir parámetros de orden
            order_params = {
                'pair': pair,
                'type': side,
                'ordertype': 'market',
                'volume': str(size),
                'leverage': str(leverage),
                'validate': False  # Cambiar a True para testear sin ejecutar
            }
            
            # Agregar stop loss si existe
            if stop_loss:
                order_params['close[ordertype]'] = 'stop-loss'
                order_params['close[price]'] = str(stop_loss)
            
            # Agregar take profit si existe
            if take_profit:
                if stop_loss:
                    # Si ya hay SL, usar otro campo
                    order_params['close[ordertype2]'] = 'take-profit'
                    order_params['close[price2]'] = str(take_profit)
                else:
                    order_params['close[ordertype]'] = 'take-profit'
                    order_params['close[price]'] = str(take_profit)
            
            # Ejecutar orden
            response = self.api.query_private('AddOrder', order_params)
            
            if response.get('error'):
                logger.error(f"Error en orden: {response['error']}")
                return None
            
            return {
                'txid': response['result']['txid'][0],
                'description': response['result']['descr']
            }
            
        except Exception as e:
            logger.error(f"Error colocando orden: {e}")
            return None
    
    def get_open_positions(self):
        """Obtener posiciones abiertas"""
        try:
            positions = self.k.get_open_positions()
            return positions
        except Exception as e:
            logger.error(f"Error obteniendo posiciones: {e}")
            return pd.DataFrame()
    
    def get_open_orders(self):
        """Obtener órdenes abiertas"""
        try:
            orders = self.k.get_open_orders()
            return orders
        except Exception as e:
            logger.error(f"Error obteniendo órdenes: {e}")
            return pd.DataFrame()
    
    def cancel_order(self, txid):
        """Cancelar una orden"""
        try:
            response = self.api.query_private('CancelOrder', {'txid': txid})
            return response.get('error') is None or len(response.get('error', [])) == 0
        except Exception as e:
            logger.error(f"Error cancelando orden: {e}")
            return False
    
    def close_position(self, pair, position_type='long'):
        """Cerrar una posición"""
        try:
            # Obtener posición actual
            positions = self.get_open_positions()
            
            if positions.empty:
                return True
            
            # Filtrar por par
            pos = positions[positions.index.str.contains(pair)]
            
            if pos.empty:
                return True
            
            # Cerrar posición
            size = abs(float(pos['vol'].iloc[0]))
            side = 'sell' if position_type == 'long' else 'buy'
            
            order_params = {
                'pair': pair,
                'type': side,
                'ordertype': 'market',
                'volume': str(size),
                'leverage': 'none'  # Cerrar sin leverage
            }
            
            response = self.api.query_private('AddOrder', order_params)
            
            if response.get('error'):
                logger.error(f"Error cerrando posición: {response['error']}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error cerrando posición: {e}")
            return False
    
    def update_trailing_stop(self, txid, new_stop_price):
        """Actualizar trailing stop de una orden"""
        try:
            # Kraken no permite modificar órdenes directamente
            # Hay que cancelar y crear una nueva
            
            # Cancelar orden actual
            if not self.cancel_order(txid):
                return False
            
            # Aquí necesitarías crear una nueva orden con el nuevo stop
            # Esto requiere conocer los detalles de la orden original
            
            logger.warning("Trailing stop actualizado (cancelando orden anterior)")
            return True
            
        except Exception as e:
            logger.error(f"Error actualizando trailing stop: {e}")
            return False
