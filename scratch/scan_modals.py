with open(r'django_app/voice_assistant/templates/voice_assistant/room.html.bak', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(840, 1278):
    l = lines[i]
    if 'id=' in l and 'modal' in l.lower():
        print(f'Line {i+1}: {l.strip()[:70]}')
