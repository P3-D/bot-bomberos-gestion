# estadisticas.py
import time
import os
import gestor_archivos # <-- Nuestro contratista
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import folium
from folium.plugins import HeatMapWithTime
from collections import defaultdict
from datetime import datetime
import re
from telegram import Update
from telegram.ext import ContextTypes

async def generar_grafico_mensual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Generando gráfico estadístico...")

    try:
        conn = sqlite3.connect('emergencias.db')
        df = pd.read_sql_query("SELECT clave FROM partes", conn)
        conn.close()

        if df.empty:
            await update.message.reply_text("Aún no hay partes registrados.")
            return

        conteo_claves = df['clave'].value_counts()

        plt.figure(figsize=(8, 6))
        conteo_claves.plot(kind='bar', color='#d32f2f', edgecolor='black')
        plt.title('🔥 Salidas por Clave Radial', fontsize=16, fontweight='bold')
        plt.xlabel('Clave de Emergencia', fontsize=12)
        plt.ylabel('Cantidad de Salidas', fontsize=12)
        plt.xticks(rotation=0)
        plt.tight_layout()

        # 🛠️ Pedimos la carpeta de hoy (esto automáticamente limpia lo viejo)
        carpeta_destino = gestor_archivos.obtener_ruta_hoy()
        
        # Le damos un nombre único basado en la hora exacta
        marca_tiempo = int(time.time())
        ruta_foto = os.path.join(carpeta_destino, f"resumen_{marca_tiempo}.png")
        
        plt.savefig(ruta_foto)
        plt.close()

        # Abrimos el archivo real y lo enviamos
        with open(ruta_foto, 'rb') as foto:
            await update.message.reply_photo(
                photo=foto, 
                caption="📈 *Resumen Estadístico Actualizado*", 
                parse_mode='Markdown'
            )

    except Exception as e:
        await update.message.reply_text(f"❌ Error al generar el gráfico: {e}")


async def generar_mapa_calor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Leer las fechas que escribió el usuario (si es que escribió alguna)
    argumentos = context.args
    fecha_inicio = None
    fecha_fin = None

    if len(argumentos) == 2:
        try:
            # Validamos que las fechas tengan formato correcto
            fecha_inicio = datetime.strptime(argumentos[0], "%d/%m/%Y")
            fecha_fin = datetime.strptime(argumentos[1], "%d/%m/%Y")
            await update.message.reply_text(f"🗺️ Mapeando desde {argumentos[0]} hasta {argumentos[1]}...")
        except ValueError:
            await update.message.reply_text("❌ Formato de fecha incorrecto. Use: /mapa DD/MM/AAAA DD/MM/AAAA")
            return
    else:
        await update.message.reply_text("🗺️ Mapeando el historial completo de la compañía...")

    try:
        conn = sqlite3.connect('emergencias.db')
        cursor = conn.cursor()
        cursor.execute("SELECT fecha, ubicacion FROM partes WHERE ubicacion LIKE 'http%'")
        registros = cursor.fetchall()
        conn.close()

        datos_por_fecha = defaultdict(list)
        
        # 2. El Filtro Maestro
        for fecha_str, link in registros:
            try:
                fecha_obj = datetime.strptime(fecha_str, "%d/%m/%Y")
                
                # Si el usuario definió un rango, ignoramos las fechas que queden fuera
                if fecha_inicio and fecha_fin:
                    if not (fecha_inicio <= fecha_obj <= fecha_fin):
                        continue # Salta a la siguiente emergencia

                # Extraemos GPS
                match = re.search(r'([-+]?\d*\.\d+|\d+),([-+]?\d*\.\d+|\d+)', link)
                if match:
                    lat, lon = float(match.group(1)), float(match.group(2))
                    fecha_formateada = fecha_obj.strftime("%Y-%m-%d")
                    datos_por_fecha[fecha_formateada].append([lat, lon])
            except ValueError:
                continue

        if not datos_por_fecha:
            await update.message.reply_text("No hay emergencias registradas en ese rango de fechas.")
            return

        # 3. Construimos la línea de tiempo
        fechas_ordenadas = sorted(datos_por_fecha.keys())
        datos_tiempo = [datos_por_fecha[f] for f in fechas_ordenadas]
        
        mapa = folium.Map(location=datos_tiempo[-1][-1], zoom_start=13, tiles='CartoDB dark_matter')
        HeatMapWithTime(
            datos_tiempo,
            index=fechas_ordenadas,
            auto_play=True,
            radius=20,
            name="Evolución de Emergencias"
        ).add_to(mapa)

        # 🛠️ Pedimos la carpeta de hoy
        carpeta_destino = gestor_archivos.obtener_ruta_hoy()
        
        marca_tiempo = int(time.time())
        ruta_mapa = os.path.join(carpeta_destino, f"mapa_espacial_{marca_tiempo}.html")

        mapa.save(ruta_mapa)

        with open(ruta_mapa, 'rb') as documento:
            mensaje = "📍 *Visor Espacial de Emergencias*"
            if fecha_inicio:
                mensaje += f"\n📅 Rango: {argumentos[0]} al {argumentos[1]}"
            
            await update.message.reply_document(
                document=documento, 
                caption=mensaje, 
                parse_mode='Markdown'
            )

    except Exception as e:
        await update.message.reply_text(f"❌ Error al generar el mapa interactivo: {e}")