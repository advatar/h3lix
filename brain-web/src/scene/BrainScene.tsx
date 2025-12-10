import { Line, OrbitControls, Sparkles } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { VisualEdge, VisualNode } from "../types";

type SceneProps = {
  nodes: VisualNode[];
  edges: VisualEdge[];
  selectedId?: string | null;
  onSelect?: (nodeId: string) => void;
};

const NodeCloud = ({
  nodes,
  selectedId,
  onSelect,
}: {
  nodes: VisualNode[];
  selectedId?: string | null;
  onSelect?: (nodeId: string) => void;
}) => {
  return (
    <>
      {nodes.map((node) => (
        <mesh
          key={node.id}
          position={[node.position.x * 10, node.position.y * 10, node.position.z * 10]}
          onClick={() => onSelect?.(node.id)}
          scale={node.id === selectedId ? 1.25 : 1}
        >
          <sphereGeometry args={[Math.max(0.08, node.size * 0.08), 24, 24]} />
          <meshStandardMaterial
            color={node.color}
            emissive={node.color}
            emissiveIntensity={0.35 + node.confidence * 0.6 + (node.id === selectedId ? 0.4 : 0)}
            roughness={0.3}
            metalness={0.15}
          />
        </mesh>
      ))}
    </>
  );
};

const EdgeLines = ({
  edges,
  nodes,
  selectedId,
}: {
  edges: VisualEdge[];
  nodes: VisualNode[];
  selectedId?: string | null;
}) => {
  const nodeIndex = new Map(nodes.map((n) => [n.id, n]));
  return (
    <>
      {edges.map((edge) => {
        const a = nodeIndex.get(edge.src);
        const b = nodeIndex.get(edge.dst);
        if (!a || !b) return null;
        return (
          <Line
            key={`${edge.src}-${edge.dst}`}
            points={[
              [a.position.x * 10, a.position.y * 10, a.position.z * 10],
              [b.position.x * 10, b.position.y * 10, b.position.z * 10],
            ]}
            color={edge.color}
            lineWidth={1.5 + Math.abs(edge.strength) * 1.5 + (selectedId && (edge.src === selectedId || edge.dst === selectedId) ? 1 : 0)}
            transparent
            opacity={selectedId && (edge.src === selectedId || edge.dst === selectedId) ? 0.95 : 0.6}
            dashed={false}
          />
        );
      })}
    </>
  );
};

export const BrainScene = ({ nodes, edges, selectedId, onSelect }: SceneProps) => {
  return (
    <Canvas camera={{ position: [0, 0, 14], fov: 48 }}>
      <color attach="background" args={["#050915"]} />
      <ambientLight intensity={0.4} />
      <pointLight position={[12, 10, 10]} intensity={1.0} />
      <pointLight position={[-12, -8, -6]} intensity={0.6} color="#54f0ff" />
      <Sparkles count={180} speed={0.3} opacity={0.3} scale={20} size={1.5} color="#3df4ff" />
      <EdgeLines edges={edges} nodes={nodes} selectedId={selectedId} />
      <NodeCloud nodes={nodes} selectedId={selectedId} onSelect={onSelect} />
      <OrbitControls makeDefault enableDamping dampingFactor={0.08} />
    </Canvas>
  );
};
