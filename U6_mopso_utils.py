"""
MOPSO utility functions for Pareto optimization
Stub implementation to satisfy imports
"""
import numpy as np
from typing import List, Optional


def dominates(sol1: np.ndarray, sol2: np.ndarray) -> bool:
    """
    Check if sol1 dominates sol2 (for maximization).
    Returns True if sol1 is better or equal in all objectives and strictly better in at least one.
    """
    all_better_or_equal = np.all(sol1 >= sol2)
    at_least_one_better = np.any(sol1 > sol2)
    return all_better_or_equal and at_least_one_better


def pareto_filter(solutions: List[np.ndarray]) -> List[np.ndarray]:
    """
    Filter solutions to keep only non-dominated solutions (Pareto front).
    """
    if not solutions:
        return []
    
    pareto_front = []
    for sol in solutions:
        is_dominated = False
        for other_sol in solutions:
            if dominates(other_sol, sol):
                is_dominated = True
                break
        if not is_dominated:
            pareto_front.append(sol)
    
    return pareto_front


def truncate_archive(archive: List[np.ndarray], max_size: int) -> List[np.ndarray]:
    """
    Truncate archive to max_size by keeping most diverse solutions.
    Simple implementation: just keep first max_size solutions if over limit.
    """
    if len(archive) <= max_size:
        return archive
    return archive[:max_size]


def select_leader(archive: List[np.ndarray]) -> Optional[np.ndarray]:
    """
    Select a leader from the archive.
    Simple implementation: return random solution from archive.
    """
    if not archive:
        return None
    return archive[np.random.randint(len(archive))]


def select_best_solution(
    archive: List[np.ndarray],
    weights: Optional[np.ndarray] = None
) -> Optional[np.ndarray]:
    """
    Select best solution from archive using weighted sum.
    If weights not provided, use equal weights.
    """
    if not archive:
        return None
    
    if weights is None:
        weights = np.ones(len(archive[0])) / len(archive[0])
    
    best_sol = None
    best_score = -np.inf
    
    for sol in archive:
        score = np.dot(weights, sol)
        if score > best_score:
            best_score = score
            best_sol = sol
    
    return best_sol
