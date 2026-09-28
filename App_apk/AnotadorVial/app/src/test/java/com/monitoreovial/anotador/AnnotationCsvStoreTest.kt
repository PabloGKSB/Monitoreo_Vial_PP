package com.monitoreovial.anotador

import com.monitoreovial.anotador.storage.AnnotationCsvStore as Store
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File
import java.io.IOException

class AnnotationCsvStoreTest {
    @get:Rule val temporary = TemporaryFolder()

    @Test fun legacyHeaderAndAppendArePreserved() {
        val file = File(temporary.root, "trip.csv")
        Store.create(file)
        val row = Store.row("trip", "2026-09-26", 123L, 4L, "BACHE")
        Store.append(file, row)
        assertEquals(Store.HEADER + "trip,2026-09-26,123,4,BACHE\n", file.readText())
    }

    @Test fun duplicateCreateDoesNotEraseRecording() {
        val file = File(temporary.root, "trip.csv")
        Store.create(file)
        Store.append(file, "original\n")
        try { Store.create(file); fail("Expected collision") } catch (_: IOException) { }
        assertEquals(Store.HEADER + "original\n", file.readText())
    }

    @Test fun replacementUsesCompleteNewSnapshot() {
        val file = File(temporary.root, "trip.csv")
        Store.create(file)
        Store.append(file, "old\n")
        Store.replace(file, sequenceOf("start\n", "end\n"))
        assertEquals(Store.HEADER + "start\nend\n", file.readText())
        assertEquals(1, temporary.root.listFiles()!!.size)
    }

    @Test fun failedSnapshotPreservesOriginalBytes() {
        val file = File(temporary.root, "trip.csv")
        Store.create(file)
        Store.append(file, "original\n")
        val before = file.readBytes()
        val broken = sequence<String> { yield("partial\n"); throw IOException("Simulated failure") }
        try { Store.replace(file, broken); fail("Expected failure") } catch (_: IOException) { }
        assertArrayEquals(before, file.readBytes())
        assertEquals(1, temporary.root.listFiles()!!.size)
    }

    @Test fun csvQuotesSpecialCharacters() {
        assertEquals("\"a,b\",\"a\"\"b\",1,2,BACHE\n", Store.row("a,b", "a\"b", 1L, 2L, "BACHE"))
    }
}
