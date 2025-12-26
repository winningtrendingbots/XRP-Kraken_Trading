
# ============================================================================
# COMPLETE STRATEGY CONFIGURATION
# ============================================================================


    """
    Complete configuration with all MQL5 features
    """
    # ========================================
    # 📊 VOLUME DERIVATIVES (CORE)
    # ========================================
    VOLUME_SMOOTH_PERIODS = 4      # Volume smoothing periods
    ACCEL_BARS_REQUIRED = 2        # Consecutive acceleration bars (1-5)
    
    # ========================================
    # ✅ CONFIRMATIONS
    # ========================================
    USE_ADX = False
    ADX_THRESHOLD = 20
    
    USE_OBV = False
    OBV_USE_TREND = False
    
    USE_PRICE_MA = False
    
    USE_RSI_FILTER = False
    RSI_OVERSOLD = 35
    RSI_OVERBOUGHT = 65
    
    USE_BB_FILTER = False
    
    MIN_CONFIRMATIONS_RATIO = 0.25
    
    # ========================================
    # 💰 RISK MANAGEMENT
    # ========================================
    INITIAL_CAPITAL = 200
    RISK_PER_TRADE = 0.05          # Risk per trade (0.01 = 1%)
    TP_POINTS = 100                # Take profit in points
    ATR_STOP_MULTIPLIER = 1.0      # Stop loss = ATR * this
    
    # ========================================
    # 🎯 TRAILING STOP
    # ========================================
    USE_TRAILING_STOP = True       # Enable trailing stop
    TRAILING_START = 25            # Points profit to activate trailing
    TRAILING_STEP = 15             # Trail by this many points
    
    # ========================================
    # 💵 PROFIT & LOSS LIMITS
    # ========================================
    PROFIT_CLOSE = 50              # Close position at this profit (points)
    MAX_DAILY_LOSS = -20          # Max daily loss in $ (negative value)
    
    # ========================================
    # 📍 POSITION MANAGEMENT
    # ========================================
    MAX_POSITIONS = 1             # Max simultaneous positions
    SAME_DIRECTION_ONLY = False    # Only positions in same direction
    MAX_BARS_IN_TRADE = 2         # Max hours in trade (for 1h TF)
    
    # ========================================
    # ⏰ TRADING HOURS
    # ========================================
    USE_TRADING_HOURS = True       # Enable trading hours restriction
    
    # Session-based trading
    TRADE_ASIAN_SESSION = False    # 00:00 - 08:00 GMT
    TRADE_EUROPEAN_SESSION = True  # 07:00 - 16:00 GMT
    TRADE_AMERICAN_SESSION = True  # 13:00 - 22:00 GMT
    SESSION_BUFFER = 15            # Minutes buffer between sessions
    
    # Custom hours (if USE_CUSTOM_HOURS = True, overrides sessions)
    USE_CUSTOM_HOURS = False       # Use specific hours instead of sessions
    START_HOUR = 0                 # Trading start hour (0-23)
    START_MINUTE = 30              # Trading start minute (0-59)
    END_HOUR = 23                  # Trading end hour (0-23)
    END_MINUTE = 59                # Trading end minute (0-59)
    
    # Days of week
    TRADE_MONDAY = True
    TRADE_TUESDAY = True
    TRADE_WEDNESDAY = True
    TRADE_THURSDAY = True
    TRADE_FRIDAY = True
    
    # ========================================
    # 📈 DATA SETTINGS
    # ========================================
    SYMBOL = 'XRP-USD'
    PERIOD = '2y'
    INTERVAL = '1h'
    COMMISSION = 0.0002            # 0.02%
