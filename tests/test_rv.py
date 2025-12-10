from noetic.rogue_variables import RogueVariableDetector


def test_rogue_variable_detection_three_sigma():
    detector = RogueVariableDetector(sigma=3.0)
    shap_vals = [0.1, 0.12, 0.11, 0.5]  # last is outlier
    features = ["f1", "f2", "f3", "f4"]
    rvs = detector.detect(shap_vals, features)
    assert any(rv.feature == "f4" for rv in rvs)
