"""
State Manager Module
Persistencia de estado entre ejecuciones del bot
"""

import json
import os
from datetime import datetime, date
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class StateManager:
    """Gestor de estado persistente"""
    
    def __init__(self, state_file='trading_state.json'):
        """
        Inicializar gestor de estado
        
        Args:
            state_file: Archivo donde guardar el estado
        """
        self.state_file = state_file
        self.state = self._load_state()
    
    def _load_state(self):
        """Cargar estado desde archivo"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    logger.info(f"Estado cargado desde {self.state_file}")
                    return state
            else:
                logger.info("No existe estado previo, creando nuevo")
                return self._create_initial_state()
        except Exception as e:
            logger.error(f"Error cargando estado: {e}")
            return self._create_initial_state()
    
    def _create_initial_state(self):
        """Crear estado inicial"""
        return {
            'positions': {},
            'daily_stats': {
                'date': str(date.today()),
                'profit': 0.0,
                'trades': 0,
                'winning_trades': 0,
                'losing_trades': 0
            },
            'capital': 0.0,
            'last_update': None,
            'trading_enabled': True
        }
    
    def save_state(self):
        """Guardar estado a archivo"""
        try:
            self.state['last_update'] = datetime.now().isoformat()
            
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            
            logger.info("Estado guardado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error guardando estado: {e}")
            return False
    
    def reset_daily_stats(self):
        """Resetear estadísticas diarias"""
        today = str(date.today())
        
        if self.state['daily_stats']['date'] != today:
            logger.info(f"Reseteando estadísticas diarias (nuevo día: {today})")
            
            self.state['daily_stats'] = {
                'date': today,
                'profit': 0.0,
                'trades': 0,
                'winning_trades': 0,
                'losing_trades': 0
            }
            self.state['trading_enabled'] = True
            self.save_state()
    
    def add_position(self, position_id, position_data):
        """Agregar posición al estado"""
        self.state['positions'][position_id] = {
            'id': position_id,
            'entry_time': datetime.now().isoformat(),
            'entry_price': position_data['entry_price'],
            'size': position_data['size'],
            'direction': position_data['direction'],
            'stop_loss': position_data['stop_loss'],
            'take_profit': position_data['take_profit'],
            'leverage': position_data['leverage'],
            'trailing_stop': position_data.get('trailing_stop', None),
            'highest_price': position_data['entry_price'] if position_data['direction'] == 'long' else None,
            'lowest_price': position_data['entry_price'] if position_data['direction'] == 'short' else None,
            'bars_open': 0
        }
        self.save_state()
        logger.info(f"Posición {position_id} agregada al estado")
    
    def update_position(self, position_id, updates):
        """Actualizar datos de una posición"""
        if position_id in self.state['positions']:
            self.state['positions'][position_id].update(updates)
            self.save_state()
            logger.info(f"Posición {position_id} actualizada")
        else:
            logger.warning(f"Posición {position_id} no encontrada en estado")
    
    def remove_position(self, position_id):
        """Eliminar posición del estado"""
        if position_id in self.state['positions']:
            del self.state['positions'][position_id]
            self.save_state()
            logger.info(f"Posición {position_id} eliminada del estado")
        else:
            logger.warning(f"Posición {position_id} no encontrada en estado")
    
    def get_position(self, position_id):
        """Obtener datos de una posición"""
        return self.state['positions'].get(position_id, None)
    
    def get_all_positions(self):
        """Obtener todas las posiciones"""
        return self.state['positions']
    
    def add_trade(self, pnl):
        """Registrar trade completado"""
        self.reset_daily_stats()  # Verificar si es nuevo día
        
        self.state['daily_stats']['trades'] += 1
        self.state['daily_stats']['profit'] += pnl
        
        if pnl > 0:
            self.state['daily_stats']['winning_trades'] += 1
        else:
            self.state['daily_stats']['losing_trades'] += 1
        
        self.save_state()
        logger.info(f"Trade registrado: P&L ${pnl:.2f}")
    
    def get_daily_profit(self):
        """Obtener profit del día"""
        self.reset_daily_stats()
        return self.state['daily_stats']['profit']
    
    def is_daily_loss_limit_hit(self, max_loss):
        """Verificar si se alcanzó el límite de pérdida diaria"""
        self.reset_daily_stats()
        daily_profit = self.state['daily_stats']['profit']
        
        if daily_profit <= max_loss:
            self.state['trading_enabled'] = False
            self.save_state()
            logger.warning(f"Límite de pérdida diaria alcanzado: ${daily_profit:.2f}")
            return True
        
        return False
    
    def can_trade(self):
        """Verificar si se puede tradear"""
        self.reset_daily_stats()
        return self.state['trading_enabled']
    
    def set_capital(self, capital):
        """Actualizar capital"""
        self.state['capital'] = capital
        self.save_state()
    
    def get_capital(self):
        """Obtener capital actual"""
        return self.state['capital']
    
    def get_daily_stats(self):
        """Obtener estadísticas diarias"""
        self.reset_daily_stats()
        stats = self.state['daily_stats'].copy()
        
        # Calcular win rate
        total = stats['trades']
        if total > 0:
            stats['win_rate'] = (stats['winning_trades'] / total) * 100
        else:
            stats['win_rate'] = 0.0
        
        return stats
    
    def increment_bars_open(self):
        """Incrementar contador de barras para todas las posiciones"""
        for position_id in self.state['positions']:
            self.state['positions'][position_id]['bars_open'] += 1
        self.save_state()
    
    def update_position_extremes(self, position_id, current_price):
        """Actualizar precios extremos de una posición (para trailing stop)"""
        if position_id not in self.state['positions']:
            return
        
        position = self.state['positions'][position_id]
        
        if position['direction'] == 'long':
            if position['highest_price'] is None or current_price > position['highest_price']:
                position['highest_price'] = current_price
        else:  # short
            if position['lowest_price'] is None or current_price < position['lowest_price']:
                position['lowest_price'] = current_price
        
        self.save_state()
