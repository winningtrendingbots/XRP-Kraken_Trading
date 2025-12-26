"""
Script de configuración rápida
Ayuda a configurar el bot paso a paso
"""

import os
import sys


def print_header():
    """Imprimir header"""
    print("\n" + "="*70)
    print("🤖 BOT DE TRADING AUTOMATIZADO - CONFIGURACIÓN")
    print("="*70 + "\n")


def print_step(step_num, title):
    """Imprimir paso"""
    print(f"\n{'─'*70}")
    print(f"PASO {step_num}: {title}")
    print('─'*70 + "\n")


def setup_kraken():
    """Configurar Kraken"""
    print_step(1, "CONFIGURACIÓN DE KRAKEN")
    
    print("Necesitas crear una API Key en Kraken:")
    print("1. Entra en tu cuenta de Kraken")
    print("2. Ve a Settings → API")
    print("3. Crea una nueva API Key con estos permisos:")
    print("   ✓ Query Funds")
    print("   ✓ Query Open Orders & Trades")
    print("   ✓ Query Closed Orders & Trades")
    print("   ✓ Create & Modify Orders")
    print("   ✓ Cancel/Close Orders")
    print()
    
    api_key = input("Introduce tu KRAKEN_API_KEY: ").strip()
    api_secret = input("Introduce tu KRAKEN_API_SECRET: ").strip()
    
    return api_key, api_secret


def setup_telegram():
    """Configurar Telegram"""
    print_step(2, "CONFIGURACIÓN DE TELEGRAM")
    
    print("Necesitas crear un Bot de Telegram:")
    print("1. Abre Telegram y busca @BotFather")
    print("2. Envía /newbot y sigue las instrucciones")
    print("3. Guarda el Bot Token que te da")
    print()
    print("Para obtener tu Chat ID:")
    print("1. Envía un mensaje a tu bot")
    print("2. Visita: https://api.telegram.org/bot<TU_TOKEN>/getUpdates")
    print("3. Busca 'chat':{'id': XXXXX} en el JSON")
    print()
    
    bot_token = input("Introduce tu TELEGRAM_BOT_TOKEN: ").strip()
    chat_id = input("Introduce tu TELEGRAM_CHAT_ID: ").strip()
    
    return bot_token, chat_id


def create_env_file(kraken_key, kraken_secret, tg_token, tg_chat):
    """Crear archivo .env para testing local"""
    print_step(3, "CREANDO ARCHIVO .ENV")
    
    env_content = f"""# Kraken API
KRAKEN_API_KEY={kraken_key}
KRAKEN_API_SECRET={kraken_secret}

# Telegram
TELEGRAM_BOT_TOKEN={tg_token}
TELEGRAM_CHAT_ID={tg_chat}
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ Archivo .env creado")
    print("⚠️  IMPORTANTE: Este archivo NO se debe subir a GitHub")
    print("   (Ya está incluido en .gitignore)")


def show_github_instructions(kraken_key, kraken_secret, tg_token, tg_chat):
    """Mostrar instrucciones para GitHub"""
    print_step(4, "CONFIGURACIÓN EN GITHUB")
    
    print("Para configurar los Secrets en GitHub:")
    print()
    print("1. Ve a tu repositorio en GitHub")
    print("2. Settings → Secrets and variables → Actions")
    print("3. Click en 'New repository secret' para cada uno:")
    print()
    print(f"   Nombre: KRAKEN_API_KEY")
    print(f"   Valor: {kraken_key}")
    print()
    print(f"   Nombre: KRAKEN_API_SECRET")
    print(f"   Valor: {kraken_secret}")
    print()
    print(f"   Nombre: TELEGRAM_BOT_TOKEN")
    print(f"   Valor: {tg_token}")
    print()
    print(f"   Nombre: TELEGRAM_CHAT_ID")
    print(f"   Valor: {tg_chat}")
    print()


def show_next_steps():
    """Mostrar próximos pasos"""
    print_step(5, "PRÓXIMOS PASOS")
    
    print("Antes de activar el bot en producción:")
    print()
    print("1️⃣  Prueba las conexiones localmente:")
    print("   $ export $(cat .env | xargs)")
    print("   $ python test_connection.py")
    print()
    print("2️⃣  Ajusta la configuración en live_trading.py:")
    print("   - Revisa los parámetros de riesgo")
    print("   - Configura el horario de trading")
    print("   - Ajusta los límites de pérdida")
    print()
    print("3️⃣  Sube el código a GitHub:")
    print("   $ git add .")
    print("   $ git commit -m 'Setup trading bot'")
    print("   $ git push")
    print()
    print("4️⃣  Configura los Secrets en GitHub (ver paso anterior)")
    print()
    print("5️⃣  Habilita GitHub Actions:")
    print("   - Ve a Actions en tu repositorio")
    print("   - Habilita los workflows")
    print()
    print("6️⃣  Monitorea el bot:")
    print("   - Revisa las notificaciones de Telegram")
    print("   - Verifica los logs en GitHub Actions")
    print("   - Comienza con cantidades pequeñas")
    print()


def main():
    """Función principal"""
    print_header()
    
    print("Este script te ayudará a configurar el bot paso a paso.\n")
    print("⚠️  IMPORTANTE:")
    print("   - Ten a mano tus credenciales de Kraken")
    print("   - Necesitarás crear un bot de Telegram")
    print("   - Asegúrate de tener balance en tu cuenta de Kraken")
    print()
    
    continuar = input("¿Deseas continuar? (s/n): ").strip().lower()
    if continuar != 's':
        print("\n❌ Configuración cancelada")
        sys.exit(0)
    
    # Paso 1: Kraken
    kraken_key, kraken_secret = setup_kraken()
    
    # Paso 2: Telegram
    tg_token, tg_chat = setup_telegram()
    
    # Paso 3: Crear .env
    create_env_file(kraken_key, kraken_secret, tg_token, tg_chat)
    
    # Paso 4: GitHub instructions
    show_github_instructions(kraken_key, kraken_secret, tg_token, tg_chat)
    
    # Paso 5: Next steps
    show_next_steps()
    
    print("\n" + "="*70)
    print("✅ CONFIGURACIÓN COMPLETADA")
    print("="*70 + "\n")
    
    print("🎉 ¡Tu bot está casi listo!")
    print("   Sigue los próximos pasos para activarlo.\n")


if __name__ == "__main__":
    main()
