import re

# Read the backup
with open('data/content.json.backup', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix line 820: "l, → ],
content = content.replace('"l,', '"],')

# Remove ALL description_de lines (including multiline values)
# Pattern: match "description_de": "..." including newlines, up to the closing quote and comma
content = re.sub(
    r',?\s*"description_de":\s*"(?:[^"\\]|\\.)*"',
    '',
    content,
    flags=re.DOTALL
)

# Write out
with open('data/content.json', 'w', encoding='utf-8') as f:
    f.write(content)

print("description_de fields removed")

# Try to load
import json
try:
    with open('data/content.json') as f:
        data = json.load(f)
    print(f"✓ SUCCESS! {len(data)} entries loaded")
except json.JSONDecodeError as e:
    print(f"✗ Error: {e}")
