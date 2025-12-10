from __future__ import annotations

import os
from typing import List, Optional

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.mirror import MirrorCore
from core.models import SomaticSample, Trial
from mpg.models import EvidenceItem, MPGEdge, MPGNode
from mpg.repository import InMemoryMPGRepository, Neo4jMPGRepository
from mpg.segmentation import lift_level
from noetic.coherence import NoeticAnalyzer
from symbolic.belief import SymbolicEngine
from somatic.processor import SomaticFeatureExtractor
from core.qrv.manager import QRVManager
from api.human_api import router as human_router
from api.collective_api import router as collective_router
from api.policy_api import router as policy_router
from api.meta_policy_api import router as meta_policy_router
from api.benchmark_hub import router as benchmark_router
from api import mobile_api as mobile_api_module
from api.mobile_api import router as mobile_router
from api.streams_api import build_streams_router
from api.consent_api import build_consent_router
from api.participant_cockpit import build_participant_router
from api.console_api import build_console_router
from api.clinical_api import build_clinical_router
from api.afm_bridge import router as afm_router
from api.protocols_api import build_protocols_router
from api.adaptation_api import build_adaptation_router
from api.cohorts_lessons_api import build_cohorts_lessons_router
from api.content_store import ContentStore
from api.brain_api import build_brain_router
from api.visualization_api import build_visualization_router
from api.synthetic_api import build_synthetic_router
from brain.service import BrainViewService
from api.qrv_api import build_qrv_router
from streams import (
    EventIngestService,
    InMemoryEventStore,
    MPGSink,
    NoeticEventProcessor,
    SomaticEventProcessor,
    SymbolicEventProcessor,
    TimeAligner,
    ConsentManager,
    StreamBus,
    PostgresEventStore,
)
from streams.synthetic import SyntheticTelemetryGenerator
from services.preferences import PreferenceStore
from services.personalization import ProtocolPersonalizationEngine
from services.llm import (
    AppleLocalLLM,
    LocalAppleConfig,
    LLMRouter,
    NativeSidecarClient,
    NativeSidecarConfig,
    RemoteVLLMClient,
    RemoteVLLMConfig,
)


def build_repo() -> Neo4jMPGRepository | InMemoryMPGRepository:
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    if uri and user and password:
        return Neo4jMPGRepository(uri, user, password)
    return InMemoryMPGRepository()


def build_event_store() -> InMemoryEventStore | PostgresEventStore:
    dsn = os.getenv("EVENT_STORE_DSN")
    table = os.getenv("EVENT_STORE_TABLE", "events")
    if dsn:
        try:
            return PostgresEventStore(dsn, table=table)
        except Exception as exc:
            print(f"[brain] Falling back to in-memory event store: {exc}")
    return InMemoryEventStore()


repo = build_repo()
somatic = SomaticFeatureExtractor()
symbolic = SymbolicEngine(repo)
noetic = NoeticAnalyzer()
aligner = TimeAligner()
event_store = build_event_store()
consent_manager = ConsentManager(default_allow=False)
mpg_sink = MPGSink(repo)
stream_bus = StreamBus()
qrv_manager = QRVManager(repo, bus=stream_bus)
mirror = MirrorCore(somatic, symbolic, noetic, repo, qrv_manager=qrv_manager)
preferences = PreferenceStore()
pper = ProtocolPersonalizationEngine()
content_store = ContentStore()
synthetic_generator = SyntheticTelemetryGenerator(stream_bus)
ingest_service = EventIngestService(
    aligner=aligner,
    store=event_store,
    somatic_processor=SomaticEventProcessor(somatic),
    symbolic_processor=SymbolicEventProcessor(symbolic),
    noetic_processor=NoeticEventProcessor(noetic),
    consent_manager=consent_manager,
    mpg_sink=mpg_sink,
    bus=stream_bus,
)
brain_view = BrainViewService(repo, event_store)


def build_llm_router() -> LLMRouter:
    clients = {}
    # Only register backends that are explicitly configured to avoid runtime 500s.
    try:
        if os.getenv("APPLE_LLM_MODEL"):
            clients["local"] = AppleLocalLLM(LocalAppleConfig())
    except Exception:
        pass
    try:
        clients["remote"] = RemoteVLLMClient(RemoteVLLMConfig())
    except Exception:
        pass
    try:
        if os.getenv("NATIVE_LLM_URL") or os.getenv("NATIVE_LLM_MODEL"):
            clients["native"] = NativeSidecarClient(NativeSidecarConfig())
    except Exception:
        pass
    default_backend = os.getenv("LLM_BACKEND_DEFAULT")
    if not default_backend and clients:
        for candidate in ("native", "local", "remote"):
            if candidate in clients:
                default_backend = candidate
                break
        if not default_backend:
            default_backend = list(clients.keys())[0]
    return LLMRouter(clients=clients, default_backend=default_backend)


llm_router = build_llm_router()

app = FastAPI(title="H3lix API", version="0.1.0")

allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
app.include_router(human_router)
app.include_router(collective_router)
app.include_router(policy_router)
app.include_router(meta_policy_router)
app.include_router(benchmark_router)
app.include_router(mobile_router)
app.include_router(build_consent_router(consent_manager))
app.include_router(build_streams_router(ingest_service))
app.include_router(build_participant_router(repo, consent_manager, preferences, event_store))
app.include_router(build_console_router(repo, event_store, llm_router))
app.include_router(build_brain_router(brain_view, stream_bus))
app.include_router(build_clinical_router(repo, event_store))
app.include_router(build_protocols_router(repo))
app.include_router(build_adaptation_router(repo, pper))
app.include_router(build_visualization_router(repo, event_store, stream_bus, synthetic_generator, qrv_manager))
app.include_router(build_synthetic_router(synthetic_generator))
app.include_router(build_cohorts_lessons_router(content_store, event_store))
app.include_router(afm_router)
app.include_router(build_qrv_router(qrv_manager))

# expose repo for therapy task lookup in mobile API
mobile_api_module.repo_hint = repo


class NodeRequest(BaseModel):
    node: MPGNode
    evidences: List[EvidenceItem] = Field(default_factory=list)
    label: str = "MPGNode"


class EdgeRequest(BaseModel):
    edge: MPGEdge
    evidences: List[EvidenceItem] = Field(default_factory=list)


class TrialRunRequest(BaseModel):
    stimulus: str
    trial: Trial
    samples: List[SomaticSample] = Field(default_factory=list)
    feature_matrix: List[List[float]] = Field(default_factory=list)
    entropy: float = 0.0
    stability: float = 0.0
    outcome: Optional[float] = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/mpg/node")
def create_node(req: NodeRequest) -> dict:
    repo.create_node(req.node, req.evidences, label=req.label)
    return {"status": "created", "id": req.node.id, "label": req.label}


@app.post("/mpg/edge")
def create_edge(req: EdgeRequest) -> dict:
    repo.create_edge(req.edge, req.evidences)
    return {"status": "created", "src": req.edge.src, "dst": req.edge.dst}


@app.get("/mpg/graph")
def get_graph(level: Optional[int] = None) -> dict:
    graph = repo.get_graph(level=level)
    nodes = [{"id": node_id, **data} for node_id, data in graph.nodes(data=True)]
    edges = [
        {"src": u, "dst": v, **data}
        for u, v, data in graph.edges(data=True)
    ]
    return {"nodes": nodes, "edges": edges}


@app.post("/mpg/lift")
def lift(level: int, strength_threshold: float = 0.6, min_size: int = 3) -> dict:
    segments = lift_level(repo, level=level, strength_threshold=strength_threshold, min_size=min_size)
    return {"status": "ok", "created_segments": [seg.id for seg in segments]}


@app.post("/mirror/run_trial")
def run_trial(req: TrialRunRequest) -> dict:
    feature_matrix = np.array(req.feature_matrix)
    result = mirror.run_trial(
        stimulus=req.stimulus,
        trial=req.trial,
        samples=req.samples,
        feature_matrix=feature_matrix,
        entropy=req.entropy,
        stability=req.stability,
        outcome=req.outcome,
    )
    return {
        "action": result["action"],
        "outcome": result["outcome"],
        "belief": result["belief"],
        "coherence": result["coherence"],
        "rogue_variables": [rv.__dict__ for rv in result["rogue_variables"]],
        "somatic_windows": result["somatic_windows"],
        "qrvm": result.get("qrvm"),
    }
