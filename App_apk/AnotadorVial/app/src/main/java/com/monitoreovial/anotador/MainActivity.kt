package com.monitoreovial.anotador

import android.Manifest
import android.app.Activity
import android.content.ClipData
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.SystemClock
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.provider.Settings
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import com.monitoreovial.anotador.ui.theme.AnotadorVialTheme
import com.monitoreovial.anotador.session.SessionClock
import com.monitoreovial.anotador.storage.AnnotationCsvStore
import com.monitoreovial.anotador.capture.CaptureState
import com.monitoreovial.anotador.capture.CapturePanel
import com.monitoreovial.anotador.ui.MonitoringApp
import kotlinx.coroutines.delay
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale


// ======================================================
// PREFERENCIAS
// ======================================================

private const val PREFS_NAME = "anotador_vial_prefs"
private const val PREF_NOMBRE_RECORRIDO = "nombre_recorrido"


// ======================================================
// MODELO DE ANOTACIÓN
// ======================================================

data class Anotacion(
    val tipo: String,
    val timestamp: String,
    val epochMs: Long,
    val hora: String,
    val elapsedMs: Long
)


// ======================================================
// SESIÓN GLOBAL
// ======================================================
//
// Esta información es compartida entre:
//
// MainActivity
// OverlayService
//
// La burbuja puede estar activa aunque
// SesionActual.activa sea FALSE.
//
// ======================================================

object SesionActual {
    var reloj: SessionClock? = null

    var nombreBase by mutableStateOf("recorrido")

    var idRecorrido by mutableStateOf("")

    var archivo by mutableStateOf<File?>(null)

    var tiempoInicioElapsed by mutableLongStateOf(0L)

    var activa by mutableStateOf(false)

    var finalizada by mutableStateOf(false)

    var duracionFinalMs by mutableLongStateOf(0L)

    val anotaciones =
        mutableStateListOf<Anotacion>()
}


// ======================================================
// MAIN ACTIVITY
// ======================================================

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {

        super.onCreate(savedInstanceState)

        SesionActual.nombreBase =
            obtenerNombreBase(this)

        solicitarPermisoNotificaciones(this)

        enableEdgeToEdge()

        setContent {

            MonitoringApp()
        }
    }


    // ==================================================
    // Cada vez que volvemos a la app comprobamos
    // si ya podemos mostrar la burbuja.
    // ==================================================

    override fun onResume() {

        super.onResume()
        CaptureState.uiVisible = true

        if (Settings.canDrawOverlays(this) &&
            getSharedPreferences("monitoring_ui", MODE_PRIVATE).getBoolean("overlay", true)) {

            iniciarOverlayService(this)
        }
    }

    override fun onPause() {
        CaptureState.uiVisible = false
        super.onPause()
    }
}


// ======================================================
// APLICACIÓN PRINCIPAL
// ======================================================

@Composable
fun AnotadorVialApp(
    modifier: Modifier = Modifier
) {

    val context =
        LocalContext.current


    var tiempoTranscurrido by remember {
        mutableLongStateOf(0L)
    }


    // ==================================================
    // CRONÓMETRO
    // ==================================================

    LaunchedEffect(
        SesionActual.activa,
        SesionActual.tiempoInicioElapsed
    ) {

        while (SesionActual.activa) {

            tiempoTranscurrido =
                SystemClock.elapsedRealtime() -
                        SesionActual.tiempoInicioElapsed

            delay(250)
        }
    }


    // ==================================================
    // DECIDIR PANTALLA
    // ==================================================

    when {

        // --------------------------------------------------
        // RECORRIDO ACTIVO
        // --------------------------------------------------

        SesionActual.activa -> {

            PantallaRecorrido(

                modifier = modifier,

                idRecorrido =
                    SesionActual.idRecorrido,

                tiempoTranscurrido =
                    tiempoTranscurrido,

                anotaciones =
                    SesionActual.anotaciones,

                onEvento = { evento ->

                    val correcto =
                        registrarEventoSesion(
                            evento
                        )

                    if (correcto) {

                        vibrar(
                            context,
                            70
                        )

                    } else {

                        Toast.makeText(
                            context,
                            "Error guardando anotación",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                },

                onDeshacer = {

                    if (
                        deshacerUltimaAnotacion()
                    ) {

                        vibrar(
                            context,
                            120
                        )

                    } else {

                        Toast.makeText(
                            context,
                            "No hay anotaciones para deshacer",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                },

                onFinalizar = {

                    if (finalizarSesion()) {

                        vibrar(
                            context,
                            150
                        )

                        // Refrescamos la burbuja.
                        // NO la cerramos.
                        iniciarOverlayService(
                            context
                        )

                        Toast.makeText(
                            context,
                            "Monitoreo finalizado",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                }
            )
        }


        // --------------------------------------------------
        // RECORRIDO FINALIZADO
        // --------------------------------------------------

        SesionActual.finalizada -> {

            PantallaFinal(

                modifier = modifier,

                idRecorrido =
                    SesionActual.idRecorrido,

                duracion =
                    SesionActual.duracionFinalMs,

                cantidadEventos =
                    cantidadEventosUsuario(),

                nombreArchivo =
                    SesionActual.archivo?.name
                        ?: "Sin archivo",

                onCompartir = {

                    SesionActual.archivo?.let {

                        compartirCSV(
                            context,
                            it
                        )
                    }
                },

                onNuevoRecorrido = {

                    limpiarParaNuevoRecorrido()

                    iniciarOverlayService(
                        context
                    )
                }
            )
        }


        // --------------------------------------------------
        // SIN RECORRIDO
        // --------------------------------------------------

        else -> {

            PantallaInicio(

                modifier =
                    modifier,

                nombreRecorrido =
                    SesionActual.nombreBase,

                onNombreChange = {

                    SesionActual.nombreBase =
                        it

                    guardarNombreBase(
                        context,
                        it
                    )
                },

                onConfigurarBurbuja = {

                    abrirConfiguracionOverlay(
                        context
                    )
                },

                onIniciar = {

                    if (
                        !Settings.canDrawOverlays(
                            context
                        )
                    ) {

                        Toast.makeText(
                            context,
                            "Primero permite mostrar la burbuja sobre otras aplicaciones",
                            Toast.LENGTH_LONG
                        ).show()

                        abrirConfiguracionOverlay(
                            context
                        )

                    } else {

                        val correcto =
                            iniciarNuevaSesion(
                                context,
                                SesionActual.nombreBase
                            )

                        if (correcto) {

                            vibrar(
                                context,
                                100
                            )

                            iniciarOverlayService(
                                context
                            )

                            Toast.makeText(
                                context,
                                "Monitoreo iniciado",
                                Toast.LENGTH_SHORT
                            ).show()

                        } else {

                            Toast.makeText(
                                context,
                                "No se pudo iniciar el monitoreo",
                                Toast.LENGTH_LONG
                            ).show()
                        }
                    }
                }
            )
        }
    }
}


// ======================================================
// PANTALLA INICIAL
// ======================================================

@Composable
fun PantallaInicio(
    modifier: Modifier,
    nombreRecorrido: String,
    onNombreChange: (String) -> Unit,
    onConfigurarBurbuja: () -> Unit,
    onIniciar: () -> Unit
) {

    Column(

        modifier = modifier
            .fillMaxSize()
            .padding(24.dp),

        verticalArrangement =
            Arrangement.Center,

        horizontalAlignment =
            Alignment.CenterHorizontally
    ) {

        Text(
            text = "ANOTADOR VIAL",
            fontSize = 30.sp,
            fontWeight = FontWeight.Bold
        )

        Spacer(
            Modifier.height(8.dp)
        )

        Text(
            text = "Registro manual de eventos viales",
            style =
                MaterialTheme.typography.bodyLarge
        )

        Spacer(
            Modifier.height(8.dp)
        )

        Text(
            text = "La burbuja puede permanecer activa antes de iniciar el monitoreo.",
            style =
                MaterialTheme.typography.bodyMedium
        )

        Spacer(
            Modifier.height(30.dp)
        )

        OutlinedTextField(

            value =
                nombreRecorrido,

            onValueChange =
                onNombreChange,

            label = {
                Text(
                    "Nombre base del recorrido"
                )
            },

            modifier =
                Modifier.fillMaxWidth(),

            singleLine =
                true
        )

        Spacer(
            Modifier.height(20.dp)
        )

        OutlinedButton(

            onClick =
                onConfigurarBurbuja,

            modifier =
                Modifier.fillMaxWidth()
        ) {

            Text(
                "⚙ PERMISO / CONFIGURAR BURBUJA"
            )
        }

        Spacer(
            Modifier.height(12.dp)
        )

        Button(

            onClick =
                onIniciar,

            modifier = Modifier
                .fillMaxWidth()
                .height(60.dp),

            shape =
                RoundedCornerShape(14.dp)
        ) {

            Text(
                text =
                    "INICIAR MONITOREO",
                fontSize =
                    18.sp,
                fontWeight =
                    FontWeight.Bold
            )
        }

        Spacer(
            Modifier.height(16.dp)
        )

        Text(
            text =
                "También puedes iniciar el monitoreo directamente desde la burbuja 🚗."
        )
    }
}


// ======================================================
// PANTALLA RECORRIDO
// ======================================================

@Composable
fun PantallaRecorrido(
    modifier: Modifier,
    idRecorrido: String,
    tiempoTranscurrido: Long,
    anotaciones: List<Anotacion>,
    onEvento: (String) -> Unit,
    onDeshacer: () -> Unit,
    onFinalizar: () -> Unit
) {

    val eventosUsuario =
        anotaciones.filter {
            !esEventoSistema(it.tipo)
        }


    Column(

        modifier = modifier
            .fillMaxSize()
            .padding(16.dp)
            .verticalScroll(rememberScrollState())
    ) {

        CapturePanel()
        Text(
            text =
                "MONITOREO ACTIVO",
            fontSize =
                24.sp,
            fontWeight =
                FontWeight.Bold,
            modifier =
                Modifier.align(
                    Alignment.CenterHorizontally
                )
        )

        Spacer(
            Modifier.height(4.dp)
        )

        Text(
            text =
                idRecorrido,
            fontSize =
                12.sp,
            modifier =
                Modifier.align(
                    Alignment.CenterHorizontally
                )
        )

        Spacer(
            Modifier.height(8.dp)
        )

        Text(
            text =
                formatearTiempo(
                    tiempoTranscurrido
                ),
            fontSize =
                28.sp,
            fontWeight =
                FontWeight.Bold,
            modifier =
                Modifier.align(
                    Alignment.CenterHorizontally
                )
        )

        Spacer(
            Modifier.height(5.dp)
        )

        Text(
            text =
                "🔴 Burbuja disponible",
            modifier =
                Modifier.align(
                    Alignment.CenterHorizontally
                )
        )

        Spacer(
            Modifier.height(18.dp)
        )


        // ==================================================
        // BACHE / LOMO
        // ==================================================

        Row(
            modifier =
                Modifier.fillMaxWidth(),
            horizontalArrangement =
                Arrangement.spacedBy(10.dp)
        ) {

            BotonEvento(
                texto =
                    "🕳 BACHE",
                modifier =
                    Modifier.weight(1f)
            ) {
                onEvento(
                    "BACHE"
                )
            }

            BotonEvento(
                texto =
                    "🚧 LOMO",
                modifier =
                    Modifier.weight(1f)
            ) {
                onEvento(
                    "LOMO_DE_TORO"
                )
            }
        }

        Spacer(
            Modifier.height(10.dp)
        )


        // ==================================================
        // DESVIACIÓN / CAMINO
        // ==================================================

        Row(
            modifier =
                Modifier.fillMaxWidth(),
            horizontalArrangement =
                Arrangement.spacedBy(10.dp)
        ) {

            BotonEvento(
                texto =
                    "↔ DESVIACIÓN",
                modifier =
                    Modifier.weight(1f)
            ) {
                onEvento(
                    "DESVIACION"
                )
            }

            BotonEvento(
                texto =
                    "⚠ CAMINO MALO",
                modifier =
                    Modifier.weight(1f)
            ) {
                onEvento(
                    "CAMINO_MALO"
                )
            }
        }

        Spacer(
            Modifier.height(10.dp)
        )


        // ==================================================
        // GIRO / OTRO
        // ==================================================

        Row(
            modifier =
                Modifier.fillMaxWidth(),
            horizontalArrangement =
                Arrangement.spacedBy(10.dp)
        ) {

            BotonEvento(
                texto =
                    "↩ GIRO",
                modifier =
                    Modifier.weight(1f)
            ) {
                onEvento(
                    "GIRO"
                )
            }

            BotonEvento(
                texto =
                    "❓ OTRO",
                modifier =
                    Modifier.weight(1f)
            ) {
                onEvento(
                    "OTRO"
                )
            }
        }

        Spacer(
            Modifier.height(15.dp)
        )

        OutlinedButton(

            onClick =
                onDeshacer,

            enabled =
                eventosUsuario.isNotEmpty(),

            modifier =
                Modifier.fillMaxWidth()
        ) {

            Text(
                "↶ DESHACER ÚLTIMA ANOTACIÓN"
            )
        }

        Spacer(
            Modifier.height(14.dp)
        )

        Text(
            text =
                "Eventos (${eventosUsuario.size})",
            fontSize =
                18.sp,
            fontWeight =
                FontWeight.Bold
        )

        HorizontalDivider(
            modifier =
                Modifier.padding(
                    vertical = 8.dp
                )
        )

        LazyColumn(

            modifier = Modifier
                .height(140.dp)
                .fillMaxWidth()
        ) {

            items(
                eventosUsuario
            ) { anotacion ->

                Row(

                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(
                            vertical = 7.dp
                        ),

                    horizontalArrangement =
                        Arrangement.SpaceBetween
                ) {

                    Text(
                        text =
                            anotacion.tipo,
                        fontWeight =
                            FontWeight.Medium
                    )

                    Text(
                        text =
                            anotacion.hora
                    )
                }

                HorizontalDivider()
            }
        }

        Spacer(
            Modifier.height(10.dp)
        )

        Button(

            onClick =
                onFinalizar,

            modifier = Modifier
                .fillMaxWidth()
                .height(58.dp),

            shape =
                RoundedCornerShape(14.dp)
        ) {

            Text(
                text =
                    "FINALIZAR MONITOREO",
                fontWeight =
                    FontWeight.Bold
            )
        }
    }
}


// ======================================================
// PANTALLA FINAL
// ======================================================

@Composable
fun PantallaFinal(
    modifier: Modifier,
    idRecorrido: String,
    duracion: Long,
    cantidadEventos: Int,
    nombreArchivo: String,
    onCompartir: () -> Unit,
    onNuevoRecorrido: () -> Unit
) {

    Column(

        modifier = modifier
            .fillMaxSize()
            .padding(24.dp)
            .verticalScroll(rememberScrollState()),

        verticalArrangement =
            Arrangement.Center,

        horizontalAlignment =
            Alignment.CenterHorizontally
    ) {

        CapturePanel()
        Text(
            text =
                "MONITOREO FINALIZADO",
            fontSize =
                26.sp,
            fontWeight =
                FontWeight.Bold
        )

        Spacer(
            Modifier.height(22.dp)
        )

        Text(
            "Recorrido"
        )

        Text(
            text =
                idRecorrido,
            fontWeight =
                FontWeight.Bold
        )

        Spacer(
            Modifier.height(16.dp)
        )

        Text(
            "Duración"
        )

        Text(
            text =
                formatearTiempo(
                    duracion
                ),
            fontSize =
                23.sp,
            fontWeight =
                FontWeight.Bold
        )

        Spacer(
            Modifier.height(16.dp)
        )

        Text(
            "Eventos viales registrados"
        )

        Text(
            text =
                cantidadEventos.toString(),
            fontSize =
                25.sp,
            fontWeight =
                FontWeight.Bold
        )

        Spacer(
            Modifier.height(16.dp)
        )

        Text(
            "Archivo CSV"
        )

        Text(
            text =
                nombreArchivo,
            fontSize =
                13.sp
        )

        Spacer(
            Modifier.height(30.dp)
        )

        Button(

            onClick =
                onCompartir,

            modifier = Modifier
                .fillMaxWidth()
                .height(58.dp)
        ) {

            Text(
                text =
                    "COMPARTIR CSV",
                fontWeight =
                    FontWeight.Bold
            )
        }

        Spacer(
            Modifier.height(12.dp)
        )

        OutlinedButton(

            onClick =
                onNuevoRecorrido,
            enabled = !CaptureState.snapshot.busy && !CaptureState.exporting,

            modifier = Modifier
                .fillMaxWidth()
                .height(55.dp)
        ) {

            Text(
                "PREPARAR NUEVO RECORRIDO"
            )
        }

        Spacer(
            Modifier.height(16.dp)
        )

        Text(
            text =
                "La burbuja 🚗 permanece disponible para el próximo monitoreo."
        )
    }
}


// ======================================================
// BOTÓN EVENTO
// ======================================================

@Composable
fun BotonEvento(
    texto: String,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {

    Button(

        onClick =
            onClick,

        modifier =
            modifier.height(68.dp),

        shape =
            RoundedCornerShape(14.dp)
    ) {

        Text(
            text =
                texto,
            fontSize =
                14.sp,
            fontWeight =
                FontWeight.Bold
        )
    }
}


// ======================================================
// INICIAR UNA NUEVA SESIÓN
// ======================================================

fun iniciarNuevaSesion(
    context: Context,
    nombreBase: String,
    gpsRequested: Boolean = true
): Boolean {
    if (CaptureState.snapshot.busy || CaptureState.exporting) return false

    if (SesionActual.activa) {

        return false
    }

    if (nombreBase.isBlank()) {

        return false
    }


    guardarNombreBase(
        context,
        nombreBase
    )


    SesionActual.nombreBase =
        nombreBase


    SesionActual.anotaciones.clear()


    val id =
        generarIdRecorrido(
            nombreBase
        )


    val archivo =
        crearArchivoRecorrido(
            context,
            id
        ) ?: return false


    SesionActual.idRecorrido =
        id

    SesionActual.archivo =
        archivo

    val reloj = SessionClock(System::currentTimeMillis, SystemClock::elapsedRealtime)
    SesionActual.reloj = reloj
    SesionActual.tiempoInicioElapsed = reloj.startedMonotonicMs

    SesionActual.duracionFinalMs =
        0L

    SesionActual.finalizada =
        false

    SesionActual.activa =
        true


    // ==================================================
    // MARCA ESPECIAL DE INICIO
    // ==================================================

    val inicioGuardado =
        registrarEventoSesion(
            evento =
                "MONITOREO_INICIO",
            elapsedForzado =
                0L
        )


    if (!inicioGuardado) {

        SesionActual.activa =
            false

        SesionActual.archivo =
            null

        archivo.delete()

        return false
    }


    CaptureState.begin(context.applicationContext, archivo, gpsRequested)
    return true
}


// ======================================================
// FINALIZAR SESIÓN
// ======================================================

fun finalizarSesion(): Boolean {

    if (!SesionActual.activa) {

        return false
    }


    val duracion = SesionActual.reloj?.elapsedMs() ?: return false


    // ==================================================
    // Guardamos FIN antes de marcar la sesión inactiva
    // ==================================================

    val finGuardado =
        registrarEventoSesion(
            evento =
                "MONITOREO_FIN",
            elapsedForzado =
                duracion
        )


    if (!finGuardado) {

        return false
    }


    SesionActual.duracionFinalMs =
        duracion

    SesionActual.activa =
        false

    SesionActual.finalizada =
        true
    CaptureState.finish()


    return true
}


// ======================================================
// REGISTRAR EVENTO
// ======================================================

fun registrarEventoSesion(
    evento: String,
    elapsedForzado: Long? = null
): Boolean {

    if (!SesionActual.activa) {

        return false
    }


    val archivo =
        SesionActual.archivo
            ?: return false


    val momento = SesionActual.reloj?.mark() ?: return false
    val epoch = momento.epochMs


    val elapsed = elapsedForzado ?: momento.elapsedMs


    val anotacion =
        Anotacion(

            tipo =
                evento,

            timestamp =
                obtenerTimestamp(
                    epoch
                ),

            epochMs =
                epoch,

            hora =
                obtenerHora(
                    epoch
                ),

            elapsedMs =
                elapsed
        )


    val correcto =
        agregarAnotacionCSV(

            archivo =
                archivo,

            idRecorrido =
                SesionActual.idRecorrido,

            anotacion =
                anotacion
        )


    if (correcto) {

        // Más nuevo primero
        SesionActual.anotaciones.add(
            0,
            anotacion
        )
    }


    return correcto
}


// ======================================================
// DESHACER ÚLTIMO EVENTO VIAL
// ======================================================
//
// No permite borrar:
//
// MONITOREO_INICIO
// MONITOREO_FIN
//
// ======================================================

fun deshacerUltimaAnotacion(): Boolean {
    if (!SesionActual.activa || CaptureState.exporting) return false

    val archivo =
        SesionActual.archivo
            ?: return false


    val indice =
        SesionActual.anotaciones
            .indexOfFirst {

                !esEventoSistema(
                    it.tipo
                )
            }


    if (indice == -1) {

        return false
    }


    val eliminada =
        SesionActual.anotaciones
            .removeAt(
                indice
            )


    val correcto =
        reescribirCSV(

            archivo =
                archivo,

            idRecorrido =
                SesionActual.idRecorrido,

            anotaciones =
                SesionActual.anotaciones
        )


    if (!correcto) {

        SesionActual.anotaciones.add(
            indice,
            eliminada
        )
    }


    return correcto
}


// ======================================================
// EVENTOS INTERNOS
// ======================================================

fun esEventoSistema(
    tipo: String
): Boolean {

    return tipo ==
            "MONITOREO_INICIO" ||
            tipo ==
            "MONITOREO_FIN"
}


// ======================================================
// CANTIDAD REAL DE EVENTOS VIALES
// ======================================================

fun cantidadEventosUsuario(): Int {

    return SesionActual.anotaciones.count {

        !esEventoSistema(
            it.tipo
        )
    }
}


// ======================================================
// LIMPIAR PARA NUEVO RECORRIDO
// ======================================================

fun limpiarParaNuevoRecorrido() {
    if (CaptureState.snapshot.busy || CaptureState.exporting || SesionActual.activa) return

    SesionActual.idRecorrido =
        ""

    SesionActual.archivo =
        null

    SesionActual.tiempoInicioElapsed =
        0L

    SesionActual.duracionFinalMs =
        0L

    SesionActual.activa =
        false

    SesionActual.finalizada =
        false

    SesionActual.anotaciones.clear()
}


// ======================================================
// NOMBRE EN SHARED PREFERENCES
// ======================================================

fun guardarNombreBase(
    context: Context,
    nombre: String
) {

    context
        .getSharedPreferences(
            PREFS_NAME,
            Context.MODE_PRIVATE
        )
        .edit()
        .putString(
            PREF_NOMBRE_RECORRIDO,
            nombre
        )
        .apply()
}


fun obtenerNombreBase(
    context: Context
): String {

    return context
        .getSharedPreferences(
            PREFS_NAME,
            Context.MODE_PRIVATE
        )
        .getString(
            PREF_NOMBRE_RECORRIDO,
            "recorrido"
        )
        ?: "recorrido"
}


// ======================================================
// GENERAR ID
// ======================================================

fun generarIdRecorrido(
    nombre: String
): String {

    val seguro =
        nombre
            .trim()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace(",", "_")


    val fecha =
        SimpleDateFormat(
            "yyyyMMdd_HHmmss_SSS",
            Locale.getDefault()
        ).format(
            Date()
        )


    return "${seguro}_$fecha"
}


// ======================================================
// CREAR CSV
// ======================================================

fun crearArchivoRecorrido(
    context: Context,
    idRecorrido: String
): File? {

    return try {

        val carpeta =
            context.getExternalFilesDir(
                Environment.DIRECTORY_DOCUMENTS
            )
                ?: return null


        if (!carpeta.exists()) {

            carpeta.mkdirs()
        }


        val archivo =
            File(
                carpeta,
                "${idRecorrido}_anotaciones.csv"
            )


        AnnotationCsvStore.create(archivo)


        archivo

    } catch (e: Exception) {

        e.printStackTrace()

        null
    }
}


// ======================================================
// AGREGAR FILA CSV
// ======================================================

fun agregarAnotacionCSV(
    archivo: File,
    idRecorrido: String,
    anotacion: Anotacion
): Boolean {

    return try {

        AnnotationCsvStore.append(archivo, AnnotationCsvStore.row(
            idRecorrido, anotacion.timestamp, anotacion.epochMs,
            anotacion.elapsedMs, anotacion.tipo
        ))

        true

    } catch (e: Exception) {

        e.printStackTrace()

        false
    }
}


// ======================================================
// REESCRIBIR CSV
// ======================================================

fun reescribirCSV(
    archivo: File,
    idRecorrido: String,
    anotaciones: List<Anotacion>
): Boolean {

    return try {

        AnnotationCsvStore.replace(archivo, anotaciones.asReversed().asSequence().map { anotacion ->
            AnnotationCsvStore.row(idRecorrido, anotacion.timestamp, anotacion.epochMs,
                anotacion.elapsedMs, anotacion.tipo)
        })

        true

    } catch (e: Exception) {

        e.printStackTrace()

        false
    }
}


// ======================================================
// TIMESTAMP
// ======================================================

fun obtenerTimestamp(
    epochMs: Long
): String {

    return SimpleDateFormat(
        "yyyy-MM-dd'T'HH:mm:ss.SSS",
        Locale.getDefault()
    ).format(
        Date(epochMs)
    )
}


// ======================================================
// HORA
// ======================================================

fun obtenerHora(
    epochMs: Long
): String {

    return SimpleDateFormat(
        "HH:mm:ss.SSS",
        Locale.getDefault()
    ).format(
        Date(epochMs)
    )
}


// ======================================================
// DURACIÓN
// ======================================================

fun formatearTiempo(
    ms: Long
): String {

    val total =
        ms / 1000

    val horas =
        total / 3600

    val minutos =
        (total % 3600) / 60

    val segundos =
        total % 60


    return String.format(
        Locale.getDefault(),
        "%02d:%02d:%02d",
        horas,
        minutos,
        segundos
    )
}


// ======================================================
// VIBRACIÓN
// ======================================================

fun vibrar(
    context: Context,
    duracionMs: Long
) {
    if (CaptureState.snapshot.busy) return

    try {

        val vibrator: Vibrator =

            if (
                Build.VERSION.SDK_INT >=
                Build.VERSION_CODES.S
            ) {

                val manager =
                    context.getSystemService(
                        Context.VIBRATOR_MANAGER_SERVICE
                    ) as VibratorManager

                manager.defaultVibrator

            } else {

                @Suppress("DEPRECATION")

                context.getSystemService(
                    Context.VIBRATOR_SERVICE
                ) as Vibrator
            }


        vibrator.vibrate(

            VibrationEffect.createOneShot(
                duracionMs,
                VibrationEffect.DEFAULT_AMPLITUDE
            )
        )

    } catch (e: Exception) {

        e.printStackTrace()
    }
}


// ======================================================
// CONFIGURACIÓN OVERLAY
// ======================================================

fun abrirConfiguracionOverlay(
    context: Context
) {

    try {

        val intent =
            Intent(
                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse(
                    "package:${context.packageName}"
                )
            )


        context.startActivity(
            intent
        )

    } catch (e: Exception) {

        e.printStackTrace()
    }
}


// ======================================================
// PERMISO NOTIFICACIONES
// ======================================================

fun solicitarPermisoNotificaciones(
    activity: Activity
) {

    if (
        Build.VERSION.SDK_INT >=
        Build.VERSION_CODES.TIRAMISU
    ) {

        if (
            ContextCompat.checkSelfPermission(
                activity,
                Manifest.permission.POST_NOTIFICATIONS
            )
            != PackageManager.PERMISSION_GRANTED
        ) {

            ActivityCompat.requestPermissions(

                activity,

                arrayOf(
                    Manifest.permission.POST_NOTIFICATIONS
                ),

                1001
            )
        }
    }
}


// ======================================================
// INICIAR / REFRESCAR OVERLAY
// ======================================================

fun iniciarOverlayService(
    context: Context
) {

    if (
        !Settings.canDrawOverlays(
            context
        )
    ) {

        return
    }


    val intent =
        Intent(
            context,
            OverlayService::class.java
        )


    ContextCompat.startForegroundService(
        context,
        intent
    )
}


// ======================================================
// COMPARTIR CSV
// ======================================================

fun compartirCSV(
    context: Context,
    archivo: File
) {

    try {

        if (!archivo.exists()) {

            Toast.makeText(
                context,
                "El archivo CSV no existe",
                Toast.LENGTH_LONG
            ).show()

            return
        }


        val uri =
            FileProvider.getUriForFile(

                context,

                "com.monitoreovial.anotador.fileprovider",

                archivo
            )


        val intent =
            Intent(
                Intent.ACTION_SEND
            ).apply {

                type =
                    "text/csv"

                putExtra(
                    Intent.EXTRA_STREAM,
                    uri
                )

                putExtra(
                    Intent.EXTRA_SUBJECT,
                    "Anotaciones de monitoreo vial"
                )

                addFlags(
                    Intent.FLAG_GRANT_READ_URI_PERMISSION
                )


                clipData =
                    ClipData.newUri(
                        context.contentResolver,
                        "CSV Anotador Vial",
                        uri
                    )
            }


        val chooser =
            Intent.createChooser(
                intent,
                "Compartir CSV"
            )


        if (context !is Activity) {

            chooser.addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK
            )
        }


        context.startActivity(
            chooser
        )

    } catch (e: Exception) {

        e.printStackTrace()

        Toast.makeText(
            context,
            "Error al compartir: ${e.message}",
            Toast.LENGTH_LONG
        ).show()
    }
}
