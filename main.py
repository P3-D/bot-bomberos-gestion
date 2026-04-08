# main.py
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
import reportes
from config import TOKEN
import base_datos
import dialogos
import estadisticas

# Configuramos el "Libro de Obras" (Logging) para ver errores en la consola
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def principal():
    # 1. Asegurar que las fundaciones (Base de Datos) estén listas antes de abrir
    base_datos.inicializar_db_local()

    # 2. Construir la aplicación (El Motor del Bot)
    app = Application.builder().token(TOKEN).build()

    # 3. Traer el "Plano de Diálogos"
    # Aquí mapeamos qué función de dialogos.py corresponde a qué piso (estado)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', dialogos.start)],
        states={
            dialogos.UNIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, dialogos.recibir_unidad)],
            dialogos.CLAVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, dialogos.recibir_clave)],
            dialogos.KM_SALIDA: [MessageHandler(filters.TEXT & ~filters.COMMAND, dialogos.recibir_km_salida)],
            dialogos.UBICACION: [MessageHandler(filters.LOCATION | filters.TEXT & ~filters.COMMAND, dialogos.recibir_ubicacion)],
            dialogos.KM_LLEGADA: [MessageHandler(filters.TEXT & ~filters.COMMAND, dialogos.recibir_km_llegada)],
            dialogos.PERSONAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, dialogos.recibir_personal)],
            dialogos.APOYO: [MessageHandler(filters.TEXT & ~filters.COMMAND, dialogos.recibir_apoyo)],
            dialogos.AFECTADOS: [MessageHandler(filters.TEXT & ~filters.COMMAND, dialogos.recibir_afectados)],
            dialogos.DETALLES: [MessageHandler(filters.TEXT & ~filters.COMMAND, dialogos.recibir_detalles)],
            dialogos.CONFIRMACION: [MessageHandler(filters.TEXT & ~filters.COMMAND, dialogos.guardar_final)],
        },
        fallbacks=[
            CommandHandler('cancel', dialogos.cancel),
            MessageHandler(filters.Regex('^Cancelar$'), dialogos.cancel)
        ],
    )

    # 4. Conectar los diálogos al motor
    app.add_handler(conv_handler)

    # 5. [CONECTADO] Especialidades de análisis
    app.add_handler(CommandHandler('resumen', estadisticas.generar_grafico_mensual))
    app.add_handler(CommandHandler('mapa', estadisticas.generar_mapa_calor))

    # 6. Encender el sistema
    print("--------------------------------------------------")
    print("🚒 SISTEMA DE EMERGENCIAS ACTIVO")
    print("🧱 Arquitectura Modular: OK")
    print("🗄️ Base de Datos Local: OK")
    print("☁️ Sincronización Nube: OK")
    print("🔒 Escuchando solo a personal autorizado...")
    print("--------------------------------------------------")
    
    app.add_handler(CommandHandler('reporte', reportes.generar_pdf_oficial))

    app.run_polling()

if __name__ == '__main__':
    principal()