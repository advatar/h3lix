using UnityEngine;

namespace H3LIX.Networking
{
    [CreateAssetMenu(fileName = "H3LIXClientConfig", menuName = "H3LIX/Client Config", order = 0)]
    public class H3LIXClientConfig : ScriptableObject
    {
        [Header("Backend")]
        [Tooltip("Base URL of FastAPI backend, e.g., http://192.168.0.10:8000")]
        public string baseUrl = "http://127.0.0.1:8000";

        [Tooltip("WebSocket relative path (appended to base URL)")]
        public string streamPath = "/v1/stream";

        [Tooltip("Optional auth token header (leave blank if unused)")]
        public string authToken = "";

        [Header("Timeouts")]
        public int httpTimeoutSeconds = 10;
        public int websocketPingSeconds = 20;
    }
}
