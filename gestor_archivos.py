import os
import shutil
from datetime import datetime, timedelta

# La carpeta principal donde guardaremos todo
CARPETA_BASE = "archivos_temporales"

def limpiar_escombros(dias_maximos=2):
    """
    Revisa la carpeta base y elimina cualquier subcarpeta que sea más antigua 
    que los 'dias_maximos' permitidos.
    """
    if not os.path.exists(CARPETA_BASE):
        return

    ahora = datetime.now()
    
    # Revisamos todo lo que hay dentro de la carpeta base
    for nombre_carpeta in os.listdir(CARPETA_BASE):
        ruta_carpeta = os.path.join(CARPETA_BASE, nombre_carpeta)
        
        if os.path.isdir(ruta_carpeta):
            try:
                # Intentamos leer la fecha del nombre de la carpeta
                fecha_carpeta = datetime.strptime(nombre_carpeta, "%Y-%m-%d")
                
                # Si la diferencia de días es mayor al límite, demoler la carpeta
                if (ahora - fecha_carpeta).days > dias_maximos:
                    shutil.rmtree(ruta_carpeta) # Borra la carpeta y todo su contenido
                    print(f"🧹 Limpieza: Carpeta temporal eliminada -> {nombre_carpeta}")
            except ValueError:
                # Si hay una carpeta que no tiene formato de fecha, no la tocamos
                pass

def obtener_ruta_hoy():
    """
    Ejecuta la limpieza, crea la carpeta del día actual y devuelve la ruta.
    """
    # 1. Pasamos la escoba primero
    limpiar_escombros(dias_maximos=2) # Borra lo que tenga más de 2 días
    
    # 2. Creamos la carpeta de hoy
    hoy = datetime.now().strftime("%Y-%m-%d")
    ruta_hoy = os.path.join(CARPETA_BASE, hoy)
    
    # Si la carpeta no existe, la construye (exist_ok evita que falle si ya existe)
    os.makedirs(ruta_hoy, exist_ok=True)
    
    return ruta_hoy