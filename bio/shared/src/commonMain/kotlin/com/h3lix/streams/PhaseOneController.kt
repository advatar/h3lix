package com.h3lix.streams

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.launch
import kotlinx.datetime.Clock
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject

/**
 * Phase 1 helper that wires AirPods HR/HRV, journaling, and E1-style task events into the QueueManager.
 */
class PhaseOneController(
    private val participantId: String,
    private val sessionId: String? = null,
    private val queue: QueueManager,
    private val somaticSource: SomaticSource? = null,
    private val defaultSegments: List<String> = emptyList()
)
{
    private val scope = CoroutineScope(Dispatchers.Default)
    private var somaticJob: Job? = null

    fun startSomatic() {
        val source = somaticSource ?: return
        somaticJob?.cancel()
        somaticJob = source.events
            .onEach { queue.enqueue(it) }
            .launchIn(scope)
        scope.launch { source.start() }
    }

    fun stopSomatic() {
        somaticJob?.cancel()
        somaticJob = null
        somaticSource?.let { scope.launch { it.stop() } }
    }

    suspend fun sendJournal(text: String, mood: Double? = null, segments: List<String> = defaultSegments) {
        val payload = buildJsonObject {
            put("text", JsonPrimitive(text))
            mood?.let { put("mood", JsonPrimitive(it)) }
            if (segments.isNotEmpty()) {
                put("segments", JsonArray(segments.map { JsonPrimitive(it) }))
            }
        }
        queue.enqueue(
            EventEnvelope(
                participantId = participantId,
                source = "ios_journal",
                streamType = StreamType.text,
                timestampUtc = Clock.System.now().toString(),
                deviceClock = deviceUptimeSeconds(),
                sessionId = sessionId,
                segments = segments.takeIf { it.isNotEmpty() },
                payload = payload
            )
        )
    }

    suspend fun sendTaskEvent(
        trialId: String,
        stimulus: String,
        choice: String,
        rtMs: Long,
        awarenessCondition: String,
        intuitionRating: Double? = null,
        segments: List<String> = defaultSegments,
        accuracy: Double? = null
    ) {
        val payload = buildJsonObject {
            put("trial_id", JsonPrimitive(trialId))
            put("stimulus", JsonPrimitive(stimulus))
            put("choice", JsonPrimitive(choice))
            put("rt_ms", JsonPrimitive(rtMs))
            put("awareness_condition", JsonPrimitive(awarenessCondition))
            intuitionRating?.let { put("intuition_rating", JsonPrimitive(it)) }
            accuracy?.let {
                put("accuracy", JsonPrimitive(it))
                // Provide hrv mean placeholder for Noetic fallback if downstream combines them.
            }
            if (segments.isNotEmpty()) {
                put("segments", buildJsonArray { segments.forEach { add(JsonPrimitive(it)) } })
            }
        }
        queue.enqueue(
            EventEnvelope(
                participantId = participantId,
                source = "ios_task",
                streamType = StreamType.task,
                timestampUtc = Clock.System.now().toString(),
                deviceClock = deviceUptimeSeconds(),
                sessionId = sessionId,
                segments = segments.takeIf { it.isNotEmpty() },
                payload = payload
            )
        )
    }

    suspend fun flush(batchSize: Int = 100) {
        queue.flush(batchSize)
    }
}

expect fun deviceUptimeSeconds(): Double
