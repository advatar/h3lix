using System.Linq;
using H3LIX.Networking;
using H3LIX.State;
using UnityEngine;

namespace H3LIX.Bootstrap
{
    /// <summary>
    /// Simple bootstrapper: refreshes sessions, loads the first snapshot, and starts streaming.
    /// Attach this to a GameObject in the scene and assign references in the inspector.
    /// </summary>
    public class H3LIXBootstrap : MonoBehaviour
    {
        [Header("References")]
        public H3LIXClientConfig clientConfig;
        public H3LIXStore store;
        public PlaybackController playback;

        private async void Start()
        {
            if (store == null || clientConfig == null)
            {
                Debug.LogError("H3LIXBootstrap missing references.");
                return;
            }

            // refresh sessions and auto-pick first
            store.RefreshSessions();
            await System.Threading.Tasks.Task.Delay(500); // allow HTTP fetch
            var sessionId = store.Sessions.FirstOrDefault()?.Id;
            if (!string.IsNullOrEmpty(sessionId))
            {
                store.LoadSnapshot(sessionId);
                store.StartStream(sessionId);
            }
            else
            {
                Debug.LogWarning("No sessions available to start stream.");
            }
        }
    }
}
