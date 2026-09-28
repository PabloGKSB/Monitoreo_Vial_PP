package com.monitoreovial.anotador.capture

import android.content.Context
import android.content.Intent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.ContextCompat
import java.io.File
import com.monitoreovial.anotador.SesionActual

data class CaptureSnapshot(
    val phase: String = "Sin captura IMU", val busy: Boolean = false,
    val accel: StreamSummary = StreamSummary(0, 0.0, 0.0, 0, 0),
    val gyro: StreamSummary = StreamSummary(0, 0.0, 0.0, 0, 0),
    val gyroAvailable: Boolean = false, val dropped: Long = 0,
    val error: String? = null, val directory: File? = null,
    val streams: Map<String, StreamSummary> = emptyMap(),
    val sensorStates: Map<String, String> = emptyMap(),
    val gpsState: String = "Sin captura", val gpsAccuracyM: Float? = null,
    val gpsAgeSeconds: Double? = null, val gpsSpeedMps: Float? = null
)

object CaptureState {
    var uiVisible = false
    var snapshot by mutableStateOf(CaptureSnapshot())
        internal set
    internal var stopRequested = false
    internal var service: RecordingService? = null
    var exporting by mutableStateOf(false)
        internal set

    fun begin(context: Context, annotations: File, gpsRequested: Boolean = true) {
        stopRequested = false
        snapshot = CaptureSnapshot(phase = "Preparando sensores", busy = true)
        try {
            ContextCompat.startForegroundService(context, Intent(context, RecordingService::class.java)
                .putExtra("annotations", annotations.absolutePath)
                .putExtra("gps_requested", gpsRequested && GpsAccess.requested(context))
                .putExtra("started_from_visible_ui", uiVisible)
                .putExtra("annotation_origin_monotonic_ms", SesionActual.reloj!!.startedMonotonicMs)
                .putExtra("annotation_origin_epoch_ms", SesionActual.reloj!!.startedEpochMs))
        } catch (error: Exception) {
            snapshot = CaptureSnapshot(phase = "Error IMU", error = error.message ?: "No se pudo iniciar captura")
        }
    }
    fun finish() {
        stopRequested = true
        if (snapshot.busy) snapshot = snapshot.copy(phase = "Guardando sensores")
        service?.finishCapture()
    }
}
