#!/usr/bin/env python3
"""lambda_sheet 的冒烟测试。"""
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / 'lambda_sheet.py'


def run(*args):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True,
    )
    return result


BASE = ['--league-home', '1.35', '--league-away', '1.05',
        '--att-h', '1.50', '--def-h', '0.90',
        '--att-a', '0.90', '--def-a', '1.10']


def test_basic_lambda():
    r = run(*BASE)
    assert r.returncode == 0, r.stderr
    # λ_H = 1.35×1.50×1.10 = 2.23；λ_A = 1.05×0.90×0.90 = 0.85
    assert 'λ_H=2.23' in r.stdout and 'λ_A=0.85' in r.stdout, r.stdout
    assert 'λ区间=H[' in r.stdout
    assert 'conservative_probability.py' in r.stdout


def test_uncertainty_widens_interval():
    tight = run(*BASE)
    loose = run(*BASE, '--n-h', '4', '--n-a', '4', '--friendly', '--lineup-unknown')
    assert tight.returncode == 0 and loose.returncode == 0
    assert 'u_H=0.30' in loose.stdout, loose.stdout
    assert 'u_H=0.15' in tight.stdout, tight.stdout


def test_invalid_inputs_fail():
    assert run(*BASE, '--adj-h', '1.5').returncode != 0
    assert run(*BASE, '--att-h', '0').returncode != 0
    assert run(*BASE, '--league-home', '-1').returncode != 0


if __name__ == '__main__':
    test_basic_lambda()
    test_uncertainty_widens_interval()
    test_invalid_inputs_fail()
    print('lambda_sheet tests OK')
