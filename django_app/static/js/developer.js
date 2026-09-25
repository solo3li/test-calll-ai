/**
 * Developer API Portal JavaScript
 * Handles live API key retrieval, rotation, visibility toggling, and code samples.
 */

let currentDeveloperKey = '';

async function loadDeveloperKeys() {
  try {
    const res = await fetch('/api/v1/keys/');
    if (!res.ok) return;
    const data = await res.json();
    if (data.status === 'success' && data.keys && data.keys.length > 0) {
      const keyObj = data.keys[0];
      currentDeveloperKey = keyObj.key || keyObj.prefix;
      const keyInput = document.getElementById('dev-api-key-input');
      const createdEl = document.getElementById('dev-key-created-at');
      const usedEl = document.getElementById('dev-key-last-used');
      const curlSample = document.getElementById('dev-curl-sample');
      const curlDialSample = document.getElementById('dev-curl-dial-sample');

      if (keyInput) keyInput.value = currentDeveloperKey;
      if (createdEl) createdEl.innerText = keyObj.created_at || '--';
      if (usedEl) usedEl.innerText = keyObj.last_used_at || 'لم يُستخدم بعد';

      if (curlSample) {
        curlSample.innerText = `curl -X GET "${window.location.origin}/api/v1/account/" \\\n  -H "X-API-Key: ${currentDeveloperKey}" \\\n  -H "Accept: application/json"`;
      }
      if (curlDialSample) {
        curlDialSample.innerText = `curl -X POST "${window.location.origin}/api/v1/calls/dial/" \\\n  -H "X-API-Key: ${currentDeveloperKey}" \\\n  -H "Content-Type: application/json" \\\n  -d '{"phone_number": "+201012345678", "call_goal": "تأكيد تفاصيل الطلب رقم 1005"}'`;
      }
    }
  } catch (e) {
    console.error('Error loading developer keys:', e);
  }
}

function toggleDevKeyVisibility() {
  const inp = document.getElementById('dev-api-key-input');
  const btn = document.getElementById('btn-toggle-dev-key');
  if (!inp || !btn) return;
  if (inp.type === 'password') {
    inp.type = 'text';
    btn.innerText = '🙈';
  } else {
    inp.type = 'password';
    btn.innerText = '👁️';
  }
}

function copyDevApiKey() {
  const inp = document.getElementById('dev-api-key-input');
  if (inp) {
    navigator.clipboard.writeText(inp.value);
    showToast('تم نسخ مفتاح API بنجاح لاستخدامه في تطبيقاتك!', 'success');
  }
}

function copyDevCurlSample() {
  const sample = document.getElementById('dev-curl-sample');
  if (sample) {
    navigator.clipboard.writeText(sample.innerText);
    showToast('تم نسخ مثال cURL إلى الحافظة!', 'success');
  }
}

async function rotateDeveloperKeyPrompt() {
  if (!confirm('هل أنت متأكد من رغبتك في تدوير مفتاح الـ API؟ سيتوقف المفتاح القديم عن العمل فوراً ولن تتمكن أي تطبيقات تستخدمه من الوصول.')) {
    return;
  }
  try {
    const res = await fetch('/api/v1/keys/rotate/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify({ name: 'مفتاح التطبيق (مُحدّث)' })
    });
    const data = await res.json();
    if (data.status === 'success') {
      showToast('تم توليد مفتاح API جديد بنجاح.', 'success');
      await loadDeveloperKeys();
    } else {
      showToast(data.message || 'فشل تدوير المفتاح', 'error');
    }
  } catch (e) {
    console.error('Error rotating developer key:', e);
    showToast('حدث خطأ أثناء الاتصال بالخادم', 'error');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadDeveloperKeys();
});
