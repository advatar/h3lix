import { useEffect } from "react";
import { Canvas } from "@react-three/fiber";
import { getSnapshot, openStream } from "./client";
import { useH3lixStore } from "./store";

type Props = { sessionId: string };

export function H3lixScene({ sessionId }: Props) {
  const setSnapshot = useH3lixStore((s) => s.setSnapshot);
  const applyEnvelope = useH3lixStore((s) => s.applyEnvelope);

  useEffect(() => {
    let socket: WebSocket | undefined;
    (async () => {
      const snap = await getSnapshot(sessionId);
      setSnapshot(snap);
      socket = openStream({
        sessionId,
        messageTypes: ["somatic_state", "symbolic_state", "noetic_state", "mpg_delta"],
        onEvent: (ev) => applyEnvelope(ev.data as any),
      });
    })().catch(console.error);
    return () => socket?.close();
  }, [sessionId, setSnapshot, applyEnvelope]);

  return (
    <Canvas camera={{ position: [0, 0, 10], fov: 45 }}>
      {/* Placeholder geometry; replace with helix and MPG city */}
      <ambientLight />
      <pointLight position={[5, 5, 5]} />
      <mesh>
        <torusKnotGeometry args={[1, 0.3, 120, 24]} />
        <meshStandardMaterial color="#3df4ff" />
      </mesh>
    </Canvas>
  );
}
