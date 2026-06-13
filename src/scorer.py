#!/usr/bin/env python3
"""
Challenge Hunter AI v2.0 — Scoring engine
Pure functions. No I/O. Fully unit-testable.
"""

from __future__ import annotations
from typing import Dict, Any


# ----------------------------------------------------------------------------
# Opportunity score (0-100): how attractive is this opportunity overall?
# ----------------------------------------------------------------------------

def calculate_opportunity_score(opportunity: Dict[str, Any]) -> int:
    """
    Higher = better.
    Weights:
        base:           50
        prize tier:     +5 to +25
        deadline sweet: +12 (14-45d), +6 (7-14d), +4 (>45d), -5 (<7d)
        ai policy:      +20 allowed, -15 unclear, -20 restricted, -40 banned
        eligibility:    +5 global, +8 solo
        difficulty:     +5 easy, -5 hard
    """
    score = 50
    prize = int(opportunity.get('prize_usd') or 0)
    days = int(opportunity.get('days_remaining') or 0)
    ai_policy = (opportunity.get('ai_policy') or 'unclear').lower()
    difficulty = (opportunity.get('difficulty') or 'medium').lower()
    eligibility = (opportunity.get('eligibility') or '').lower()
    team_size = (opportunity.get('team_size') or '').lower()

    # Prize
    if prize > 50000:
        score += 25
    elif prize > 10000:
        score += 20
    elif prize > 5000:
        score += 15
    elif prize > 2000:
        score += 10
    elif prize > 500:
        score += 5

    # Deadline
    if 14 <= days <= 45:
        score += 12
    elif 7 <= days < 14:
        score += 6
    elif days > 45:
        score += 4
    elif 0 < days < 7:
        score -= 5

    # AI policy
    if ai_policy == 'allowed':
        score += 20
    elif ai_policy == 'unclear':
        score -= 15
    elif ai_policy == 'restricted':
        score -= 20
    elif ai_policy == 'banned':
        score -= 40

    # Eligibility & team
    if 'global' in eligibility:
        score += 5
    if 'solo' in team_size:
        score += 8

    # Difficulty
    if difficulty == 'easy':
        score += 5
    elif difficulty == 'hard':
        score -= 5

    return max(0, min(100, score))


# ----------------------------------------------------------------------------
# Win probability (5-95%): chance of winning if you enter
# ----------------------------------------------------------------------------

def calculate_win_probability(opportunity: Dict[str, Any]) -> int:
    """
    Deterministic estimate. The real odds are unknowable.
    """
    prob = 30
    prize = int(opportunity.get('prize_usd') or 0)
    days = int(opportunity.get('days_remaining') or 0)
    ai_policy = (opportunity.get('ai_policy') or 'unclear').lower()
    difficulty = (opportunity.get('difficulty') or 'medium').lower()

    if prize > 5000:
        prob += 10
    if days > 14:
        prob += 10
    if ai_policy == 'allowed':
        prob += 20
    if difficulty == 'easy':
        prob += 15
    elif difficulty == 'hard':
        prob -= 15
    if prize > 50000:
        prob -= 10

    return max(5, min(95, prob))


# ----------------------------------------------------------------------------
# Expected value
# ----------------------------------------------------------------------------

def calculate_expected_value(prize_usd: int, win_probability: int) -> float:
    """EV = prize * (win_prob / 100)."""
    return round(float(prize_usd) * (win_probability / 100.0), 2)


# ----------------------------------------------------------------------------
# Convenience: score a row in one call
# ----------------------------------------------------------------------------

def score_all(opportunity: Dict[str, Any]) -> Dict[str, Any]:
    """Return {score, win_probability, expected_value} without mutating input."""
    score = calculate_opportunity_score(opportunity)
    prob = calculate_win_probability(opportunity)
    ev = calculate_expected_value(
        int(opportunity.get('prize_usd') or 0), prob
    )
    return {
        'opportunity_score': score,
        'win_probability': prob,
        'expected_value': ev,
    }


if __name__ == '__main__':
    sample = {
        'prize_usd': 10000,
        'days_remaining': 30,
        'ai_policy': 'allowed',
        'difficulty': 'medium',
        'eligibility': 'Global, solo or team',
        'team_size': 'solo',
    }
    print(score_all(sample))
