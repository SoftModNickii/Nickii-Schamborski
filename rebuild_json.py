#!/usr/bin/env python3
"""
Nuclear option: Parse the broken JSON tolerantly
"""
import re
import json

with open('data/content.json.backup', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix known issues first
content = content.replace('"l,', '"],')

# Remove description_de  - match ONLY the description_de line
# Pattern: comma (optional), whitespace, "description_de": "VALUE",
# where VALUE can span multiple lines
def remove_desc_de(text):
    # Find all ,\s*"description_de": and match until the next ",\s*" pattern
    import re
    result = text
    while True:
        match = re.search(r',\s*"description_de":\s*"', result)
        if not match:
            break
        start = match.start()
        # Find the closing " followed by comma or }
        rest = result[match.end():]
        # Count quotes to find the matching close
        depth = 0
        pos = 0
        while pos < len(rest):
            if rest[pos] == '\\':
                pos += 2
                continue
            if rest[pos] == '"':
                # This is the closing quote
                # Check if followed by comma
                end_pos = pos + 1
                while end_pos < len(rest) and rest[end_pos] in ' \t\n':
                    end_pos += 1
                if end_pos < len(rest) and rest[end_pos] == ',':
                    end_pos += 1
                # Remove from start to end_pos
                result = result[:start] + result[match.end() + end_pos:]
                break
            pos += 1
        else:
            break  # Could not find closing
    return result

content = remove_desc_de(content)

# Save intermediate
with open('data/content_cleaned.json', 'w', encoding='utf-8') as f:
    f.write(content)

# Try to parse
try:
    data = json.loads(content)
    print(f"✓ SUCCESS! Loaded {len(data)} entries")
    
    # Re-save with proper formatting
    with open('data/content.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("✓ Saved to content.json")
    
except json.JSONDecodeError as e:
    print(f"Still broken: {e}")
    print(f"Line {e.lineno}: {e.msg}")
    
    # Show context
    lines = content.split('\n')
    start = max(0, e.lineno - 3)
    end = min(len(lines), e.lineno + 2)
    print("\nContext:")
    for i in range(start, end):
        marker = ">>> " if i == e.lineno - 1 else "    "
        print(f"{marker}{i+1}: {lines[i][:100]}")
