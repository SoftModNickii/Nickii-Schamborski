#!/usr/bin/env python3
import json
import re

# Load the now-working JSON
with open('data/content.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Read the backup line by line
with open('data/content.json.backup', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Extract description_de values
german_descriptions = {}
current_id = None

for line in lines:
    # Check for ID
    id_match = re.search(r'"id":\s*"([^"]+)"', line)
    if id_match:
        current_id = id_match.group(1)
    
    # Check for description_de
    if '"description_de":' in line and current_id:
        # Extract the value (everything after "description_de": ")
        value_match = re.search(r'"description_de":\s*"(.+)"', line)
        if value_match:
            desc_value = value_match.group(1)
            # Remove trailing comma if present
            if desc_value.endswith(','):
                desc_value = desc_value[:-1]
            # Clean up - remove German quotes „" and fancy quotes
            desc_value = desc_value.replace('„', '')
            desc_value = desc_value.replace('"', '')
            desc_value = desc_value.replace('"', '')
            german_descriptions[current_id] = desc_value

print(f"Extracted {len(german_descriptions)} German descriptions")

# Add description_de to matching entries
added = 0
for entry in data:
    entry_id = entry.get('id')
    if entry_id in german_descriptions:
        entry['description_de'] = german_descriptions[entry_id]
        added += 1
        print(f"✓ Added description_de to: {entry.get('title', entry_id)}")

print(f"\nAdded {added} German descriptions")

# Save with proper JSON encoding (auto-escapes everything)
with open('data/content.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("✓ Saved to content.json with proper escaping")

# Validate
with open('data/content.json', 'r', encoding='utf-8') as f:
    validated = json.load(f)
print(f"✓ Validation successful: {len(validated)} entries")
