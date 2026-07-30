#!/usr/bin/env python
"""Gated Stage 5D design-review scaffold.

This script never launches Stage 5D broad compute. It writes a design-review JSON
only if Stage 5C.2B passes, and otherwise writes a blocked decision.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage5c2b-results', default='results/stage5c2b_lite')
    ap.add_argument('--out', default='results/stage5d_design_review')
    args = ap.parse_args()
    dec_path = ROOT / args.stage5c2b_results / 'analysis' / 'stage5c2b_decision.json'
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    if not dec_path.exists():
        payload = {
            'stage': 'stage5d_design_review_gate',
            'stage5d_design_review_allowed': False,
            'stage5d_broad_compute_allowed': False,
            'route': 'blocked_missing_stage5c2b_decision',
            'reasons': ['missing_stage5c2b_decision'],
        }
    else:
        c2b = json.loads(dec_path.read_text())
        allowed = bool(c2b.get('stage5c3_design_review_allowed', False))
        payload = {
            'stage': 'stage5d_design_review_gate',
            'stage5d_design_review_allowed': allowed,
            'stage5d_broad_compute_allowed': False,
            'route': 'prepare_stage5d_protocol_scaffold_only' if allowed else 'stage5d_blocked_until_stage5c2b_passes',
            'reasons': ['stage5c2b_passed_prepare_protocol_only'] if allowed else ['stage5c2b_not_passed'],
            'claim_scope': 'Stage 5D is a gated design-review scaffold only. No Stage 5D compute, no publication claim.',
        }
        if allowed:
            protocol = {
                'stage': 'stage5d_protocol_scaffold',
                'status': 'design_review_only_not_executable_broad_compute',
                'locked_inputs_required': [
                    'stage5c2b_candidate_gate_table.csv',
                    'stage5c2b_decision.json',
                    'stage5c2_holdout_core_gate_table.csv',
                    'validation gates',
                    'root-relative manifest and fresh-unzip test transcript',
                ],
                'allowed_next_step': 'Stage 5C3 mini-family design review before any Stage 5D compute',
                'forbidden_now': [
                    'broad finite-size compute',
                    'publication-ready claims',
                    'component-mechanism proof',
                    'exact mobile-hole dynamics claim',
                    'constructive recovery claim',
                ],
            }
            (out / 'stage5d_protocol_scaffold.json').write_text(json.dumps(protocol, indent=2))
    (out / 'stage5d_gate_decision.json').write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))

if __name__ == '__main__':
    main()
