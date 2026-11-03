import os
import wave
import time
import ctypes
import threading
import queue
import numpy as np


class AudioEngineWorker:
    def __init__(self):
        self.lib = self._cargar_libreria()
        self.sample_rate = 0
        self.num_canales = 0
        self.sample_width = 2
        self.num_muestras = 0
        self.buffer_ram = None          # Bloque contiguo ctypes en RAM (In-Place)
        self.onda_original_preview = None  # Submuestreo ligero solo para graficar UI

    def _cargar_libreria(self):
        """RNF-003: Portabilidad FFI entre Windows (.dll) y Linux (.so)."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        nombre_binario = "motor.dll" if os.name == "nt" else "libmotor.so"
        ruta_binario = os.path.join(base_dir, "motor_cpp", nombre_binario)

        if not os.path.exists(ruta_binario):
            raise FileNotFoundError(f"No se encontró la librería compilada en: {ruta_binario}")

        lib = ctypes.CDLL(ruta_binario)

        # RF-011 y RF-012: Definir tipos estrictos de punteros y argumentos para C++
        lib.procesar_audio_inplace.argtypes = [
            ctypes.POINTER(ctypes.c_int16),  # int16_t* buffer (Puntero a RAM)
            ctypes.c_int32,                  # int32_t num_muestras
            ctypes.c_int32,                  # int32_t intensidad
            ctypes.c_float                   # float ganancia_db
        ]
        lib.procesar_audio_inplace.restype = None
        return lib

    def validar_y_cargar_wav(self, ruta_archivo: str) -> dict:
        """RF-002, RF-003, RF-004: Verifica cabecera RIFF/WAVE y extrae metadatos."""
        with open(ruta_archivo, "rb") as f:
            cabecera = f.read(12)
            if len(cabecera) < 12 or cabecera[0:4] != b"RIFF" or cabecera[8:12] != b"WAVE":
                raise ValueError("Archivo inválido. La cabecera no corresponde a un formato RIFF/WAVE válido.")

        with wave.open(ruta_archivo, "rb") as wav_file:
            self.num_canales = wav_file.getnchannels()
            self.sample_rate = wav_file.getframerate()
            self.sample_width = wav_file.getsampwidth()
            num_frames = wav_file.getnframes()

            if self.sample_width != 2:
                raise ValueError("Solo se admiten archivos WAV PCM de 16 bits.")

            raw_bytes = wav_file.readframes(num_frames)

        # RF-005 y Script DB-002: Reservar bloque contiguo en RAM
        self.alloc_memory(raw_bytes)

        return {
            "archivo": os.path.basename(ruta_archivo),
            "cabecera": "RIFF/WAVE válida",
            "sample_rate": f"{self.sample_rate} Hz",
            "canales": f"Estéreo (2)" if self.num_canales == 2 else f"Mono ({self.num_canales})",
            "muestras": self.num_muestras,
            "direccion_ram": hex(ctypes.addressof(self.buffer_ram))
        }

    def alloc_memory(self, raw_bytes: bytes):
        """DB-002: Reserva un bloque de RAM contiguo (int16) accesible por puntero desde C++."""
        arreglo_np = np.frombuffer(raw_bytes, dtype=np.int16)
        self.num_muestras = len(arreglo_np)

        # Guardamos una vista reducida (máx. 5000 puntos) únicamente para dibujar la gráfica original en UI
        paso = max(1, self.num_muestras // 5000)
        self.onda_original_preview = arreglo_np[::paso].copy()

        # Reserva del arreglo nativo de C en memoria RAM para sobrescritura In-Place
        TipoArregloC = ctypes.c_int16 * self.num_muestras
        self.buffer_ram = TipoArregloC.from_buffer_copy(raw_bytes)

    def ejecutar_en_hilo(self, intensidad: int, ganancia_db: float, cola_mensajes: queue.Queue):
        """Capa 2: Levanta el Worker Thread para no congelar el hilo principal de Tkinter."""
        hilo = threading.Thread(
            target=self._tarea_cruce_frontera,
            args=(intensidad, ganancia_db, cola_mensajes),
            daemon=True
        )
        hilo.start()

    def _tarea_cruce_frontera(self, intensidad: int, ganancia_db: float, cola_mensajes: queue.Queue):
        """RF-011, RF-012, RF-013 y RNF-001: Invoca C++ In-Place y mide tiempos con perf_counter."""
        try:
            cola_mensajes.put({"estado": "progreso", "porcentaje": 35, "detalle": "Punteros de memoria asignados (ctypes)"})

            puntero_ram = ctypes.cast(self.buffer_ram, ctypes.POINTER(ctypes.c_int16))

            cola_mensajes.put({"estado": "progreso", "porcentaje": 70, "detalle": "Procesando en motor C++ (In-Place)..."})

            # RNF-001: Medición de rendimiento en milisegundos
            inicio = time.perf_counter()
            self.lib.procesar_audio_inplace(
                puntero_ram,
                ctypes.c_int32(self.num_muestras),
                ctypes.c_int32(intensidad),
                ctypes.c_float(ganancia_db)
            )
            tiempo_ms = (time.perf_counter() - inicio) * 1000.0

            # Extraer vista reducida de la memoria ya sobrescrita para la gráfica comparativa
            arreglo_actualizado = np.ctypeslib.as_array(self.buffer_ram)
            paso = max(1, self.num_muestras // 5000)
            onda_procesada_preview = arreglo_actualizado[::paso].copy()

            cola_mensajes.put({
                "estado": "completado",
                "porcentaje": 100,
                "tiempo_ms": round(tiempo_ms, 2),
                "muestras": self.num_muestras,
                "onda_original": self.onda_original_preview,
                "onda_procesada": onda_procesada_preview
            })
        except Exception as e:
            cola_mensajes.put({"estado": "error", "mensaje": str(e)})

    def exportar_wav(self, ruta_destino: str):
        """RF-015: Empaqueta el arreglo de RAM modificado de vuelta a un archivo .wav físico."""
        if self.buffer_ram is None:
            raise RuntimeError("No hay datos en memoria RAM para exportar.")

        with wave.open(ruta_destino, "wb") as wav_out:
            wav_out.setnchannels(self.num_canales)
            wav_out.setsampwidth(self.sample_width)
            wav_out.setframerate(self.sample_rate)
            wav_out.writeframes(bytes(self.buffer_ram))