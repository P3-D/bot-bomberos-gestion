# config.py
import os
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

# Variables globales que otros archivos van a importar
TOKEN = os.getenv("TELEGRAM_TOKEN")
ID_PLANILLA = os.getenv("ID_PLANILLA")

# En config.py
UNIDADES_DISPONIBLES = ['B-1', 'B-2', 'BX-1', 'R-1']
CLAVES_FRECUENTES = ['10-0', '10-3', '10-4', '6-3']
VERSION_SOFTWARE = "v0.3.0 - Marcha Blanca"

if not TOKEN or not ID_PLANILLA:
    print("❌ ERROR CRÍTICO: Faltan credenciales en el archivo .env")
    exit()