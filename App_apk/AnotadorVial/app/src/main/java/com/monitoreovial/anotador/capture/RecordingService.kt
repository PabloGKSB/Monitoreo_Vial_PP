package com.monitoreovial.anotador.capture

import android.app.*
import android.content.Intent
import android.content.pm.ServiceInfo
import android.hardware.*
import android.location.LocationManager
import android.os.*
import androidx.core.app.NotificationCompat
import com.monitoreovial.anotador.MainActivity
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.util.concurrent.atomic.AtomicBoolean

class RecordingService : Service(), SensorEventListener {
    private val main = Handler(Looper.getMainLooper())
    private lateinit var thread: HandlerThread
    private lateinit var collector: Handler
    private lateinit var manager: SensorManager
    private lateinit var notification: Notification
    @Volatile private var writer: ImuSessionWriter? = null
    @Volatile private var gps: GpsCollector? = null
    @Volatile private var sensorStates: Map<String, String> = emptyMap()
    private var gpsInitialState = "Sin captura"
    private var gpsRequested = false
    private var gpsEligible = false
    private var directory: File? = null
    private var metadata = JSONObject()
    private val closing = AtomicBoolean(false)
    private val completed = AtomicBoolean(false)
    private var completionReady = false
    @Volatile private var destroyed = false
    private var started = false
    @Volatile private var terminalError: String? = null
    private val sensorTypes = linkedMapOf(
        Sensor.TYPE_ACCELEROMETER to "accelerometer", Sensor.TYPE_GYROSCOPE to "gyroscope",
        Sensor.TYPE_GRAVITY to "gravity", Sensor.TYPE_LINEAR_ACCELERATION to "linear_acceleration",
        Sensor.TYPE_ROTATION_VECTOR to "rotation_vector")
    private val ticker = object : Runnable {
        override fun run() { publish(); if (CaptureState.snapshot.busy) main.postDelayed(this, 500) }
    }

    override fun onCreate() {
        super.onCreate()
        manager = getSystemService(SENSOR_SERVICE) as SensorManager
        thread = HandlerThread("imu-collector").also { it.start() }
        collector = Handler(thread.looper)
        val notifications = getSystemService(NotificationManager::class.java)
        notifications.createNotificationChannel(NotificationChannel("imu_capture", "Captura de sensores", NotificationManager.IMPORTANCE_LOW))
        val open = PendingIntent.getActivity(this, 20, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        notification = NotificationCompat.Builder(this, "imu_capture")
            .setSmallIcon(android.R.drawable.ic_menu_compass).setContentTitle("Monitoreo vial activo")
            .setContentText("Captura de sensores del recorrido").setContentIntent(open).setOngoing(true).build()
        if (Build.VERSION.SDK_INT >= 29) startForeground(2002, notification,
            if (Build.VERSION.SDK_INT >= 34) ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE else 0)
        else startForeground(2002, notification)
        CaptureState.service = this
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (started) return START_NOT_STICKY
        started = true
        val path = intent?.getStringExtra("annotations")
        gpsRequested = intent?.getBooleanExtra("gps_requested", false) == true
        gpsInitialState = when {
            !gpsRequested -> "Deshabilitado para esta sesión"
            intent?.getBooleanExtra("started_from_visible_ui", false) != true -> "Requiere inicio desde la app"
            else -> GpsAccess.readiness(this)
        }
        gpsEligible = gpsInitialState == "Disponible"
        if (gpsEligible) try {
            if (Build.VERSION.SDK_INT >= 29) {
                val type = ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION or
                    if (Build.VERSION.SDK_INT >= 34) ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE else 0
                startForeground(2002, notification, type)
            }
        } catch (_: SecurityException) { gpsEligible = false; gpsInitialState = "GPS no autorizado al iniciar" }
        collector.post {
            try {
                require(path != null) { "Missing annotation session" }
                val annotationFile = File(path)
                val allowed = getExternalFilesDir(Environment.DIRECTORY_DOCUMENTS)!!.canonicalFile
                require(annotationFile.canonicalFile.parentFile == allowed && annotationFile.isFile) { "Invalid session path" }
                val folder = File(allowed, annotationFile.nameWithoutExtension + "_imu")
                check(folder.mkdir()) { "Capture folder exists or cannot be created" }
                directory = folder
                val origin = SystemClock.elapsedRealtimeNanos()
                val epoch = System.currentTimeMillis()
                metadata = JSONObject().put("schema_version", CaptureSchema.VERSION)
                    .put("state", "RECORDING").put("annotations_file", annotationFile.name)
                    .put("origin_monotonic_ns", origin.toString()).put("origin_epoch_ms", epoch)
                    .put("annotation_origin_monotonic_ms", intent!!.getLongExtra("annotation_origin_monotonic_ms", -1))
                    .put("annotation_origin_epoch_ms", intent.getLongExtra("annotation_origin_epoch_ms", -1))
                    .put("requested_period_us", 10000).put("gps_requested_interval_ms", 1000)
                    .put("gps_requested", gpsRequested).put("gps_available", false).put("gps_initial_state", gpsInitialState)
                    .put("accelerometer_semantics", "TYPE_ACCELEROMETER includes gravity, m/s2, device axes")
                    .put("gyroscope_semantics", "TYPE_GYROSCOPE rad/s, device axes")
                    .put("gravity_semantics", "TYPE_GRAVITY m/s2, device axes, Android estimate")
                    .put("linear_acceleration_semantics", "TYPE_LINEAR_ACCELERATION m/s2, device axes, Android estimate")
                    .put("rotation_vector_semantics", "TYPE_ROTATION_VECTOR qx,qy,qz,qw; absent optional components left blank; heading accuracy rad")
                    .put("gps_semantics", "GPS_PROVIDER WGS84 degrees; altitude m above WGS84 ellipsoid; speed m/s; bearing degrees; accuracy m; independent location epoch retained")
                    .put("device", Build.MODEL).put("android", Build.VERSION.RELEASE)
                    .put("annotation_semantics", "Retrospective button reference; not impact time")
                    .put("haptic_feedback_during_capture", false)
                val available = sensorTypes.mapValues { (type, _) -> manager.getDefaultSensor(type) }
                sensorStates = sensorTypes.map { (type, name) -> name to if (available[type] != null) "Disponible" else "No disponible" }.toMap()
                val info = JSONObject()
                for ((type, name) in sensorTypes) {
                    val sensor = available[type]
                    info.put(name, JSONObject().put("available", sensor != null).put("name", sensor?.name ?: JSONObject.NULL)
                        .put("vendor", sensor?.vendor ?: JSONObject.NULL).put("resolution", sensor?.resolution ?: JSONObject.NULL)
                        .put("max_range", sensor?.maximumRange ?: JSONObject.NULL).put("min_delay_us", sensor?.minDelay ?: JSONObject.NULL))
                }
                metadata.put("sensors", info)
                writeMetadata()
                check(available[Sensor.TYPE_ACCELEROMETER] != null) { "Acelerómetro no disponible" }
                writer = ImuSessionWriter(folder, origin, epoch, CaptureSchema.columns.keys.toList()) { error -> collector.post { complete(error) } }
                writer!!.start()
                for ((type, name) in sensorTypes) {
                    val sensor = available[type] ?: continue
                    val registered = manager.registerListener(this, sensor, 10000, collector)
                    sensorStates = sensorStates + (name to if (registered) "Registrado" else "Error al registrar")
                    if (type == Sensor.TYPE_ACCELEROMETER) check(registered) { "No se pudo registrar acelerómetro" }
                }
                if (gpsEligible) {
                    gps = GpsCollector(getSystemService(LOCATION_SERVICE) as LocationManager) { sample ->
                        if (!closing.get()) writer?.offer(sample)
                    }.also { it.start(collector.looper) }
                }
                metadata.put("gps_registered", gps?.registered == true).put("sensor_states", JSONObject(sensorStates))
                writeMetadata()
                main.post {
                    CaptureState.snapshot = CaptureState.snapshot.copy(phase = "Capturando sensores", directory = folder,
                        gyroAvailable = available[Sensor.TYPE_GYROSCOPE] != null)
                    main.post(ticker)
                    if (CaptureState.stopRequested) finishCapture()
                }
            } catch (error: Exception) {
                terminalError = error.message ?: error.javaClass.simpleName
                stopSources()
                closing.set(true)
                if (writer != null) writer!!.finish() else complete(terminalError)
            }
        }
        return START_NOT_STICKY
    }

    override fun onSensorChanged(event: SensorEvent) {
        if (closing.get()) return
        val name = sensorTypes[event.sensor.type] ?: return
        val v = event.values
        if (v.size < 3) return
        val sample = if (event.sensor.type == Sensor.TYPE_ROTATION_VECTOR)
            RotationSample(event.timestamp, v[0], v[1], v[2], v.getOrNull(3), v.getOrNull(4), v.size, event.accuracy)
        else ImuSample(name, event.timestamp, v[0], v[1], v[2])
        writer?.offer(sample)
    }
    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit
    private fun stopSources() { manager.unregisterListener(this); gps?.close() }
    fun finishCapture() {
        if (!closing.compareAndSet(false, true)) return
        collector.post { stopSources(); writer?.finish() }
    }
    private fun publish() {
        val empty = StreamSummary(0, 0.0, 0.0, 0, 0)
        val stats = writer?.stats?.mapValues { it.value.snapshot() }.orEmpty()
        val fix = gps?.lastFix
        val age = fix?.let { ((SystemClock.elapsedRealtimeNanos() - it.timestampNs) / 1e9).coerceAtLeast(0.0) }
        val state = gps?.state ?: gpsInitialState
        CaptureState.snapshot = CaptureState.snapshot.copy(
            accel = stats["accelerometer"] ?: empty, gyro = stats["gyroscope"] ?: empty,
            dropped = writer?.dropped?.get() ?: 0, streams = stats, sensorStates = sensorStates,
            gpsState = if (state == "Recibiendo GPS" && (age ?: 0.0) > 10.0) "Sin fijación reciente" else state,
            gpsAccuracyM = fix?.accuracyM, gpsAgeSeconds = age, gpsSpeedMps = fix?.speedMps)
    }
    private fun complete(error: String?) {
        if (!completed.compareAndSet(false, true)) return
        closing.set(true)
        terminalError = terminalError ?: error
        stopSources()
        try {
            val w = writer
            if (w != null && w.stats.getValue("accelerometer").snapshot().count == 0L)
                terminalError = terminalError ?: "No se recibieron muestras de acelerómetro"
            val warnings = JSONArray()
            for ((name, state) in sensorStates) {
                if (state != "Registrado") warnings.put("$name: $state")
                else if ((w?.stats?.get(name)?.snapshot()?.count ?: 0L) == 0L) warnings.put("$name: sin muestras")
            }
            val gpsCount = w?.stats?.get("gps")?.snapshot()?.count ?: 0L
            val lastFix = gps?.lastFix
            val lastFixAge = lastFix?.let { ((SystemClock.elapsedRealtimeNanos() - it.timestampNs) / 1e9).coerceAtLeast(0.0) }
            val lastGpsState = gps?.state ?: gpsInitialState
            if (gpsRequested && gpsCount == 0L) warnings.put("GPS solicitado sin fijaciones guardadas")
            if ((w?.dropped?.get() ?: 0L) > 0L) warnings.put("Descartes por cola llena")
            metadata.put("state", if (terminalError == null) "COMPLETED" else "INCOMPLETE")
                .put("error", terminalError ?: JSONObject.NULL).put("quality_warnings", warnings)
                .put("gps_available", gpsCount > 0)
                .put("gps_final_state", if (lastGpsState == "Recibiendo GPS" && (lastFixAge ?: 0.0) > 10.0) "Sin fijación reciente" else lastGpsState)
                .put("gps_last_fix_age_s", lastFixAge ?: JSONObject.NULL)
                .put("gps_last_fix_monotonic_ns", lastFix?.timestampNs?.toString() ?: JSONObject.NULL)
                .put("queue_dropped", w?.dropped?.get() ?: 0).put("pending_unwritten", w?.pendingCount() ?: 0)
            for ((name, stats) in w?.stats.orEmpty()) {
                val s = stats.snapshot()
                metadata.put(name + "_quality", JSONObject().put("samples", s.count).put("effective_hz", s.hz)
                    .put("max_gap_ms", s.maxGapMs).put("intervals_over_100ms", s.gapsOver100Ms).put("non_increasing", s.nonIncreasing))
            }
            writeMetadata()
        } catch (problem: Exception) { terminalError = terminalError ?: problem.message ?: "Metadata failure" }
        main.post {
            main.removeCallbacks(ticker)
            completionReady = true
            publish()
            CaptureState.snapshot = CaptureState.snapshot.copy(busy = !destroyed, directory = directory,
                phase = if (terminalError == null) "Captura guardada" else "Captura incompleta", error = terminalError)
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
            if (destroyed) thread.quitSafely()
        }
    }
    private fun writeMetadata() {
        val dir = directory ?: return
        val tmp = File(dir, "metadata.json.tmp")
        FileOutputStream(tmp).use { stream -> stream.write(metadata.toString(2).toByteArray(Charsets.UTF_8)); stream.fd.sync() }
        java.nio.file.Files.move(tmp.toPath(), File(dir, "metadata.json").toPath(),
            java.nio.file.StandardCopyOption.REPLACE_EXISTING, java.nio.file.StandardCopyOption.ATOMIC_MOVE)
    }
    override fun onDestroy() {
        destroyed = true
        main.removeCallbacks(ticker)
        if (!completionReady) { if (!completed.get()) terminalError = "Servicio interrumpido"; finishCapture() }
        else { CaptureState.snapshot = CaptureState.snapshot.copy(busy = false); thread.quitSafely() }
        if (CaptureState.service === this) CaptureState.service = null
        super.onDestroy()
    }
    override fun onBind(intent: Intent?): IBinder? = null
}
