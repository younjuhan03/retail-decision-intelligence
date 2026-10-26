"""Deterministic decision review: no invented confidence, unsupported savings, or LLM dependency."""
import numpy as np


def review(solution, costs, budget, evidence_ready=False, coverage=None):
    status = solution['status']
    q = solution.get('orders')
    flags = []
    spend = None
    if status == 'INFEASIBLE':
        flags.append(solution.get('reason', 'Constraints infeasible'))
    elif q is None:
        status = 'REVIEW REQUIRED'
        flags.append('No verified solver allocation is available')
    else:
        q, c = np.asarray(q), np.asarray(costs)
        if q.shape != c.shape or not np.isfinite(q).all() or (q < 0).any() or not np.equal(q, np.floor(q)).all():
            status = 'INFEASIBLE'
            flags.append('Order allocation is invalid')
        else:
            spend = float(q @ c)
            if spend > budget + 1e-6:
                status = 'INFEASIBLE'
                flags.append('Budget violated')
            elif not len(q) or not np.any(q):
                status = 'HOLD'
            elif not evidence_ready:
                status = 'REVIEW REQUIRED'
                flags.append('Out-of-sample business evidence has not been established')
            elif coverage is None or coverage < .70:
                status = 'REVIEW REQUIRED'
                flags.append('Forecast uncertainty coverage is missing or below review threshold (70%)')
    flags.append('Purchase costs, initial inventory, penalties and lead times are modeled assumptions')
    flags.append('Observed sales are a censored-demand proxy; no actual Walmart savings claim')
    return {'status': status, 'purchasing_expenditure': spend, 'budget': float(budget),
            'budget_slack': float(budget - spend) if spend is not None else None,
            'flags': flags, 'explanation': f'{status}. ' + (f'Verified integer order expenditure: ${spend:,.2f} of ${budget:,.2f}. ' if spend is not None else 'No executable allocation. ') + ' '.join(flags)}
