package com.monitoreovial.anotador

import com.monitoreovial.anotador.capture.*
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

class ImuWriterTest {
    @get:Rule val tmp = TemporaryFolder()
    @Test fun drainsQueueAndKeepsNativeTimes() {
        val done = CountDownLatch(1)
        var failure: String? = "not finished"
        val writer = ImuSessionWriter(tmp.root, 1_000_000_000L, 2000L, listOf("accelerometer")) { failure = it; done.countDown() }
        writer.start()
        assertTrue(writer.offer(ImuSample("accelerometer", 1_010_000_000L, 1f, 2f, 3f)))
        writer.finish()
        assertTrue(done.await(5, TimeUnit.SECONDS))
        assertNull(failure)
        val lines = File(tmp.root, "accelerometer.csv").readLines()
        assertEquals(2, lines.size)
        assertEquals("1010000000,2010,0.01,1.0,2.0,3.0", lines[1])
        assertFalse(writer.offer(ImuSample("accelerometer", 2L, 0f, 0f, 0f)))
    }
    @Test fun queueIsBoundedAndReportsLoss() {
        val done = CountDownLatch(1)
        val writer = ImuSessionWriter(tmp.root, 0, 0, listOf("accelerometer"), 1) { done.countDown() }
        assertTrue(writer.offer(ImuSample("accelerometer", 1L, 0f, 0f, 0f)))
        assertFalse(writer.offer(ImuSample("accelerometer", 2L, 0f, 0f, 0f)))
        assertEquals(1L, writer.dropped.get())
        writer.finish(); writer.start()
        assertTrue(done.await(5, TimeUnit.SECONDS))
        assertEquals(1L, writer.stats.getValue("accelerometer").snapshot().count)
    }
    @Test fun qualityUsesActualIntervals() {
        val stats = StreamStats()
        listOf(0L, 10_000_000L, 20_000_000L, 220_000_000L).forEach { stats.add(it) }
        val s = stats.snapshot()
        assertEquals(4L, s.count)
        assertEquals(3.0 / .22, s.hz, .00001)
        assertEquals(200.0, s.maxGapMs, .001)
        assertEquals(1L, s.gapsOver100Ms)
    }
    @Test fun storageFailureIsReportedWithoutReplacingOldSensorFile() {
        val original = File(tmp.root, "accelerometer.csv").apply { writeText("old") }
        val done = CountDownLatch(1)
        var failure: String? = null
        val writer = ImuSessionWriter(tmp.root, 0, 0, listOf("accelerometer")) { failure = it; done.countDown() }
        writer.start()
        assertTrue(done.await(5, TimeUnit.SECONDS))
        assertNotNull(failure)
        assertEquals("old", original.readText())
    }
}
