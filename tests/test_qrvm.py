from core.qrv.models import QMSState
from core.qrv.spectral import SpectralRogueDetector


def test_spectral_detector_triggers_on_ablation_improvement():
    observed = QMSState(basis=["a", "b"], amplitudes=[1.0 + 0j, 0.0 + 0j], norm=1.0)
    predicted = QMSState(basis=["a", "b"], amplitudes=[0.0 + 0j, 1.0 + 0j], norm=1.0)
    detector = SpectralRogueDetector()
    result = detector.detect(observed, predicted)
    assert result.triggered is True
    assert "a" in result.rogue_segments

