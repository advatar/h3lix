using System;
using System.Collections.Concurrent;
using UnityEngine;

namespace H3LIX.Utilities
{
    public class ThreadDispatcher : MonoBehaviour
    {
        private static ThreadDispatcher _instance;
        private readonly ConcurrentQueue<Action> _queue = new();

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        private static void Init()
        {
            if (_instance != null) return;
            var go = new GameObject("H3LIXThreadDispatcher");
            _instance = go.AddComponent<ThreadDispatcher>();
            DontDestroyOnLoad(go);
        }

        public static void Enqueue(Action action)
        {
            _instance?._queue.Enqueue(action);
        }

        private void Update()
        {
            while (_queue.TryDequeue(out var action))
            {
                action?.Invoke();
            }
        }
    }
}
