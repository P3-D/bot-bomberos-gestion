# reportes.py
import sqlite3
import pandas as pd
from fpdf import FPDF
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import time
from datetime import datetime
import gestor_archivos
from telegram import Update
from telegram.ext import ContextTypes

# Diccionario para que el PDF se vea profesional en español
MESES = {
    1: 'ENERO', 2: 'FEBRERO', 3: 'MARZO', 4: 'ABRIL', 
    5: 'MAYO', 6: 'JUNIO', 7: 'JULIO', 8: 'AGOSTO', 
    9: 'SEPTIEMBRE', 10: 'OCTUBRE', 11: 'NOVIEMBRE', 12: 'DICIEMBRE'
}

async def generar_pdf_oficial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Leer argumentos del usuario (Ej: /reporte 04/2026)
    argumentos = context.args
    mes_filtro = None
    anio_filtro = None
    titulo_periodo = "HISTÓRICO GLOBAL"

    if len(argumentos) == 1:
        try:
            # Validamos que el formato sea MM/AAAA
            fecha_req = datetime.strptime(argumentos[0], "%m/%Y")
            mes_filtro = fecha_req.month
            anio_filtro = fecha_req.year
            titulo_periodo = f"{MESES[mes_filtro]} {anio_filtro}"
            await update.message.reply_text(f"📄 Compilando reporte operativo de {titulo_periodo.title()}...")
        except ValueError:
            await update.message.reply_text("❌ Formato incorrecto. Use: /reporte MM/AAAA (Ejemplo: /reporte 04/2026)")
            return
    else:
        await update.message.reply_text("📄 Compilando reporte operativo histórico global...")

    try:
        # 2. Extraer los datos brutos
        conn = sqlite3.connect('emergencias.db')
        df = pd.read_sql_query("SELECT * FROM partes", conn)
        conn.close()

        if df.empty:
            await update.message.reply_text("❌ La base de datos está vacía. No hay información para reportar.")
            return

        # 3. El Filtro Temporal (Convertimos la columna fecha de texto a un formato inteligente)
        df['fecha_dt'] = pd.to_datetime(df['fecha'], format='%d/%m/%Y', errors='coerce')
        
        if mes_filtro and anio_filtro:
            # Filtramos el DataFrame para dejar solo las filas que coincidan con el mes y año
            df = df[(df['fecha_dt'].dt.month == mes_filtro) & (df['fecha_dt'].dt.year == anio_filtro)]
            
            if df.empty:
                await update.message.reply_text(f"❌ No se registraron despachos durante {titulo_periodo.title()}.")
                return

        # 4. Cálculos Estadísticos del periodo
        total_despachos = len(df)
        total_km = df['km_recorridos'].sum()
        unidad_frecuente = df['unidad'].value_counts().idxmax()
        fecha_emision = datetime.now().strftime("%d/%m/%Y %H:%M")

        # 5. Generar el Gráfico
        conteo_claves = df['clave'].value_counts()
        plt.figure(figsize=(7, 4))
        conteo_claves.plot(kind='bar', color='#b71c1c', edgecolor='black')
        plt.title(f'Distribución de Despachos ({titulo_periodo})', fontweight='bold')
        plt.ylabel('Cantidad')
        plt.xticks(rotation=0)
        plt.tight_layout()
        
        carpeta_destino = gestor_archivos.obtener_ruta_hoy()
        ruta_grafico = os.path.join(carpeta_destino, f"grafico_temp_{int(time.time())}.png")
        plt.savefig(ruta_grafico)
        plt.close()

        # 6. Maquetación del PDF
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        # --- ENCABEZADO ---
        pdf.set_font("Arial", style='B', size=16)
        pdf.cell(200, 10, txt=f"REPORTE DE OPERACIONES - {titulo_periodo}", ln=True, align='C')
        
        pdf.set_font("Arial", style='I', size=10)
        pdf.cell(200, 10, txt="Documento generado automáticamente por Sistema Autónomo", ln=True, align='C')
        pdf.ln(5)

        # --- SECCIÓN DE DATOS DUROS ---
        pdf.set_font("Arial", style='B', size=12)
        pdf.cell(200, 10, txt="1. RESUMEN ESTADÍSTICO", ln=True, align='L')
        
        pdf.set_font("Arial", size=11)
        pdf.cell(200, 8, txt=f"Fecha de Emisión: {fecha_emision}", ln=True, align='L')
        pdf.cell(200, 8, txt=f"Total de Despachos en el Periodo: {total_despachos} emergencias.", ln=True, align='L')
        pdf.cell(200, 8, txt=f"Kilometraje Total Recorrido: {total_km} km.", ln=True, align='L')
        pdf.cell(200, 8, txt=f"Unidad con Mayor Demanda: {unidad_frecuente}", ln=True, align='L')
        pdf.ln(10)

        # --- SECCIÓN DE GRÁFICO ---
        pdf.set_font("Arial", style='B', size=12)
        pdf.cell(200, 10, txt="2. ANÁLISIS DE INCIDENCIAS", ln=True, align='L')
        pdf.image(ruta_grafico, x=15, w=180) 
        
        # --- FIRMAS / PIE DE PÁGINA ---
        pdf.set_y(250)
        pdf.set_font("Arial", style='B', size=10)
        pdf.cell(90, 10, txt="__________________________", ln=0, align='C')
        pdf.cell(90, 10, txt="__________________________", ln=1, align='C')
        pdf.set_font("Arial", size=10)
        pdf.cell(90, 5, txt="Capitán de Compañía", ln=0, align='C')
        pdf.cell(90, 5, txt="Oficial de Guardia", ln=1, align='C')

        # 7. Guardar y Entregar
        marca_tiempo = int(time.time())
        nombre_pdf = f"Reporte_{titulo_periodo.replace(' ', '_')}_{marca_tiempo}.pdf"
        ruta_pdf = os.path.join(carpeta_destino, nombre_pdf)
        pdf.output(ruta_pdf)

        with open(ruta_pdf, 'rb') as documento:
            await update.message.reply_document(
                document=documento, 
                caption=f"✅ *Reporte Oficial: {titulo_periodo}*\nListo para revisión y firma.", 
                parse_mode='Markdown'
            )

    except Exception as e:
        await update.message.reply_text(f"❌ Error crítico al generar el documento: {e}")