#!/usr/bin/env python3
"""关键规则回归：不改仓库数据，只用临时日夹构造测试。"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from audit_delivery import evidence, ticket_audit, snapshot
from structure_gate import get_enforced_direction


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.day = Path(self.tmp.name)
        self.draft = self.day / '01-竞彩分析.md'
        self.draft.write_text('交卷模式=下注单\n【票面候选】005｜012｜剔=无\n'
                              '## 周四005 主 vs 客\n方向=锁主｜倾向=主胜\n'
                              '## 周四012 甲 vs 乙\n方向=锁客｜倾向=客胜\n'
                              '【今日票面】\n预算=按注数\n稳=4元｜005主胜×012客胜｜翻倍=过\n账本=过｜翻倍=过\n', encoding='utf-8')

    def ticket(self, first=('1.6',), second=('1.5',), stake='4'):
        return {'tickets': [{'name': '稳', 'stake_yuan': stake, 'multiple': 1,
                             'odds_captured_at': '2026-11-05T10:00:00+08:00',
                             'legs': [{'match_id': '005', 'play': '胜平负', 'choices': [
                                 {'option': f'项{i}', 'sp': sp} for i, sp in enumerate(first)]},
                                      {'match_id': '012', 'play': '胜平负', 'choices': [
                                          {'option': f'项{i}', 'sp': sp} for i, sp in enumerate(second)]}]}]}

    def test_no_market_forced_direction(self):
        self.assertEqual(get_enforced_direction(2.48, 3.33, 2.35), (None, None))

    def test_every_route_and_actual_stake(self):
        self.assertFalse(ticket_audit(self.day, self.draft, self.ticket(('2.2',), ('2.0',), '2')))
        errors = ticket_audit(self.day, self.draft, self.ticket(('2.8', '1.2'), ('1.6',), '4'))
        self.assertTrue(any('命中路 2' in e for e in errors), errors)
        self.assertTrue(any('本金应为 4' in e for e in ticket_audit(
            self.day, self.draft, self.ticket(('2.8', '2.7'), ('1.6',), '2'))))

    def test_watch_and_same_match_rejected(self):
        text = self.draft.read_text().replace('方向=锁客｜倾向=客胜', '方向=观望｜倾向=不定｜弃因=无一侧')
        self.draft.write_text(text)
        self.assertTrue(any('观望' in e for e in ticket_audit(self.day, self.draft,
                                                                self.ticket(('2.5',), ('2.5',), '2'))))

    def test_stable_handicap_draw_rejected(self):
        ticket = self.ticket(('2.5',), ('2.5',), '2')
        ticket['tickets'][0]['legs'][0]['choices'][0]['option'] = '让平(主-1)'
        self.assertTrue(any('让平禁止进稳' in e for e in ticket_audit(self.day, self.draft, ticket)))

    def test_evidence_hash_and_sidecar(self):
        self.draft.write_text(self.draft.read_text().replace('005｜012｜剔=', '005｜剔='))
        sidecar = self.day / '01a-认真拆-005.md'
        sidecar.write_text('\n'.join(('【近况比分表】','【赛程前后】','【排除因果】','【反剧本因果】','【三页取证】')))
        raw = self.day / '_raw'
        raw.mkdir()
        records = {}
        for name in ('analysisJs','detail','list_spf','coach','referee','cat'):
            f = raw / (name + '.txt')
            f.write_text(name)
            records[name] = {'path': '_raw/' + f.name, 'sha256': hashlib.sha256(f.read_bytes()).hexdigest()}
        manifest = {'matches': {'005': records}}
        self.assertEqual(evidence(self.day, self.draft, manifest)[0], [])
        (raw / 'coach.txt').write_text('changed')
        self.assertTrue(any('哈希' in e for e in evidence(self.day, self.draft, manifest)[0]))

    def test_freeze_before_kickoff_no_overwrite(self):
        manifest = {'day': '2026-11-05', 'captured_at': '2026-11-05T10:00:00+08:00',
                    'fixtures': [{'match_id': '005', 'kickoff_at': '2026-11-05T20:00:00+08:00',
                                  'lean': '主胜', 'p_model': {'主胜':'0.5','平':'0.3','客胜':'0.2'}}]}
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
