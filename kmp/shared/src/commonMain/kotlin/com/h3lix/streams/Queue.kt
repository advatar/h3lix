package com.h3lix.streams

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

/**
 * Minimal offline queue abstraction; wire to SQLDelight on each platform.
 */
interface PendingEventDao {
    suspend fun insert(id: String, payload: String, priority: Int)
    suspend fun loadOldest(limit: Int = 100): List<PendingEventRow>
    suspend fun delete(ids: List<String>)
}

data class PendingEventRow(
    val id: String,
    val payload: String,
    val priority: Int
) {
    fun toEventEnvelope(json: Json = Json): EventEnvelope =
        json.decodeFromString(EventEnvelope.serializer(), payload)
}

class QueueManager(
    private val dao: PendingEventDao,
    private val client: suspend (List<EventEnvelope>) -> Unit,
    private val json: Json = Json
) {
    suspend fun enqueue(event: EventEnvelope, priority: Int = 1) {
        val payload = json.encodeToString(EventEnvelope.serializer(), event)
        dao.insert(event.eventId, payload, priority)
    }

    suspend fun flush(batchSize: Int = 100) = withContext(Dispatchers.Default) {
        val rows = dao.loadOldest(limit = batchSize)
        if (rows.isEmpty()) return@withContext
        val events = rows.map { it.toEventEnvelope(json) }
        try {
            client(events)
            dao.delete(rows.map { it.id })
        } catch (_: Exception) {
            // keep rows for retry; backoff handled by caller
        }
    }
}
