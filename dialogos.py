# dialogos.py
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import base_datos # Importamos la "Obra Gruesa"

# Herramientas de Normalización

def normalizar_clave(texto):
    """Transforma variaciones como '10 4', '10.4', o '104' en el estándar '10-4'"""
    texto_limpio = texto.strip().upper()
    # Cambiamos puntos y espacios por guiones
    texto_limpio = texto_limpio.replace(" ", "-").replace(".", "-")
    
    # Si alguien escribe los números de corrido (ej: "104" o "1014")
    if len(texto_limpio) >= 3 and "-" not in texto_limpio and texto_limpio.startswith("10"):
        texto_limpio = f"10-{texto_limpio[2:]}"
        
    return texto_limpio

def sanitizar_texto(texto):
    """Elimina espacios dobles accidentales y fuerza la primera letra a mayúscula"""
    # Si alguien escribe '  incendio    estructural ', lo deja como 'Incendio estructural'
    texto_limpio = " ".join(texto.split())
    return texto_limpio.capitalize()

# 1. DEFINICIÓN DE ESTADOS (Los "Pisos" de nuestro edificio)
UNIDAD, CLAVE, KM_SALIDA, UBICACION, KM_LLEGADA, PERSONAL, APOYO, AFECTADOS, DETALLES, CONFIRMACION = range(10)

# ---------------------------------------------------------
# FLUJO DE CONVERSACIÓN
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    
    # El diálogo le pregunta a la base de datos quién está autorizado
    usuarios_mapa = base_datos.obtener_mapa_usuarios()
    
    if user_id not in usuarios_mapa:
        await update.message.reply_text("⛔ Acceso denegado. No estás autorizado en la planilla.")
        return ConversationHandler.END

    context.user_data['responsable'] = usuarios_mapa[user_id]
    context.user_data['fecha'] = datetime.now().strftime("%d/%m/%Y")
    context.user_data['hora'] = datetime.now().strftime("%H:%M:%S")
    context.user_data['lista_apoyo'] = []
    context.user_data['lista_afectados'] = []
    
    teclado_unidades = [['B-2', 'R-2'], ['BF-2'], ['Cancelar']]
    await update.message.reply_text(
        f"🚨 *Nuevo Parte de Emergencia* 🚨\n\nResponsable: *{context.user_data['responsable']}*\n\n¿Qué unidad sale?",
        reply_markup=ReplyKeyboardMarkup(teclado_unidades, one_time_keyboard=True, resize_keyboard=True),
        parse_mode='Markdown'
    )
    return UNIDAD

async def recibir_unidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    if texto == 'Cancelar':
        await update.message.reply_text("Registro cancelado.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    
    context.user_data['unidad'] = texto
    teclado_claves = [['10-0', '10-2'], ['10-3', '10-4'], ['10-14', 'Otra Clave']]
    await update.message.reply_text(
        f"✅ Unidad *{texto}*.\n\nIndique la *Clave del Llamado*:",
        reply_markup=ReplyKeyboardMarkup(teclado_claves, one_time_keyboard=True, resize_keyboard=True),
        parse_mode='Markdown'
    )
    return CLAVE

async def recibir_clave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    if texto == 'Otra Clave':
        await update.message.reply_text("✍️ *Escriba la clave radial manualmente*:", reply_markup=ReplyKeyboardRemove(), parse_mode='Markdown')
        return CLAVE 
    
    # 🔍 AQUÍ APLICAMOS EL FILTRO
    clave_limpia = normalizar_clave(texto)
    context.user_data['clave'] = clave_limpia
    
    await update.message.reply_text(f"✅ Clave *{clave_limpia}*.\n\n*Kilometraje de salida* (solo números):", parse_mode='Markdown')
    return KM_SALIDA

async def recibir_km_salida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if not texto.isdigit():
        await update.message.reply_text("❌ Ingrese *solo números* para el KM de salida:")
        return KM_SALIDA
    
    context.user_data['km_salida'] = texto
    boton_ubicacion = KeyboardButton("📍 Enviar mi ubicación actual", request_location=True)
    await update.message.reply_text(
        "📍 *Ubicación*\nEnvía GPS o escribe dirección:",
        reply_markup=ReplyKeyboardMarkup([[boton_ubicacion]], one_time_keyboard=True, resize_keyboard=True),
        parse_mode='Markdown'
    )
    return UBICACION

async def recibir_ubicacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.location:
        lat, lon = update.message.location.latitude, update.message.location.longitude
        context.user_data['ubicacion'] = f"http://maps.google.com/maps?q={lat},{lon}"
    else:
        context.user_data['ubicacion'] = update.message.text
        
    await update.message.reply_text("✅ Ubicación recibida.\n\nIndique *Kilometraje de llegada*:", reply_markup=ReplyKeyboardRemove())
    return KM_LLEGADA

async def recibir_km_llegada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if not texto.isdigit():
        await update.message.reply_text("❌ Ingrese *solo números*:")
        return KM_LLEGADA
    
    km_l = int(texto)
    km_s = int(context.user_data.get('km_salida', 0))
    if km_l < km_s:
        await update.message.reply_text(f"❌ Error: Llegada ({km_l}) menor que Salida ({km_s}). Reintente:")
        return KM_LLEGADA
    
    context.user_data['km_llegada'] = str(km_l)
    await update.message.reply_text("👨‍🚒 Ingrese los *nombres del personal* a bordo:", parse_mode='Markdown')
    return PERSONAL

async def recibir_personal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['personal'] = update.message.text
    await update.message.reply_text("🚓 *Apoyo Concurrente*:", reply_markup=ReplyKeyboardMarkup([['Sin Apoyo']], one_time_keyboard=True, resize_keyboard=True), parse_mode='Markdown')
    return APOYO

async def recibir_apoyo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    if texto in ['Sin Apoyo', '✅ Siguiente paso']:
        await update.message.reply_text("🏥 *Personas Afectadas*:", reply_markup=ReplyKeyboardMarkup([['Sin Afectados']], one_time_keyboard=True, resize_keyboard=True), parse_mode='Markdown')
        return AFECTADOS
    
    context.user_data['lista_apoyo'].append(texto)
    await update.message.reply_text("✔️ Registrado. ¿Otro? o '✅ Siguiente paso'", reply_markup=ReplyKeyboardMarkup([['✅ Siguiente paso']], resize_keyboard=True))
    return APOYO

async def recibir_afectados(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    if texto in ['Sin Afectados', '➡️ Continuar']:
        await update.message.reply_text("📝 *Detalle del trabajo realizado* (mínimo 15 letras):", reply_markup=ReplyKeyboardRemove(), parse_mode='Markdown')
        return DETALLES
    
    context.user_data['lista_afectados'].append(texto)
    await update.message.reply_text("✔️ Registrado. ¿Otro? o '➡️ Continuar'", reply_markup=ReplyKeyboardMarkup([['➡️ Continuar']], resize_keyboard=True))
    return AFECTADOS

# ---------------------------------------------------------
# EL PUENTE ENTRE EL DIÁLOGO Y LA BASE DE DATOS
# ---------------------------------------------------------
async def recibir_detalles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    
    # 🔍 AQUÍ APLICAMOS EL FILTRO AL TEXTO LARGO
    texto_limpio = sanitizar_texto(texto)
    
    if len(texto_limpio) < 15:
        await update.message.reply_text("⚠️ Informe muy corto. Sea más descriptivo:")
        return DETALLES

    context.user_data['detalles'] = texto_limpio
    
    
    km_s = int(context.user_data.get('km_salida', 0))
    km_l = int(context.user_data.get('km_llegada', 0))
    km_rec = km_l - km_s
    
    # Validación lógica de maquinaria
    if km_rec > 1000:
        await update.message.reply_text("❌ Error: Los kilómetros recorridos superan los 1.000 km. Revise las cifras.")
        return CONFIRMACION
    
    # 2. Le mostramos la "Maqueta" antes de guardar
    resumen = (
        f"📋 *BORRADOR DEL PARTE*\n\n"
        f"🚒 *Unidad:* {context.user_data.get('unidad')} | *Clave:* {context.user_data.get('clave')}\n"
        f"🛣️ *Kilómetros Recorridos:* {km_rec} km\n"
        f"👨‍🚒 *Personal:* {context.user_data.get('personal')}\n"
        f"📝 *Detalle:* {texto}\n\n"
        f"¿La información es correcta?"
    )
    
    # 3. Le damos dos botones claros
    teclado_final = [['✅ Sí, Guardar Parte'], ['❌ No, Cancelar y Empezar de cero']]
    await update.message.reply_text(
        resumen, 
        reply_markup=ReplyKeyboardMarkup(teclado_final, one_time_keyboard=True, resize_keyboard=True),
        parse_mode='Markdown'
    )
    return CONFIRMACION # Lo enviamos a la sala de espera final

async def guardar_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Tomamos lo que escribió, le quitamos espacios y lo pasamos a minúsculas
    respuesta = update.message.text.strip().lower()
    
    # ❌ SI DICE NO (Acepta el botón, o texto escrito a mano)
    if respuesta in ['❌ no, cancelar y empezar de cero', 'no', 'cancelar']:
        await update.message.reply_text("🗑️ Borrador eliminado. Escriba /start para crear un parte nuevo.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
        
    # ✅ SI DICE SÍ (Acepta el botón, o texto escrito a mano)
    elif respuesta in ['✅ sí, guardar parte', 'si', 'sí', 'guardar']:
        await update.message.reply_text("⏳ Procesando reporte...", reply_markup=ReplyKeyboardRemove())
        
        # Recuperamos los datos
        km_s = int(context.user_data.get('km_salida', 0))
        km_l = int(context.user_data.get('km_llegada', 0))
        km_rec = km_l - km_s
        apoyos = "\n".join(context.user_data.get('lista_apoyo', [])) or "Ninguno"
        afectados = "\n".join(context.user_data.get('lista_afectados', [])) or "Ninguno"

        # Empaquetamos
        fila = [
            context.user_data['fecha'], context.user_data['hora'], context.user_data['unidad'],
            context.user_data['clave'], km_s, context.user_data['ubicacion'], km_l,
            km_rec, context.user_data['personal'], apoyos, afectados, context.user_data['detalles'], 
            context.user_data['responsable']
        ]

        # Llamamos a nuestra fundación
        import base_datos # Nos aseguramos de que el puente exista
        mensaje_resultado = base_datos.guardar_emergencia(fila)

        await update.message.reply_text(
            f"🏁 *¡Parte Guardado Exitosamente!*\n\n"
            f"🖥️ Sistema: _{mensaje_resultado}_", 
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    else:
        # Si de verdad escribió algo sin sentido, le recordamos cómo salir
        await update.message.reply_text("⚠️ Responda 'Sí' para guardar el parte, o 'No' para cancelar.")
        return CONFIRMACION

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Proceso cancelado.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END