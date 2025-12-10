package com.h3lix.streams

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.plugins.ContentNegotiation
import io.ktor.client.plugins.HttpTimeout
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logging
import io.ktor.client.request.HttpRequestBuilder
import io.ktor.client.request.headers
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.HttpStatusCode
import io.ktor.http.contentType
import io.ktor.http.isSuccess
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

@Serializable
private data class ConsentUpdateRequest(
    @SerialName("participant_id") val participantId: String,
    val scopes: List<String>
)

@Serializable
private data class EventBatchEnvelope(
    val events: List<EventEnvelope>
)

class StreamsApiClient(
    private val baseUrl: String,
    private val authToken: String? = null,
    private val json: Json = Json { ignoreUnknownKeys = true; encodeDefaults = true },
    private val http: HttpClient = defaultHttpClient(json)
) {
    suspend fun setConsent(participantId: String, scopes: List<String> = listOf("wearables")) {
        val url = "$baseUrl/consent/participant"
        val req = ConsentUpdateRequest(participantId = participantId, scopes = scopes)
        val resp = http.post(url) {
            applyHeaders()
            contentType(ContentType.Application.Json)
            setBody(req)
        }
        if (resp.status != HttpStatusCode.OK) {
            throw IllegalStateException("Consent failed: ${resp.status}")
        }
    }

    suspend fun postEvents(events: List<EventEnvelope>) {
        if (events.isEmpty()) return
        val url = "$baseUrl/streams/events"
        val resp = http.post(url) {
            applyHeaders()
            contentType(ContentType.Application.Json)
            setBody(EventBatchEnvelope(events))
        }
        if (!resp.status.isSuccess()) {
            val body = runCatching { resp.body<String>() }.getOrNull()
            throw IllegalStateException("Ingest failed: ${resp.status} ${body ?: ""}")
        }
    }

    private fun HttpRequestBuilder.applyHeaders() {
        headers {
            authToken?.let { append("Authorization", "Bearer $it") }
        }
    }
}

private fun defaultHttpClient(json: Json): HttpClient =
    HttpClient {
        install(ContentNegotiation) {
            json(json)
        }
        install(HttpTimeout) {
            requestTimeoutMillis = 30_000
            connectTimeoutMillis = 10_000
            socketTimeoutMillis = 30_000
        }
        install(Logging) {
            level = LogLevel.INFO
        }
    }
