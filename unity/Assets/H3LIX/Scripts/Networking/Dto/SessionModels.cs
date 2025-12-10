using System.Collections.Generic;
using Newtonsoft.Json;

namespace H3LIX.Networking.Dto
{
    public class SessionSummary
    {
        [JsonProperty("session_id")] public string Id { get; set; }
        [JsonProperty("experiment_id")] public string ExperimentId { get; set; }
        [JsonProperty("subject_id")] public string SubjectId { get; set; }
        [JsonProperty("status")] public string Status { get; set; }
        [JsonProperty("started_utc")] public string StartedUtc { get; set; }
        [JsonProperty("ended_utc")] public string EndedUtc { get; set; }
    }

    public class Cohort
    {
        [JsonProperty("cohort_id")] public string Id { get; set; }
        [JsonProperty("name")] public string Name { get; set; }
        [JsonProperty("description")] public string Description { get; set; }
        [JsonProperty("member_sessions")] public List<string> MemberSessions { get; set; } = new();
        [JsonProperty("created_utc")] public string CreatedUtc { get; set; }
    }

    public class NoeticSample
    {
        [JsonProperty("t_rel_ms")] public int TRelMs { get; set; }
        [JsonProperty("global_coherence_score")] public double GlobalCoherenceScore { get; set; }
        [JsonProperty("entropy_change")] public double EntropyChange { get; set; }
        [JsonProperty("band_strengths")] public List<double> BandStrengths { get; set; } = new();
    }

    public class SubjectNoeticSeries
    {
        [JsonProperty("session_id")] public string Id { get; set; }
        [JsonProperty("subject_label")] public string SubjectLabel { get; set; }
        [JsonProperty("samples")] public List<NoeticSample> Samples { get; set; } = new();
    }

    public class GroupNoeticSample
    {
        [JsonProperty("t_rel_ms")] public int TRelMs { get; set; }
        [JsonProperty("mean_global_coherence")] public double MeanGlobalCoherence { get; set; }
        [JsonProperty("dispersion_global_coherence")] public double DispersionGlobalCoherence { get; set; }
        [JsonProperty("band_sync_index")] public List<double> BandSyncIndex { get; set; } = new();
    }

    public class CohortNoeticSummary
    {
        [JsonProperty("cohort_id")] public string CohortId { get; set; }
        [JsonProperty("members")] public List<SubjectNoeticSeries> Members { get; set; } = new();
        [JsonProperty("group")] public List<GroupNoeticSample> Group { get; set; } = new();
    }
}
