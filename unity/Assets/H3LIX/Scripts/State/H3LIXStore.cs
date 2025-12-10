using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using H3LIX.Networking;
using H3LIX.Networking.Dto;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace H3LIX.State
{
    public class H3LIXStore : MonoBehaviour
    {
        public H3LIXClientConfig Config;
        public H3LIXClient Client { get; private set; }

        public List<SessionSummary> Sessions { get; private set; } = new();
        public List<Cohort> Cohorts { get; private set; } = new();
        public SnapshotResponse Snapshot { get; private set; }
        public SomaticStatePayload Somatic { get; private set; }
        public SymbolicStatePayload Symbolic { get; private set; }
        public NoeticStatePayload Noetic { get; private set; }
        public DecisionCyclePayload Decision { get; private set; }
        public List<RogueVariableEventPayload> Rogues { get; private set; } = new();
        public List<MufsEventPayload> Mufs { get; private set; } = new();
        public MpgGraphState Graph { get; private set; } = new();
        public InteractionMode Mode { get; private set; } = InteractionMode.Live;
        public int LatestTRelMs { get; private set; }

        private void Awake()
        {
            Client = new H3LIXClient(Config);
        }

        private void OnDestroy()
        {
            Client?.Dispose();
        }

        private void Update()
        {
            // Drain inbound queue on main thread
            while (Client != null && Client.Inbound.TryDequeue(out var env))
            {
                Apply(env);
            }
        }

        public async void RefreshSessions()
        {
            try
            {
                Sessions = await Client.FetchSessions();
            }
            catch (System.Exception ex)
            {
                Debug.LogWarning($"RefreshSessions failed: {ex}");
            }
        }

        public async void RefreshCohorts()
        {
            try
            {
                Cohorts = await Client.FetchCohorts();
            }
            catch (System.Exception ex)
            {
                Debug.LogWarning($"RefreshCohorts failed: {ex}");
            }
        }

        public async void LoadSnapshot(string sessionId)
        {
            try
            {
                Snapshot = await Client.FetchSnapshot(sessionId);
                Somatic = Snapshot.Somatic;
                Symbolic = Snapshot.Symbolic;
                Noetic = Snapshot.Noetic;
                Decision = Snapshot.LastDecisionCycle;
                Graph = MpgGraphState.FromSnapshot(Snapshot.Mpg);
                LatestTRelMs = Mathf.Max(LatestTRelMs, Snapshot.TRelMs);
            }
            catch (System.Exception ex)
            {
                Debug.LogWarning($"LoadSnapshot failed: {ex}");
            }
        }

        public async void StartStream(string sessionId)
        {
            try
            {
                await Client.OpenStream(sessionId);
            }
            catch (System.Exception ex)
            {
                Debug.LogWarning($"StartStream failed: {ex}");
            }
        }

        public async void StopStream()
        {
            await Client.CloseStream();
        }

        public async Task<ReplayResponse> FetchReplay(string sessionId, int fromMs, int toMs)
        {
            return await Client.FetchReplay(sessionId, fromMs, toMs);
        }

        private void Apply(AnyTelemetryEnvelope env)
        {
            try
            {
                switch (env.MessageType)
                {
                    case MessageType.SomaticState:
                        Somatic = env.GetPayload<SomaticStatePayload>();
                        UpdateLatestTime(Somatic?.TRelMs);
                        break;
                    case MessageType.SymbolicState:
                        Symbolic = env.GetPayload<SymbolicStatePayload>();
                        UpdateLatestTime(Symbolic?.TRelMs);
                        break;
                    case MessageType.NoeticState:
                        Noetic = env.GetPayload<NoeticStatePayload>();
                        UpdateLatestTime(Noetic?.TRelMs);
                        break;
                    case MessageType.DecisionCycle:
                        Decision = env.GetPayload<DecisionCyclePayload>();
                        break;
                    case MessageType.MpgDelta:
                        var delta = env.GetPayload<MpgDeltaPayload>();
                        if (delta != null)
                        {
                            Graph.ApplyDelta(delta);
                        }
                        break;
                    case MessageType.RogueVariableEvent:
                        var rv = env.GetPayload<RogueVariableEventPayload>();
                        if (rv != null)
                        {
                            Rogues.Insert(0, rv);
                            if (Rogues.Count > 50) Rogues.RemoveAt(Rogues.Count - 1);
                        }
                        break;
                    case MessageType.MufsEvent:
                        var mufs = env.GetPayload<MufsEventPayload>();
                        if (mufs != null)
                        {
                            Mufs.Insert(0, mufs);
                            if (Mufs.Count > 50) Mufs.RemoveAt(Mufs.Count - 1);
                        }
                        break;
                }
            }
            catch (System.Exception ex)
            {
                Debug.LogWarning($"Failed to apply telemetry envelope: {ex}");
            }
        }

        private void UpdateLatestTime(int? tRelMs)
        {
            if (tRelMs.HasValue)
            {
                LatestTRelMs = Mathf.Max(LatestTRelMs, tRelMs.Value);
            }
        }
    }

    public class MpgGraphState
    {
        public string MpgId;
        public int Level;
        public string LastDeltaId;
        public List<MpgLevelSummary> LevelSummaries = new();
        public Dictionary<string, MpgNode> Nodes = new();
        public Dictionary<string, MpgEdge> Edges = new();
        public Dictionary<string, MpgSegment> Segments = new();

        public static MpgGraphState FromSnapshot(SnapshotMpg snap)
        {
            if (snap == null || snap.BaseSubgraph == null) return new MpgGraphState();
            var g = new MpgGraphState
            {
                MpgId = snap.MpgId,
                Level = snap.BaseSubgraph.Level,
                LevelSummaries = snap.LevelSummaries ?? new List<MpgLevelSummary>()
            };
            if (snap.BaseSubgraph.Nodes != null)
            {
                foreach (var n in snap.BaseSubgraph.Nodes) g.Nodes[n.Id] = n;
            }
            if (snap.BaseSubgraph.Edges != null)
            {
                foreach (var e in snap.BaseSubgraph.Edges) g.Edges[e.Id] = e;
            }
            if (snap.BaseSubgraph.Segments != null)
            {
                foreach (var s in snap.BaseSubgraph.Segments) g.Segments[s.Id] = s;
            }
            return g;
        }

        public void ApplyDelta(MpgDeltaPayload delta)
        {
            if (delta == null) return;
            MpgId = string.IsNullOrEmpty(delta.MpgId) ? MpgId : delta.MpgId;
            Level = delta.Level;
            LastDeltaId = delta.DeltaId;

            foreach (var op in delta.Operations ?? Enumerable.Empty<MpgOperation>())
            {
                switch (op.Kind)
                {
                    case MpgOperationKind.AddNode:
                        if (op.Node != null) Nodes[op.Node.Id] = op.Node;
                        break;
                    case MpgOperationKind.UpdateNode:
                        if (op.Node != null) Nodes[op.Node.Id] = op.Node;
                        else if (op.NodeId != null && Nodes.TryGetValue(op.NodeId, out var existingNode))
                        {
                            var mergedNode = MergeNode(existingNode, op.Patch);
                            if (mergedNode != null) Nodes[op.NodeId] = mergedNode;
                        }
                        break;
                    case MpgOperationKind.AddEdge:
                        if (op.Edge != null) Edges[op.Edge.Id] = op.Edge;
                        break;
                    case MpgOperationKind.UpdateEdge:
                        if (op.Edge != null) Edges[op.Edge.Id] = op.Edge;
                        else if (op.EdgeId != null && Edges.TryGetValue(op.EdgeId, out var existingEdge))
                        {
                            var mergedEdge = MergeEdge(existingEdge, op.Patch);
                            if (mergedEdge != null) Edges[op.EdgeId] = mergedEdge;
                        }
                        break;
                    case MpgOperationKind.AddSegment:
                        if (op.Segment != null) Segments[op.Segment.Id] = op.Segment;
                        break;
                    case MpgOperationKind.UpdateSegment:
                        if (op.Segment != null) Segments[op.Segment.Id] = op.Segment;
                        else if (op.SegmentId != null && Segments.TryGetValue(op.SegmentId, out var existingSegment))
                        {
                            var mergedSeg = MergeSegment(existingSegment, op.Patch);
                            if (mergedSeg != null) Segments[op.SegmentId] = mergedSeg;
                        }
                        break;
                }
            }
        }

        private static MpgNode MergeNode(MpgNode current, JObject patch)
        {
            if (current == null || patch == null) return current;
            var metrics = MergeMetrics(current.Metrics, patch.TryGetObject("metrics"));
            return new MpgNode
            {
                Id = current.Id,
                Label = patch.TryGetString("label", current.Label),
                Description = patch.TryGetString("description", current.Description),
                LayerTags = current.LayerTags,
                Metrics = metrics,
                Confidence = patch.TryGetDouble("confidence", current.Confidence),
                Importance = patch.TryGetDouble("importance", current.Importance),
                Roles = patch.TryGetStringList("roles", current.Roles),
                EvidencePreview = current.EvidencePreview,
                ReasoningProvenance = current.ReasoningProvenance
            };
        }

        private static MpgEdge MergeEdge(MpgEdge current, JObject patch)
        {
            if (current == null || patch == null) return current;
            return new MpgEdge
            {
                Id = current.Id,
                Source = current.Source,
                Target = current.Target,
                Type = current.Type,
                Strength = patch.TryGetDouble("strength", current.Strength),
                Confidence = patch.TryGetDouble("confidence", current.Confidence)
            };
        }

        private static MpgSegment MergeSegment(MpgSegment current, JObject patch)
        {
            if (current == null || patch == null) return current;
            return new MpgSegment
            {
                Id = current.Id,
                Label = current.Label,
                Level = current.Level,
                MemberNodeIds = current.MemberNodeIds,
                Cohesion = patch.TryGetDouble("cohesion", current.Cohesion),
                AverageImportance = patch.TryGetDouble("average_importance", current.AverageImportance),
                AverageConfidence = patch.TryGetDouble("average_confidence", current.AverageConfidence),
                AffectiveLoad = patch.TryGetNullableDouble("affective_load", current.AffectiveLoad)
            };
        }

        private static MpgNodeMetrics MergeMetrics(MpgNodeMetrics current, JObject patch)
        {
            if (current == null || patch == null) return current;
            return new MpgNodeMetrics
            {
                Valence = patch.TryGetDouble("valence", current.Valence),
                Intensity = patch.TryGetDouble("intensity", current.Intensity),
                Recency = patch.TryGetDouble("recency", current.Recency),
                Stability = patch.TryGetDouble("stability", current.Stability)
            };
        }
    }

    internal static class JObjectExtensions
    {
        public static double TryGetDouble(this JObject obj, string prop, double fallback)
        {
            if (obj == null) return fallback;
            var token = obj[prop];
            if (token != null && double.TryParse(token.ToString(), out var value)) return value;
            return fallback;
        }

        public static double? TryGetNullableDouble(this JObject obj, string prop, double? fallback)
        {
            if (obj == null) return fallback;
            var token = obj[prop];
            if (token == null) return fallback;
            if (double.TryParse(token.ToString(), out var value)) return value;
            return fallback;
        }

        public static string TryGetString(this JObject obj, string prop, string fallback)
        {
            if (obj == null) return fallback;
            var token = obj[prop];
            return token != null ? token.ToString() : fallback;
        }

        public static List<string> TryGetStringList(this JObject obj, string prop, List<string> fallback)
        {
            if (obj == null) return fallback;
            if (obj[prop] is JArray arr)
            {
                return arr.Values<string>().ToList();
            }
            return fallback;
        }

        public static JObject TryGetObject(this JObject obj, string prop)
        {
            return obj?[prop] as JObject;
        }
    }
}
