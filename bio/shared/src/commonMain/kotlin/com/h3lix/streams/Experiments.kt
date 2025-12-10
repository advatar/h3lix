package com.h3lix.streams

import kotlinx.serialization.Serializable

@Serializable
data class MobileTrialConfig(
    val trialId: String,
    val stimulusType: String,
    val stimulusPayload: String,
    val awarenessCondition: String,
    val maskType: String? = null,
    val decisionOptions: List<String>,
    val itiMs: Long = 1000,
    val planId: String? = null
)

@Serializable
data class MobileSession(
    val sessionId: String,
    val participantId: String
)

@Serializable
data class TaskEvent(
    val trialId: String,
    val sessionId: String,
    val planId: String? = null,
    val awarenessCondition: String,
    val maskType: String? = null,
    val choice: String? = null,
    val rtMs: Long? = null,
    val intuitionRating: Double? = null,
    val confidenceRating: Double? = null,
    val awarenessCheck: String? = null,
    val segments: List<String>? = null
)
