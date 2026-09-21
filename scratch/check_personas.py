import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'django_app/voice_assistant/templates/voice_assistant/room.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
match = re.search(r'<div id="tab-personas"[^>]*>(.*?)</div>\s*<!-- ==================== Tab 3', text, re.DOTALL)
if match:
    print('Content length of tab-personas:', len(match.group(1).strip()))
    print('Preview:\n', match.group(1).strip()[:500])
else:
    print('tab-personas not matched with regex')
    # search where tab-personas is
    idx = text.find('id="tab-personas"')
    print('Found id="tab-personas" at index:', idx)
    print(text[idx:idx+800])
