using System.Text;
using H3LIX.State;
using UnityEngine;
using UnityEngine.UI;

namespace H3LIX.UI
{
    /// <summary>
    /// Lightweight HUD that surfaces key telemetry fields from the store.
    /// Attach to a UI GameObject and assign references created in the sample scene.
    /// </summary>
    public class TelemetryHUD : MonoBehaviour
    {
        public H3LIXStore store;
        public Text text;

        private void Reset()
        {
            text = GetComponentInChildren<Text>();
        }

        private void Update()
        {
            if (store == null || text == null) return;

            var sb = new StringBuilder();
            sb.AppendLine($"t_rel: {store.LatestTRelMs} ms");
            sb.AppendLine($"Nodes: {store.Graph?.Nodes?.Count ?? 0} | Edges: {store.Graph?.Edges?.Count ?? 0}");

            if (store.Noetic != null)
            {
                sb.Append($"Noetic: {store.Noetic.GlobalCoherenceScore:F2}");
                if (store.Noetic.IntuitiveAccuracyEstimate != null)
                {
                    sb.Append($" | Intuition p>base: {store.Noetic.IntuitiveAccuracyEstimate.PBetterThanBaseline:F2}");
                }
                sb.AppendLine();
            }

            if (store.Symbolic != null)
            {
                var predCount = store.Symbolic.Predictions?.Count ?? 0;
                var regionCount = store.Symbolic.UncertaintyRegions?.Count ?? 0;
                sb.AppendLine($"Symbolic: {store.Symbolic.Beliefs?.Count ?? 0} beliefs | {predCount} preds | {regionCount} regions");
            }

            sb.AppendLine($"Rogue events: {store.Rogues.Count} | MUFS: {store.Mufs.Count}");
            text.text = sb.ToString();
        }
    }
}
