from itertools import product
import numpy as np
import pytest
from retailos.inventory import Scenario, optimize, simulate, feasible_baseline
from retailos.review import review


def test_milp_matches_exhaustive_enumeration():
    d = np.array([[[1., 2., 0.], [0., 1., 2.]], [[0., 0., 3.], [1., 1., 0.]]])
    c = np.array([2., 3.]); initial = np.array([1., 0.]); s = Scenario(12., .02, 4., 1)
    solution = optimize(d, c, initial, s)
    brute = min(np.mean([simulate(path, q, c, initial, s)['total_cost'] for path in d])
                for q in product(range(7), range(5)) if np.dot(q, c) <= s.budget)
    assert solution['status'] == 'APPROVE'
    assert solution['objective'] == pytest.approx(brute)
    replay = np.mean([simulate(path, solution['orders'], c, initial, s)['total_cost'] for path in d])
    assert replay == pytest.approx(brute)

@pytest.mark.parametrize('budget', [0., .1, 5., 1000.])
def test_feasibility_and_integer_orders(budget):
    d = np.ones((2, 3, 4)) * 5
    c = np.array([1., 2., 3.]); stock = np.zeros(3); s = Scenario(budget, lead_days=0)
    q = optimize(d, c, stock, s)['orders']
    assert (q >= 0).all() and (q == np.floor(q)).all() and q @ c <= budget + 1e-6
    for target in [np.array([4., 8., 1.]), np.array([0., 0., 0.])]:
        base = feasible_baseline(target, c, budget)
        assert base @ c <= budget + 1e-6


def test_costs_inventory_and_lead_hand_calculation():
    s = Scenario(20., .1, 3., 1)
    r = simulate(np.array([[2., 3., 1.]]), [4], [2.], [1.], s)
    assert r['procurement'] == 8
    assert r['unmet_units'] == 1
    assert r['holding_cost'] == pytest.approx(.2)
    assert r['lost_sales_penalty'] == 6
    assert r['total_cost'] == pytest.approx(14.2)
    assert r['fill_rate'] == pytest.approx(5 / 6)
    assert r['ending_inventory'] == 0


def test_no_sales_no_orders_and_empty_candidates():
    assert not optimize(np.zeros((1, 2, 28)), [1., 2.], [0., 0.], Scenario(10.))['orders'].any()
    assert optimize(np.empty((1, 0, 28)), [], [], Scenario(10.))['status'] == 'HOLD'
    assert simulate(np.zeros((1, 3)), [0], [1.], [0.], Scenario(0., lead_days=0))['fill_rate'] is None


def test_infeasible_minimum():
    sol = optimize(np.ones((1, 2, 28)), [2., 2.], [0., 0.], Scenario(0.), min_orders=[1, 1])
    assert sol['status'] == 'INFEASIBLE' and sol['orders'] is None

@pytest.mark.parametrize('value', [-1., np.nan, np.inf])
def test_invalid_demand(value):
    with pytest.raises(ValueError):
        optimize(np.full((1, 1, 28), value), [1.], [0.], Scenario(1.))


def test_huge_demand_finite_and_late_arrival():
    r = optimize(np.full((1, 1, 28), 1e5), [1.], [0.], Scenario(10., lead_days=28))
    assert r['orders'][0] == 0

@pytest.mark.parametrize('q', [[-1], [1.5], [np.nan], [11]])
def test_replay_rejects_invalid_or_overbudget(q):
    with pytest.raises(ValueError):
        simulate(np.ones((1, 28)), q, [1.], [0.], Scenario(10.))


def test_grounded_states_and_numbers():
    sol = {'status': 'APPROVE', 'orders': np.array([2, 3])}
    r = review(sol, [2., 1.], 10., evidence_ready=True, coverage=.8)
    assert r['status'] == 'APPROVE' and r['purchasing_expenditure'] == 7
    assert '$7.00' in r['explanation']
    assert review(sol, [2., 1.], 10.)['status'] == 'REVIEW REQUIRED'
    assert review(sol, [2., 1.], 10., True, .2)['status'] == 'REVIEW REQUIRED'
    assert review(sol, [2., 1.], 1.)['status'] == 'INFEASIBLE'
    assert review({'status': 'HOLD', 'orders': np.array([0])}, [1.], 0.)['status'] == 'HOLD'
    assert review({'status': 'REVIEW REQUIRED', 'orders': None}, [], 1.)['status'] == 'REVIEW REQUIRED'
    assert review({'status': 'INFEASIBLE', 'orders': None}, [], 1.)['status'] == 'INFEASIBLE'


def test_solver_timeout_never_approves_incumbent(monkeypatch):
    import retailos.inventory as inv
    from types import SimpleNamespace
    monkeypatch.setattr(inv, 'milp', lambda *a, **k: SimpleNamespace(status=1, x=np.array([2.]), message='Time limit reached'))
    r = inv.optimize(np.ones((1, 1, 28)), [1.], [0.], Scenario(5.))
    assert r['status'] == 'REVIEW REQUIRED' and r['orders'] is None
