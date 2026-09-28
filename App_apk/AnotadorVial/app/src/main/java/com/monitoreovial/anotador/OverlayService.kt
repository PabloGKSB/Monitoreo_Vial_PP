package com.monitoreovial.anotador

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.IBinder
import android.provider.Settings
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.core.app.NotificationCompat
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min


class OverlayService : Service() {

    companion object {

        private const val CHANNEL_ID =
            "anotador_vial_overlay"

        private const val NOTIFICATION_ID =
            9001
    }


    private lateinit var windowManager:
            WindowManager


    private var bubbleView:
            TextView? = null


    private var panelView:
            LinearLayout? = null


    private lateinit var bubbleParams:
            WindowManager.LayoutParams


    private lateinit var panelParams:
            WindowManager.LayoutParams


    private var panelVisible =
        false


    // ======================================================
    // CREATE
    // ======================================================

    override fun onCreate() {

        super.onCreate()


        windowManager =
            getSystemService(
                WINDOW_SERVICE
            ) as WindowManager


        crearCanalNotificacion()


        iniciarPrimerPlano()
    }


    // ======================================================
    // START
    // ======================================================

    override fun onStartCommand(
        intent: Intent?,
        flags: Int,
        startId: Int
    ): Int {


        if (
            !Settings.canDrawOverlays(
                this
            )
        ) {

            Toast.makeText(
                this,
                "No hay permiso para mostrar la burbuja",
                Toast.LENGTH_LONG
            ).show()


            stopSelf()

            return START_NOT_STICKY
        }


        // Si estaba abierto el panel,
        // lo cerramos para reconstruirlo
        // con el estado actual.
        if (panelVisible) {

            ocultarPanel()
        }


        if (bubbleView == null) {

            crearBurbuja()

        } else {

            actualizarAparienciaBurbuja()
        }


        actualizarNotificacion()


        return START_NOT_STICKY
    }


    // ======================================================
    // FOREGROUND
    // ======================================================

    private fun iniciarPrimerPlano() {


        val intent =
            Intent(
                this,
                MainActivity::class.java
            )


        val pendingIntent =
            PendingIntent.getActivity(

                this,

                0,

                intent,

                PendingIntent.FLAG_UPDATE_CURRENT or
                        PendingIntent.FLAG_IMMUTABLE
            )


        val notification =
            crearNotificacion(
                pendingIntent
            )


        if (
            Build.VERSION.SDK_INT >=
            Build.VERSION_CODES.UPSIDE_DOWN_CAKE
        ) {

            startForeground(

                NOTIFICATION_ID,

                notification,

                ServiceInfo
                    .FOREGROUND_SERVICE_TYPE_SPECIAL_USE
            )

        } else {

            startForeground(
                NOTIFICATION_ID,
                notification
            )
        }
    }


    // ======================================================
    // NOTIFICACIÓN
    // ======================================================

    private fun crearNotificacion(
        pendingIntent: PendingIntent
    ) =
        NotificationCompat.Builder(
            this,
            CHANNEL_ID
        )

            .setContentTitle(
                "Anotador Vial"
            )

            .setContentText(

                if (SesionActual.activa) {

                    "Monitoreo activo · ${cantidadEventosUsuario()} eventos"

                } else {

                    "Burbuja lista · sin monitoreo activo"
                }
            )

            .setSmallIcon(
                android.R.drawable.ic_menu_compass
            )

            .setPriority(
                NotificationCompat.PRIORITY_LOW
            )

            .setOngoing(true)

            .setContentIntent(
                pendingIntent
            )

            .build()


    private fun actualizarNotificacion() {

        try {

            val intent =
                Intent(
                    this,
                    MainActivity::class.java
                )


            val pendingIntent =
                PendingIntent.getActivity(

                    this,

                    0,

                    intent,

                    PendingIntent.FLAG_UPDATE_CURRENT or
                            PendingIntent.FLAG_IMMUTABLE
                )


            val manager =
                getSystemService(
                    NotificationManager::class.java
                )


            manager.notify(

                NOTIFICATION_ID,

                crearNotificacion(
                    pendingIntent
                )
            )

        } catch (e: Exception) {

            e.printStackTrace()
        }
    }


    // ======================================================
    // CANAL
    // ======================================================

    private fun crearCanalNotificacion() {

        if (
            Build.VERSION.SDK_INT >=
            Build.VERSION_CODES.O
        ) {

            val canal =
                NotificationChannel(

                    CHANNEL_ID,

                    "Anotador Vial",

                    NotificationManager
                        .IMPORTANCE_LOW
                )


            canal.description =
                "Mantiene disponible la burbuja del Anotador Vial"


            val manager =
                getSystemService(
                    NotificationManager::class.java
                )


            manager.createNotificationChannel(
                canal
            )
        }
    }


    // ======================================================
    // BURBUJA
    // ======================================================

    private fun crearBurbuja() {


        val burbuja =
            TextView(
                this
            ).apply {

                text =
                    "🚗"

                textSize =
                    29f

                gravity =
                    Gravity.CENTER


                setPadding(
                    dp(6),
                    dp(6),
                    dp(6),
                    dp(6)
                )


                elevation =
                    dp(8).toFloat()


                background =
                    crearFondoBurbuja()
            }


        val anchoPantalla =
            resources
                .displayMetrics
                .widthPixels


        val altoPantalla =
            resources
                .displayMetrics
                .heightPixels


        bubbleParams =
            WindowManager.LayoutParams(

                dp(62),

                dp(62),

                WindowManager.LayoutParams
                    .TYPE_APPLICATION_OVERLAY,

                WindowManager.LayoutParams
                    .FLAG_NOT_FOCUSABLE,

                PixelFormat.TRANSLUCENT
            )


        bubbleParams.gravity =
            Gravity.TOP or
                    Gravity.START


        bubbleParams.x =
            anchoPantalla -
                    dp(80)


        bubbleParams.y =
            altoPantalla / 3


        // ==================================================
        // ARRASTRAR / TOCAR
        // ==================================================

        burbuja.setOnTouchListener(

            object :
                View.OnTouchListener {


                var inicioX =
                    0

                var inicioY =
                    0

                var touchX =
                    0f

                var touchY =
                    0f

                var movido =
                    false


                override fun onTouch(
                    view: View?,
                    event: MotionEvent?
                ): Boolean {


                    event
                        ?: return false


                    when (
                        event.action
                    ) {


                        MotionEvent.ACTION_DOWN -> {

                            inicioX =
                                bubbleParams.x

                            inicioY =
                                bubbleParams.y

                            touchX =
                                event.rawX

                            touchY =
                                event.rawY

                            movido =
                                false

                            return true
                        }


                        MotionEvent.ACTION_MOVE -> {

                            val dx =
                                (
                                        event.rawX -
                                                touchX
                                        ).toInt()


                            val dy =
                                (
                                        event.rawY -
                                                touchY
                                        ).toInt()


                            if (
                                abs(dx) >
                                dp(5) ||
                                abs(dy) >
                                dp(5)
                            ) {

                                movido =
                                    true
                            }


                            bubbleParams.x =
                                limitarX(
                                    inicioX + dx
                                )


                            bubbleParams.y =
                                limitarY(
                                    inicioY + dy
                                )


                            try {

                                windowManager
                                    .updateViewLayout(

                                        burbuja,

                                        bubbleParams
                                    )


                                if (
                                    panelVisible
                                ) {

                                    actualizarPosicionPanel()
                                }

                            } catch (
                                e: Exception
                            ) {

                                e.printStackTrace()
                            }


                            return true
                        }


                        MotionEvent.ACTION_UP -> {

                            if (!movido) {

                                alternarPanel()
                            }


                            return true
                        }
                    }


                    return false
                }
            }
        )


        try {

            windowManager.addView(
                burbuja,
                bubbleParams
            )


            bubbleView =
                burbuja

        } catch (e: Exception) {

            e.printStackTrace()


            Toast.makeText(
                this,
                "No se pudo crear la burbuja",
                Toast.LENGTH_LONG
            ).show()
        }
    }


    // ======================================================
    // COLOR BURBUJA
    // ======================================================

    private fun crearFondoBurbuja():
            GradientDrawable {


        return GradientDrawable().apply {

            shape =
                GradientDrawable.OVAL


            if (SesionActual.activa) {

                // Activa
                setColor(
                    Color.rgb(
                        190,
                        45,
                        45
                    )
                )

            } else {

                // Esperando
                setColor(
                    Color.rgb(
                        35,
                        105,
                        190
                    )
                )
            }
        }
    }


    private fun actualizarAparienciaBurbuja() {

        bubbleView?.background =
            crearFondoBurbuja()
    }


    // ======================================================
    // PANEL
    // ======================================================

    private fun alternarPanel() {

        if (panelVisible) {

            ocultarPanel()

        } else {

            mostrarPanel()
        }
    }


    private fun mostrarPanel() {

        if (panelVisible) {

            return
        }


        val panel =

            if (SesionActual.activa) {

                crearPanelActivo()

            } else {

                crearPanelEsperando()
            }


        panelParams =
            WindowManager.LayoutParams(

                dp(230),

                WindowManager.LayoutParams
                    .WRAP_CONTENT,

                WindowManager.LayoutParams
                    .TYPE_APPLICATION_OVERLAY,

                WindowManager.LayoutParams
                    .FLAG_NOT_FOCUSABLE,

                PixelFormat.TRANSLUCENT
            )


        panelParams.gravity =
            Gravity.TOP or
                    Gravity.START


        calcularPosicionPanel()


        try {

            windowManager.addView(
                panel,
                panelParams
            )


            panelView =
                panel


            panelVisible =
                true

        } catch (e: Exception) {

            e.printStackTrace()
        }
    }


    private fun ocultarPanel() {

        val panel =
            panelView


        if (
            panel != null &&
            panelVisible
        ) {

            try {

                windowManager.removeView(
                    panel
                )

            } catch (
                e: Exception
            ) {

                e.printStackTrace()
            }
        }


        panelView =
            null


        panelVisible =
            false
    }


    // ======================================================
    // PANEL SIN MONITOREO
    // ======================================================

    private fun crearPanelEsperando():
            LinearLayout {


        val panel =
            crearBasePanel()


        panel.addView(

            crearTextoPanel(

                if (
                    SesionActual.finalizada
                ) {

                    "MONITOREO FINALIZADO"

                } else {

                    "ANOTADOR VIAL"
                },

                16f,
                true
            )
        )


        panel.addView(

            crearTextoPanel(
                "🚗 Burbuja lista",
                14f,
                false
            )
        )


        val nombreBase =
            obtenerNombreBase(
                this
            )


        panel.addView(

            crearTextoPanel(
                "Recorrido: $nombreBase",
                12f,
                false
            )
        )


        val iniciar =
            Button(
                this
            ).apply {


                text =
                    "▶ INICIAR MONITOREO"

                isAllCaps =
                    false


                setOnClickListener {
                    if (com.monitoreovial.anotador.capture.GpsAccess.requested(this@OverlayService)) {
                        abrirAplicacion()
                        Toast.makeText(this@OverlayService, "Inicia desde la app para comprobar permisos GPS", Toast.LENGTH_LONG).show()
                        ocultarPanel()
                        return@setOnClickListener
                    }


                    val correcto =
                        iniciarNuevaSesion(

                            this@OverlayService,

                            obtenerNombreBase(
                                this@OverlayService
                            )
                        )


                    if (correcto) {

                        vibrar(
                            this@OverlayService,
                            100
                        )


                        actualizarAparienciaBurbuja()

                        actualizarNotificacion()


                        Toast.makeText(
                            this@OverlayService,
                            "Monitoreo iniciado",
                            Toast.LENGTH_SHORT
                        ).show()


                        ocultarPanel()

                    } else {

                        Toast.makeText(
                            this@OverlayService,
                            "No se pudo iniciar el monitoreo",
                            Toast.LENGTH_LONG
                        ).show()
                    }
                }
            }


        panel.addView(
            iniciar
        )


        val abrirApp =
            Button(
                this
            ).apply {


                text =
                    "📱 ABRIR APP"

                isAllCaps =
                    false


                setOnClickListener {

                    abrirAplicacion()
                }
            }


        panel.addView(
            abrirApp
        )


        return panel
    }


    // ======================================================
    // PANEL CON MONITOREO ACTIVO
    // ======================================================

    private fun crearPanelActivo():
            LinearLayout {


        val panel =
            crearBasePanel()


        panel.addView(

            crearTextoPanel(
                "🔴 MONITOREO ACTIVO",
                16f,
                true
            )
        )


        panel.addView(

            crearTextoPanel(
                "${cantidadEventosUsuario()} eventos",
                12f,
                false
            )
        )


        panel.addView(
            crearBotonEvento(
                "🕳 BACHE",
                "BACHE"
            )
        )


        panel.addView(
            crearBotonEvento(
                "🚧 LOMO DE TORO",
                "LOMO_DE_TORO"
            )
        )


        panel.addView(
            crearBotonEvento(
                "↔ DESVIACIÓN",
                "DESVIACION"
            )
        )


        panel.addView(
            crearBotonEvento(
                "⚠ CAMINO MALO",
                "CAMINO_MALO"
            )
        )


        panel.addView(
            crearBotonEvento(
                "↩ GIRO",
                "GIRO"
            )
        )


        panel.addView(
            crearBotonEvento(
                "❓ OTRO",
                "OTRO"
            )
        )


        // ==================================================
        // DESHACER
        // ==================================================

        val deshacer =
            Button(
                this
            ).apply {


                text =
                    "↶ DESHACER"

                isAllCaps =
                    false


                setOnClickListener {


                    val correcto =
                        deshacerUltimaAnotacion()


                    if (correcto) {

                        vibrar(
                            this@OverlayService,
                            120
                        )


                        actualizarNotificacion()

                    } else {

                        Toast.makeText(
                            this@OverlayService,
                            "No hay eventos para deshacer",
                            Toast.LENGTH_SHORT
                        ).show()
                    }


                    ocultarPanel()
                }
            }


        panel.addView(
            deshacer
        )


        // ==================================================
        // FINALIZAR
        // ==================================================

        val finalizar =
            Button(
                this
            ).apply {


                text =
                    "■ FINALIZAR MONITOREO"

                isAllCaps =
                    false


                setOnClickListener {


                    val correcto =
                        finalizarSesion()


                    if (correcto) {

                        vibrar(
                            this@OverlayService,
                            160
                        )


                        actualizarAparienciaBurbuja()

                        actualizarNotificacion()


                        Toast.makeText(
                            this@OverlayService,
                            "Recorrido finalizado. Guardando captura propia.",
                            Toast.LENGTH_LONG
                        ).show()


                        ocultarPanel()

                    } else {

                        Toast.makeText(
                            this@OverlayService,
                            "No se pudo finalizar",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                }
            }


        panel.addView(
            finalizar
        )


        // ==================================================
        // ABRIR APP
        // ==================================================

        val abrirApp =
            Button(
                this
            ).apply {


                text =
                    "📱 ABRIR APP"

                isAllCaps =
                    false


                setOnClickListener {

                    abrirAplicacion()
                }
            }


        panel.addView(
            abrirApp
        )


        return panel
    }


    // ======================================================
    // BASE PANEL
    // ======================================================

    private fun crearBasePanel():
            LinearLayout {


        return LinearLayout(
            this
        ).apply {


            orientation =
                LinearLayout.VERTICAL


            setPadding(
                dp(10),
                dp(10),
                dp(10),
                dp(10)
            )


            elevation =
                dp(10).toFloat()


            background =
                GradientDrawable().apply {


                    cornerRadius =
                        dp(16).toFloat()


                    setColor(
                        Color.rgb(
                            35,
                            35,
                            40
                        )
                    )
                }
        }
    }


    // ======================================================
    // TEXTO DEL PANEL
    // ======================================================

    private fun crearTextoPanel(
        texto: String,
        tamano: Float,
        negrita: Boolean
    ): TextView {


        return TextView(
            this
        ).apply {


            text =
                texto


            textSize =
                tamano


            setTextColor(
                Color.WHITE
            )


            gravity =
                Gravity.CENTER


            setPadding(
                dp(4),
                dp(5),
                dp(4),
                dp(7)
            )


            if (negrita) {

                setTypeface(
                    typeface,
                    android.graphics.Typeface.BOLD
                )
            }
        }
    }


    // ======================================================
    // BOTÓN EVENTO
    // ======================================================

    private fun crearBotonEvento(
        texto: String,
        evento: String
    ): Button {


        return Button(
            this
        ).apply {


            text =
                texto


            isAllCaps =
                false


            setOnClickListener {


                val correcto =
                    registrarEventoSesion(
                        evento
                    )


                if (correcto) {

                    vibrar(
                        this@OverlayService,
                        70
                    )


                    actualizarNotificacion()

                } else {

                    Toast.makeText(
                        this@OverlayService,
                        "Error guardando evento",
                        Toast.LENGTH_SHORT
                    ).show()
                }


                // Muy importante:
                // anotamos y se cierra inmediatamente.
                ocultarPanel()
            }
        }
    }


    // ======================================================
    // ABRIR APP
    // ======================================================

    private fun abrirAplicacion() {


        ocultarPanel()


        val intent =
            Intent(
                this,
                MainActivity::class.java
            ).apply {


                addFlags(

                    Intent.FLAG_ACTIVITY_NEW_TASK or
                            Intent.FLAG_ACTIVITY_REORDER_TO_FRONT
                )
            }


        startActivity(
            intent
        )
    }


    // ======================================================
    // POSICIÓN PANEL
    // ======================================================

    private fun calcularPosicionPanel() {


        val anchoPantalla =
            resources
                .displayMetrics
                .widthPixels


        val altoPantalla =
            resources
                .displayMetrics
                .heightPixels


        val anchoPanel =
            dp(230)


        val anchoBurbuja =
            dp(62)


        val espacio =
            dp(8)


        panelParams.x =

            if (
                bubbleParams.x >
                anchoPantalla / 2
            ) {

                max(
                    0,
                    bubbleParams.x -
                            anchoPanel -
                            espacio
                )

            } else {

                min(
                    anchoPantalla -
                            anchoPanel,

                    bubbleParams.x +
                            anchoBurbuja +
                            espacio
                )
            }


        val altoEstimado =

            if (
                SesionActual.activa
            ) {

                dp(580)

            } else {

                dp(260)
            }


        panelParams.y =
            min(
                bubbleParams.y,
                max(
                    dp(30),
                    altoPantalla -
                            altoEstimado
                )
            )
    }


    private fun actualizarPosicionPanel() {


        if (
            !panelVisible ||
            panelView == null
        ) {

            return
        }


        calcularPosicionPanel()


        try {

            windowManager
                .updateViewLayout(
                    panelView,
                    panelParams
                )

        } catch (e: Exception) {

            e.printStackTrace()
        }
    }


    // ======================================================
    // LÍMITES BURBUJA
    // ======================================================

    private fun limitarX(
        x: Int
    ): Int {


        val ancho =
            resources
                .displayMetrics
                .widthPixels


        return max(
            0,
            min(
                x,
                ancho -
                        dp(62)
            )
        )
    }


    private fun limitarY(
        y: Int
    ): Int {


        val alto =
            resources
                .displayMetrics
                .heightPixels


        return max(
            dp(30),
            min(
                y,
                alto -
                        dp(100)
            )
        )
    }


    // ======================================================
    // DP
    // ======================================================

    private fun dp(
        valor: Int
    ): Int {


        return (
                valor *
                        resources
                            .displayMetrics
                            .density
                ).toInt()
    }


    // ======================================================
    // DESTROY
    // ======================================================

    override fun onDestroy() {


        ocultarPanel()


        bubbleView?.let {


            try {

                windowManager.removeView(
                    it
                )

            } catch (e: Exception) {

                e.printStackTrace()
            }
        }


        bubbleView =
            null


        stopForeground(
            STOP_FOREGROUND_REMOVE
        )


        super.onDestroy()
    }


    // ======================================================
    // BIND
    // ======================================================

    override fun onBind(
        intent: Intent?
    ): IBinder? {

        return null
    }
}
