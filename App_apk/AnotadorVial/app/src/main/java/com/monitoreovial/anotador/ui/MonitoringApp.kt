package com.monitoreovial.anotador.ui

import android.content.ClipData
import android.Manifest
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import android.content.Context
import android.content.Intent
import android.hardware.Sensor
import android.hardware.SensorManager
import android.os.Environment
import android.os.SystemClock
import android.provider.Settings
import android.widget.Toast
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.FileProvider
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.compose.ui.platform.LocalLifecycleOwner
import com.monitoreovial.anotador.*
import com.monitoreovial.anotador.capture.CaptureState
import com.monitoreovial.anotador.capture.GpsAccess
import com.monitoreovial.anotador.capture.CaptureSchema
import com.monitoreovial.anotador.capture.ImuArchive
import com.monitoreovial.anotador.history.SavedEvent
import com.monitoreovial.anotador.history.SavedTrip
import com.monitoreovial.anotador.history.TripHistory
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private val Good = Color(0xFF16805D)
private val Amber = Color(0xFFA56500)
private val Blue = Color(0xFF1462E8)
private val tabs = listOf("Inicio", "Recorridos", "Eventos", "Ajustes")
private val tabIcons = listOf(Icons.Default.Home, Icons.Default.Place, Icons.AutoMirrored.Filled.List, Icons.Default.Settings)
private data class SensorInfo(val name: String, val available: Boolean, val deviceName: String)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MonitoringApp() {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences("monitoring_ui", Context.MODE_PRIVATE) }
    var dark by rememberSaveable { mutableStateOf(prefs.getBoolean("dark", false)) }
    var overlay by rememberSaveable { mutableStateOf(prefs.getBoolean("overlay", true)) }
    var overlayPermission by remember { mutableStateOf(Settings.canDrawOverlays(context)) }
    var gpsEnabled by rememberSaveable { mutableStateOf(GpsAccess.requested(context)) }
    var gpsReadiness by remember { mutableStateOf(GpsAccess.readiness(context)) }
    var pendingGpsStart by rememberSaveable { mutableStateOf(false) }
    var gpsPermissionReturned by rememberSaveable { mutableStateOf(false) }
    var gpsWarning by rememberSaveable { mutableStateOf<String?>(null) }
    var tab by rememberSaveable { mutableIntStateOf(0) }
    var selectedPath by rememberSaveable { mutableStateOf<String?>(null) }
    var refresh by remember { mutableIntStateOf(0) }
    var history by remember { mutableStateOf<List<SavedTrip>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var loadError by remember { mutableStateOf<String?>(null) }
    var actionError by remember { mutableStateOf<String?>(null) }
    var annotating by rememberSaveable { mutableStateOf(false) }
    var confirmingStop by rememberSaveable { mutableStateOf(false) }
    var elapsed by remember { mutableLongStateOf(0) }
    val scope = rememberCoroutineScope()
    val active = SesionActual.activa
    val capture = CaptureState.snapshot
    val documents = remember { context.getExternalFilesDir(Environment.DIRECTORY_DOCUMENTS) }
    val sensors = remember {
        val manager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
        listOf("Acelerómetro" to Sensor.TYPE_ACCELEROMETER, "Giroscopio" to Sensor.TYPE_GYROSCOPE,
            "Gravedad" to Sensor.TYPE_GRAVITY, "Aceleración lineal" to Sensor.TYPE_LINEAR_ACCELERATION,
            "Vector de rotación" to Sensor.TYPE_ROTATION_VECTOR).map { (name, type) ->
            val sensor = manager.getDefaultSensor(type)
            SensorInfo(name, sensor != null, sensor?.name ?: "No disponible")
        }
    }
    val owner = LocalLifecycleOwner.current
    DisposableEffect(owner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                overlayPermission = Settings.canDrawOverlays(context)
                gpsReadiness = GpsAccess.readiness(context)
                refresh++
            }
        }
        owner.lifecycle.addObserver(observer)
        onDispose { owner.lifecycle.removeObserver(observer) }
    }
    LaunchedEffect(active, SesionActual.tiempoInicioElapsed) {
        if (active) { tab = 0; selectedPath = null }
        while (SesionActual.activa) {
            elapsed = SystemClock.elapsedRealtime() - SesionActual.tiempoInicioElapsed
            delay(500)
        }
        annotating = false
        confirmingStop = false
    }
    LaunchedEffect(refresh, active, capture.busy) {
        loading = true
        loadError = null
        val excluded = SesionActual.archivo.takeIf { active || capture.busy }
        try {
            history = withContext(Dispatchers.IO) {
                TripHistory.load(documents ?: error("Almacenamiento no disponible"), excluded)
            }
        } catch (cancelled: CancellationException) { throw cancelled }
        catch (error: Exception) { loadError = error.message ?: "No se pudo cargar el historial" }
        finally { loading = false }
    }
    val selected = history.firstOrNull { it.file.absolutePath == selectedPath }
    fun startCapture(includeGps: Boolean) {
        if (SesionActual.activa || CaptureState.snapshot.busy || CaptureState.exporting) return
        actionError = null
        if (SesionActual.finalizada) limpiarParaNuevoRecorrido()
        if (!iniciarNuevaSesion(context, SesionActual.nombreBase, gpsRequested = includeGps)) actionError = "No se pudo iniciar el recorrido"
        else if (overlay && Settings.canDrawOverlays(context)) iniciarOverlayService(context)
    }
    val locationPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
        gpsReadiness = GpsAccess.readiness(context)
        gpsPermissionReturned = true
    }
    LaunchedEffect(pendingGpsStart, gpsPermissionReturned) {
        if (pendingGpsStart && gpsPermissionReturned) {
            while (!CaptureState.uiVisible) delay(100)
            if (pendingGpsStart) {
                pendingGpsStart = false
                gpsPermissionReturned = false
                gpsReadiness = GpsAccess.readiness(context)
                if (gpsReadiness == "Disponible") startCapture(true) else gpsWarning = gpsReadiness
            }
        }
    }
    fun requestStart() {
        gpsReadiness = GpsAccess.readiness(context)
        when {
            !gpsEnabled -> startCapture(false)
            !GpsAccess.precise(context) -> {
                pendingGpsStart = true
                gpsPermissionReturned = false
                locationPermission.launch(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION))
            }
            gpsReadiness != "Disponible" -> gpsWarning = gpsReadiness
            else -> startCapture(true)
        }
    }
    BackHandler(selectedPath != null || tab != 0) {
        if (selectedPath != null) selectedPath = null else tab = 0
    }
    fun export(trip: SavedTrip) {
        if (CaptureState.exporting || (trip.file == SesionActual.archivo && (active || capture.busy))) return
        scope.launch {
            CaptureState.exporting = true
            actionError = null
            try {
                val file = withContext(Dispatchers.IO) {
                    if (trip.imuDirectory.isDirectory) {
                        val output = File(trip.file.parentFile, "${trip.imuDirectory.name}_${System.currentTimeMillis()}.zip")
                        ImuArchive.create(trip.imuDirectory, trip.file, output)
                        output
                    } else trip.file
                }
                val uri = FileProvider.getUriForFile(context, "com.monitoreovial.anotador.fileprovider", file)
                val intent = Intent(Intent.ACTION_SEND).setType(if (file.extension == "zip") "application/zip" else "text/csv")
                    .putExtra(Intent.EXTRA_STREAM, uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                intent.clipData = ClipData.newUri(context.contentResolver, "Recorrido", uri)
                context.startActivity(Intent.createChooser(intent, "Exportar recorrido"))
            } catch (cancelled: CancellationException) { throw cancelled }
            catch (error: Exception) { actionError = error.message ?: "No se pudo exportar" }
            finally { CaptureState.exporting = false }
        }
    }
    val scheme = if (dark) darkColorScheme(primary = Color(0xFF9BBEFF), secondary = Color(0xFF76D6B1),
        background = Color(0xFF151719), surface = Color(0xFF1C1F22)) else lightColorScheme(
        primary = Blue, secondary = Good, tertiary = Amber, background = Color(0xFFF7F9FC),
        surface = Color.White, surfaceVariant = Color(0xFFEDF1F6), onSurface = Color(0xFF192431),
        onBackground = Color(0xFF192431), onSurfaceVariant = Color(0xFF526173))
    val base = Typography()
    val type = base.copy(titleLarge = base.titleLarge.copy(letterSpacing = 0.sp, fontWeight = FontWeight.Bold),
        titleMedium = base.titleMedium.copy(letterSpacing = 0.sp, fontWeight = FontWeight.SemiBold),
        bodyLarge = base.bodyLarge.copy(letterSpacing = 0.sp), bodyMedium = base.bodyMedium.copy(letterSpacing = 0.sp),
        bodySmall = base.bodySmall.copy(letterSpacing = 0.sp), labelLarge = base.labelLarge.copy(letterSpacing = 0.sp),
        labelMedium = base.labelMedium.copy(letterSpacing = 0.sp), labelSmall = base.labelSmall.copy(letterSpacing = 0.sp))
    MaterialTheme(colorScheme = scheme, typography = type, shapes = Shapes(
        small = RoundedCornerShape(8.dp), medium = RoundedCornerShape(8.dp), large = RoundedCornerShape(8.dp))) {
        Scaffold(
            topBar = { TopAppBar(title = {
                Column { Text(if (selectedPath != null) "Detalle del recorrido" else "Anotador Vial", style = MaterialTheme.typography.titleLarge)
                    if (selectedPath == null) Text("Monitoreo vial", style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant) }
            }, navigationIcon = { if (selectedPath != null) ToolButton("Volver", Icons.AutoMirrored.Filled.ArrowBack) { selectedPath = null } },
                actions = { if (selectedPath == null && (tab == 1 || tab == 2)) ToolButton("Actualizar", Icons.Default.Refresh) { refresh++ } }) },
            bottomBar = { NavigationBar(containerColor = MaterialTheme.colorScheme.surface) {
                tabs.forEachIndexed { index, title -> NavigationBarItem(selected = tab == index,
                    onClick = { tab = index; selectedPath = null }, icon = { Icon(tabIcons[index], null) },
                    label = { Text(title, maxLines = 1) }, modifier = Modifier.testTag("tab_$index")) }
            } }
        ) { padding ->
            Column(Modifier.fillMaxSize().padding(padding)) {
                if (active && (tab != 0 || selectedPath != null)) {
                    Row(Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.secondaryContainer)
                        .clickable { tab = 0; selectedPath = null }.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.PlayArrow, null, Modifier.size(20.dp))
                        Text("  Captura en curso · ${formatearTiempo(elapsed)}", style = MaterialTheme.typography.labelLarge)
                    }
                }
                actionError?.let { message ->
                    Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp), verticalAlignment = Alignment.CenterVertically) {
                        Text(message, Modifier.weight(1f), color = MaterialTheme.colorScheme.error)
                        ToolButton("Cerrar aviso", Icons.Default.Close) { actionError = null }
                    }
                }
                if (selected != null) {
                    TripDetail(selected, CaptureState.exporting, onExport = { export(selected) },
                        onCsv = { compartirCSV(context, selected.file) })
                } else when (tab) {
                    0 -> LazyColumn(Modifier.fillMaxSize().testTag("home_content"), contentPadding = PaddingValues(20.dp),
                        verticalArrangement = Arrangement.spacedBy(18.dp)) {
                        if (active || capture.busy) {
                            item { SectionTitle(if (active) "Recorrido en curso" else "Guardando recorrido")
                                Text(SesionActual.idRecorrido, style = MaterialTheme.typography.bodySmall) }
                            item { Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                                Metric("Tiempo", formatearTiempo(if (active) elapsed else SesionActual.duracionFinalMs), Modifier.weight(1f))
                                Metric("Marcas", cantidadEventosUsuario().toString(), Modifier.weight(1f))
                            } }
                            item { Button(onClick = { annotating = true }, enabled = active, modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp)) {
                                Icon(Icons.Default.Add, null); Spacer(Modifier.width(8.dp)); Text("Registrar evento") } }
                            item { OutlinedButton(onClick = { confirmingStop = true }, enabled = active,
                                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp), colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error)) {
                                Icon(Icons.Default.Close, null); Spacer(Modifier.width(8.dp)); Text(if (active) "Finalizar recorrido" else "Guardando") } }
                            item { AcquisitionStatus() }
                            item { Row(verticalAlignment = Alignment.CenterVertically) {
                                Text("Anotaciones recientes", Modifier.weight(1f), style = MaterialTheme.typography.titleMedium)
                                if (active && cantidadEventosUsuario() > 0) ToolButton("Deshacer última marca", Icons.Default.Refresh) {
                                    if (!deshacerUltimaAnotacion()) actionError = "No se pudo deshacer la marca"
                                }
                            } }
                            val events = SesionActual.anotaciones.filter { !esEventoSistema(it.tipo) }.take(8)
                            if (events.isEmpty()) item { EmptyState("Sin anotaciones", Icons.Default.Edit) }
                            items(events) { e -> EventRow(SavedEvent(e.tipo, e.hora, e.epochMs, e.elapsedMs)) }
                        } else {
                            item { Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                Icon(Icons.Default.Place, null, Modifier.size(36.dp), tint = MaterialTheme.colorScheme.primary)
                                Column { SectionTitle(if (SesionActual.finalizada) "Recorrido finalizado" else "Nuevo recorrido")
                                    Text("Sensores, GPS y marcas manuales", style = MaterialTheme.typography.bodyMedium,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant) }
                            } }
                            if (SesionActual.finalizada) {
                                item { AcquisitionStatus()
                                    history.firstOrNull { it.file == SesionActual.archivo }?.let { trip ->
                                        TextButton(onClick = { tab = 1; selectedPath = trip.file.absolutePath }) { Text("Ver resumen del recorrido") }
                                    }
                                }
                            }
                            item { OutlinedTextField(value = SesionActual.nombreBase, onValueChange = {
                                SesionActual.nombreBase = it; guardarNombreBase(context, it)
                            }, label = { Text("Nombre del recorrido") }, singleLine = true, modifier = Modifier.fillMaxWidth().testTag("trip_name")) }
                            item { SectionTitle("Sensores")
                                sensors.forEach { SensorRow(it.name, if (it.available) "Disponible" else "No disponible", if (it.available) Good else Amber) }
                                SensorRow("GPS", if (gpsEnabled) gpsReadiness else "Deshabilitado", if (gpsEnabled && gpsReadiness == "Disponible") Good else Amber)
                            }
                            item { Button(enabled = SesionActual.nombreBase.isNotBlank() && sensors.first().available && !CaptureState.exporting && !pendingGpsStart,
                                modifier = Modifier.fillMaxWidth().heightIn(min = 54.dp).testTag("start_trip"), onClick = {
                                    requestStart()
                                }) { Icon(Icons.Default.PlayArrow, null); Spacer(Modifier.width(8.dp)); Text("Iniciar recorrido") } }
                            item { HorizontalDivider() }
                            item { SectionTitle("Recientes") }
                            if (loading) item { LinearProgressIndicator(Modifier.fillMaxWidth()) }
                            if (!loading && history.isEmpty()) item { EmptyState("Sin recorridos guardados", Icons.Default.Place) }
                            items(history.take(3), key = { it.file.absolutePath }) { trip -> TripRow(trip) { tab = 1; selectedPath = trip.file.absolutePath } }
                        }
                        loadError?.let { item { Text(it, color = MaterialTheme.colorScheme.error) } }
                    }
                    1 -> LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        item { SectionTitle("Recorridos guardados") }
                        if (loading) item { LinearProgressIndicator(Modifier.fillMaxWidth()) }
                        loadError?.let { item { Text(it, color = MaterialTheme.colorScheme.error) } }
                        if (!loading && history.isEmpty()) item { EmptyState("Sin recorridos guardados", Icons.Default.Place) }
                        items(history, key = { it.file.absolutePath }) { trip -> TripRow(trip) { selectedPath = trip.file.absolutePath } }
                    }
                    2 -> {
                        var query by rememberSaveable { mutableStateOf("") }
                        val current = SesionActual.anotaciones.filter { !esEventoSistema(it.tipo) }.map { SavedEvent(it.tipo, it.hora, it.epochMs, it.elapsedMs) }
                        val records = history.flatMap { trip -> trip.events.map { Triple(it, trip.id, trip.file.absolutePath) } } +
                            if (active || capture.busy) current.map { Triple(it, SesionActual.idRecorrido, "") } else emptyList()
                        val filtered = records.filter { eventName(it.first.type).contains(query, true) || it.second.contains(query, true) }.sortedByDescending { it.first.epochMs }
                        LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                            item { SectionTitle("Eventos registrados") }
                            item { OutlinedTextField(query, { query = it }, label = { Text("Buscar evento o recorrido") },
                                leadingIcon = { Icon(Icons.Default.Search, null) }, singleLine = true, modifier = Modifier.fillMaxWidth()) }
                            if (loading) item { LinearProgressIndicator(Modifier.fillMaxWidth()) }
                            loadError?.let { item { Text(it, color = MaterialTheme.colorScheme.error) } }
                            if (!loading && filtered.isEmpty()) item { EmptyState("Sin eventos para mostrar", Icons.Default.Edit) }
                            items(filtered) { (event, tripId, path) ->
                                Surface(shape = RoundedCornerShape(8.dp), modifier = Modifier.fillMaxWidth().clickable {
                                    if (path.isBlank()) tab = 0 else { selectedPath = path; tab = 1 }
                                }) { Column(Modifier.padding(14.dp)) { EventRow(event); Text(tripId, style = MaterialTheme.typography.bodySmall) } }
                            }
                        }
                    }
                    3 -> LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                        item { SectionTitle("Preferencias") }
                        item { SettingSwitch("Tema oscuro", dark) { dark = it; prefs.edit().putBoolean("dark", it).apply() } }
                        item { SettingSwitch("Burbuja flotante", overlay) {
                            overlay = it; prefs.edit().putBoolean("overlay", it).apply()
                            if (!it) context.stopService(Intent(context, OverlayService::class.java))
                            else if (Settings.canDrawOverlays(context)) iniciarOverlayService(context) else abrirConfiguracionOverlay(context)
                        } }
                        if (overlay && !overlayPermission) item { OutlinedButton(onClick = { abrirConfiguracionOverlay(context) }) {
                            Icon(Icons.Default.Settings, null); Spacer(Modifier.width(8.dp)); Text("Conceder permiso de burbuja") } }
                        item { HorizontalDivider() }
                        item { SectionTitle("Adquisición") }
                        items(sensors) { sensor -> Column { Text(sensor.name, style = MaterialTheme.typography.titleMedium)
                            Text(sensor.deviceName, style = MaterialTheme.typography.bodySmall)
                            Text(if (sensor.available) "100 Hz solicitados" else "No disponible", style = MaterialTheme.typography.bodyMedium) } }
                        item { SettingSwitch("Registrar GPS", gpsEnabled, enabled = !active && !capture.busy && !pendingGpsStart) {
                            gpsEnabled = it; prefs.edit().putBoolean("gps", it).apply()
                        } }
                        item { SensorRow("GPS", if (gpsEnabled) gpsReadiness else "Deshabilitado", if (gpsEnabled && gpsReadiness == "Disponible") Good else Amber)
                            Text("Intervalo solicitado: 1 s", style = MaterialTheme.typography.bodySmall)
                            if (gpsEnabled) TextButton(onClick = {
                                if (!GpsAccess.precise(context)) locationPermission.launch(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION))
                                else context.startActivity(Intent(Settings.ACTION_LOCATION_SOURCE_SETTINGS))
                            }, enabled = !active && !capture.busy) { Text("Permisos y ubicación") }
                        }
                        item { SensorRow("Vibración durante captura", "Desactivada", Good) }
                        item { HorizontalDivider() }
                        item { SectionTitle("Registro")
                            Text("Formato: ${CaptureSchema.VERSION}", style = MaterialTheme.typography.bodyMedium)
                            Text("Anotaciones: referencias retrospectivas", style = MaterialTheme.typography.bodyMedium)
                            Text("Detección automática: no implementada", style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                }
            }
        }
        if (annotating && active) {
            ModalBottomSheet(onDismissRequest = { annotating = false }) {
                Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal = 20.dp).padding(bottom = 28.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("Registrar evento", Modifier.weight(1f), style = MaterialTheme.typography.titleLarge)
                        ToolButton("Cerrar", Icons.Default.Close) { annotating = false }
                    }
                    listOf("BACHE", "LOMO_DE_TORO", "DESVIACION", "CAMINO_MALO", "GIRO", "OTRO").chunked(2).forEach { pair ->
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            pair.forEach { event -> OutlinedButton(modifier = Modifier.weight(1f).heightIn(min = 72.dp),
                                colors = ButtonDefaults.outlinedButtonColors(contentColor = when (event) {
                                    "BACHE" -> MaterialTheme.colorScheme.error
                                    "LOMO_DE_TORO" -> if (dark) Color(0xFFFFD27E) else Amber
                                    "CAMINO_MALO" -> MaterialTheme.colorScheme.secondary
                                    else -> MaterialTheme.colorScheme.primary
                                }), onClick = {
                                if (registrarEventoSesion(event)) { annotating = false; Toast.makeText(context, "Marca registrada", Toast.LENGTH_SHORT).show() }
                                else { annotating = false; actionError = "No se pudo guardar la anotación" }
                            }) { Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Icon(when (event) { "BACHE", "LOMO_DE_TORO" -> Icons.Default.Warning
                                    "DESVIACION" -> Icons.Default.Place; "GIRO" -> Icons.Default.Refresh
                                    "CAMINO_MALO" -> Icons.Default.Build; else -> Icons.Default.MoreVert }, null, Modifier.size(20.dp))
                                Text(eventName(event))
                            } } }
                        }
                    }
                }
            }
        }
        if (confirmingStop && active) AlertDialog(onDismissRequest = { confirmingStop = false },
            title = { Text("¿Finalizar recorrido?") }, text = { Text("Se cerrará la captura y se guardarán los datos pendientes.") },
            confirmButton = { TextButton(onClick = {
                confirmingStop = false
                if (!finalizarSesion()) actionError = "No se pudo finalizar. La captura sigue activa."
                else if (overlay && Settings.canDrawOverlays(context)) iniciarOverlayService(context)
            }) { Text("Finalizar") } }, dismissButton = { TextButton(onClick = { confirmingStop = false }) { Text("Continuar") } })
        gpsWarning?.let { warning -> AlertDialog(onDismissRequest = { gpsWarning = null },
            title = { Text("GPS no disponible") }, text = { Text("$warning. Puedes revisar la ubicación o continuar solo con sensores.") },
            confirmButton = { TextButton(onClick = { gpsWarning = null; startCapture(false) }) { Text("Continuar sin GPS") } },
            dismissButton = { TextButton(onClick = {
                gpsWarning = null
                if (!GpsAccess.precise(context)) context.startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:${context.packageName}")))
                else context.startActivity(Intent(Settings.ACTION_LOCATION_SOURCE_SETTINGS))
            }) { Text("Revisar ajustes") } }) }
    }
}

@Composable private fun SectionTitle(title: String) { Text(title, style = MaterialTheme.typography.titleMedium) }
@Composable private fun Metric(label: String, value: String, modifier: Modifier = Modifier) {
    Column(modifier) { Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, style = MaterialTheme.typography.titleLarge) }
}
@OptIn(ExperimentalMaterial3Api::class)
@Composable private fun ToolButton(label: String, icon: ImageVector, onClick: () -> Unit) {
    TooltipBox(positionProvider = TooltipDefaults.rememberPlainTooltipPositionProvider(),
        tooltip = { PlainTooltip { Text(label) } }, state = rememberTooltipState()) {
        IconButton(onClick = onClick) { Icon(icon, contentDescription = label) }
    }
}
@Composable private fun SensorRow(name: String, status: String, color: Color) {
    Row(Modifier.fillMaxWidth().padding(vertical = 10.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
        Icon(if (color == Good) Icons.Default.Check else Icons.Default.Info, null, Modifier.size(18.dp), tint = color)
        Text(name, Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium)
        Text(status, Modifier.widthIn(max = 180.dp), style = MaterialTheme.typography.bodySmall)
    }
}
@Composable private fun AcquisitionStatus() {
    val s = CaptureState.snapshot
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(s.phase, color = if (s.error != null) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
            style = MaterialTheme.typography.titleMedium)
        SensorRow("Acelerómetro", "${s.accel.count} muestras · ${hz(s.accel.hz)} Hz", if (s.accel.count > 0) Good else Amber)
        SensorRow("Giroscopio", if (s.gyroAvailable) "${s.gyro.count} muestras · ${hz(s.gyro.hz)} Hz" else "Sin datos", if (s.gyro.count > 0) Good else Amber)
        listOf("gravity" to "Gravedad", "linear_acceleration" to "Aceleración lineal", "rotation_vector" to "Vector de rotación").forEach { (key, label) ->
            val stats = s.streams[key]
            val status = s.sensorStates[key]
            SensorRow(label, if (stats != null && stats.count > 0) "${stats.count} muestras · ${hz(stats.hz)} Hz" else status ?: "Sin datos",
                if ((stats?.count ?: 0) > 0) Good else Amber)
        }
        SensorRow("GPS", s.gpsState, if (s.gpsState == "Recibiendo GPS") Good else Amber)
        Text("${s.streams["gps"]?.count ?: 0} fijaciones guardadas", style = MaterialTheme.typography.bodySmall)
        s.gpsAgeSeconds?.let { age ->
            Text("Última fijación: hace ${hz(age)} s · Precisión: ${s.gpsAccuracyM?.let { hz(it.toDouble()) + " m" } ?: "no informada"}", style = MaterialTheme.typography.bodySmall)
            s.gpsSpeedMps?.let { Text("Última velocidad GPS: ${hz(it * 3.6)} km/h", style = MaterialTheme.typography.bodySmall) }
        }
        if (s.dropped > 0) Text("Descartadas: ${s.dropped}", color = MaterialTheme.colorScheme.error)
        s.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
    }
}
@Composable private fun EmptyState(text: String, icon: ImageVector) {
    Column(Modifier.fillMaxWidth().padding(vertical = 28.dp), horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Icon(icon, null, Modifier.size(32.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(text, style = MaterialTheme.typography.bodyMedium)
    }
}
@Composable private fun SettingSwitch(title: String, checked: Boolean, enabled: Boolean = true, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(title, Modifier.weight(1f)); Switch(checked, onChange, enabled = enabled)
    }
}
@Composable private fun TripRow(trip: SavedTrip, onClick: () -> Unit) {
    Surface(modifier = Modifier.fillMaxWidth().clickable(onClick = onClick), shape = RoundedCornerShape(8.dp)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(trip.id, style = MaterialTheme.typography.titleMedium)
            Text(trip.startedEpochMs?.let { date(it) } ?: "Fecha no disponible", style = MaterialTheme.typography.bodySmall)
            Text(if (trip.error != null) "Archivo con incidencias" else if (trip.closed) "Sesión finalizada · ${trip.events.size} marcas" else "Sin cierre confirmado",
                color = if (trip.closed && trip.error == null) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodyMedium)
            Text(if (trip.imuDirectory.isDirectory) "Anotaciones + archivos IMU" else "Anotaciones CSV", style = MaterialTheme.typography.bodySmall)
        }
    }
}
@Composable private fun EventRow(event: SavedEvent) {
    Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
        Icon(Icons.Default.Edit, null, Modifier.size(20.dp), tint = MaterialTheme.colorScheme.primary)
        Column(Modifier.weight(1f)) { Text(eventName(event.type), style = MaterialTheme.typography.titleMedium)
            Text("Manual · ${time(event.epochMs)}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
        Text("+${formatearTiempo(event.elapsedMs)}", style = MaterialTheme.typography.bodySmall)
    }
}
@Composable private fun TripDetail(trip: SavedTrip, exporting: Boolean, onExport: () -> Unit, onCsv: () -> Unit) {
    var metadata by remember(trip.file) { mutableStateOf<JSONObject?>(null) }
    var metadataError by remember(trip.file) { mutableStateOf<String?>(null) }
    LaunchedEffect(trip.file) {
        if (trip.imuDirectory.isDirectory) try {
            metadata = withContext(Dispatchers.IO) { JSONObject(File(trip.imuDirectory, "metadata.json").readText(Charsets.UTF_8)) }
        } catch (cancelled: CancellationException) { throw cancelled }
        catch (_: Exception) { metadataError = "Metadatos IMU ausentes o no legibles" }
    }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        item { SectionTitle(trip.id); Text(trip.startedEpochMs?.let { date(it) } ?: "Fecha desconocida", style = MaterialTheme.typography.bodySmall) }
        item { Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Metric("Duración", trip.durationMs?.let { formatearTiempo(it) } ?: "Sin cierre", Modifier.weight(1f))
            Metric("Marcas", if (trip.error == null) trip.events.size.toString() else "Sin lectura", Modifier.weight(1f))
        } }
        trip.error?.let { item { Text(it, color = MaterialTheme.colorScheme.error) } }
        metadataError?.let { item { Text(it, color = MaterialTheme.colorScheme.error) } }
        metadata?.let { m ->
            item { HorizontalDivider(); SectionTitle("Calidad de captura")
                Text(when (m.optString("state")) { "COMPLETED" -> "Archivos IMU cerrados"; "INCOMPLETE" -> "Captura IMU incompleta"; else -> "Cierre IMU no confirmado" })
                listOf("accelerometer" to "Acelerómetro", "gyroscope" to "Giroscopio", "gravity" to "Gravedad",
                    "linear_acceleration" to "Aceleración lineal", "rotation_vector" to "Vector de rotación", "gps" to "GPS").forEach { (key, label) ->
                    m.optJSONObject(key + "_quality")?.let { q ->
                        SensorRow(label, "${q.optLong("samples")} muestras · ${hz(q.optDouble("effective_hz", 0.0))} Hz", if (q.optLong("samples") > 0) Good else Amber)
                        Text("Intervalo máximo: ${hz(q.optDouble("max_gap_ms", 0.0))} ms", style = MaterialTheme.typography.bodySmall)
                    }
                }
                Text("Descartadas: ${m.optLong("queue_dropped")} · Sin escribir: ${m.optInt("pending_unwritten")}", style = MaterialTheme.typography.bodySmall)
                if (!m.isNull("error") && m.optString("error").isNotBlank()) Text(m.optString("error"), color = MaterialTheme.colorScheme.error)
                m.optJSONArray("quality_warnings")?.let { warnings ->
                    for (i in 0 until warnings.length()) Text(warnings.getString(i), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
                }
                if (m.has("gps_final_state")) Text("GPS al cierre: ${m.optString("gps_final_state")}", style = MaterialTheme.typography.bodySmall)
            }
        }
        item { Button(onClick = onExport, enabled = !exporting, modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp)) {
            Icon(Icons.Default.Share, null); Spacer(Modifier.width(8.dp)); Text(if (exporting) "Preparando archivo" else "Exportar recorrido") }
            if (trip.imuDirectory.isDirectory) TextButton(onClick = onCsv, enabled = !exporting) { Text("Exportar solo anotaciones CSV") }
        }
        item { HorizontalDivider(); SectionTitle("Anotaciones manuales") }
        if (trip.events.isEmpty()) item { EmptyState("Sin anotaciones", Icons.Default.Edit) }
        items(trip.events) { EventRow(it) }
    }
}
private fun eventName(type: String): String = when (type) {
    "BACHE" -> "Bache"; "LOMO_DE_TORO" -> "Lomo de toro"; "DESVIACION" -> "Desviación"
    "CAMINO_MALO" -> "Camino irregular"; "GIRO" -> "Giro"; "OTRO" -> "Otro evento"; else -> type
}
private fun hz(value: Double) = String.format(Locale.US, "%.1f", value)
private fun date(value: Long) = SimpleDateFormat("dd MMM yyyy · HH:mm", Locale.forLanguageTag("es-CL")).format(Date(value))
private fun time(value: Long) = SimpleDateFormat("HH:mm:ss", Locale.forLanguageTag("es-CL")).format(Date(value))
