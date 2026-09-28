package com.monitoreovial.anotador.history

import org.apache.commons.csv.CSVFormat
import java.io.File

data class SavedEvent(val type: String, val timestamp: String, val epochMs: Long, val elapsedMs: Long)
data class SavedTrip(
    val file: File, val id: String, val startedEpochMs: Long?, val durationMs: Long?,
    val events: List<SavedEvent>, val closed: Boolean, val error: String? = null
) {
    val imuDirectory: File get() = File(file.parentFile, file.nameWithoutExtension + "_imu")
}

/** Read legacy exports without mutating recordings or inferring a missing end marker. */
object TripHistory {
    fun load(directory: File, excluded: File? = null): List<SavedTrip> {
        val files = directory.listFiles() ?: if (directory.exists()) error("No se puede leer el historial") else return emptyList()
        return files.filter { it.isFile && it.name.endsWith("_anotaciones.csv") && it != excluded }
            .map { file ->
                try { read(file) } catch (error: Exception) {
                    SavedTrip(file, file.nameWithoutExtension, null, null, emptyList(), false,
                        error.message ?: "Archivo no legible")
                }
            }.sortedByDescending { it.startedEpochMs ?: it.file.lastModified() }
    }

    fun read(file: File): SavedTrip {
        val format = CSVFormat.RFC4180.builder().setHeader().setSkipHeaderRecord(true).get()
        file.bufferedReader(Charsets.UTF_8).use { reader ->
            format.parse(reader).use { parser ->
                val required = setOf("trip_id", "timestamp", "epoch_ms", "elapsed_ms", "event_type")
                require(parser.headerMap.keys.containsAll(required)) { "Cabecera de anotaciones incompatible" }
                var id: String? = null
                var start: Long? = null
                var end: Long? = null
                val events = mutableListOf<SavedEvent>()
                for (row in parser) {
                    val trip = row.get("trip_id")
                    require(id == null || id == trip) { "Identificadores de recorrido mezclados" }
                    id = trip
                    val epoch = row.get("epoch_ms").toLong()
                    val elapsed = row.get("elapsed_ms").toLong()
                    require(elapsed >= 0) { "Tiempo transcurrido negativo" }
                    when (val type = row.get("event_type")) {
                        "MONITOREO_INICIO" -> { require(start == null) { "Inicio duplicado" }; start = epoch }
                        "MONITOREO_FIN" -> { require(end == null) { "Fin duplicado" }; end = elapsed }
                        else -> events += SavedEvent(type, row.get("timestamp"), epoch, elapsed)
                    }
                }
                require(start != null) { "Sin marca de inicio" }
                return SavedTrip(file, id ?: file.nameWithoutExtension, start, end,
                    events.sortedBy { it.elapsedMs }, end != null)
            }
        }
    }
}
