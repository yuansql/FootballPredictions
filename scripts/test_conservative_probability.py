#!/usr/bin/env python3
import unittest

from conservative_probability import (conservative_handicap, conservative_model,
                                      conservative_top_scores, corner_points,
                                      joint_conservative)
from probability_model import (handicap_probabilities, result_probabilities,
                               score_matrix, total_goals_probabilities)


class ConservativeProbabilityTests(unittest.TestCase):
    def test_degenerate_interval_equals_point_estimate(self):
        model = conservative_model(1.6, 1.1, 1.6, 1.6, 1.1, 1.1)
        point = result_probabilities(score_matrix(1.6, 1.1))
        for wrote, want in zip(model['result'], point):
            self.assertAlmostEqual(wrote, want, places=9)

    def test_corner_points_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            corner_points(2.1, 1.0, 1.38, 1.86, 0.8, 1.2)
        with self.assertRaises(ValueError):
            corner_points(1.6, 1.0, 1.38, 1.86, 0.0, 1.2)
        with self.assertRaises(ValueError):
            corner_points(1.6, 1.0, 1.86, 1.38, 0.8, 1.2)
        self.assertEqual(len(corner_points(1.6, 1.0, 1.38, 1.86, 0.8, 1.2)), 4)

    def test_conservative_never_exceeds_point_estimate(self):
        model = conservative_model(1.62, 1.05, 1.38, 1.86, 0.86, 1.28)
        point = result_probabilities(score_matrix(1.62, 1.05))
        for label, cons, want in zip(('主胜', '平', '客胜'), model['result'], point):
            self.assertLessEqual(cons, want + 1e-12, label)
        self.assertLess(sum(model['result']), 1.0)
        self.assertLess(sum(model['total_goals']), 1.0)

        for line in (-1, 0, 1):
            for cons, want in zip(conservative_handicap(model, line),
                                  handicap_probabilities(score_matrix(1.62, 1.05), line)):
                self.assertLessEqual(cons, want + 1e-12)

    def test_worst_corner_is_reported_per_outcome(self):
        model = conservative_model(1.62, 1.05, 1.38, 1.86, 0.86, 1.28)
        for index, worst in enumerate(model['result_worst_corner']):
            self.assertAlmostEqual(model['result_per_corner'][worst][index],
                                   model['result'][index], places=12)

    def test_split_sensitivity_at_equal_lambda_sum(self):
        """同 λ 总量、不同主客分配：总进球完全不变，胜平负/让球大幅变动。

        这就是手工统一打折做不到的区分——角点 (1.2,1.8) 与 (1.8,1.2) 总量都是 3.0。
        """
        low_split = score_matrix(1.2, 1.8)
        high_split = score_matrix(1.8, 1.2)
        low_totals = total_goals_probabilities(low_split)
        high_totals = total_goals_probabilities(high_split)
        for a, b in zip(low_totals, high_totals):  # 动态截断长度可不同，逐位比对重叠段
            self.assertAlmostEqual(a, b, places=9)
        for tail in (low_totals[len(high_totals):], high_totals[len(low_totals):]):
            self.assertLess(sum(tail), 1e-6)

        low_result = result_probabilities(low_split)
        high_result = result_probabilities(high_split)
        self.assertAlmostEqual(low_result[1], high_result[1], places=9)  # 平局只看总量
        self.assertGreater(abs(low_result[0] - high_result[0]), 0.15)  # 主胜/客胜互换
        self.assertAlmostEqual(low_result[0], high_result[2], places=9)

        low_hc = handicap_probabilities(low_split, -1)
        high_hc = handicap_probabilities(high_split, -1)
        self.assertGreater(abs(low_hc[0] - high_hc[0]), 0.15)

    def test_top_scores_are_cellwise_minima(self):
        model = conservative_model(1.62, 1.05, 1.38, 1.86, 0.86, 1.28)
        top = conservative_top_scores(model, 3)
        self.assertEqual(len(top), 3)
        point = score_matrix(1.62, 1.05)['matrix']
        for i, j, probability in top:
            across_corners = min(
                m['matrix'][i][j] if i < len(m['matrix']) and j < len(m['matrix'][i]) else 0.0
                for m in model['models']
            )
            self.assertAlmostEqual(probability, across_corners, places=12)
            self.assertLessEqual(probability, point[i][j] + 1e-12)
        self.assertEqual(top, tuple(sorted(top, key=lambda item: item[2], reverse=True)))

    def test_wider_interval_is_more_conservative(self):
        narrow = conservative_model(1.6, 1.1, 1.5, 1.7, 1.0, 1.2)['result']
        wide = conservative_model(1.6, 1.1, 1.2, 2.0, 0.7, 1.5)['result']
        for cons, want in zip(wide, narrow):
            self.assertLessEqual(cons, want + 1e-12)

    def test_joint_conservative_applies_rho(self):
        self.assertAlmostEqual(joint_conservative((0.5, 0.4)), 0.2)
        self.assertAlmostEqual(joint_conservative((0.5, 0.4), rho=0.85), 0.17)
        for bad in (0, -0.1, 1.2):
            with self.assertRaises(ValueError):
                joint_conservative((0.5, 0.4), rho=bad)
        with self.assertRaises(ValueError):
            joint_conservative((0.5, 1.4))


if __name__ == '__main__':
    unittest.main()
