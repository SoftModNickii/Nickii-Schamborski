#!/usr/bin/env python3
import json

# Read the file as text
with open('data/content.json', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace German curly quotes with escaped standard quotes within JSON strings
# „ is the opening German quote (U+201E)
# " is the closing German quote (U+201C)
content = content.replace('„', '\\"')
content = content.replace('"', '\\"')

# Write back
with open('data/content.json', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed German quotation marks in content.json')

# Validate JSON
try:
    with open('data/content.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f'✓ JSON is now valid! {len(data)} items loaded successfully.')
except json.JSONDecodeError as e:
    print(f'✗ JSON error at line {e.lineno}, column {e.colno}: {e.msg}')
