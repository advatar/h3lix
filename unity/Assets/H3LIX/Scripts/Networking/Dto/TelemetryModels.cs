using System.Collections.Generic;
using Newtonsoft.Json;

namespace H3LIX.Networking.Dto
{
    public class SomaticAnticipatoryMarker
    {
        [JsonProperty("marker_type")] public string MarkerType { get; set; }
        [JsonProperty("lead_time_ms")] public int LeadTimeMs { get; set; }
        [JsonProperty("confidence")] public double Confidence { get; set; }
    }

    public class SomaticStatePayload
    {
        [JsonProperty("t_rel_ms")] public int TRelMs { get; set; }
        [JsonProperty("window_ms")] public int WindowMs { get; set; }
        [JsonProperty("features")] public Dictionary<string, double> Features { get; set; }
        [JsonProperty("innovation")] public Dictionary<string, double> Innovation { get; set; }
        [JsonProperty("covariance_diag")] public Dictionary<string, double> CovarianceDiag { get; set; }
        [JsonProperty("global_uncertainty_score")] public double? GlobalUncertaintyScore { get; set; }
        [JsonProperty("change_point")] public bool ChangePoint { get; set; }
        [JsonProperty("anomaly_score")] public double? AnomalyScore { get; set; }
        [JsonProperty("anticipatory_markers")] public List<SomaticAnticipatoryMarker> AnticipatoryMarkers { get; set; }
    }

    public class SymbolicBelief
    {
        [JsonProperty("id")] public string Id { get; set; }
        [JsonProperty("kind")] public string Kind { get; set; }
        [JsonProperty("label")] public string Label { get; set; }
        [JsonProperty("description")] public string Description { get; set; }
        [JsonProperty("valence")] public double? Valence { get; set; }
        [JsonProperty("intensity")] public double? Intensity { get; set; }
        [JsonProperty("recency")] public double? Recency { get; set; }
        [JsonProperty("stability")] public double? Stability { get; set; }
        [JsonProperty("confidence")] public double Confidence { get; set; }
        [JsonProperty("importance")] public double Importance { get; set; }
    }

    public class SymbolicPredictionOption
    {
        [JsonProperty("value")] public string Value { get; set; }
        [JsonProperty("probability")] public double Probability { get; set; }
    }

    public class SymbolicPrediction
    {
        [JsonProperty("id")] public string Id { get; set; }
        [JsonProperty("target_type")] public string TargetType { get; set; }
        [JsonProperty("horizon_ms")] public int? HorizonMs { get; set; }
        [JsonProperty("topk")] public List<SymbolicPredictionOption> TopK { get; set; } = new();
        [JsonProperty("brier_score")] public double? BrierScore { get; set; }
        [JsonProperty("realized_value")] public string RealizedValue { get; set; }
        [JsonProperty("realized_error")] public double? RealizedError { get; set; }
    }

    public class SymbolicUncertaintyRegion
    {
        [JsonProperty("label")] public string Label { get; set; }
        [JsonProperty("belief_ids")] public List<string> BeliefIds { get; set; } = new();
        [JsonProperty("comment")] public string Comment { get; set; }
    }

    public class SymbolicStatePayload
    {
        [JsonProperty("t_rel_ms")] public int TRelMs { get; set; }
        [JsonProperty("belief_revision_id")] public string BeliefRevisionId { get; set; }
        [JsonProperty("beliefs")] public List<SymbolicBelief> Beliefs { get; set; } = new();
        [JsonProperty("predictions")] public List<SymbolicPrediction> Predictions { get; set; } = new();
        [JsonProperty("uncertainty_regions")] public List<SymbolicUncertaintyRegion> UncertaintyRegions { get; set; } = new();
    }

    public class NoeticStreamCorrelation
    {
        [JsonProperty("stream_x")] public string StreamX { get; set; }
        [JsonProperty("stream_y")] public string StreamY { get; set; }
        [JsonProperty("r")] public double R { get; set; }
    }

    public class NoeticSpectrumBand
    {
        [JsonProperty("band_label")] public string BandLabel { get; set; }
        [JsonProperty("freq_range_hz")] public List<double> FreqRangeHz { get; set; }
        [JsonProperty("coherence_strength")] public double CoherenceStrength { get; set; }
    }

    public class NoeticIntuitiveAccuracyEstimate
    {
        [JsonProperty("p_better_than_baseline")] public double PBetterThanBaseline { get; set; }
        [JsonProperty("calibration_error")] public double? CalibrationError { get; set; }
    }

    public class NoeticStatePayload
    {
        [JsonProperty("t_rel_ms")] public int TRelMs { get; set; }
        [JsonProperty("window_ms")] public int WindowMs { get; set; }
        [JsonProperty("global_coherence_score")] public double GlobalCoherenceScore { get; set; }
        [JsonProperty("entropy_change")] public double EntropyChange { get; set; }
        [JsonProperty("stream_correlations")] public List<NoeticStreamCorrelation> StreamCorrelations { get; set; } = new();
        [JsonProperty("coherence_spectrum")] public List<NoeticSpectrumBand> CoherenceSpectrum { get; set; } = new();
        [JsonProperty("intuitive_accuracy_estimate")] public NoeticIntuitiveAccuracyEstimate IntuitiveAccuracyEstimate { get; set; }
    }

    public class DecisionAction
    {
        [JsonProperty("action_id")] public string ActionId { get; set; }
        [JsonProperty("label")] public string Label { get; set; }
        [JsonProperty("params")] public Dictionary<string, object> Params { get; set; }
    }

    public class DecisionOutcome
    {
        [JsonProperty("label")] public string Label { get; set; }
        [JsonProperty("metrics")] public Dictionary<string, double> Metrics { get; set; }
    }

    public class NoeticAdjustment
    {
        [JsonProperty("attention_gain")] public double? AttentionGain { get; set; }
        [JsonProperty("decision_threshold_delta")] public double? DecisionThresholdDelta { get; set; }
        [JsonProperty("learning_rate_delta")] public double? LearningRateDelta { get; set; }
    }

    public class StimulusRef
    {
        [JsonProperty("channel")] public string Channel { get; set; }
        [JsonProperty("ref_id")] public string RefId { get; set; }
    }

    public class DecisionCyclePayload
    {
        [JsonProperty("sork_cycle_id")] public string SorkCycleId { get; set; }
        [JsonProperty("decision_id")] public string DecisionId { get; set; }
        [JsonProperty("phase")] public string Phase { get; set; }
        [JsonProperty("phase_started_utc")] public string PhaseStartedUtc { get; set; }
        [JsonProperty("phase_ended_utc")] public string PhaseEndedUtc { get; set; }
        [JsonProperty("stimulus_refs")] public List<StimulusRef> StimulusRefs { get; set; }
        [JsonProperty("organism_belief_ids")] public List<string> OrganismBeliefIds { get; set; }
        [JsonProperty("response_action")] public DecisionAction ResponseAction { get; set; }
        [JsonProperty("consequence_outcome")] public DecisionOutcome ConsequenceOutcome { get; set; }
        [JsonProperty("noetic_adjustments")] public NoeticAdjustment NoeticAdjustments { get; set; }
    }

    public class RogueVariableImpactFactors
    {
        [JsonProperty("rate_of_change")] public double RateOfChange { get; set; }
        [JsonProperty("breadth_of_impact")] public double BreadthOfImpact { get; set; }
        [JsonProperty("amplification")] public double Amplification { get; set; }
        [JsonProperty("emotional_load")] public double EmotionalLoad { get; set; }
        [JsonProperty("gate_leverage")] public double? GateLeverage { get; set; }
        [JsonProperty("robustness")] public double? Robustness { get; set; }
    }

    public class RogueVariableShapleyStats
    {
        [JsonProperty("mean_abs_contrib")] public double MeanAbsContrib { get; set; }
        [JsonProperty("std_abs_contrib")] public double StdAbsContrib { get; set; }
        [JsonProperty("candidate_abs_contrib")] public double CandidateAbsContrib { get; set; }
        [JsonProperty("z_score")] public double ZScore { get; set; }
    }

    public class RogueVariableEventPayload
    {
        [JsonProperty("rogue_id")] public string RogueId { get; set; }
        [JsonProperty("mpg_id")] public string MpgId { get; set; }
        [JsonProperty("candidate_type")] public string CandidateType { get; set; }
        [JsonProperty("level_range")] public List<int> LevelRange { get; set; } = new();
        [JsonProperty("segment_ids")] public List<string> SegmentIds { get; set; } = new();
        [JsonProperty("pathway_nodes")] public List<string> PathwayNodes { get; set; } = new();
        [JsonProperty("shapley_stats")] public RogueVariableShapleyStats ShapleyStats { get; set; }
        [JsonProperty("potency_index")] public double PotencyIndex { get; set; }
        [JsonProperty("impact_factors")] public RogueVariableImpactFactors ImpactFactors { get; set; }
        [JsonProperty("t_rel_ms")] public int? TRelMs { get; set; }
    }

    public class DecisionUtility
    {
        [JsonProperty("choice")] public string Choice { get; set; }
        [JsonProperty("utility")] public Dictionary<string, double> Utility { get; set; }
    }

    public class MufsEventPayload
    {
        [JsonProperty("mufs_id")] public string MufsId { get; set; }
        [JsonProperty("decision_id")] public string DecisionId { get; set; }
        [JsonProperty("mpg_id")] public string MpgId { get; set; }
        [JsonProperty("t_rel_ms")] public int? TRelMs { get; set; }
        [JsonProperty("unawareness_types")] public List<string> UnawarenessTypes { get; set; } = new();
        [JsonProperty("input_unaware_refs")] public List<string> InputUnawareRefs { get; set; } = new();
        [JsonProperty("process_unaware_node_ids")] public List<string> ProcessUnawareNodeIds { get; set; } = new();
        [JsonProperty("decision_full")] public DecisionUtility DecisionFull { get; set; }
        [JsonProperty("decision_without_U")] public DecisionUtility DecisionWithoutU { get; set; }
        [JsonProperty("minimal")] public bool Minimal { get; set; }
        [JsonProperty("search_metadata")] public Dictionary<string, object> SearchMetadata { get; set; }
    }
}
