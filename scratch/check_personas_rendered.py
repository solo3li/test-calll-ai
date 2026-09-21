import requests
import urllib3
import sys

sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()

s = requests.Session()
s.verify = False
s.get('https://localhost/login/')
csrf = s.cookies.get('csrftoken', '')
s.post('https://localhost/login/', data={'username': 'admin', 'password': 'admin123456', 'csrfmiddlewaretoken': csrf}, headers={'Referer': 'https://localhost/login/'})

r = s.get('https://localhost/api/agents/profiles/')
data = r.json()
print("Total profiles ready for rendering:", len(data['profiles']))
for p in data['profiles']:
    status = "[نشط للمكالمات]" if p['is_active'] else "[غير مفعل]"
    print(f" -> {p['name']} ({status}) - {p['dialect_display']} - Voice: {p['voice_name']}")
