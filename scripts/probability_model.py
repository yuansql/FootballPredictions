#!/usr/bin/env python3
"""统一的胜平负/让球/总进球概率与真实 EV 计算。"""
from __future__ import annotations

import math


def devig_multiplicative(odds):
    values = [float(value) for value in odds]
    if len(values) < 2 or any(not math.isfinite(value) or value <= 1 for value in values):
        raise ValueError('赔率须为至少两个大于 1 的有限数')
    inverse = [1 / value for value in values]
    overround = sum(inverse)
    return tuple(value / overround for value in inverse)


def break_even_probability(sp):
    value = float(sp)
    if not math.isfinite(value) or value <= 1:
        raise ValueError('实际 SP 须为大于 1 的有限数')
    return 1 / value


def expected_value(p_model, sp):
    probability = float(p_model)
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError('模型概率须在 0..1')
    return probability * float(sp) - 1


def poisson_probabilities(lam, tail_tolerance=1e-4, max_goals=30):
    mean = float(lam)
    tolerance = float(tail_tolerance)
    if not math.isfinite(mean) or mean <= 0:
        raise ValueError('λ 须为正有限数')
    if not 0 < tolerance < 0.05:
        raise ValueError('tail_tolerance 须在 0..0.05')
    probabilities = [math.exp(-mean)]
    total = probabilities[0]
    for goals in range(1, max_goals + 1):
        probabilities.append(probabilities[-1] * mean / goals)
        total += probabilities[-1]
        if goals >= math.ceil(mean) and 1 - total <= tolerance:
            return tuple(probabilities)
    raise ValueError('λ 过大或 max_goals 太小，尾部未达到精度要求')


def score_matrix(lambda_home, lambda_away, tail_tolerance=1e-4):
    home = poisson_probabilities(lambda_home, tail_tolerance)
    away = poisson_probabilities(lambda_away, tail_tolerance)
    matrix = tuple(tuple(h * a for a in away) for h in home)
    coverage = sum(map(sum, matrix))
    return {'home': home, 'away': away, 'matrix': matrix, 'coverage': coverage}


def _normalized(matrix):
    coverage = sum(map(sum, matrix))
    if coverage <= 0:
        raise ValueError('比分矩阵无概率质量')
    return coverage


def result_probabilities(model):
    matrix = model['matrix']
    coverage = _normalized(matrix)
    home = sum(cell for i, row in enumerate(matrix) for j, cell in enumerate(row) if i > j)
    draw = sum(row[i] for i, row in enumerate(matrix) if i < len(row))
    away = sum(cell for i, row in enumerate(matrix) for j, cell in enumerate(row) if i < j)
    return tuple(value / coverage for value in (home, draw, away))


def handicap_probabilities(model, home_handicap):
    line = int(home_handicap)
    matrix = model['matrix']
    coverage = _normalized(matrix)
    buckets = [0.0, 0.0, 0.0]
    for home, row in enumerate(matrix):
        for away, probability in enumerate(row):
            adjusted = home + line - away
            buckets[0 if adjusted > 0 else 1 if adjusted == 0 else 2] += probability
    return tuple(value / coverage for value in buckets)


def total_goals_probabilities(model):
    matrix = model['matrix']
    coverage = _normalized(matrix)
    totals = [0.0] * (len(matrix) + len(matrix[0]) - 1)
    for home, row in enumerate(matrix):
        for away, probability in enumerate(row):
            totals[home + away] += probability
    return tuple(value / coverage for value in totals)


def top_scores(model, limit=3):
    matrix = model['matrix']
    scores = [(home, away, probability) for home, row in enumerate(matrix)
              for away, probability in enumerate(row)]
    return tuple(sorted(scores, key=lambda item: item[2], reverse=True)[:limit])


def brier_score(probabilities, outcome_index):
    if len(probabilities) != 3 or outcome_index not in (0, 1, 2):
        raise ValueError('Brier 输入须为三项概率和 0/1/2 结果索引')
    return sum((probability - float(index == outcome_index)) ** 2
               for index, probability in enumerate(probabilities))


def log_loss(probabilities, outcome_index, epsilon=1e-15):
    if outcome_index not in (0, 1, 2):
        raise ValueError('结果索引须为 0/1/2')
    probability = min(max(float(probabilities[outcome_index]), epsilon), 1 - epsilon)
    return -math.log(probability)
