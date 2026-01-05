import json
import re

# Read the broken file as text
with open('data/content.json.backup', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix known structural issues
content = content.replace('"l,', '"],')

# Strategy: Find description_de fields and escape/remove ALL quotes inside them
# Pattern: "description_de": "TEXT"
def fix_desc_de(match):
    value = match.group(1)
    # Replace all quote-like characters with simple single quotes or remove them
    value = value.replace('\u201e', '')  # „
    value = value.replace('\u201c', '')  # "
    value = value.replace('\u201d', '')  # "
    value = value.replace('"', '\\"')  # Escape any remaining "
    return f'"description_de": "{value}"'

content = re.sub(r'"description_de":\s*"([^"]*(?:[„""][^"]*)*)"', fix_desc_de, content, flags=re.DOTALL)

# Write out
with open('data/content.json', 'w', encoding='utf-8') as f:
    f.write(content)

# Now try to load and validate
try:
    with open('data/content.json') as f:
        data = json.load(f)
    print(f'✓ Geladen: {len(data)} entries')
    
    # Save it properly formatted
    with open('data/content.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print('✓ Neu geschrieben mit korrektem Escaping')
    
except json.JSONDecodeError as e:
    print(f'✗ Fehler Zeile {e.lineno}, Spalte {e.colno}: {e.msg}')
    lines = content.split('\n')
    if e.lineno <= len(lines):
        print(f'Zeile {e.lineno}: {lines[e.lineno-1][:200]}')
