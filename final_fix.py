#!/usr/bin/env python3
import json
import re

# Read backup
with open('data/content.json.backup', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Remove all lines containing "description_de":
filtered_lines = [line for line in lines if '"description_de":' not in line]

# Join back
content = ''.join(filtered_lines)

# Fix known issue: "l, → ],
content = content.replace('"l,', '"],')

# Fix trailing commas before closing braces (from removed description_de)
# Pattern: ",\n\s*}" → "\n\s*}"
content = re.sub(r'",\s*\n(\s*})', r'"\n\1', content)

# Write temporary file
with open('data/content.json', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Removed description_de lines. Total lines: {len(filtered_lines)}")

# Try to parse
try:
    data = json.loads(content)
    print(f"✓ SUCCESS! Loaded {len(data)} entries")
    
    # Re-save with proper formatting
    with open('data/content.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("✓ Saved formatted JSON")
    
except json.JSONDecodeError as e:
    print(f"✗ Error: {e}")
    print(f"Line {e.lineno}, col {e.colno}: {e.msg}")
