#!/usr/bin/env python3
"""执行门禁回归：列表同编号跨日、观望进球、候选顺序、审计状态、复盘分母。"""
from pathlib import Path
import tempfile
import unittest

from lint_execution import _fixture_rows, lint_execution, lint_review


class ExecutionGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.day = Path(self.temp.name)
        (self.day / '_raw').mkdir()
        (self.day / '_raw/jc-list.txt').write_text(
            '123 true 周四 009 欧罗巴杯 22:00 塞尔塔 - 圣吉联合 2.31 3.42 2.97 亚欧析 荐 2.03 3.30 2.92 变\n'
            '124 true 周五 009 法甲 22:00 图卢兹 - 斯特拉斯 2.04 3.70 3.29 亚欧析 荐 1.84 3.60 3.15 变\n', encoding='utf-8')
        self.draft = self.day / '01-竞彩分析.md'

    def lint(self, header='周四009 塞尔塔 vs 圣吉罗斯', direction='方向=观望｜进球=2-3',
             candidate='【票面候选】无｜弃因=情报不足', review=''):
        text = f'{candidate}\n交卷模式=研究板\n## {header}\n{direction}\n'
        text += ('【今日票面】\n方案=空仓\n账本=未触发｜翻倍=未触发\n'
                 '证据审计=未触发｜票面算术=未触发｜赛前冻结=未验证\n')
        self.draft.write_text(text, encoding='utf-8')
        sec = [{'header': header, 'lines': [header, direction]}]
        return lint_execution(sec, '2026-11-06', str(self.draft))

    def test_identity_with_weekday_and_alias(self):
        rows = _fixture_rows((self.day / '_raw/jc-list.txt').read_text())
        self.assertEqual(rows[('周四', '009')][1], '圣吉联合')
        self.assertNotIn('lint_fixture_identity', [x['rule'] for x in self.lint()])
        self.assertTrue(any(x['rule'] == 'lint_fixture_identity' and x['severity'] == 'ERROR'
                            for x in self.lint(header='周四009 塞尔塔 vs 圣加仑')))

    def test_goals_and_live_exception(self):
        self.assertTrue(any(x['rule'] == 'lint_goals_required' for x in self.lint(direction='方向=观望｜进球=不定')))
        self.assertFalse(any(x['rule'] == 'lint_goals_required' for x in self.lint(direction='方向=观望｜进球=2-3')))
        self.assertTrue(any(x['rule'] == 'lint_goals_required' for x in self.lint(direction='方向=观望｜进球=不定｜抄盘时已开赛')))
        self.assertFalse(any(x['rule'] == 'lint_goals_required' for x in self.lint(direction='排除=暂缓｜理由=已开赛\n方向=观望｜进球=不定')))

    def test_candidate_and_status(self):
        self.assertTrue(any(x['rule'] == 'lint_candidate_order' for x in self.lint(
            candidate='【票面候选】无｜弃因=翻倍不过凑不成二串')))
        self.assertTrue(any(x['rule'] == 'lint_audit_status' for x in self.lint(
            candidate='【票面候选】009｜剔=其余情报薄')))
        self.assertEqual(self.lint(), [])

    def test_review_two_denominators(self):
        self.draft.write_text('【全场汇总表】\n| 编号 | 对阵 | 排除 | 推方向 | 倾向 | 让球胜平负 | 比分 | 进球 | 强制 |\n'
                              '|---|---|---|---|---|---|---|---|---|\n'
                              '| 009 | 塞尔塔 vs 圣吉罗斯 | 暂缓 | 主不败 | 主胜 | 不定 | 比分弃权 | 2-3 | 主胜/2-0/1-0/1-1 |\n')
        (self.day / '03-复盘.md').write_text('| 比分三格 | 0/1 |\n')
        self.assertTrue(any(x['severity'] == 'ERROR' for x in lint_review(self.day)))
        (self.day / '03-复盘.md').write_text('出手比分篮=0/0；强制比分三格=0/1。\n')
        self.assertFalse(any(x['severity'] == 'ERROR' for x in lint_review(self.day)))


if __name__ == '__main__':
    unittest.main()
