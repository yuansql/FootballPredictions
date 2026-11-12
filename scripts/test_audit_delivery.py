#!/usr/bin/env python3
"""关键规则回归：不改仓库数据，只用临时日夹构造测试。"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from audit_delivery import evidence, ticket_audit, snapshot
from structure_gate import get_enforced_direction


def choice(sp, p_model='0.65', p_conservative='0.60', option='主胜'):
    return {'option': option, 'sp': sp, 'p_model': p_model, 'p_conservative': p_conservative}


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.day = Path(self.tmp.name)
        self.draft = self.day / '01-竞彩分析.md'
        self.draft.write_text('交卷模式=下注单\n【票面候选】005｜012｜剔=无\n'
                              '## 周四005 主 vs 客\n方向=锁主｜倾向=主胜\n'
                              '## 周四012 甲 vs 乙\n方向=锁客｜倾向=客胜\n'
                              '【今日票面】\n预算=按注数\n稳=2元｜005主胜×012客胜\n'
                              '账本=过｜EV审计=过｜联合概率=独立近似\n', encoding='utf-8')

    def ticket(self, first=None, second=None, stake='2'):
        first = first or [choice('2.2')]
        second = second or [choice('2.0')]
        return {'tickets': [{'name': '稳', 'stake_yuan': stake, 'multiple': 1,
                             'joint_probability': '独立近似',
                             'odds_captured_at': '2026-11-05T10:00:00+08:00',
                             'legs': [{'match_id': '005', 'play': '胜平负', 'choices': first},
                                      {'match_id': '012', 'play': '胜平负', 'choices': second}]}]}

    def test_no_market_forced_direction(self):
        self.assertEqual(get_enforced_direction(2.48, 3.33, 2.35), (None, None))

    def test_ev_uses_every_route_and_actual_stake(self):
        self.assertEqual(ticket_audit(self.day, self.draft, self.ticket()), [])
        low_return_routes = self.ticket(
            [choice('2.8', '0.45', '0.40'), choice('1.2', '0.85', '0.80', '平')],
            [choice('1.6', '0.70', '0.65')], '4')
        self.assertEqual(ticket_audit(self.day, self.draft, low_return_routes), [])
        errors = ticket_audit(self.day, self.draft, self.ticket(stake='4'))
        self.assertTrue(any('本金应为 2' in error for error in errors), errors)

    def test_non_positive_conservative_ev_rejected(self):
        ticket = self.ticket([choice('2.0', '0.45', '0.40')],
                             [choice('2.0', '0.45', '0.40')])
        errors = ticket_audit(self.day, self.draft, ticket)
        self.assertTrue(any('保守EV=' in error for error in errors), errors)

    def test_probabilities_required_and_conservative_not_higher(self):
        ticket = self.ticket()
        del ticket['tickets'][0]['legs'][0]['choices'][0]['p_model']
        ticket['tickets'][0]['legs'][1]['choices'][0]['p_conservative'] = '0.70'
        errors = ticket_audit(self.day, self.draft, ticket)
        self.assertTrue(any('p_model' in error for error in errors), errors)
        self.assertTrue(any('保守概率不得高于模型概率' in error for error in errors), errors)

    def test_watch_and_same_match_rejected(self):
        text = self.draft.read_text().replace('方向=锁客｜倾向=客胜', '方向=观望｜倾向=不定｜弃因=无一侧')
        self.draft.write_text(text)
        self.assertTrue(any('观望' in error for error in ticket_audit(self.day, self.draft, self.ticket())))
        ticket = self.ticket()
        ticket['tickets'][0]['legs'][1]['match_id'] = '005'
        self.assertTrue(any('同场' in error for error in ticket_audit(self.day, self.draft, ticket)))

    def test_handicap_draw_and_stars_are_not_ticket_bans(self):
        ticket = self.ticket([choice('2.5', option='让平(主-1)')], [choice('2.5')])
        text = self.draft.read_text().replace('方向=锁主｜倾向=主胜', '方向=锁主｜倾向=主胜\n【研究推荐】★★★☆☆')
        self.draft.write_text(text, encoding='utf-8')
        self.assertEqual(ticket_audit(self.day, self.draft, ticket), [])

    def test_evidence_hash_and_sidecar(self):
        self.draft.write_text(self.draft.read_text().replace('005｜012｜剔=', '005｜剔='))
        sidecar = self.day / '01a-认真拆-005.md'
        sidecar.write_text('\n'.join(('【近况比分表】', '【赛程前后】', '【排除因果】', '【反剧本因果】', '【三页取证】')))
        raw = self.day / '_raw'
        raw.mkdir()
        records = {}
        for name in ('analysisJs', 'detail', 'list_spf', 'coach', 'referee', 'cat'):
            file = raw / (name + '.txt')
            file.write_text(name)
            records[name] = {'path': '_raw/' + file.name, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}
        manifest = {'matches': {'005': records}}
        self.assertEqual(evidence(self.day, self.draft, manifest)[0], [])
        (raw / 'coach.txt').write_text('changed')
        self.assertTrue(any('哈希' in error for error in evidence(self.day, self.draft, manifest)[0]))

    def test_freeze_before_kickoff_no_overwrite(self):
        manifest = {'day': '2026-11-05', 'captured_at': '2026-11-05T10:00:00+08:00',
                    'fixtures': [{'match_id': '005', 'kickoff_at': '2026-11-05T20:00:00+08:00',
                                  'lean': '主胜', 'p_model': {'主胜': '0.5', '平': '0.3', '客胜': '0.2'}}]}
        out = self.day / 'frozen.json'
        (self.day / 'predictions.json').write_text(json.dumps(manifest))
        result = snapshot(self.day, self.draft, self.day / 'predictions.json', out)
        self.assertEqual(result['schema'], 1)
        with self.assertRaises(ValueError):
            snapshot(self.day, self.draft, self.day / 'predictions.json', out)
        manifest['captured_at'] = '2026-11-05T21:00:00+08:00'
        (self.day / 'predictions.json').write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            snapshot(self.day, self.draft, self.day / 'predictions.json', self.day / 'late.json')


if __name__ == '__main__':
    unittest.main()
