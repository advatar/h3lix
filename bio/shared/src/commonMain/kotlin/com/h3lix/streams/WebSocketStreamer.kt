package com.h3lix.streams

import io.ktor.client.HttpClient
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logging
import io.ktor.client.plugins.websocket.WebSockets
import io.ktor.client.plugins.websocket.webSocket
import io.ktor.http.HttpHeaders
import io.ktor.serialization.kotlinx.json.json
import io.ktor.websocket.send
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

/**
 * Minimal websocket client for streaming EventEnvelope payloads to the backend
 * ingest endpoint (ws(s)://<host>/streams/ingest).
 */
class EventWebSocketClient(
    private val url: String,
    private val authToken: String? = null,
    private val json: Json = Json { ignoreUnknownKeys = true; encodeDefaults = true }
) {
    private val client = HttpClient {
        install(WebSockets)
        install(ContentNegotiation) {
            json(json)
        }
        install(Logging) {
            level = LogLevel.INFO
        }
    }

    /**
    * Streams events over a single websocket session. Batches messages to reduce frames.
    */
    suspend fun stream(events: Flow<EventEnvelope>, batchSize: Int = 1) {
        client.webSocket(
            urlString = url,
            request = {
                authToken?.let { header(HttpHeaders.Authorization, "Bearer $it") }
            }
        ) {
            val buffer = mutableListOf<EventEnvelope>()
            events.collect { event ->
                buffer += event
                if (buffer.size >= batchSize) {
                    send(json.encodeToString(EventBatch.serializer(), EventBatch(buffer.toList())))
                    buffer.clear()
                }
            }
            if (buffer.isNotEmpty()) {
                send(json.encodeToString(EventBatch.serializer(), EventBatch(buffer.toList())))
            }
        }
    }

    /**
    * Sends a single EventEnvelope then closes the websocket.
    */
    suspend fun send(event: EventEnvelope) {
        stream(flowOf(event))
    }

    fun close() = client.close()
}
