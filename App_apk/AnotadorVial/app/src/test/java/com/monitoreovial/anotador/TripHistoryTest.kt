package com.monitoreovial.anotador

import com.monitoreovial.anotador.history.TripHistory
import com.monitoreovial.anotador.storage.AnnotationCsvStore as Csv
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File

class TripHistoryTest {
    @get:Rule val tmp = TemporaryFolder()
    private fun trip(name: String = "test_anotaciones.csv", closed: Boolean = true): File {
        val file = File(tmp.root, name)
        Csv.create(file)
        Csv.append(file, Csv.row("Ruta, \"norte\"", "inicio", 1000, 0, "MONITOREO_INICIO"))
        Csv.append(file, Csv.row("Ruta, \"norte\"", "marca", 3000, 2000, "BACHE"))
        if (closed) Csv.append(file, Csv.row("Ruta, \"norte\"", "fin", 4000, 3000, "MONITOREO_FIN"))
        return file
    }
    @Test fun readsEscapedIdsAndSeparatesSystemEvents() {
        val saved = TripHistory.read(trip())
        assertEquals("Ruta, \"norte\"", saved.id)
        assertEquals(1, saved.events.size)
        assertEquals(3000L, saved.durationMs)
        assertTrue(saved.closed)
    }
    @Test fun missingEndRemainsIncomplete() {
        val saved = TripHistory.read(trip(closed = false))
        assertFalse(saved.closed)
        assertNull(saved.durationMs)
    }
    @Test fun corruptFileDoesNotHideGoodRecordings() {
        trip()
        File(tmp.root, "bad_anotaciones.csv").writeText("bad")
        val records = TripHistory.load(tmp.root)
        assertEquals(2, records.size)
        assertEquals(1, records.count { it.error != null })
    }
    @Test fun skipsActiveRecordingAndUnrelatedFilesWithoutChangingData() {
        val active = trip()
        val bytes = active.readBytes()
        File(tmp.root, "accelerometer.csv").writeText("raw")
        assertTrue(TripHistory.load(tmp.root, active).isEmpty())
        assertArrayEquals(bytes, active.readBytes())
    }
    @Test fun supportsQuotedMultilineFields() {
        val file = trip()
        Csv.append(file, Csv.row("Ruta, \"norte\"", "linea\nsegunda", 3500, 2500, "OTRO"))
        assertEquals("linea\nsegunda", TripHistory.read(file).events.last().timestamp)
    }
}
