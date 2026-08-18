#!/usr/bin/env python3
"""Verify dimension chain closure."""
import json

with open('out/1f_view.json') as f:
    data = json.load(f)

# Group dimensions by chain
chains = {}
for dim in data['dimensions']:
    chain_id = dim['chain_id']
    if chain_id not in chains:
        chains[chain_id] = {'overall': None, 'segments': []}

    if dim['role'] == 'overall':
        chains[chain_id]['overall'] = dim['value_m']
    else:
        chains[chain_id]['segments'].append(dim['value_m'])

# Check closure
print("Dimension chain closure check:")
for chain_id in sorted(chains.keys()):
    chain = chains[chain_id]
    overall = chain['overall']
    seg_sum = sum(chain['segments'])
    closes = abs(overall - seg_sum) < 0.01
    status = "✓ CLOSES" if closes else "✗ FAILS"
    print(f"  {chain_id}: overall={overall:.2f}m, segments_sum={seg_sum:.2f}m [{status}]")
