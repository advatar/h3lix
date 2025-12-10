package com.h3lix.laiza

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.h3lix.streams.EventEnvelope
import com.h3lix.streams.InMemoryPendingEventDao
import com.h3lix.streams.PhaseOneController
import com.h3lix.streams.QueueManager
import com.h3lix.streams.StreamType
import com.h3lix.streams.StreamsApiClient
import com.h3lix.streams.airpodsSourceFor
import com.h3lix.streams.sampleEvent
import kotlinx.coroutines.launch
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

@Composable
fun App() {
    val json = remember { Json { prettyPrint = true; ignoreUnknownKeys = true; encodeDefaults = true } }
    val scope = rememberCoroutineScope()

    var participantId by remember { mutableStateOf("P-lab") }
    var sessionId by remember { mutableStateOf("S-lab") }
    var journalText by remember { mutableStateOf("") }
    var mood by remember { mutableStateOf(0f) }
    var status by remember { mutableStateOf("Idle") }
    var lastBatch by remember { mutableStateOf("[]") }
    var baseUrl by remember { mutableStateOf("http://localhost:8000") }

    val pendingDao = remember { InMemoryPendingEventDao() }
    val apiClient = remember(baseUrl) { StreamsApiClient(baseUrl.trimEnd('/'), json = json) }
    val client: suspend (List<EventEnvelope>) -> Unit = { events ->
        lastBatch = json.encodeToString(events)
        apiClient.postEvents(events)
        status = "Sent ${events.size} event(s)"
    }
    val queue = remember(baseUrl) { QueueManager(pendingDao, client, json) }
    val defaultSegments = remember { listOf("seg-phase1") }
    val airpodsSource = remember(participantId, sessionId) {
        airpodsSourceFor(participantId, sessionId, defaultSegments)
    }
    val controller = remember(participantId, sessionId, airpodsSource) {
        PhaseOneController(
            participantId = participantId,
            sessionId = sessionId,
            queue = queue,
            somaticSource = airpodsSource,
            defaultSegments = defaultSegments
        )
    }

    MaterialTheme {
        Surface(modifier = Modifier.fillMaxSize()) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(24.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp, Alignment.Top),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(text = "Phase 1 – iOS (AirPods Pro 3)", style = MaterialTheme.typography.headlineSmall)
                Text(text = "Stream HR/HRV + journaling + E1 tasks into EventEnvelope", style = MaterialTheme.typography.bodyMedium)

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    OutlinedTextField(
                        value = participantId,
                        onValueChange = { participantId = it },
                        label = { Text("Participant ID") },
                        modifier = Modifier.weight(1f)
                    )
                    OutlinedTextField(
                        value = sessionId,
                        onValueChange = { sessionId = it },
                        label = { Text("Session ID") },
                        modifier = Modifier.weight(1f)
                    )
                }

                OutlinedTextField(
                    value = baseUrl,
                    onValueChange = { baseUrl = it },
                    label = { Text("API Base URL") },
                    modifier = Modifier.fillMaxWidth()
                )

                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Button(onClick = {
                        scope.launch {
                            try {
                                apiClient.setConsent(participantId, scopes = listOf("wearables"))
                                status = "Consent set for $participantId"
                            } catch (t: Throwable) {
                                status = "Consent failed: ${t.message}"
                            }
                        }
                    }) { Text("Set consent") }
                    Button(onClick = {
                        scope.launch {
                            try {
                                queue.flush()
                                status = "Flushed queue"
                            } catch (t: Throwable) {
                                status = "Flush failed: ${t.message}"
                            }
                        }
                    }) { Text("Flush") }
                }

                Text(text = "Journal", style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(
                    value = journalText,
                    onValueChange = { journalText = it },
                    label = { Text("What happened?") },
                    modifier = Modifier.fillMaxWidth()
                )
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
                    Text("Mood ${"%.2f".format(mood)}", modifier = Modifier.weight(1f))
                    Slider(
                        value = mood,
                        onValueChange = { mood = it },
                        valueRange = -1f..1f,
                        modifier = Modifier.weight(2f)
                    )
                }
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Button(onClick = {
                        scope.launch {
                            controller.sendJournal(journalText, mood.toDouble())
                            controller.flush()
                        }
                        status = "Journal queued"
                    }) { Text("Send journal") }
                    Button(onClick = {
                        val ev = sampleEvent(participantId = participantId, source = "kmp-demo", streamType = StreamType.somatic)
                        scope.launch {
                            queue.enqueue(ev)
                            controller.flush()
                        }
                        status = "Synthetic somatic event queued"
                    }) { Text("Synthetic somatic") }
                }

                Text(text = "E1 task (2AFC)", style = MaterialTheme.typography.titleMedium)
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Button(onClick = {
                        scope.launch {
                            controller.sendTaskEvent(
                                trialId = "E1-001",
                                stimulus = "Choose safer option",
                                choice = "A",
                                rtMs = 720,
                                awarenessCondition = "FULL",
                                intuitionRating = 0.5
                            )
                            controller.flush()
                        }
                        status = "E1 task event queued"
                    }) { Text("Log task choice") }
                    Button(onClick = {
                        scope.launch { controller.flush() }
                        status = "Flushed queue"
                    }) { Text("Flush") }
                }

                Text(text = "AirPods stream", style = MaterialTheme.typography.titleMedium)
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Button(
                        enabled = airpodsSource != null,
                        onClick = {
                            controller.startSomatic()
                            status = if (airpodsSource != null) "AirPods stream started" else "AirPods not available on this platform"
                        }
                    ) { Text("Start HR/HRV") }
                    Button(
                        onClick = {
                            controller.stopSomatic()
                            status = "AirPods stream stopped"
                        }
                    ) { Text("Stop") }
                }

                Spacer(Modifier.height(8.dp))
                Text(text = "Status: $status", style = MaterialTheme.typography.bodyMedium)
                Text(text = "Last batch payload:", style = MaterialTheme.typography.titleSmall)
                Text(text = lastBatch, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
