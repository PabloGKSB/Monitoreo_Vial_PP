package com.monitoreovial.anotador

import com.monitoreovial.anotador.capture.ImuArchive
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File
import java.util.zip.ZipFile

class ImuArchiveTest {
    @get:Rule val tmp = TemporaryFolder()
    @Test fun bundlesRawMetadataAndAnnotationsWithoutTemporaryFiles() {
        val folder = tmp.newFolder("imu")
        File(folder, "metadata.json").writeText("{\"state\":\"COMPLETED\"}")
        File(folder, "accelerometer.csv").writeText("raw\n")
        File(folder, "metadata.json.tmp").writeText("partial")
        val annotations = tmp.newFile("annotations.csv").apply { writeText("annotations\n") }
        val output = File(tmp.root, "session.zip")
        ImuArchive.create(folder, annotations, output)
        ZipFile(output).use { zip ->
            assertEquals(setOf("metadata.json", "accelerometer.csv", "annotations.csv"), zip.entries().asSequence().map { it.name }.toSet())
            assertEquals("raw\n", zip.getInputStream(zip.getEntry("accelerometer.csv")).bufferedReader().use { it.readText() })
        }
    }
    @Test fun refusesToReplaceExistingArchive() {
        val folder = tmp.newFolder("imu")
        File(folder, "metadata.json").writeText("{}")
        val annotations = tmp.newFile("annotations.csv")
        val output = tmp.newFile("existing.zip").apply { writeText("preserve") }
        try { ImuArchive.create(folder, annotations, output); fail("Expected refusal") }
        catch (_: IllegalStateException) { }
        assertEquals("preserve", output.readText())
    }
    @Test fun refusesSessionWithoutMetadata() {
        val output = File(tmp.root, "missing.zip")
        try { ImuArchive.create(tmp.newFolder("imu"), tmp.newFile("annotations.csv"), output); fail("Expected refusal") }
        catch (_: IllegalArgumentException) { }
        assertFalse(output.exists())
    }
}
