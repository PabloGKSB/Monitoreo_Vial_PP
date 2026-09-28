package com.monitoreovial.anotador.capture

import android.content.ClipData
import android.content.Intent
import android.os.Handler
import android.os.Looper
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.sp
import androidx.core.content.FileProvider
import com.monitoreovial.anotador.SesionActual
import java.io.File
import java.util.Locale

@Composable fun CapturePanel() {
    val s = CaptureState.snapshot
    val context = LocalContext.current
    Column {
        Text(s.phase, fontSize = 13.sp)
        Text("GPS: ${s.gpsState}", fontSize = 12.sp)
        Text(String.format(Locale.US, "Acc: %d / %.1f Hz | Giro: %s", s.accel.count, s.accel.hz,
            if (s.gyroAvailable) "${s.gyro.count} / %.1f Hz".format(Locale.US, s.gyro.hz) else "no disponible"), fontSize = 12.sp)
        if (s.dropped > 0) Text("Muestras descartadas por cola llena: ${s.dropped}", fontSize = 12.sp)
        s.error?.let { Text(it, fontSize = 12.sp) }
        if (!s.busy && !SesionActual.activa && s.directory != null) {
            OutlinedButton(enabled = !CaptureState.exporting, onClick = {
                val annotations = SesionActual.archivo ?: return@OutlinedButton
                CaptureState.exporting = true
                Thread({
                    var output: File? = null
                    var failure: String? = null
                    try {
                        val zip = File(s.directory.parentFile, "${s.directory.name}_${System.currentTimeMillis()}.zip")
                        output = zip
                        ImuArchive.create(s.directory, annotations, zip)
                    } catch (error: Exception) { failure = error.message ?: "Error de exportacion" }
                    Handler(Looper.getMainLooper()).post {
                        CaptureState.exporting = false
                        try {
                            if (failure != null) error(failure!!)
                            val uri = FileProvider.getUriForFile(context, "com.monitoreovial.anotador.fileprovider", output!!)
                            val intent = Intent(Intent.ACTION_SEND).setType("application/zip")
                                .putExtra(Intent.EXTRA_STREAM, uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                            intent.clipData = ClipData.newUri(context.contentResolver, "Captura IMU", uri)
                            context.startActivity(Intent.createChooser(intent, "Compartir captura IMU"))
                        } catch (error: Exception) {
                            CaptureState.snapshot = CaptureState.snapshot.copy(error = error.message ?: "No se pudo compartir")
                        }
                    }
                }, "imu-export").start()
            }) { Text(if (CaptureState.exporting) "Preparando ZIP" else "COMPARTIR CAPTURA IMU") }
        }
    }
}
