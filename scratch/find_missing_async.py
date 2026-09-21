import re

with open('scratch/test_room.js', encoding='utf-8') as f:
    code = f.read()

# Find all functions
fn_pattern = re.compile(r'(async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\([^)]*\)\s*\{')
pos = 0
results = []
for match in fn_pattern.finditer(code):
    is_async = bool(match.group(1))
    name = match.group(2)
    start = match.end()
    
    # find matching brace
    brace_count = 1
    i = start
    while i < len(code) and brace_count > 0:
        if code[i] == '{':
            brace_count += 1
        elif code[i] == '}':
            brace_count -= 1
        i += 1
    
    body = code[start:i]
    if 'await ' in body and not is_async:
        results.append(name)

print("Functions with await but missing async:", results)
