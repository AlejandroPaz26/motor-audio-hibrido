import os
from worker import AudioEngineWorker

def ejecutar_demostracion():
    print("=" * 60)
    print("DEMOSTRACIÓN DE CONSOLA: MOTOR HÍBRIDO PYTHON + C++ (IN-PLACE)")
    print("=" * 60)

    # 1. Inicializar el worker (carga automática de motor.dll o libmotor.so)
    try:
        print("\n[+] Inicializando el Worker y cargando el motor nativo...")
        worker = AudioEngineWorker()
        print("[Éxito] Motor FFI vinculado correctamente.")
    except Exception as e:
        print(f"[Error crítico] No se pudo cargar el motor: {e}")
        return

    # 2. Definir ruta del archivo de audio de prueba
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(base_dir, "assets_audio")
    
    # Crear carpeta assets_audio si no existe
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)

    print(f"\n[i] Coloque un archivo de audio .wav de prueba en la carpeta: {assets_dir}")
    nombre_archivo = input("Ingrese el nombre del archivo .wav (ej. prueba.wav): ").strip()
    ruta_wav = os.path.join(assets_dir, nombre_archivo)

    if not os.path.exists(ruta_wav):
        print(f"[Error] No se encontró el archivo en: {ruta_wav}")
        print("Por favor, agregue un archivo .wav válido en la carpeta assets_audio e intente de nuevo.")
        return

    # 3. Validar cabecera y cargar metadatos (RF-002, RF-003, RF-004)
    try:
        print(f"\n[+] Validando cabecera RIFF/WAVE y leyendo metadatos de '{nombre_archivo}'...")
        metadata = worker.validar_y_cargar_wav(ruta_wav)
        print("[Éxito] Archivo validado correctamente:")
        for clave, valor in metadata.items():
            print(f"    - {clave}: {valor}")
    except Exception as e:
        print(f"[Error de Validación]: {e}")
        return

    # 4. Configurar parámetros del filtro
    print("\n[+] Configuración de parámetros para el motor C++:")
    try:
        intensidad = int(input("Ingrese la intensidad del filtro (0 a 100%): "))
        ganancia_db = float(input("Ingrese la ganancia en decibelios (ej. -3.0 o 2.5): "))
    except ValueError:
        print("[Error] Ingrese valores numéricos válidos.")
        return

    # 5. Ejecución del procesamiento In-Place simulando una cola de mensajes
    import queue
    cola = queue.Queue()

    print("\n[+] Ejecutando procesamiento asíncrono en C++ (In-Place)...")
    worker.ejecutar_en_hilo(intensidad, ganancia_db, cola)

    # Esperar el resultado de la cola
    resultado = cola.get()
    
    if resultado["estado"] == "completado":
        print("\n[¡PROCESO COMPLETADO EXITOSAMENTE!]")
        print(f"    - Tiempo de ejecución en C++: {resultado['tiempo_ms']} ms (RNF-001)")
        print(f"    - Muestras totales procesadas: {resultado['muestras']}")
        print(f"    - Consumo de memoria adicional: O(1) [In-Place puro]")

        # 6. Exportar resultado físico (RF-015)
        nombre_salida = f"procesado_{nombre_archivo}"
        ruta_salida = os.path.join(assets_dir, nombre_salida)
        worker.exportar_wav(ruta_salida)
        print(f"\n[Éxito] Archivo de salida exportado en disco:")
        print(f"    -> {ruta_salida}")
        print("    Ya puede reproducir este archivo en su reproductor favorito (VLC/WMP).")
    else:
        print(f"\n[Error durante el procesamiento]: {resultado.get('mensaje')}")

    print("\n" + "=" * 60)
    print("FIN DE LA DEMOSTRACIÓN TÉCNICA")
    print("=" * 60)

if __name__ == "__main__":
    ejecutar_demostracion()