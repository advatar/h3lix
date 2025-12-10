using H3LIX.State;
using UnityEngine;
using UnityEngine.UI;

namespace H3LIX.UI
{
    /// <summary>
    /// Minimal UI wiring: buttons for snapshot/stream and status label.
    /// Attach to a Canvas and assign references.
    /// </summary>
    public class DashboardBootstrap : MonoBehaviour
    {
        public H3LIXStore store;
        public InputField sessionIdInput;
        public Button loadSnapshotButton;
        public Button startStreamButton;
        public Button stopStreamButton;
        public Text statusText;

        private void Start()
        {
            if (loadSnapshotButton != null) loadSnapshotButton.onClick.AddListener(LoadSnapshot);
            if (startStreamButton != null) startStreamButton.onClick.AddListener(StartStream);
            if (stopStreamButton != null) stopStreamButton.onClick.AddListener(StopStream);
            UpdateStatus("Idle");
        }

        private void Update()
        {
            if (store == null || statusText == null) return;
            var coherence = store.Noetic != null ? store.Noetic.GlobalCoherenceScore.ToString("F2") : "--";
            var preds = store.Symbolic?.Predictions?.Count ?? 0;
            statusText.text = $"Mode: {store.Mode} | Nodes: {store.Graph?.Nodes?.Count ?? 0} | Noetic: {coherence} | Preds: {preds} | Rogue/MUFS: {store.Rogues.Count}/{store.Mufs.Count}";
        }

        private void LoadSnapshot()
        {
            if (store == null) return;
            var id = sessionIdInput != null ? sessionIdInput.text : "";
            if (string.IsNullOrEmpty(id))
            {
                if (store.Sessions.Count > 0) id = store.Sessions[0].Id;
            }
            if (!string.IsNullOrEmpty(id))
            {
                store.LoadSnapshot(id);
            }
        }

        private void StartStream()
        {
            if (store == null) return;
            var id = sessionIdInput != null ? sessionIdInput.text : "";
            if (string.IsNullOrEmpty(id))
            {
                if (store.Sessions.Count > 0) id = store.Sessions[0].Id;
            }
            if (!string.IsNullOrEmpty(id))
            {
                store.StartStream(id);
            }
            UpdateStatus("Streaming");
        }

        private void StopStream()
        {
            if (store == null) return;
            store.StopStream();
            UpdateStatus("Stopped");
        }

        private void UpdateStatus(string msg)
        {
            if (statusText != null) statusText.text = msg;
        }
    }
}
