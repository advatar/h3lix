package com.h3lix.streams

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlin.random.Random
import kotlin.system.*
import kotlin.uuid.ExperimentalUuidApi
import kotlin.uuid.Uuid

@Serializable
enum class StreamType {
    somatic, text, audio, video, meta, task
}

@Serializable
data class Quality(
    val samplingRateHz: Double? = null,
    val signalToNoise: Double? = null,
    val completeness: Double? = null,
    val batteryLevel: Double? = null,
)

@OptIn(ExperimentalUuidApi::class)
@Serializable
data class EventEnvelope(
    val eventId: String = Uuid.random().toString(),
    val participantId: String,
    val source: String,
    val streamType: StreamType,
    val timestampUtc: String,
    val deviceClock: Double? = null,
    val sessionId: String? = null,
    val scope: String? = null,
    val segments: List<String>? = null,
    val payload: JsonElement = JsonNull,
    val quality: Quality? = null,
)

@Serializable
data class EventBatch(
    val events: List<EventEnvelope> = emptyList()
)
