using System.Collections.Generic;
using H3LIX.Networking.Dto;
using H3LIX.State;
using UnityEngine;
using UnityEngine.UI;

namespace H3LIX.UI
{
    /// <summary>
    /// Simple timeline slider with markers; triggers replay fetch on drag end.
    /// </summary>
    public class TimelineController : MonoBehaviour
    {
        public Slider slider;
        public H3LIXStore store;
        public PlaybackController playback;
        public int windowMs = 10_000;

        private bool _dragging;

        private void Start()
        {
            if (slider != null)
            {
                slider.onValueChanged.AddListener(OnValueChanged);
            }
        }

        private void OnValueChanged(float value)
        {
            _dragging = true;
        }

        public async void OnPointerUp()
        {
            if (store == null || playback == null || slider == null) return;
            var center = (int)slider.value;
            var from = Mathf.Max(0, center - windowMs / 2);
            var to = center + windowMs / 2;
            var sessionId = store.Snapshot?.SessionId ?? (store.Sessions.Count > 0 ? store.Sessions[0].Id : null);
            if (string.IsNullOrEmpty(sessionId)) return;
            var replay = await store.FetchReplay(sessionId, from, to);
            playback.SetReplayFrames(replay);
            playback.SetMode(InteractionMode.Replay);
            _dragging = false;
        }
    }
}
