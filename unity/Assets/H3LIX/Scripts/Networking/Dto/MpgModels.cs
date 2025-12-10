using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace H3LIX.Networking.Dto
{
    public class MpgEvidencePreview
    {
        [JsonProperty("evidence_id")] public string EvidenceId { get; set; }
        [JsonProperty("snippet")] public string Snippet { get; set; }
        [JsonProperty("source_class")] public string SourceClass { get; set; }
        [JsonProperty("timestamp_utc")] public string TimestampUtc { get; set; }
    }

    public class MpgNodeMetrics
    {
        [JsonProperty("valence")] public double Valence { get; set; }
        [JsonProperty("intensity")] public double Intensity { get; set; }
        [JsonProperty("recency")] public double Recency { get; set; }
        [JsonProperty("stability")] public double Stability { get; set; }
    }

    public class MpgNode
    {
        [JsonProperty("id")] public string Id { get; set; }
        [JsonProperty("label")] public string Label { get; set; }
        [JsonProperty("description")] public string Description { get; set; }
        [JsonProperty("layer_tags")] public List<string> LayerTags { get; set; } = new();
        [JsonProperty("metrics")] public MpgNodeMetrics Metrics { get; set; }
        [JsonProperty("confidence")] public double Confidence { get; set; }
        [JsonProperty("importance")] public double Importance { get; set; }
        [JsonProperty("roles")] public List<string> Roles { get; set; } = new();
        [JsonProperty("evidence_preview")] public List<MpgEvidencePreview> EvidencePreview { get; set; } = new();
        [JsonProperty("reasoning_provenance")] public string ReasoningProvenance { get; set; }
    }

    public class MpgEdge
    {
        [JsonProperty("id")] public string Id { get; set; }
        [JsonProperty("source")] public string Source { get; set; }
        [JsonProperty("target")] public string Target { get; set; }
        [JsonProperty("type")] public string Type { get; set; }
        [JsonProperty("strength")] public double Strength { get; set; }
        [JsonProperty("confidence")] public double Confidence { get; set; }
    }

    public class MpgSegment
    {
        [JsonProperty("id")] public string Id { get; set; }
        [JsonProperty("label")] public string Label { get; set; }
        [JsonProperty("level")] public int Level { get; set; }
        [JsonProperty("member_node_ids")] public List<string> MemberNodeIds { get; set; } = new();
        [JsonProperty("cohesion")] public double Cohesion { get; set; }
        [JsonProperty("average_importance")] public double AverageImportance { get; set; }
        [JsonProperty("average_confidence")] public double AverageConfidence { get; set; }
        [JsonProperty("affective_load")] public double? AffectiveLoad { get; set; }
    }

    public enum MpgOperationKind
    {
        [JsonProperty("add_node")] AddNode,
        [JsonProperty("update_node")] UpdateNode,
        [JsonProperty("add_edge")] AddEdge,
        [JsonProperty("update_edge")] UpdateEdge,
        [JsonProperty("add_segment")] AddSegment,
        [JsonProperty("update_segment")] UpdateSegment
    }

    public class MpgOperation
    {
        [JsonProperty("kind")] public MpgOperationKind Kind { get; set; }
        [JsonProperty("node")] public MpgNode Node { get; set; }
        [JsonProperty("node_id")] public string NodeId { get; set; }
        [JsonProperty("edge")] public MpgEdge Edge { get; set; }
        [JsonProperty("edge_id")] public string EdgeId { get; set; }
        [JsonProperty("segment")] public MpgSegment Segment { get; set; }
        [JsonProperty("segment_id")] public string SegmentId { get; set; }
        [JsonProperty("patch")] public JObject Patch { get; set; }
    }

    public class MpgDeltaPayload
    {
        [JsonProperty("mpg_id")] public string MpgId { get; set; }
        [JsonProperty("level")] public int Level { get; set; }
        [JsonProperty("delta_id")] public string DeltaId { get; set; }
        [JsonProperty("operations")] public List<MpgOperation> Operations { get; set; }
    }

    public class SnapshotMpg
    {
        [JsonProperty("mpg_id")] public string MpgId { get; set; }
        [JsonProperty("level_summaries")] public List<MpgLevelSummary> LevelSummaries { get; set; }
        [JsonProperty("base_subgraph")] public MpgSubgraphResponse BaseSubgraph { get; set; }
    }

    public class MpgLevelSummary
    {
        [JsonProperty("level")] public int Level { get; set; }
        [JsonProperty("node_count")] public int NodeCount { get; set; }
        [JsonProperty("segment_count")] public int SegmentCount { get; set; }
    }

    public class MpgSubgraphResponse
    {
        [JsonProperty("mpg_id")] public string MpgId { get; set; }
        [JsonProperty("level")] public int Level { get; set; }
        [JsonProperty("center_node_id")] public string CenterNodeId { get; set; }
        [JsonProperty("nodes")] public List<MpgNode> Nodes { get; set; }
        [JsonProperty("edges")] public List<MpgEdge> Edges { get; set; }
        [JsonProperty("segments")] public List<MpgSegment> Segments { get; set; }
    }

    public class SnapshotResponse
    {
        [JsonProperty("session_id")] public string SessionId { get; set; }
        [JsonProperty("t_rel_ms")] public int TRelMs { get; set; }
        [JsonProperty("somatic")] public SomaticStatePayload Somatic { get; set; }
        [JsonProperty("symbolic")] public SymbolicStatePayload Symbolic { get; set; }
        [JsonProperty("noetic")] public NoeticStatePayload Noetic { get; set; }
        [JsonProperty("last_decision_cycle")] public DecisionCyclePayload LastDecisionCycle { get; set; }
        [JsonProperty("mpg")] public SnapshotMpg Mpg { get; set; }
    }
}
