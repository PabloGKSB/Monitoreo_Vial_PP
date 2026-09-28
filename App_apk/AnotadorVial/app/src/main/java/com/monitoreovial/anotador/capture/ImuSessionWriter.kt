package com.monitoreovial.anotador.capture

import java.io.File
import java.io.FileOutputStream
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicLong

data class ImuSample(override val sensor: String, override val timestampNs: Long, val x: Float, val y: Float, val z: Float) : CaptureSample {
    override fun cells() = listOf(x.toString(), y.toString(), z.toString())
}
data class StreamSummary(val count: Long, val hz: Double, val maxGapMs: Double, val gapsOver100Ms: Long, val nonIncreasing: Long)

class StreamStats {
    private var count = 0L
    private var first = 0L
    private var last = 0L
    private var maxGap = 0L
    private var gaps = 0L
    private var nonIncreasing = 0L
    @Synchronized fun add(time: Long) {
        if (count == 0L) first = time else {
            val dt = time - last
            if (dt <= 0) nonIncreasing++
            if (dt > 100_000_000L) gaps++
            maxGap = maxOf(maxGap, dt)
        }
        last = time
        count++
    }
    @Synchronized fun snapshot() = StreamSummary(count,
        if (count > 1 && last > first) (count - 1) * 1e9 / (last - first) else 0.0,
        maxGap / 1e6, gaps, nonIncreasing)
}

/** Bounded queue: native sensor callbacks never wait for disk I/O. */
class ImuSessionWriter(
    directory: File,
    private val originNs: Long,
    private val epochMs: Long,
    sensorNames: List<String>,
    capacity: Int = 4096,
    private val finished: (String?) -> Unit
) {
    init { require(sensorNames.distinct().size == sensorNames.size && sensorNames.all { it in CaptureSchema.columns }) }
    private val queue = ArrayBlockingQueue<CaptureSample>(capacity)
    private val gate = Any()
    @Volatile private var accepting = true
    @Volatile private var finishing = false
    val dropped = AtomicLong(0)
    val stats = sensorNames.associateWith { StreamStats() }
    private val worker = Thread({
        val streams = mutableMapOf<String, FileOutputStream>()
        val writers = mutableMapOf<String, java.io.BufferedWriter>()
        var failure: String? = null
        try {
            for (name in sensorNames) {
                val file = File(directory, "$name.csv")
                check(file.createNewFile()) { "Sensor file already exists" }
                val stream = FileOutputStream(file)
                streams[name] = stream
                val writer = stream.bufferedWriter(Charsets.UTF_8)
                writers[name] = writer
                writer.write(CaptureSchema.header(name))
                writer.flush()
            }
            var lastFlush = System.nanoTime()
            while (!finishing || queue.isNotEmpty()) {
                val sample = queue.poll(100, TimeUnit.MILLISECONDS)
                if (sample != null) {
                    val row = CaptureSchema.row(sample, originNs, epochMs)
                    writers.getValue(sample.sensor).write(row)
                    stats.getValue(sample.sensor).add(sample.timestampNs)
                }
                if (System.nanoTime() - lastFlush >= 1_000_000_000L) {
                    writers.values.forEach { it.flush() }
                    lastFlush = System.nanoTime()
                }
            }
        } catch (error: Exception) {
            failure = error.message ?: error.javaClass.simpleName
        } finally {
            synchronized(gate) { accepting = false; finishing = true }
            for ((name, stream) in streams) {
                try { writers[name]?.flush(); stream.fd.sync() }
                catch (error: Exception) { failure = failure ?: error.message ?: "Flush failed" }
                try { writers[name]?.close(); stream.close() }
                catch (error: Exception) { failure = failure ?: error.message ?: "Close failed" }
            }
            finished(failure)
        }
    }, "imu-csv-writer")

    fun start() = worker.start()
    fun offer(sample: CaptureSample): Boolean = synchronized(gate) {
        require(sample.sensor in stats) { "Unregistered sample stream" }
        if (!accepting) return false
        if (queue.offer(sample)) true else { dropped.incrementAndGet(); false }
    }
    fun finish() = synchronized(gate) { accepting = false; finishing = true }
    fun pendingCount(): Int = queue.size
}
