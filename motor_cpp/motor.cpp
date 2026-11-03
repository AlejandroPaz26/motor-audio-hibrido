#include <cstdint>
#include <cmath>
#include <algorithm>

// Macro de portabilidad para exportar símbolos en Windows (.dll) y Linux (.so)
#if defined(_WIN32) || defined(_WIN64)
    #define EXPORT __declspec(dllexport)
#else
    #define EXPORT __attribute__((visibility("default")))
#endif

extern "C" {

    /**
     * Procesa un arreglo de muestras de audio PCM de 16 bits In-Place.
     * 
     * @param buffer        Puntero al inicio del arreglo en Memoria RAM (int16_t*).
     * @param num_muestras  Longitud total del arreglo unidimensional.
     * @param intensidad    Intensidad del filtro matemático (0 a 100%).
     * @param ganancia_db   Ajuste de ganancia en decibelios (ej. -3.0f).
     */
    EXPORT void procesar_audio_inplace(int16_t* buffer, int32_t num_muestras, int32_t intensidad, float ganancia_db) {
        if (buffer == nullptr || num_muestras <= 0) {
            return;
        }

        // 1. Convertir ganancia de decibelios (dB) a factor lineal: 10^(dB / 20)
        float factor_ganancia = std::pow(10.0f, ganancia_db / 20.0f);

        // 2. Normalizar la intensidad del filtro (0.0 a 1.0) para el filtro paso-bajo / suavizado
        float alpha = std::clamp(intensidad / 100.0f, 0.0f, 1.0f);

        float muestra_anterior = static_cast<float>(buffer[0]);

        // 3. Iteración secuencial y sobrescritura In-Place (O(1) en memoria adicional)
        for (int32_t i = 0; i < num_muestras; ++i) {
            float muestra_actual = static_cast<float>(buffer[i]);

            // Aplicar filtro matemático ponderado según la intensidad
            float muestra_filtrada = (1.0f - alpha * 0.5f) * muestra_actual + (alpha * 0.5f) * muestra_anterior;
            muestra_anterior = muestra_filtrada;

            // Aplicar factor de ganancia
            float resultado = muestra_filtrada * factor_ganancia;

            // Clamping en los límites de 16-bit PCM [-32768, 32767] para evitar saturación (clipping)
            if (resultado > 32767.0f) resultado = 32767.0f;
            if (resultado < -32768.0f) resultado = -32768.0f;

            // Sobrescritura directa en la misma celda de memoria RAM
            buffer[i] = static_cast<int16_t>(resultado);
        }
    }

}