"""Scenario MILP with integer orders and daily inventory / lost-sales accounting."""
from dataclasses import dataclass
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import lil_matrix


@dataclass(frozen=True)
class Scenario:
    budget: float
    holding_ratio: float = .002
    penalty_multiple: float = 3.0
    lead_days: int = 2

    def validate(self, horizon):
        if not np.isfinite([self.budget, self.holding_ratio, self.penalty_multiple]).all():
            raise ValueError('Non-finite scenario input')
        if min(self.budget, self.holding_ratio, self.penalty_multiple) < 0:
            raise ValueError('Negative scenario input')
        if not isinstance(self.lead_days, (int, np.integer)) or not 0 <= self.lead_days <= horizon:
            raise ValueError('Lead days must be an integer from zero to horizon')


def validate_inputs(demand, costs, initial, scenario):
    d, c, stock = np.asarray(demand, dtype=float), np.asarray(costs, dtype=float), np.asarray(initial, dtype=float)
    if d.ndim != 3 or d.shape[0] < 1 or d.shape[2] < 1:
        raise ValueError('Demand shape must be scenarios x SKUs x days')
    if c.shape != (d.shape[1],) or stock.shape != c.shape:
        raise ValueError('SKU dimension mismatch')
    if not all(np.isfinite(a).all() for a in [d, c, stock]):
        raise ValueError('Non-finite demand, costs, or inventory')
    if (d < 0).any() or (c <= 0).any() or (stock < 0).any():
        raise ValueError('Demand/inventory nonnegative; costs strictly positive')
    scenario.validate(d.shape[2])
    return d, c, stock


def optimize(demand, costs, initial, scenario, min_orders=None):
    d, c, initial = validate_inputs(demand, costs, initial, scenario)
    S, N, H = d.shape
    lower = np.zeros(N) if min_orders is None else np.asarray(min_orders, dtype=float)
    if lower.shape != (N,) or not np.isfinite(lower).all() or (lower < 0).any() or not np.equal(lower, np.floor(lower)).all():
        raise ValueError('Minimum orders must be nonnegative integers')
    if lower @ c > scenario.budget + 1e-8:
        return {'status': 'INFEASIBLE', 'orders': None, 'reason': 'Minimum orders exceed budget'}
    if N == 0:
        return {'status': 'HOLD', 'orders': np.zeros(0, dtype=int), 'objective': 0.0, 'reason': 'No candidates'}
    # q_i is shared across demand scenarios; I_sit and L_sit are nonnegative recourse.
    size = S * N * H
    total = N + 2 * size
    obj = np.zeros(total)
    obj[:N] = c
    obj[N:N + size] = np.tile(np.repeat(c * scenario.holding_ratio / S, H), S)
    obj[N + size:] = np.tile(np.repeat(c * scenario.penalty_multiple / S, H), S)
    A = lil_matrix((size + 1, total))
    rhs = np.empty(size + 1)
    A[0, :N] = c
    rhs[0] = scenario.budget
    for s in range(S):
        for i in range(N):
            for t in range(H):
                k = (s * N + i) * H + t
                row = k + 1
                A[row, N + k] = 1  # I_t - I_(t-1) - q(arrival) - L_t = -d_t
                A[row, N + size + k] = -1
                if t:
                    A[row, N + k - 1] = -1
                if t == scenario.lead_days:
                    A[row, i] = -1
                rhs[row] = -d[s, i, t] + (initial[i] if t == 0 else 0)
    lo = np.zeros(total)
    lo[:N] = lower
    hi = np.full(total, np.inf)
    hi[:N] = np.floor(scenario.budget / c)
    constraint_lo = rhs.copy()
    constraint_lo[0] = -np.inf
    result = milp(obj, integrality=np.r_[np.ones(N), np.zeros(2 * size)],
                  bounds=Bounds(lo, hi), constraints=LinearConstraint(A.tocsr(), constraint_lo, rhs),
                  options={'time_limit': 45, 'mip_rel_gap': 0.0001})
    # Never call a timed-out incumbent an approved optimum.
    if result.status != 0 or result.x is None:
        return {'status': 'INFEASIBLE' if result.status == 2 else 'REVIEW REQUIRED', 'orders': None, 'reason': result.message}
    orders = np.rint(result.x[:N]).astype(int)
    if orders @ c > scenario.budget + 1e-6:
        raise AssertionError('Solver returned budget violation')
    return {'status': 'APPROVE', 'orders': orders, 'objective': float(result.fun), 'mip_gap': float(result.mip_gap), 'reason': 'Optimal scenario solution; assumptions require human review'}


def feasible_baseline(target, costs, budget):
    target, c = np.asarray(target, dtype=float), np.asarray(costs, dtype=float)
    if target.shape != c.shape or not np.isfinite(target).all() or not np.isfinite(c).all() or (target < 0).any() or (c <= 0).any() or not np.isfinite(budget) or budget < 0:
        raise ValueError('Invalid baseline target, costs, or budget')
    q = np.ceil(target).astype(int)
    if q @ c > budget and q @ c > 0:
        # Same proportional reduction + largest-remainder feasible rounding for both baselines.
        scaled = q * budget / (q @ c)
        q = np.floor(scaled).astype(int)
        remainder = scaled - q
        for i in np.argsort(-remainder, kind='stable'):
            if remainder[i] > 0 and q @ c + c[i] <= budget + 1e-8:
                q[i] += 1
    return q


def simulate(actual, orders, costs, initial, scenario):
    actual = np.asarray(actual, dtype=float)
    if actual.ndim != 2:
        raise ValueError('Actual sales proxy must be SKU x day')
    d, c, stock = validate_inputs(actual[None], costs, initial, scenario)
    q = np.asarray(orders, dtype=float)
    if q.shape != c.shape or not np.isfinite(q).all() or (q < 0).any() or not np.equal(q, np.floor(q)).all():
        raise ValueError('Orders must be nonnegative integers')
    procurement = float(q @ c)
    if procurement > scenario.budget + 1e-6:
        raise ValueError('Order exceeds budget')
    inventory = stock.copy()
    lost = np.zeros_like(stock)
    holding = 0.0
    for t in range(actual.shape[1]):
        if t == scenario.lead_days:
            inventory += q
        served = np.minimum(inventory, actual[:, t])
        lost += actual[:, t] - served
        inventory -= served
        holding += float(inventory @ (c * scenario.holding_ratio))
    penalty = float(lost @ (c * scenario.penalty_multiple))
    total_units = float(actual.sum())
    return {'total_cost': procurement + holding + penalty, 'procurement': procurement, 'holding_cost': holding,
            'lost_sales_penalty': penalty, 'unmet_units': float(lost.sum()), 'proxy_units': total_units,
            'fill_rate': 1 - float(lost.sum()) / total_units if total_units else None,
            'budget_utilization': procurement / scenario.budget if scenario.budget else 0.0,
            'ending_inventory': float(inventory.sum())}
