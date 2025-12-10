using System.Collections.Generic;
using Newtonsoft.Json;

namespace H3LIX.Networking.Dto
{
    public class ReplayResponse
    {
        [JsonProperty("session_id")] public string SessionId { get; set; }
        [JsonProperty("from_ms")] public int FromMs { get; set; }
        [JsonProperty("to_ms")] public int ToMs { get; set; }
        [JsonProperty("messages")] public List<AnyTelemetryEnvelope> Messages { get; set; }
    }
}
