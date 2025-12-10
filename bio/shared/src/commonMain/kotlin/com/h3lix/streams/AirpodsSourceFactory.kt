package com.h3lix.streams

/**
 * Platform hook: returns a SomaticSource for AirPods Pro 3 HR/HRV on iOS, null elsewhere.
 */
expect fun airpodsSourceFor(
    participantId: String,
    sessionId: String?,
    segments: List<String> = emptyList()
): SomaticSource?
