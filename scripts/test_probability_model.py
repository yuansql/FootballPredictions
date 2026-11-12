#!/usr/bin/env python3
import math
import unittest

from probability_model import (brier_score, break_even_probability, devig_multiplicative,
                               expected_value, handicap_probabilities, log_loss,
                               result_probabilities, score_matrix, total_goals_probabilities)


class ProbabilityModelTests(unittest.TestCase):
    def test_real_ev_differs_from_devig_edge(self):
        market = devig_multiplicative((1.8, 3.8, 4.5))
        self.assertAlmostEqual(market[0], (1 / 1.8) / (1 / 1.8 + 1 / 3.8 + 1 / 4.5), places=4)
        self.assertAlmostEqual(break_even_probability(1.8), 1 / 1.8)
        self.assertLess(expected_value(0.511, 1.8), 0)
        self.assertGreater(expected_value(0.60, 1.8), 0)

    def test_dynamic_truncation_and_markets_share_matrix(self):
        model = score_matrix(3.2, 2.8)
        self.assertGreater(len(model['home']), 6)
        self.assertGreater(len(model['away']), 6)
        self.assertGreater(model['coverage'], 0.9995)
        self.assertAlmostEqual(sum(result_probabilities(model)), 1)
        self.assertAlmostEqual(sum(handicap_probabilities(model, -1)), 1)
        self.assertAlmostEqual(sum(total_goals_probabilities(model)), 1)
        self.assertAlmostEqual(total_goals_probabilities(model)[0], model['matrix'][0][0] / model['coverage'])

    def test_handicap_sign(self):
        model = score_matrix(1.5, 1.0)
        win, push, lose = handicap_probabilities(model, -1)
        diagonal = min(len(model['matrix']), len(model['matrix'][0])) - 1
        expected_push = sum(model['matrix'][i + 1][i] for i in range(diagonal)) / model['coverage']
        self.assertAlmostEqual(push, expected_push, places=6)
        self.assertAlmostEqual(win + push + lose, 1)

    def test_scoring_metrics(self):
        self.assertAlmostEqual(brier_score((0.5, 0.3, 0.2), 0), 0.38)
        self.assertAlmostEqual(log_loss((0.5, 0.3, 0.2), 0), -math.log(0.5))


if __name__ == '__main__':
    unittest.main()
