package com.monitoreovial.anotador.capture

sealed interface CaptureSample {
    val sensor: String
    val timestampNs: Long
    fun cells(): List<String>
}

data class RotationSample(
    override val timestampNs: Long, val x: Float, val y: Float, val z: Float,
    val w: Float?, val headingAccuracyRad: Float?, val valueCount: Int, val accuracy: Int
) : CaptureSample {
    override val sensor = "rotation_vector"
    override fun cells() = listOf(x, y, z, w, headingAccuracyRad, valueCount, accuracy).map { it?.toString().orEmpty() }
}

data class GpsSample(
    override val timestampNs: Long, val epochMs: Long, val latitude: Double, val longitude: Double,
    val altitudeM: Double?, val speedMps: Float?, val bearingDeg: Float?, val accuracyM: Float?,
    val verticalAccuracyM: Float?, val speedAccuracyMps: Float?, val bearingAccuracyDeg: Float?,
    val mock: Boolean
) : CaptureSample {
    override val sensor = "gps"
    override fun cells() = listOf(epochMs, latitude, longitude, altitudeM, speedMps, bearingDeg,
        accuracyM, verticalAccuracyM, speedAccuracyMps, bearingAccuracyDeg, "gps", mock).map { it?.toString().orEmpty() }
}

object CaptureSchema {
    const val VERSION = "capture-preview-2"
    val columns = mapOf(
        "accelerometer" to "x,y,z", "gyroscope" to "x,y,z", "gravity" to "x,y,z",
        "linear_acceleration" to "x,y,z",
        "rotation_vector" to "qx,qy,qz,qw,heading_accuracy_rad,value_count,sensor_accuracy",
        "gps" to "location_epoch_ms,latitude,longitude,altitude_m,speed_mps,bearing_deg,horizontal_accuracy_m,vertical_accuracy_m,speed_accuracy_mps,bearing_accuracy_deg,provider,is_mock"
    )
    fun header(sensor: String) = "sensor_timestamp_ns,epoch_ms_derived,seconds_elapsed," + columns.getValue(sensor) + "\n"
    fun row(sample: CaptureSample, originNs: Long, epochMs: Long): String {
        val delta = sample.timestampNs - originNs
        return (listOf(sample.timestampNs.toString(), (epochMs + delta / 1_000_000L).toString(), (delta / 1e9).toString()) + sample.cells()).joinToString(",") + "\n"
    }
}
