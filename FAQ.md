# ❓ Preguntas Frecuentes (FAQ)

## 📋 Índice
1. [Configuración Inicial](#configuración-inicial)
2. [Problemas Comunes](#problemas-comunes)
3. [Trading y Estrategia](#trading-y-estrategia)
4. [Costos y Comisiones](#costos-y-comisiones)
5. [Seguridad](#seguridad)
6. [Optimización](#optimización)

---

## Configuración Inicial

### ¿Cuánto capital necesito para empezar?
**Recomendado mínimo: $500-1000**
- Con menos de $500, las comisiones impactarán significativamente
- El bot calculará automáticamente el tamaño de posición según tu balance
- Puedes empezar con menos para probar, pero ten en cuenta las limitaciones

### ¿Qué permisos necesita la API Key de Kraken?
Permisos necesarios:
- ✅ Query Funds
- ✅ Query Open Orders & Trades
- ✅ Query Closed Orders & Trades
- ✅ Create & Modify Orders
- ✅ Cancel/Close Orders

**NO necesitas:**
- ❌ Withdraw Funds
- ❌ Transfer to/from subaccounts

### ¿Puedo usar esto con otros exchanges?
No directamente. El código está específicamente diseñado para Kraken. Para usar otros exchanges necesitarías:
- Adaptar el módulo `kraken_trader.py`
- Cambiar la librería de API
- Ajustar el formato de órdenes y datos

### ¿Funciona en cuenta demo?
Kraken no ofrece cuenta demo con API. Alternativas:
- Empieza con cantidades muy pequeñas
- Usa el script de backtest para probar la estrategia
- Considera paper trading en otro exchange

---

## Problemas Comunes

### Error: "TypeError: '>=' not supported between instances of 'float' and 'NoneType'"

**Causa:** Los datos descargados de Kraken contienen valores nulos o la estructura no es la esperada.

**Solución:**

1. **Ejecuta el script de diagnóstico:**
   ```bash
   export $(cat .env | xargs)
   python debug_data.py
   ```
   Esto mostrará exactamente qué hay en los datos.

2. **Verifica el par de trading:**
   - ETH/USD en Kraken es `XETHZUSD`
   - XRP/USD en Kraken es `XXRPZUSD`
   - BTC/USD en Kraken es `XXBTZUSD`

3. **El código actualizado ya maneja esto:**
   - Limpia valores nulos automáticamente
   - Rellena gaps con forward/backward fill
   - Valida datos antes de calcular indicadores

4. **Si sigue fallando:**
   - Revisa los logs detallados en GitHub Actions
   - Verifica que el par tiene liquidez suficiente
   - Prueba con otro par (ej: XXBTZUSD para Bitcoin)

### El bot no ejecuta ninguna orden

**Posibles causas:**

1. **Horario de trading**: Verifica `USE_TRADING_HOURS` en config
   ```python
   USE_TRADING_HOURS = True
   TRADE_EUROPEAN_SESSION = True
   TRADE_AMERICAN_SESSION = True
   ```

2. **Balance insuficiente**: Mínimo ~$100 disponible
   - Verifica en Kraken → Funding
   - Asegúrate de tener margen disponible

3. **No hay señales**: La estrategia es selectiva
   - Revisa los logs para ver las señales detectadas
   - Considera ajustar `ACCEL_BARS_REQUIRED`
   - Activa menos confirmaciones

4. **Límite de pérdida diaria alcanzado**
   - El bot se detiene si alcanza `MAX_DAILY_LOSS`
   - Se resetea automáticamente al día siguiente

### Error: "API key invalid"

**Soluciones:**
1. Verifica que copiaste la key completa (incluido == al final)
2. Confirma que la key está activa en Kraken
3. Revisa que los Secrets en GitHub están bien escritos:
   - No espacios extras
   - No saltos de línea
   - Formato exacto de Kraken

### Error: "Insufficient funds"

**Causas comunes:**
1. **Balance real vs disponible**:
   - Balance en orden != Balance disponible
   - Verifica en Kraken → Funding → Available

2. **Margin insuficiente**:
   - Con apalancamiento necesitas margen
   - El bot calculará según tu balance disponible

3. **Posición mínima de Kraken**:
   - ETH: mínimo 0.001 ETH
   - Verifica minimums en Kraken docs

### No recibo notificaciones de Telegram

**Checklist:**
1. ✅ Enviaste `/start` a tu bot
2. ✅ El `CHAT_ID` es correcto (números, no @username)
3. ✅ El `BOT_TOKEN` es correcto
4. ✅ El bot no está bloqueado por ti
5. ✅ Verifica en logs que no hay errores de API

**Para obtener tu Chat ID correctamente:**
```bash
# 1. Envía un mensaje a tu bot
# 2. Ejecuta:
curl https://api.telegram.org/bot<TU_TOKEN>/getUpdates
# 3. Busca: "chat":{"id":12345678}
```

### GitHub Actions falla constantemente

**Soluciones:**

1. **Verifica los Secrets**:
   - Settings → Secrets and variables → Actions
   - Todos deben estar presentes y correctos

2. **Límite de minutos**:
   - Plan gratuito: 2000 min/mes
   - 96 ejecuciones/día × ~10 min = ~960 min/mes
   - Monitorea uso en Settings → Billing

3. **Rate limits de Kraken**:
   - El código maneja automáticamente
   - Si persiste, contacta soporte Kraken

4. **Revisa logs específicos**:
   - Ve al workflow fallido
   - Busca el mensaje de error exacto

---

## Trading y Estrategia

### ¿Cómo funciona el apalancamiento automático?

El bot calcula el apalancamiento óptimo:

```python
# Ejemplo con balance de $1000 y riesgo 5%
risk_amount = $1000 × 0.05 = $50
stop_loss = 200 points = $200

# Tamaño ideal sin leverage
size = $50 / $200 = 0.25 ETH
costo = 0.25 × $3000 = $750

# Como $750 > $1000, necesitamos leverage
leverage = 750 / 1000 = 0.75x → mínimo 2x (config)

# Con 2x leverage:
margin_needed = $750 / 2 = $375 ✅
```

### ¿Qué es el "trailing stop" y cómo funciona?

Trailing stop sigue el precio favorable:

**Ejemplo con TRAILING_START=25, TRAILING_STEP=15:**

1. Compras ETH a $3000
2. Precio sube a $3025 (+25 points) → Trailing activo
3. Stop inicial en $3000 (SL normal)
4. Precio sube a $3040
   - Profit = 40 points
   - Nuevo stop = $3000 + (40 - 15) = $3025
5. Precio sigue subiendo, stop sigue 15 points atrás
6. Si precio baja 15 points desde máximo → Cierra con profit

### ¿Cuántas operaciones esperadas por día?

**Varía según:**
- Volatilidad del mercado: 2-10 señales/día
- Configuración de confirmaciones: más restrictivo = menos señales
- Horario de trading: sesión americana suele tener más volumen

**Configuración conservadora:** 2-5 trades/día
**Configuración agresiva:** 5-15 trades/día

### ¿Qué hacer si pierde dinero constantemente?

**Ajustes recomendados:**

1. **Reduce riesgo**:
   ```python
   RISK_PER_TRADE = 0.02  # Baja a 2%
   MAX_DAILY_LOSS = -100  # Más conservador
   ```

2. **Aumenta confirmaciones**:
   ```python
   USE_ADX = True
   USE_RSI_FILTER = True
   MIN_CONFIRMATIONS_RATIO = 0.5  # 50% confirmaciones
   ```

3. **Ajusta parámetros**:
   ```python
   ACCEL_BARS_REQUIRED = 3  # Más conservador
   ATR_STOP_MULTIPLIER = 2.5  # Stop más amplio
   ```

4. **Limita posiciones**:
   ```python
   MAX_POSITIONS = 1  # Solo 1 posición a la vez
   SAME_DIRECTION_ONLY = True
   ```

### ¿Puedo hacer trading 24/7?

**Sí, pero no recomendado:**

Razones para limitar horarios:
- Menor liquidez en sesión asiática (crypto menos afectado)
- Spreads más amplios
- Mayor volatilidad aleatoria

**Recomendación:**
```python
USE_TRADING_HOURS = True
TRADE_EUROPEAN_SESSION = True   # Mejor liquidez
TRADE_AMERICAN_SESSION = True   # Mayor volumen
TRADE_ASIAN_SESSION = False     # Opcional
```

---

## Costos y Comisiones

### ¿Cuánto cuesta operar en Kraken?

**Comisiones de trading:**
- Maker: 0.16% - 0.26%
- Taker: 0.26% - 0.40%
- Con volumen alto las fees bajan

**Comisiones de margin:**
- 0.02% cada 4 horas (0.12%/día)
- Solo se cobra en posiciones abiertas

**Ejemplo con trade de $1000:**
- Entrada: $1000 × 0.0026 = $2.60
- Salida: $1000 × 0.0026 = $2.60
- Total: ~$5.20 en comisiones

### ¿Por qué el bot usa apalancamiento?

**Dos razones:**

1. **Evitar comisión mínima de orden**:
   - Kraken cobra mínimo por orden pequeña
   - Con leverage puedes tener posiciones más grandes

2. **Optimizar capital**:
   - Mantener liquidez para múltiples posiciones
   - Mejor gestión de riesgo

**Importante:** El bot usa leverage responsablemente (2-5x)

### ¿Hay costos de GitHub Actions?

**Plan gratuito:**
- 2000 minutos/mes
- Con este bot: ~1000 min/mes
- Suficiente para uso personal

**Si excedes:**
- $0.008 por minuto extra
- ~$8 por 1000 minutos adicionales
- Considera GitHub Pro ($4/mes = 3000 min)

---

## Seguridad

### ¿Es seguro guardar las keys en GitHub?

**Usando GitHub Secrets: SÍ**
- Encriptados en reposo
- Solo accesibles en workflows
- No visibles en logs
- No accesibles vía API

**NUNCA:**
- ❌ Subas keys en código
- ❌ Pongas keys en comments
- ❌ Compartas tu repositorio privado

### ¿Qué pasa si hackean mi GitHub?

**Protecciones:**
1. **2FA obligatorio**: Actívalo siempre
2. **Secrets encriptados**: No son visibles incluso con acceso
3. **Permisos de API limitados**: No pueden retirar fondos

**Mejores prácticas:**
- Usa contraseñas únicas
- Activa 2FA en GitHub y Kraken
- Revisa activity log regularmente
- Usa API key separada para el bot

### ¿Puedo perder más dinero del que tengo?

**Con margin: Técnicamente sí, pero:**
- Kraken tiene liquidación automática
- El bot usa stops en todas las posiciones
- Límite de pérdida diaria protege
- Leverage bajo (2-5x) reduce riesgo

**Para mayor seguridad:**
- Mantén solo capital de trading en cuenta
- No uses leverage alto
- Monitorea regularmente

---

## Optimización

### ¿Cómo optimizar la estrategia?

**Proceso recomendado:**

1. **Backtest con diferentes parámetros:**
   ```python
   # Prueba rangos
   ACCEL_BARS_REQUIRED: 1-5
   RISK_PER_TRADE: 0.01-0.10
   ATR_STOP_MULTIPLIER: 1.5-3.0
   ```

2. **Forward test:**
   - Ejecuta con capital mínimo
   - Monitorea 1-2 semanas
   - Ajusta según resultados

3. **Optimización continua:**
   - Revisa métricas semanalmente
   - Ajusta basado en mercado
   - Mantén log de cambios

### ¿Qué métricas debo monitorear?

**Métricas clave:**

1. **Win Rate**: Objetivo 40-60%
2. **Profit Factor**: >1.5 bueno, >2.0 excelente
3. **Max Drawdown**: <20% aceptable
4. **Sharpe Ratio**: >1.0 bueno
5. **Average Win/Loss**: Ratio >1.5

**Red flags:**
- ⚠️ Win rate <30%
- ⚠️ Profit factor <1.2
- ⚠️ Drawdown >30%
- ⚠️ Pérdidas consecutivas >5

### ¿Debo usar todas las confirmaciones?

**Depende de tu estilo:**

**Agresivo** (más trades):
```python
USE_ADX = False
USE_OBV = False
USE_PRICE_MA = False
MIN_CONFIRMATIONS_RATIO = 0.25
```

**Conservador** (menos pero mejor calidad):
```python
USE_ADX = True
USE_OBV = True
USE_PRICE_MA = True
USE_RSI_FILTER = True
MIN_CONFIRMATIONS_RATIO = 0.50
```

**Recomendación:** Empieza conservador, relaja restricciones gradualmente.

---

## 💬 ¿Más Preguntas?

Si tu pregunta no está aquí:
1. Revisa los logs de GitHub Actions
2. Verifica las notificaciones de Telegram
3. Revisa el código y comentarios
4. Haz un backtest para entender el comportamiento

**Recuerda:** Empieza pequeño, monitorea constantemente, ajusta gradualmente.
