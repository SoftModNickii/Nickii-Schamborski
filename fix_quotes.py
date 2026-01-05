#!/usr/bin/env python3
# Fix German quotes in JSON

import json

with open('data/content.json.backup', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all German quoted terms with escaped versions
replacements = [
    ('„MeMärchen"', 'MeMärchen'),
    ('„Meme"', 'Meme'),
    ('„Märchen"', 'Märchen'),
    ('„DealWithIt"', 'DealWithIt'),
    ('„Retter"', 'Retter'),
    ('„Verwehrte Zuflucht"', 'Verwehrte Zuflucht'),
    ('„Familycare"', 'Familycare'),
    ('„Verstorbene"', 'Verstorbene'),
    ('„Instrument der öffentlichen Kritik"', 'Instrument der öffentlichen Kritik'),
    ('„Wolfsburg"', 'Wolfsburg'),
    ('„Angels Tutorial"', 'Angels Tutorial'),
    ('„Perfektionierung"', 'Perfektionierung'),
    ('„kulturellem Zombismus"', 'kulturellem Zombismus'),
]

for old, new in replacements:
    content = content.replace(old, new)

with open('data/content.json', 'w', encoding='utf-8') as f:
    f.write(content)

# Validate
try:
    with open('data/content.json') as f:
        data = json.load(f)
    print(f"✓ SUCCESS! {len(data)} entries loaded")
except Exception as e:
    print(f"✗ Error: {e}")
