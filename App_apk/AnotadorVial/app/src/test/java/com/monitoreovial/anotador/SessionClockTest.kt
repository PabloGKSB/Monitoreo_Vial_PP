package com.monitoreovial.anotador

import com.monitoreovial.anotador.session.SessionClock
import org.junit.Assert.assertEquals
import org.junit.Test

class SessionClockTest {
    @Test fun civilClockJumpDoesNotChangeDuration() {
        var epoch = 100000L
        var monotonic = 5000L
        val clock = SessionClock({ epoch }, { monotonic })
        epoch -= 60000L
        monotonic += 2500L
        val mark = clock.mark()
        assertEquals(2500L, mark.elapsedMs)
        assertEquals(40000L, mark.epochMs)
        assertEquals(100000L, clock.startedEpochMs)
    }

    @Test fun newSessionHasItsOwnOrigin() {
        var monotonic = 20L
        val first = SessionClock({ 1000L }, { monotonic })
        monotonic = 100L
        val second = SessionClock({ 1080L }, { monotonic })
        assertEquals(80L, first.elapsedMs())
        assertEquals(0L, second.elapsedMs())
    }
}
