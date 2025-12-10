using System.IO;
using H3LIX.Bootstrap;
using H3LIX.Networking;
using H3LIX.State;
using H3LIX.UI;
using H3LIX.Visuals;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using UnityEngine.SceneManagement;

namespace H3LIX.EditorTools
{
    /// <summary>
    /// Menu item to generate a sample scene with H3LIX components wired up.
    /// </summary>
    public static class CreateSampleScene
    {
        private const string ConfigPath = "Assets/Resources/H3LIXClientConfig.asset";

        [MenuItem("H3LIX/Create Sample Scene")]
        public static void Generate()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
            scene.name = "H3LIXSample";

            var config = EnsureConfig();

            // Root
            var root = new GameObject("H3LIXRoot");
            var store = root.AddComponent<H3LIXStore>();
            store.Config = config;
            var playback = root.AddComponent<PlaybackController>();
            var bootstrap = root.AddComponent<H3LIXBootstrap>();
            bootstrap.clientConfig = config;
            bootstrap.store = store;
            bootstrap.playback = playback;

            // Graph
            var graph = new GameObject("Graph");
            graph.transform.SetParent(root.transform);
            var graphRenderer = graph.AddComponent<GraphRenderer>();
            graphRenderer.store = store;
            graphRenderer.nodeMaterial = CreateMaterial("NodeMat", Color.cyan);
            graphRenderer.edgeMaterial = CreateMaterial("EdgeMat", Color.gray);

            // Coherence wall placeholder
            var wall = new GameObject("CoherenceWall");
            wall.transform.SetParent(root.transform);
            var wallRenderer = wall.AddComponent<CoherenceWallRenderer>();
            wallRenderer.store = store;
            wallRenderer.barMaterial = CreateMaterial("WallBarMat", Color.green);

            // HUD overlay
            var hud = CreateHud(store);
            hud.transform.SetParent(root.transform);

            // Camera positioning
            var cam = Camera.main;
            if (cam != null)
            {
                cam.transform.position = new Vector3(0, 1.5f, -2f);
                cam.transform.LookAt(root.transform);
            }

            // Save scene
            var folder = "Assets/H3LIX/Scenes";
            if (!Directory.Exists(folder)) Directory.CreateDirectory(folder);
            var scenePath = Path.Combine(folder, "H3LIXSample.unity");
            EditorSceneManager.SaveScene(scene, scenePath);
            AssetDatabase.Refresh();
            Debug.Log($"H3LIX sample scene created at {scenePath}");
        }

        private static H3LIXClientConfig EnsureConfig()
        {
            var dir = Path.GetDirectoryName(ConfigPath);
            if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);
            var existing = AssetDatabase.LoadAssetAtPath<H3LIXClientConfig>(ConfigPath);
            if (existing != null) return existing;
            var config = ScriptableObject.CreateInstance<H3LIXClientConfig>();
            AssetDatabase.CreateAsset(config, ConfigPath);
            AssetDatabase.SaveAssets();
            return config;
        }

        private static GameObject CreateHud(H3LIXStore store)
        {
            var canvasGo = new GameObject("HUDCanvas");
            var canvas = canvasGo.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvasGo.AddComponent<CanvasScaler>();
            canvasGo.AddComponent<GraphicRaycaster>();

            // Panel
            var panel = new GameObject("HUDPanel");
            panel.transform.SetParent(canvasGo.transform, false);
            var rect = panel.AddComponent<RectTransform>();
            rect.anchorMin = new Vector2(0f, 1f);
            rect.anchorMax = new Vector2(0f, 1f);
            rect.pivot = new Vector2(0f, 1f);
            rect.anchoredPosition = new Vector2(20f, -20f);
            rect.sizeDelta = new Vector2(420f, 140f);

            var img = panel.AddComponent<Image>();
            img.color = new Color(0f, 0f, 0f, 0.4f);

            // Text
            var textGo = new GameObject("HUDText");
            textGo.transform.SetParent(panel.transform, false);
            var textRect = textGo.AddComponent<RectTransform>();
            textRect.anchorMin = new Vector2(0f, 0f);
            textRect.anchorMax = new Vector2(1f, 1f);
            textRect.offsetMin = new Vector2(10f, 10f);
            textRect.offsetMax = new Vector2(-10f, -10f);

            var text = textGo.AddComponent<Text>();
            text.font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            text.fontSize = 16;
            text.color = Color.white;
            text.alignment = TextAnchor.UpperLeft;

            var hud = panel.AddComponent<TelemetryHUD>();
            hud.store = store;
            hud.text = text;

            // Event system (safe for UI interaction if needed)
            if (Object.FindObjectOfType<EventSystem>() == null)
            {
                var es = new GameObject("EventSystem");
                es.AddComponent<EventSystem>();
                es.AddComponent<StandaloneInputModule>();
                es.transform.SetParent(canvasGo.transform, false);
            }

            return canvasGo;
        }

        private static Material CreateMaterial(string name, Color color)
        {
            var mat = new Material(Shader.Find("Standard"));
            mat.color = color;
            mat.name = name;
            return mat;
        }
    }
}
