from experiments.human_runner import DecisionEngine, mufs_search
import numpy as np


class DummyModel:
    def __init__(self, bias: float = 0.0):
        self.bias = bias

    def predict(self, x):
        # x shape (1, d)
        logits = x[0].sum() + self.bias
        return np.array([1 if logits > 0 else 0])


def test_mufs_search_finds_flip_with_hidden_segment():
    feature_order = ["f1", "f2"]
    segment_order = ["s1"]
    model = DummyModel(bias=-0.1)
    engine = DecisionEngine(model, feature_order, segment_order)

    features = {"f1": 0.2, "f2": 0.2}
    segments = ["s1"]
    hidden_inputs = []
    hidden_segments = ["s1"]
    input_score = {}
    segment_score = {"s1": 1.0}

    res = mufs_search(engine, features, segments, hidden_inputs, hidden_segments, input_score, segment_score, max_subset_size=2)
    assert res.exists
    assert res.segment_ids == ["s1"]
