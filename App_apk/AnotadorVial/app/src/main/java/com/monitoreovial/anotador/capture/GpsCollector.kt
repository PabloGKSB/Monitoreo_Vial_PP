package com.monitoreovial.anotador.capture

import android.annotation.SuppressLint
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import android.os.Build
import android.os.Looper

class GpsCollector(private val manager: LocationManager, private val accept: (GpsSample) -> Unit) : LocationListener {
    @Volatile var state = "Sin captura"
        private set
    @Volatile var lastFix: GpsSample? = null
        private set
    var registered = false
        private set

    @SuppressLint("MissingPermission")
    fun start(looper: Looper) {
        try {
            manager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 1000L, 0f, this, looper)
            registered = true
            state = "Esperando fijación"
        } catch (_: SecurityException) { state = "Sin permiso preciso" }
        catch (_: IllegalArgumentException) { state = "GPS no disponible" }
        catch (_: RuntimeException) { state = "Error al registrar GPS" }
    }
    override fun onLocationChanged(location: Location) {
        if (!registered) return
        val sample = GpsSample(location.elapsedRealtimeNanos, location.time, location.latitude, location.longitude,
            if (location.hasAltitude()) location.altitude else null,
            if (location.hasSpeed()) location.speed else null,
            if (location.hasBearing()) location.bearing else null,
            if (location.hasAccuracy()) location.accuracy else null,
            if (location.hasVerticalAccuracy()) location.verticalAccuracyMeters else null,
            if (location.hasSpeedAccuracy()) location.speedAccuracyMetersPerSecond else null,
            if (location.hasBearingAccuracy()) location.bearingAccuracyDegrees else null,
            if (Build.VERSION.SDK_INT >= 31) location.isMock else location.isFromMockProvider)
        lastFix = sample
        state = "Recibiendo GPS"
        accept(sample)
    }
    override fun onProviderDisabled(provider: String) { state = "GPS desactivado" }
    override fun onProviderEnabled(provider: String) { state = "Esperando fijación" }
    @Deprecated("Legacy Android callback")
    override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) = Unit
    fun close() {
        if (registered) {
            registered = false
            try { manager.removeUpdates(this) } catch (_: SecurityException) { state = "Permiso revocado" }
        }
    }
}
