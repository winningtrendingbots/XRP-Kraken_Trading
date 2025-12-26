# ⚡ Quick Start - Bot de Trading Kraken

Guía rápida para poner el bot en marcha en **5 minutos**.

---

## 📋 Prerequisitos

- [ ] Cuenta en Kraken con fondos
- [ ] Cuenta en Telegram
- [ ] Cuenta en GitHub

---

## 🚀 Configuración Express (5 minutos)

### **Paso 1: Clona el Repositorio** (30 seg)

```bash
git clone https://github.com/TU_USUARIO/kraken-trading-bot.git
cd kraken-trading-bot
```

### **Paso 2: Configura Credenciales** (2 min)

#### A. Kraken API:
1. Ve a [Kraken → Settings → API](https://www.kraken.com/u/security/api)
2. Click en "Generate New Key"
3. Nombre: `Trading Bot`
4. Permisos necesarios:
   - ✅ Query Funds
   - ✅ Query Open Orders & Trades
   - ✅ Query Closed Orders & Trades
   - ✅ Create & Modify Orders
   - ✅ Cancel/Close Orders
5. Guarda tu **API Key** y **Private Key**

#### B. Telegram Bot:
1. Abre Telegram → busca [@BotFather](https://t.me/botfather)
2. Envía: `/newbot`
3. Nombre: `Mi Trading Bot`
4. Username: `mi_trading_bot` (debe terminar en `_bot`)
5. Guarda el **Bot Token**

6. Para obtener tu **Chat ID**:
   - Envía cualquier mensaje a tu bot
   - Visita: `https://api.telegram.org/bot<TU_TOKEN>/getUpdates`
   - Busca: `"chat":{"id":12345678}`

### **Paso 3: Configura GitHub Secrets** (1 min)

1. Ve a tu repositorio en GitHub
2. **Settings** → **Secrets and variables** → **Actions**
3. Click en **New repository secret** 4 veces:

```
Nombre: KRAKEN_API_KEY
Valor:  [tu API key de Kraken]

Nombre: KRAKEN_API_SECRET
Valor:  [tu Private key de Kraken]

Nombre: TELEGRAM_BOT_TOKEN
Valor:  [token de @BotFather]

Nombre: TELEGRAM_CHAT_ID
Valor:  [tu chat ID numérico]
```

### **Paso 4: Prueba Local (Opcional)** (1 min)

```bash
# Instalar dependencias
pip install -r requirements.txt

# Crear archivo .env
cat > .env << EOF
KRAKEN_API_KEY=tu_api_key
KRAKEN_API_SECRET=tu_private_key
TELEGRAM_BOT_TOKEN=tu_bot_token
TELEGRAM_CHAT_ID=tu_chat_id
EOF

# Exportar variables
export $(cat .env | xargs)

# Ejecutar tests
python test_connection.py
```

Si ves "✅ TODOS LOS TESTS PASARON", continúa.

### **Paso 5: Activar Bot** (30 seg)

```bash
# Subir a GitHub
git add .
git commit -m "Configurar bot de trading"
git push
```

El bot empezará a ejecutarse automáticamente cada 15 minutos.

---

## 📱 Verificar que Funciona

Dentro de 15 minutos deberías recibir en Telegram:

```
🚀 BOT DE TRADING INICIADO

📅 Fecha: 2025-12-26 16:00:00
💱 Par: ETH-USD
⏱ Intervalo: 1h

⚙️ Configuración:
• Capital inicial: $10,000.00
• Riesgo por trade: 5.0%
• Apalancamiento: 2-5x
• Trailing stop: ✅
• Pérdida diaria máx: $-200.0

✅ Sistema listo para operar
```

---

## ⚙️ Configuración Recomendada por Nivel

### 🟢 Principiante (Conservador)
```python
# En live_trading.py → ProductionConfig:

RISK_PER_TRADE = 0.02          # 2% por trade
MAX_DAILY_LOSS = -50           # $50 máximo/día
MAX_POSITIONS = 1              # Solo 1 posición
LEVERAGE_MIN = 2
LEVERAGE_MAX = 2               # Sin leverage alto

USE_ADX = True                 # Más confirmaciones
USE_RSI_FILTER = True
MIN_CONFIRMATIONS_RATIO = 0.5  # 50% confirmaciones
```

### 🟡 Intermedio (Balanceado)
```python
RISK_PER_TRADE = 0.03          # 3% por trade
MAX_DAILY_LOSS = -100          # $100 máximo/día
MAX_POSITIONS = 3              # Hasta 3 posiciones
LEVERAGE_MAX = 3               # Leverage moderado

USE_ADX = True
MIN_CONFIRMATIONS_RATIO = 0.3
```

### 🔴 Avanzado (Agresivo)
```python
RISK_PER_TRADE = 0.05          # 5% por trade
MAX_DAILY_LOSS = -200          # $200 máximo/día
MAX_POSITIONS = 5              # Múltiples posiciones
LEVERAGE_MAX = 5               # Leverage alto

USE_ADX = False                # Menos restricciones
MIN_CONFIRMATIONS_RATIO = 0.25
```

**⚠️ Empieza SIEMPRE con configuración Principiante**

---

## 📊 Monitoreo Diario

### Telegram (Tiempo Real)
Recibirás notificaciones para:
- 🟢 Compras ejecutadas
- 🔴 Ventas ejecutadas
- 💰 Posiciones cerradas con P&L
- 📈 Updates de trailing stop
- ⚠️ Alertas importantes

### GitHub Actions (Logs Detallados)
1. Ve a tu repo → **Actions**
2. Click en último "Kraken Trading Bot" run
3. Abre **trade** → **Ejecutar bot de trading**
4. Verás logs completos

---

## 🛑 Control Manual

### Pausar el Bot:
```
GitHub → Actions → Kraken Trading Bot → "..." → Disable workflow
```

### Reanudar:
```
GitHub → Actions → Kraken Trading Bot → "..." → Enable workflow
```

### Ejecutar Ahora:
```
GitHub → Actions → Kraken Trading Bot → Run workflow
```

### Cerrar Todas las Posiciones:
En Kraken web → Trade → Cerrar posiciones manualmente

O edita `live_trading.py` temporalmente:
```python
# Al inicio de run():
self.kraken.close_position('XETHZUSD', 'long')
self.kraken.close_position('XETHZUSD', 'short')
return  # Salir sin operar
```

---

## 🔧 Troubleshooting Express

### ❌ No recibo mensajes de Telegram
```bash
# Verificar bot token
curl https://api.telegram.org/bot<TU_TOKEN>/getMe

# Verificar chat ID
curl https://api.telegram.org/bot<TU_TOKEN>/getUpdates

# Asegúrate de haber enviado /start al bot
```

### ❌ Workflow falla en GitHub
1. Revisa que los 4 Secrets estén configurados
2. Verifica que no hay espacios extras en los secrets
3. Mira el error exacto en los logs del workflow
4. Ejecuta `python debug_data.py` localmente

### ❌ "Insufficient funds"
- Verifica balance en Kraken → Funding
- Asegúrate de tener al menos $100 disponibles
- Margin debe estar activo en tu cuenta

### ❌ No ejecuta trades
- Revisa horario: `USE_TRADING_HOURS = True/False`
- Espera señales: la estrategia es selectiva
- Verifica que no alcanzaste límite diario
- Mira logs para ver si detecta señales

---

## 📈 Optimización (Después de 1 semana)

### Métricas a Revisar:

```python
# Revisa resumen diario en Telegram
Win Rate: debería estar entre 40-60%
P&L diario: positivo más días que negativo
Drawdown: no más de 20%
```

### Si Win Rate < 40%:
```python
# Aumenta confirmaciones
USE_ADX = True
USE_RSI_FILTER = True
MIN_CONFIRMATIONS_RATIO = 0.5
```

### Si muy pocos trades:
```python
# Relaja restricciones
USE_ADX = False
MIN_CONFIRMATIONS_RATIO = 0.25
USE_TRADING_HOURS = False  # Opera 24/7
```

### Si pérdidas grandes:
```python
# Reduce riesgo
RISK_PER_TRADE = 0.01  # 1%
MAX_DAILY_LOSS = -50
ATR_STOP_MULTIPLIER = 2.5  # Stop más amplio
```

---

## 📚 Recursos Útiles

### Scripts Disponibles:
```bash
python setup.py           # Configuración interactiva
python test_connection.py # Verificar conexiones
python debug_data.py      # Diagnosticar datos
python live_trading.py    # Ejecutar bot (manual)
```

### Documentación:
- `README.md` - Guía completa
- `FAQ.md` - Preguntas frecuentes
- `BUGFIX_NOTES.md` - Correcciones aplicadas

### Archivos a Editar:
- `live_trading.py` → Clase `ProductionConfig` (parámetros)
- `.github/workflows/trading.yml` → Schedule (frecuencia)

---

## 🎯 Checklist de Éxito

Después de 24 horas, deberías tener:

- [ ] ✅ Bot ejecutándose cada 15 min
- [ ] ✅ Notificaciones en Telegram funcionando
- [ ] ✅ Al menos 1 señal detectada (puede no ejecutar si no cumple condiciones)
- [ ] ✅ Logs visibles en GitHub Actions
- [ ] ✅ Estado guardándose correctamente
- [ ] ✅ Sin errores en workflows

Si todo está ✅, ¡tu bot está funcionando correctamente!

---

## 💡 Pro Tips

1. **Empieza pequeño**: $100-500 para probar
2. **Monitorea diario**: Revisa Telegram y GitHub Actions
3. **Ajusta gradualmente**: No cambies todo a la vez
4. **Ten paciencia**: La estrategia no opera cada 15 min
5. **Mantén logs**: Descarga artifacts de GitHub Actions
6. **Backups**: El estado se guarda automáticamente
7. **2FA siempre**: En Kraken y GitHub

---

## 🚨 Recordatorios Importantes

⚠️ **Nunca compartas tus API keys**
⚠️ **Empieza con cantidades que puedas perder**
⚠️ **El trading tiene riesgos**
⚠️ **No dejes el bot sin supervisión mucho tiempo**
⚠️ **Revisa métricas semanalmente**

---

## 🎉 ¡Listo!

Tu bot ya está operando. Recibirás updates en Telegram.

**Siguiente paso:** Espera 24-48 horas y revisa las métricas.

**Preguntas:** Revisa `FAQ.md`

**¡Feliz trading! 🚀📈**
