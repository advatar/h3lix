package com.h3lix.streams

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.merge

/**
 * Abstraction for platform-specific somatic sources (HR, steps, motion, etc.).
 */
interface SomaticSource {
    val id: String
    val events: Flow<EventEnvelope>
    suspend fun start()
    suspend fun stop()
}

class SomaticManager(private val sources: List<SomaticSource>) {
    fun events(): Flow<EventEnvelope> = sources.map { it.events }.merge()
    suspend fun startAll() {
        sources.forEach { it.start() }
    }
    suspend fun stopAll() {
        sources.forEach { it.stop() }
    }
}
