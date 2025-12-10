package com.h3lix.streams

import kotlinx.datetime.Clock
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject

fun sampleEvent(
    participantId: String = "P-demo",
    source: String = "kmp-demo",
    streamType: StreamType = StreamType.somatic
): EventEnvelope = EventEnvelope(
    participantId = participantId,
    source = source,
    streamType = streamType,
    timestampUtc = Clock.System.now().toString(),
    payload = buildJsonObject {
        put("hr", JsonPrimitive(72))
        put("hrv", JsonPrimitive(45.0))
        put("note", JsonPrimitive("Synthetic example payload"))
    },
    quality = Quality(
        samplingRateHz = 25.0,
        signalToNoise = 0.9
    )
)
