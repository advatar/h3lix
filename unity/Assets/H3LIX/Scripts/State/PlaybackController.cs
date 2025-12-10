using H3LIX.Networking.Dto;
using UnityEngine;

namespace H3LIX.State
{
    public class PlaybackController : MonoBehaviour
    {
        public InteractionMode Mode { get; private set; } = InteractionMode.Live;
        public ReplayResponse LastReplay { get; private set; }

        public void SetMode(InteractionMode mode)
        {
            Mode = mode;
        }

        public bool HasCache(int fromMs, int toMs) => LastReplay != null;
        public void SetReplayFrames(ReplayResponse replay)
        {
            LastReplay = replay;
        }
    }
}
