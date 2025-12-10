using System.Collections.Generic;
using Newtonsoft.Json;

namespace H3LIX.Networking.Dto
{
    public class MpgEchoMember
    {
        [JsonProperty("session_id")] public string SessionId { get; set; }
        [JsonProperty("segment_id")] public string SegmentId { get; set; }
    }

    public class MpgEchoWindow
    {
        [JsonProperty("trial_id")] public string TrialId { get; set; }
        [JsonProperty("t_rel_ms_start")] public int TRelMsStart { get; set; }
        [JsonProperty("t_rel_ms_end")] public int TRelMsEnd { get; set; }
    }

    public class MpgEchoGroup
    {
        [JsonProperty("echo_id")] public string Id { get; set; }
        [JsonProperty("label")] public string Label { get; set; }
        [JsonProperty("member_segments")] public List<MpgEchoMember> MemberSegments { get; set; } = new();
        [JsonProperty("consistency_score")] public double ConsistencyScore { get; set; }
        [JsonProperty("occurrence_windows")] public List<MpgEchoWindow> OccurrenceWindows { get; set; } = new();
    }

    public class CohortMpgEchoResponse
    {
        [JsonProperty("cohort_id")] public string CohortId { get; set; }
        [JsonProperty("echoes")] public List<MpgEchoGroup> Echoes { get; set; } = new();
    }
}
