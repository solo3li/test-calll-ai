with open('django_app/voice_assistant/templates/voice_assistant/room.html', encoding='utf-8') as f:
    for i, l in enumerate(f):
        if 'id="tab-' in l:
            print(f'Line {i+1}: {l.strip()[:60]}')
