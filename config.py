# config.py
import os
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

# Variables globales que otros archivos van a importar
TOKEN = os.getenv("TELEGRAM_TOKEN")
ID_PLANILLA = os.getenv("ID_PLANILLA")

if not TOKEN or not ID_PLANILLA:
    print("❌ ERROR CRÍTICO: Faltan credenciales en el archivo .env")
    exit()