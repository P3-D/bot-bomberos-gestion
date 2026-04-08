# base_datos.py
import sqlite3
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Importamos el ID desde nuestro nuevo archivo de configuración
from config import ID_PLANILLA

# =========================================================
# 1. CONEXIÓN A LA NUBE (Google Sheets)
# =========================================================
def conectar_sheets():
    """Devuelve las dos pestañas necesarias de Google Sheets."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
    gc = gspread.authorize(creds)
    archivo = gc.open_by_key(ID_PLANILLA)
    
    sheet = archivo.sheet1                    # Pestaña principal (los partes)
    user_sheet = archivo.worksheet("Usuarios") # Pestaña de personal autorizado
    return sheet, user_sheet

def obtener_mapa_usuarios():
    """Lee la pestaña de Usuarios y devuelve el mapa para autorizar ingresos."""
    try:
        _, user_sheet = conectar_sheets()
        registros = user_sheet.get_all_records()
        return {str(r['ID']): r['Nombre'] for r in registros}
    except Exception as e:
        print(f"⚠️ Error al leer usuarios de Google Sheets: {e}")
        return {} # Devuelve vacío si falla, bloqueando el acceso por seguridad

# =========================================================
# 2. CONEXIÓN LOCAL (Bodega SQLite)
# =========================================================
def inicializar_db_local():
    """Crea las tablas en SQLite si es la primera vez que arranca el bot."""
    conn = sqlite3.connect('emergencias.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS partes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            hora TEXT,
            unidad TEXT,
            clave TEXT,
            km_salida INTEGER,
            ubicacion TEXT,
            km_llegada INTEGER,
            km_recorridos INTEGER,
            personal TEXT,
            apoyos TEXT,
            afectados TEXT,
            detalles TEXT,
            responsable TEXT
        )
    ''')

    # 2. Tabla de Usuarios 
    # Usamos el telegram_id como PRIMARY KEY para que no se repitan voluntarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            telegram_id INTEGER PRIMARY KEY,
            nombre TEXT,
            rango TEXT DEFAULT 'voluntario',
            estado TEXT DEFAULT 'activo'
        )
    ''')
    
    conn.commit()
    conn.close()
    print("🏗️ Base de datos verificada y lista.")

# =========================================================
# 3. EL PUENTE DE GUARDADO (La función principal)
# =========================================================
def guardar_emergencia(fila_datos):
    """
    Recibe los datos del diálogo.
    Guarda PRIMERO en local (seguro) y LUEGO sube a la nube.
    """
    estado_final = ""
    
    # PASO A: GUARDADO LOCAL (Nuestra fuente de verdad)
    try:
        conn = sqlite3.connect('emergencias.db')
        cursor = conn.cursor()
        query = '''
            INSERT INTO partes 
            (fecha, hora, unidad, clave, km_salida, ubicacion, km_llegada, km_recorridos, personal, apoyos, afectados, detalles, responsable) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        # 'fila_datos' es exactamente la lista de 13 elementos que armamos en dialogos.py
        cursor.execute(query, tuple(fila_datos))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Error crítico al guardar en SQLite: {e}")
        return "Error en almacenamiento local. Contacte al administrador."

    # PASO B: SINCRONIZACIÓN EN NUBE (El reflejo en Google Sheets)
    try:
        sheet, _ = conectar_sheets()
        sheet.append_row(fila_datos)
        estado_final = "Guardado local y Sincronizado en la nube ☁️"
    except Exception as e:
        print(f"⚠️ Falló sincronización con Sheets: {e}")
        estado_final = "Guardado local ✅ (Nube fuera de línea, se sincronizará luego)"
        
    return estado_final