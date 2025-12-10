package com.h3lix.streams

actual fun airpodsSourceFor(
    participantId: String,
    sessionId: String?,
    segments: List<String>
): SomaticSource? = AirpodsHealthKitSource(participantId = participantId, sessionId = sessionId, defaultSegments = segments)
