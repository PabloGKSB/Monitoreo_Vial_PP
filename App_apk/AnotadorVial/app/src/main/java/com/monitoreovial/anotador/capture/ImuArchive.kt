package com.monitoreovial.anotador.capture

import java.io.File
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

object ImuArchive {
    fun create(directory: File, annotations: File, output: File) {
        require(directory.isDirectory && annotations.isFile) { "Missing capture or annotations" }
        require(File(directory, "metadata.json").isFile) { "Missing capture metadata" }
        val inputs = directory.listFiles()?.filter { it.isFile && !it.name.endsWith(".tmp") }.orEmpty() + annotations
        require(inputs.map { it.name }.distinct().size == inputs.size) { "Duplicate archive entry" }
        check(output.createNewFile()) { "Archive already exists" }
        try {
            ZipOutputStream(output.outputStream().buffered()).use { stream ->
                for (file in inputs) {
                    stream.putNextEntry(ZipEntry(file.name))
                    file.inputStream().use { it.copyTo(stream) }
                    stream.closeEntry()
                }
            }
        } catch (error: Exception) {
            output.delete()
            throw error
        }
    }
}
