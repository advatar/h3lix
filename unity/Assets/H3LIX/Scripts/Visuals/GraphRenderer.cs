using System.Collections.Generic;
using H3LIX.Networking.Dto;
using H3LIX.State;
using UnityEngine;

namespace H3LIX.Visuals
{
    /// <summary>
    /// Lightweight MPG graph renderer using spheres and line renderers.
    /// Attach to a GameObject and assign a H3LIXStore reference.
    /// </summary>
    public class GraphRenderer : MonoBehaviour
    {
        public H3LIXStore store;
        public Material nodeMaterial;
        public Material edgeMaterial;
        public float nodeScale = 0.05f;
        public float edgeWidth = 0.005f;
        public int maxNodes = 500;

        private readonly Dictionary<string, GameObject> _nodeObjects = new();
        private readonly Dictionary<string, LineRenderer> _edgeObjects = new();

        private void Update()
        {
            if (store == null || store.Graph == null) return;
            RenderNodes();
            RenderEdges();
        }

        private void RenderNodes()
        {
            int count = 0;
            foreach (var kvp in store.Graph.Nodes)
            {
                if (count++ > maxNodes) break;
                var node = kvp.Value;
                if (!_nodeObjects.TryGetValue(node.Id, out var go))
                {
                    go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                    go.transform.SetParent(transform, false);
                    go.transform.localScale = Vector3.one * nodeScale;
                    if (nodeMaterial != null) go.GetComponent<Renderer>().material = nodeMaterial;
                    _nodeObjects[node.Id] = go;
                }
                go.transform.localPosition = LayoutPosition(node);
                var color = ImportanceColor(node.Importance, node.Metrics?.Valence ?? 0);
                var renderer = go.GetComponent<Renderer>();
                if (renderer != null && renderer.material.HasProperty("_Color"))
                {
                    renderer.material.color = color;
                }
            }
        }

        private void RenderEdges()
        {
            int count = 0;
            foreach (var kvp in store.Graph.Edges)
            {
                if (count++ > maxNodes * 2) break;
                var edge = kvp.Value;
                if (!store.Graph.Nodes.TryGetValue(edge.Source, out var src) ||
                    !store.Graph.Nodes.TryGetValue(edge.Target, out var dst))
                {
                    continue;
                }
                if (!_edgeObjects.TryGetValue(edge.Id, out var lr))
                {
                    var go = new GameObject($"edge-{edge.Id}");
                    go.transform.SetParent(transform, false);
                    lr = go.AddComponent<LineRenderer>();
                    lr.useWorldSpace = false;
                    lr.widthMultiplier = edgeWidth;
                    lr.positionCount = 2;
                    if (edgeMaterial != null) lr.material = edgeMaterial;
                    _edgeObjects[edge.Id] = lr;
                }
                lr.SetPosition(0, LayoutPosition(src));
                lr.SetPosition(1, LayoutPosition(dst));
                var color = ImportanceColor(edge.Strength, 0);
                lr.startColor = color;
                lr.endColor = color;
            }
        }

        private Vector3 LayoutPosition(MpgNode node)
        {
            // Simple deterministic layout based on hash + level
            var h = node.Id.GetHashCode();
            float x = Mathf.Sin(h) * 0.5f;
            float z = Mathf.Cos(h) * 0.5f;
            float y = node.Metrics?.Stability != null ? (float)node.Metrics.Stability * 0.2f : 0;
            return new Vector3(x, y, z);
        }

        private Color ImportanceColor(double importance, double valence)
        {
            float t = Mathf.Clamp01((float)importance);
            var baseColor = Color.Lerp(Color.gray, Color.cyan, t);
            if (valence < 0) baseColor = Color.Lerp(baseColor, Color.red, (float)(-valence));
            else baseColor = Color.Lerp(baseColor, Color.green, (float)valence);
            baseColor.a = 0.8f;
            return baseColor;
        }
    }
}
