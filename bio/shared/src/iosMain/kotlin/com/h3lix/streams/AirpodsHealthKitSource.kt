package com.h3lix.streams

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.datetime.Clock
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import platform.Foundation.NSDate
import platform.Foundation.NSError
import platform.Foundation.NSISO8601DateFormatter
import platform.HealthKit.HKAnchoredObjectQuery
import platform.HealthKit.HKAnchoredObjectQueryBlock
import platform.HealthKit.HKHeartbeatSeriesQuery
import platform.HealthKit.HKHeartbeatSeriesSample
import platform.HealthKit.HKHealthStore
import platform.HealthKit.HKObjectQueryNoLimit
import platform.HealthKit.HKObjectType
import platform.HealthKit.HKQuantitySample
import platform.HealthKit.HKQuantityType
import platform.HealthKit.HKQuantityTypeIdentifierHeartRate
import platform.HealthKit.HKQuantityTypeIdentifierHeartRateVariabilitySDNN
import platform.HealthKit.HKQuery
import platform.HealthKit.HKQueryAnchor
import platform.HealthKit.HKSeriesTypeIdentifierHeartbeatSeries
import platform.HealthKit.HKUnit
import platform.HealthKit.isHealthDataAvailable
import kotlin.coroutines.resume
import kotlin.coroutines.suspendCoroutine
import kotlin.math.sqrt

/**
 * HealthKit-backed somatic source for AirPods Pro 3 HR / HRV.
 * Emits EventEnvelope(s) with samples [{channel: hr|hrv_sdnn, value, timestamp_utc}].
 */
class AirpodsHealthKitSource(
    private val participantId: String,
    private val sessionId: String? = null,
    private val defaultSegments: List<String> = emptyList()
) : SomaticSource {

    override val id: String = "ios_airpods_pro3"
    override val events: MutableSharedFlow<EventEnvelope> = MutableSharedFlow(extraBufferCapacity = 64)

    private val healthStore = HKHealthStore()
    private var hrAnchor: HKQueryAnchor? = null
    private var hrvAnchor: HKQueryAnchor? = null
    private var heartbeatAnchor: HKQueryAnchor? = null
    private var hrQuery: HKAnchoredObjectQuery? = null
    private var hrvQuery: HKAnchoredObjectQuery? = null
    private var heartbeatQuery: HKAnchoredObjectQuery? = null
    private val isoFormatter = NSISO8601DateFormatter()

    private data class RR(val timestamp: Double, val ms: Double)
    private val rrBuffer = mutableListOf<RR>()
    private var lastBeatTimestamp: Double? = null
    private val hrvWindowSeconds = 120.0

    private val heartRateType: HKQuantityType =
        HKObjectType.quantityTypeForIdentifier(HKQuantityTypeIdentifierHeartRate)!!
    private val hrvType: HKQuantityType =
        HKObjectType.quantityTypeForIdentifier(HKQuantityTypeIdentifierHeartRateVariabilitySDNN)!!
    private val heartbeatSeriesType = HKObjectType.seriesTypeForIdentifier(HKSeriesTypeIdentifierHeartbeatSeries)
    private val hrUnit = HKUnit.unitFromString("count/min")
    private val hrvUnit = HKUnit.unitFromString("ms")

    override suspend fun start() {
        if (!HKHealthStore.isHealthDataAvailable()) return
        if (!authorize()) return
        startHeartRateStream()
        startHrvStream()
        startHeartbeatStream()
    }

    override suspend fun stop() {
        hrQuery?.let { healthStore.stopQuery(it) }
        hrvQuery?.let { healthStore.stopQuery(it) }
        heartbeatQuery?.let { healthStore.stopQuery(it) }
        hrQuery = null
        hrvQuery = null
        heartbeatQuery = null
        hrAnchor = null
        hrvAnchor = null
        heartbeatAnchor = null
        rrBuffer.clear()
        lastBeatTimestamp = null
    }

    private suspend fun authorize(): Boolean = suspendCoroutine { cont ->
        healthStore.requestAuthorizationToShareTypes(
            toShare = null,
            toRead = setOfNotNull<HKObjectType>(heartRateType, hrvType, heartbeatSeriesType)
        ) { granted: Boolean, _: NSError? ->
            cont.resume(granted)
        }
    }

    private fun startHeartRateStream() {
        val handler = anchoredHandler(channel = "hr", unit = hrUnit) { anchor -> hrAnchor = anchor }
        val query = HKAnchoredObjectQuery(
            type = heartRateType,
            predicate = null,
            anchor = hrAnchor,
            limit = HKObjectQueryNoLimit,
            resultsHandler = handler
        )
        hrQuery = query
        healthStore.executeQuery(query)
    }

    private fun startHrvStream() {
        val handler = anchoredHandler(channel = "hrv_sdnn", unit = hrvUnit) { anchor -> hrvAnchor = anchor }
        val query = HKAnchoredObjectQuery(
            type = hrvType,
            predicate = null,
            anchor = hrvAnchor,
            limit = HKObjectQueryNoLimit,
            resultsHandler = handler
        )
        hrvQuery = query
        healthStore.executeQuery(query)
    }

    private fun startHeartbeatStream() {
        val heartbeatType = heartbeatSeriesType ?: return
        val handler: HKAnchoredObjectQueryBlock = { _: HKAnchoredObjectQuery?, samples, _, newAnchor, _ ->
            heartbeatAnchor = newAnchor
            val list = samples as? List<*> ?: return@HKAnchoredObjectQueryBlock
            list.forEach { item ->
                val series = item as? HKHeartbeatSeriesSample ?: return@forEach
                enumerateSeries(series)
            }
        }
        val query = HKAnchoredObjectQuery(
            type = heartbeatType,
            predicate = null,
            anchor = heartbeatAnchor,
            limit = HKObjectQueryNoLimit,
            resultsHandler = handler
        )
        query.updateHandler = handler
        heartbeatQuery = query
        healthStore.executeQuery(query)
    }

    private fun enumerateSeries(series: HKHeartbeatSeriesSample) {
        val startSeconds = series.startDate.timeIntervalSinceReferenceDate
        val seriesQuery = HKHeartbeatSeriesQuery(heartbeatSeries = series) { _: HKHeartbeatSeriesQuery?, timeSinceStart: Double, precededByGap: Boolean, done: Boolean, error ->
            if (error != null) return@HKHeartbeatSeriesQuery
            if (precededByGap) {
                lastBeatTimestamp = null
            }
            val beatSeconds = startSeconds + timeSinceStart
            handleBeat(beatSeconds)
            if (done) {
                // no-op
            }
        }
        healthStore.executeQuery(seriesQuery)
    }

    private fun handleBeat(beatSeconds: Double) {
        val last = lastBeatTimestamp
        if (last != null) {
            val intervalMs = (beatSeconds - last) * 1000.0
            if (intervalMs in 250.0..2000.0) {
                rrBuffer.add(RR(timestamp = beatSeconds, ms = intervalMs))
                val cutoff = beatSeconds - hrvWindowSeconds
                val filtered = rrBuffer.filter { it.timestamp >= cutoff }
                rrBuffer.clear()
                rrBuffer.addAll(filtered)
                val rmssd = computeRmssd()
                if (rmssd != null) {
                    emitHrvRmssd(rmssd, beatSeconds)
                }
            } else if (intervalMs > 2000.0) {
                lastBeatTimestamp = null
            }
        }
        lastBeatTimestamp = beatSeconds
    }

    private fun computeRmssd(): Double? {
        if (rrBuffer.size < 2) return null
        var sumSq = 0.0
        var count = 0
        for (idx in 1 until rrBuffer.size) {
            val diff = rrBuffer[idx].ms - rrBuffer[idx - 1].ms
            sumSq += diff * diff
            count++
        }
        if (count == 0) return null
        return sqrt(sumSq / count.toDouble())
    }

    private fun emitHrvRmssd(rmssd: Double, beatSeconds: Double) {
        val date = NSDate.dateWithTimeIntervalSinceReferenceDate(beatSeconds)
        val iso = isoFormatter.stringFromDate(date) ?: Clock.System.now().toString()
        val payload = buildJsonObject {
            put(
                "samples",
                buildJsonArray {
                    add(
                        buildJsonObject {
                            put("channel", JsonPrimitive("hrv_rmssd"))
                            put("value", JsonPrimitive(rmssd))
                            put("timestamp_utc", JsonPrimitive(iso))
                        }
                    )
                }
            )
            put("hrv_rmssd_ms", JsonPrimitive(rmssd))
            if (defaultSegments.isNotEmpty()) {
                put("segments", JsonArray(defaultSegments.map { JsonPrimitive(it) }))
            }
        }
        val envelope = EventEnvelope(
            participantId = participantId,
            source = id,
            streamType = StreamType.somatic,
            timestampUtc = iso,
            deviceClock = deviceUptimeSeconds(),
            sessionId = sessionId,
            segments = defaultSegments.takeIf { it.isNotEmpty() },
            payload = payload,
            quality = Quality(
                samplingRateHz = 1.0,
                signalToNoise = null,
                batteryLevel = null
            )
        )
        events.tryEmit(envelope)
    }

    private fun anchoredHandler(
        channel: String,
        unit: HKUnit,
        updateAnchor: (HKQueryAnchor?) -> Unit
    ): HKAnchoredObjectQueryBlock {
        return { _, samples, _, newAnchor, _ ->
            updateAnchor(newAnchor)
            val list = samples as? List<*> ?: return@HKAnchoredObjectQueryBlock
            val values = mutableListOf<Double>()
            val payloadSamples = buildJsonArray {
                list.forEach { item ->
                    val sample = item as? HKQuantitySample ?: return@forEach
                    val value = sample.quantity().doubleValueForUnit(unit)
                    values.add(value)
                    add(
                        buildJsonObject {
                            put("channel", JsonPrimitive(channel))
                            put("value", JsonPrimitive(value))
                            put("timestamp_utc", JsonPrimitive(sampleIso(sample)))
                        }
                    )
                }
            }
            if (payloadSamples.isEmpty()) return@HKAnchoredObjectQueryBlock
            val envelope = EventEnvelope(
                participantId = participantId,
                source = id,
                streamType = StreamType.somatic,
                timestampUtc = Clock.System.now().toString(),
                deviceClock = deviceUptimeSeconds(),
                sessionId = sessionId,
                segments = defaultSegments.takeIf { it.isNotEmpty() },
                payload = buildJsonObject {
                    put("samples", payloadSamples)
                    if (channel == "hrv_sdnn" && values.isNotEmpty()) {
                        val mean = values.average()
                        put("hrv_sdnn_mean", JsonPrimitive(mean))
                    }
                    if (defaultSegments.isNotEmpty()) {
                        put("segments", JsonArray(defaultSegments.map { JsonPrimitive(it) }))
                    }
                },
                quality = Quality(
                    samplingRateHz = 1.0,
                    signalToNoise = null,
                    batteryLevel = null
                )
            )
            events.tryEmit(envelope)
        }
    }

    private fun sampleIso(sample: HKQuantitySample): String {
        val date = sample.startDate ?: return Clock.System.now().toString()
        return isoFormatter.stringFromDate(date) ?: Clock.System.now().toString()
    }
}
