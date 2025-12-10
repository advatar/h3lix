using System;
using Newtonsoft.Json;
using Newtonsoft.Json.Converters;
using Newtonsoft.Json.Linq;

namespace H3LIX.Networking.Dto
{
    [JsonConverter(typeof(StringEnumConverter))]
    public enum MessageType
    {
        [JsonProperty("somatic_state")] SomaticState,
        [JsonProperty("symbolic_state")] SymbolicState,
        [JsonProperty("noetic_state")] NoeticState,
        [JsonProperty("decision_cycle")] DecisionCycle,
        [JsonProperty("mpg_delta")] MpgDelta,
        [JsonProperty("rogue_variable_event")] RogueVariableEvent,
        [JsonProperty("mufs_event")] MufsEvent
    }

    [JsonConverter(typeof(StringEnumConverter))]
    public enum SourceLayer
    {
        [JsonProperty("Somatic")] Somatic,
        [JsonProperty("Symbolic")] Symbolic,
        [JsonProperty("Noetic")] Noetic,
        [JsonProperty("MirrorCore")] MirrorCore,
        [JsonProperty("MPG")] MPG
    }

    public class AnyTelemetryEnvelope
    {
        [JsonProperty("v")] public string Version { get; set; }
        [JsonProperty("message_type")] public MessageType MessageType { get; set; }
        [JsonProperty("timestamp_utc")] public string TimestampUtc { get; set; }
        [JsonProperty("experiment_id")] public string ExperimentId { get; set; }
        [JsonProperty("session_id")] public string SessionId { get; set; }
        [JsonProperty("subject_id")] public string SubjectId { get; set; }
        [JsonProperty("run_id")] public string RunId { get; set; }
        [JsonProperty("sork_cycle_id")] public string SorkCycleId { get; set; }
        [JsonProperty("decision_id")] public string DecisionId { get; set; }
        [JsonProperty("source_layer")] public SourceLayer SourceLayer { get; set; }
        [JsonProperty("sequence")] public int Sequence { get; set; }
        [JsonProperty("payload")] public JObject Payload { get; set; }

        public T GetPayload<T>()
        {
            return Payload != null ? Payload.ToObject<T>() : default;
        }
    }
}
