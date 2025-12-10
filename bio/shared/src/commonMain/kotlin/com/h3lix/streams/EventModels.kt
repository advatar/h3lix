package com.h3lix.streams

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlin.uuid.ExperimentalUuidApi
import kotlin.uuid.Uuid

@Serializable
enum class StreamType {
    somatic, text, audio, video, meta, task
}

@Serializable
data class Quality(
    @SerialName("sampling_rate_hz") val samplingRateHz: Double? = null,
    @SerialName("signal_to_noise") val signalToNoise: Double? = null,
    val completeness: Double? = null,
    @SerialName("battery_level") val batteryLevel: Double? = null,
)

@OptIn(ExperimentalUuidApi::class)
@Serializable
data class EventEnvelope(
    @SerialName("event_id") val eventId: String = Uuid.random().toString(),
    @SerialName("participant_id") val participantId: String,
    val source: String,
    @SerialName("stream_type") val streamType: StreamType,
    @SerialName("timestamp_utc") val timestampUtc: String,
    @SerialName("device_clock") val deviceClock: Double? = null,
    @SerialName("session_id") val sessionId: String? = null,
    val scope: String? = null,
    val segments: List<String>? = null,
    val payload: JsonElement = JsonNull,
    val quality: Quality? = null,
)

@Serializable
data class EventBatch(
    val events: List<EventEnvelope> = emptyList()
)
