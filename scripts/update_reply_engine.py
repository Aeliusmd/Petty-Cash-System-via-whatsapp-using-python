import re

from pathlib import Path

# Read the file
target_file = Path(__file__).parent.parent / 'backend' / 'app' / 'reply_engine.py'
with open(target_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the specific section
old_pattern = r'''                
                return f"""📦 \*\{selected_cat\['name'\]\}\*

Please describe:
• What was purchased
• Amount
• Purpose

Example: "Stationery supplies, Rs\.1500, Office use\""""'''

new_code = '''                
                # Use custom prompt message if available, otherwise use default
                prompt = selected_cat.get('prompt_message')
                if not prompt:
                    prompt = f"""📦 *{selected_cat['name']}*

Please describe:
• What was purchased
• Amount
• Purpose

Example: "Stationery supplies, Rs.1500, Office use\""""
                
                return prompt'''

# Try to replace
if 'return f"""📦 *{selected_cat[\'name\']}*' in content:
    # Find the exact location
    lines = content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Look for the return statement
        if 'return f"""📦 *{selected_cat[\'name\']}*' in line:
            # Replace this section (lines 710-718)
            # Add the new code
            new_lines.append('                ')
            new_lines.append('                # Use custom prompt message if available, otherwise use default')
            new_lines.append('                prompt = selected_cat.get(\'prompt_message\')')
            new_lines.append('                if not prompt:')
            new_lines.append('                    prompt = f"""📦 *{selected_cat[\'name\']}*')
            new_lines.append('')
            new_lines.append('Please describe:')
            new_lines.append('• What was purchased')
            new_lines.append('• Amount')
            new_lines.append('• Purpose')
            new_lines.append('')
            new_lines.append('Example: "Stationery supplies, Rs.1500, Office use\""""')
            new_lines.append('                ')
            new_lines.append('                return prompt')
            # Skip the old lines (until we find the closing """)
            i += 1
            while i < len(lines) and 'Example: "Stationery supplies' not in lines[i]:
                i += 1
            i += 1  # Skip the line with Example
        else:
            new_lines.append(line)
        i += 1
    
    # Write back
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    print("✅ Successfully updated reply_engine.py")
else:
    print("❌ Could not find the target code section")
