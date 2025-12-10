import numpy as np

from policies.contextual_bandit import ActionDef, LinearUCBBandit


def test_bandit_selects_action_and_updates():
    actions = [
        ActionDef(id="a1", name="A1", params_template={}),
        ActionDef(id="a2", name="A2", params_template={}),
    ]
    bandit = LinearUCBBandit(actions, d=3, alpha=1.0)
    x = np.array([0.1, 0.2, -0.1])
    action = bandit.select_action(x)
    assert action.id in {"a1", "a2"}
    bandit.update(x, action.id, reward=0.5)
    # after update, theta should move in direction of x
    theta = bandit._theta(action.id)
    assert theta.shape == (3, 1)
