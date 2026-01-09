#!/usr/bin/env python3
import json

# Read the file as text
with open('data/content.json', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace German quotes with escaped regular quotes
content = content.replace('„', '\\"')
content = content.replace('"', '\\"')

# Write back
with open('data/content.json', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed German quotation marks in content.json')

# Validate JSON
try:
    with open('data/content.json', 'r', encoding='utf-8') as f:
        json.load(f)
    print('✓ JSON is now valid!')
except json.JSONDecodeError as e:
    print(f'✗ JSON error: {e}')
