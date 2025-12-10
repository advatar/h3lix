using System.Collections.Generic;
using System.Linq;
using H3LIX.Networking.Dto;
using H3LIX.State;
using UnityEngine;

namespace H3LIX.Visuals
{
    /// <summary>
    /// Simple coherence wall: bars for subjects, line for group ribbon.
    /// Attach to a GameObject and assign the store; create child cubes for bars dynamically.
    /// </summary>
    public class CoherenceWallRenderer : MonoBehaviour
    {
        public H3LIXStore store;
        public Material barMaterial;
        public float barWidth = 0.05f;
        public float barSpacing = 0.08f;
        public int maxSubjects = 8;

        private readonly List<GameObject> _bars = new();

        private void Update()
        {
            if (store == null || store.Cohorts == null || store.Cohorts.Count == 0) return;
            // Use first cohort for now
            // This renderer expects NoeticSummary to be fetched separately if needed
        }

        public void RenderSummary(CohortNoeticSummary summary)
        {
            ClearBars();
            if (summary?.Members == null) return;
            int idx = 0;
            foreach (var member in summary.Members.Take(maxSubjects))
            {
                var meanC = MeanCoherence(member.Samples);
                var bar = GameObject.CreatePrimitive(PrimitiveType.Cube);
                bar.transform.SetParent(transform, false);
                bar.transform.localPosition = new Vector3(idx * barSpacing, (float)meanC * 0.5f, 0);
                bar.transform.localScale = new Vector3(barWidth, Mathf.Max(0.01f, (float)meanC), barWidth);
                if (barMaterial != null) bar.GetComponent<Renderer>().material = barMaterial;
                _bars.Add(bar);
                idx++;
            }
        }

        private double MeanCoherence(List<NoeticSample> samples)
        {
            if (samples == null || samples.Count == 0) return 0;
            double sum = 0;
            foreach (var s in samples) sum += s.GlobalCoherenceScore;
            return sum / samples.Count;
        }

        private void ClearBars()
        {
            foreach (var b in _bars) Destroy(b);
            _bars.Clear();
        }
    }
}
