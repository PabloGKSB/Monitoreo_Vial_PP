package com.monitoreovial.anotador.capture

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.LocationManager
import androidx.core.content.ContextCompat

object GpsAccess {
    fun requested(context: Context) = context.getSharedPreferences("monitoring_ui", Context.MODE_PRIVATE).getBoolean("gps", true)
    fun precise(context: Context) = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
    fun readiness(context: Context): String {
        if (!precise(context)) return "Sin permiso preciso"
        val manager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        return when {
            !manager.allProviders.contains(LocationManager.GPS_PROVIDER) -> "GPS no disponible"
            !manager.isProviderEnabled(LocationManager.GPS_PROVIDER) -> "GPS desactivado"
            else -> "Disponible"
        }
    }
}
