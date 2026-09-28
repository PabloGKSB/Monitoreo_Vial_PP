package com.monitoreovial.anotador.storage

import java.io.File
import java.io.FileOutputStream
import java.nio.file.Files
import java.nio.file.StandardCopyOption

/** Legacy-compatible annotation storage; not a high-frequency sensor writer. */
object AnnotationCsvStore {
    const val HEADER = "trip_id,timestamp,epoch_ms,elapsed_ms,event_type\n"

    fun row(tripId: String, timestamp: String, epochMs: Long, elapsedMs: Long, type: String): String =
        listOf(tripId, timestamp, epochMs.toString(), elapsedMs.toString(), type)
            .joinToString(",") { escape(it) } + "\n"

    private fun escape(value: String): String =
        if (value.any { it == ',' || it == '"' || it == '\n' || it == '\r' })
            "\"" + value.replace("\"", "\"\"") + "\"" else value

    @Synchronized
    fun create(file: File) {
        // Never truncate a recording if a generated name happens to collide.
        Files.createFile(file.toPath())
        try {
            writeAndSync(file, HEADER, false)
        } catch (error: Exception) {
            file.delete()
            throw error
        }
    }

    @Synchronized
    fun append(file: File, row: String) {
        require(file.isFile) { "Missing annotation file" }
        writeAndSync(file, row, true)
    }

    @Synchronized
    fun replace(file: File, rows: Sequence<String>) {
        require(file.isFile) { "Missing annotation file" }
        val temporary = File.createTempFile("annotations-", ".tmp", file.absoluteFile.parentFile)
        try {
            FileOutputStream(temporary).use { stream ->
                stream.write(HEADER.toByteArray(Charsets.UTF_8))
                rows.forEach { stream.write(it.toByteArray(Charsets.UTF_8)) }
                stream.fd.sync()
            }
            // Same-directory atomic replacement; fail rather than truncate the original.
            Files.move(temporary.toPath(), file.toPath(),
                StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
        } finally {
            temporary.delete()
        }
    }

    private fun writeAndSync(file: File, value: String, append: Boolean) {
        FileOutputStream(file, append).use { stream ->
            stream.write(value.toByteArray(Charsets.UTF_8))
            stream.fd.sync()
        }
    }
}
