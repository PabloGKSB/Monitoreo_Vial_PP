package com.monitoreovial.anotador.session

data class AnnotationTime(val epochMs: Long, val elapsedMs: Long)

/** Preserve civil time for correlation and monotonic time for durations. */
class SessionClock(
    private val epochNow: () -> Long,
    private val monotonicNow: () -> Long
) {
    val startedMonotonicMs: Long = monotonicNow()
    val startedEpochMs: Long = epochNow()

    fun elapsedMs(): Long = monotonicNow() - startedMonotonicMs

    fun mark(): AnnotationTime = AnnotationTime(epochNow(), elapsedMs())
}
