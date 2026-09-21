
    // Bilingual Localization Dictionary
    const I18N = {
      ar: {
        app_title: "المساعد الصوتي الذكي",
        app_subtitle: "منظومة الذكاء الاصطناعي",
        role_admin: "مدير النظام (Super Admin)",
        btn_django_admin: "⚙️ لوحة الإدارة",
        btn_logout: "🚪 خروج",
        nav_voice: "غرفة المساعد الصوتي",
        nav_personas: "الشخصيات واللهجات",
        nav_rag: "قاعدة المعرفة RAG",
        nav_callcenter: "مركز الاتصالات والطوابير",
        nav_telephony: "الربط الهاتفي والسنترال",
        nav_crm: "ذاكرة وسجل العملاء",
        nav_store: "متجر وأدوات MCP",
        metric_calls: "المكالمات النشطة",
        metric_latency: "زمن استجابة الـ AI",
        metric_rag: "فهرس المعرفة",
        metric_rag_status: "متصل ومحدث",
        metric_queue: "جاهزية الطوابير",
        floating_hint: "محادثة مستمرة عبر LiveKit",
        btn_full_room: "غرفة الصوت",
        switch_to: "English"
      },
      en: {
        app_title: "Smart Voice AI",
        app_subtitle: "Enterprise Voice Platform",
        role_admin: "Super Admin",
        btn_django_admin: "⚙️ Admin Panel",
        btn_logout: "🚪 Logout",
        nav_voice: "Voice Assistant Room",
        nav_personas: "AI Personas & Dialects",
        nav_rag: "Knowledge Base (RAG)",
        nav_callcenter: "Call Center & Queues",
        nav_telephony: "Telephony & PBX",
        nav_crm: "Customer CRM & Memory",
        nav_store: "FastMCP Store & Tools",
        metric_calls: "Active Calls",
        metric_latency: "AI Response Latency",
        metric_rag: "Knowledge Index",
        metric_rag_status: "Online & Indexed",
        metric_queue: "Queue Readiness",
        floating_hint: "Live session streaming via LiveKit",
        btn_full_room: "Voice Room",
        switch_to: "العربية"
      }
    };

    let currentLanguage = localStorage.getItem('voice_app_lang') || 'ar';
    let activeTabId = 'voice';

    function applyLanguage(lang) {
      currentLanguage = lang;
      localStorage.setItem('voice_app_lang', lang);
      const isRtl = lang === 'ar';
      
      document.documentElement.dir = isRtl ? 'rtl' : 'ltr';
      document.documentElement.lang = lang;
      
      // Update lang switch button text
      const langText = document.getElementById('lang-text');
      if (langText) {
        langText.innerText = I18N[lang].switch_to;
      }

      // Update all elements with data-i18n
      document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (I18N[lang] && I18N[lang][key]) {
          el.innerText = I18N[lang][key];
        }
      });

      // Update current section title
      updateHeaderTitle();
    }

    function toggleLanguage() {
      const nextLang = currentLanguage === 'ar' ? 'en' : 'ar';
      applyLanguage(nextLang);
    }

    function updateHeaderTitle() {
      const titleEl = document.querySelector('#current-section-title span');
      if (titleEl) {
        const key = 'nav_' + activeTabId;
        if (I18N[currentLanguage] && I18N[currentLanguage][key]) {
          titleEl.innerText = I18N[currentLanguage][key];
        }
      }
    }

    // SPA Tab Switching Logic
    function switchTab(tabId) {
      activeTabId = tabId;
      
      // Hide all panels
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      
      // Show selected panel
      const target = document.getElementById('tab-' + tabId);
      if (target) {
        target.classList.add('active');
      }

      // Update sidebar nav active styling
      document.querySelectorAll('.nav-item').forEach(btn => {
        btn.classList.remove('bg-white/15', 'text-white', 'border', 'border-[#D4AF37]/30');
        btn.classList.add('text-[#EADBC8]');
      });
      
      const activeNavBtn = document.getElementById('nav-btn-' + tabId);
      if (activeNavBtn) {
        activeNavBtn.classList.add('bg-white/15', 'text-white', 'border', 'border-[#D4AF37]/30');
        activeNavBtn.classList.remove('text-[#EADBC8]');
      }

      updateHeaderTitle();
      syncFloatingVoiceBar();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // Sidebar Collapse / Expand
    function toggleSidebar() {
      const sidebar = document.getElementById('sidebar');
      const icon = document.getElementById('sidebar-toggle-icon');
      if (!sidebar) return;

      const isExpanded = sidebar.classList.contains('sidebar-expanded');
      if (isExpanded) {
        sidebar.classList.remove('sidebar-expanded');
        sidebar.classList.add('sidebar-collapsed');
        if (icon) icon.classList.add('rotate-180');
      } else {
        sidebar.classList.remove('sidebar-collapsed');
        sidebar.classList.add('sidebar-expanded');
        if (icon) icon.classList.remove('rotate-180');
      }
    }

    // Sync Floating Voice Widget when browsing other sections
    function syncFloatingVoiceBar() {
      const floatingBar = document.getElementById('floating-voice-bar');
      if (!floatingBar) return;

      // Show floating bar only if we are outside the voice room AND call is active
      const isVoiceRoom = activeTabId === 'voice';
      const isCallActive = (livekitRoom && livekitRoom.state === 'connected') || (btnEnd && !btnEnd.disabled);

      if (!isVoiceRoom && isCallActive) {
        floatingBar.classList.remove('opacity-0', 'pointer-events-none', 'scale-95');
        floatingBar.classList.add('opacity-100', 'pointer-events-auto', 'scale-100');
        
        const floatingStatus = document.getElementById('floating-status');
        const mainCallStatus = document.getElementById('call-status');
        if (floatingStatus && mainCallStatus) {
          floatingStatus.innerText = mainCallStatus.innerText;
        }
      } else {
        floatingBar.classList.add('opacity-0', 'pointer-events-none', 'scale-95');
        floatingBar.classList.remove('opacity-100', 'pointer-events-auto', 'scale-100');
      }
    }

    // Periodically check floating voice bar state
    setInterval(syncFloatingVoiceBar, 1000);

    // Apply saved language on page boot
    document.addEventListener('DOMContentLoaded', () => {
      applyLanguage(currentLanguage);
    });

    // ==================== ORIGINAL ENGINE JAVASCRIPT ====================
    
    let livekitRoom = null;
    let centrifugeClient = null;
    let currentSubscription = null;
    let isMuted = false;
    let audioContext = null;
    let micAnalyser = null;
    let micSource = null;
    let micAnimId = null;

    // DOM Elements
    const btnStart = document.getElementById('btn-start');
    const btnMute = document.getElementById('btn-mute');
    const btnEnd = document.getElementById('btn-end');
    const callStatus = document.getElementById('call-status');
    const subStatus = document.getElementById('sub-status');
    const orb = document.getElementById('visualizer-orb');
    const transcriptBox = document.getElementById('transcript-box');
    const cfStatusBadge = document.getElementById('centrifugo-status');
    const lkStatusBadge = document.getElementById('livekit-status');
    const micContainer = document.getElementById('mic-level-container');
    const micBar = document.getElementById('mic-level-bar');
    const micText = document.getElementById('mic-level-text');

    const fileInput = document.getElementById('file-input');
    const uploadLabel = document.getElementById('upload-file-label');
    const btnUpload = document.getElementById('btn-upload');
    const uploadStatus = document.getElementById('upload-status');
    const docsTbody = document.getElementById('docs-tbody');

    function getCookie(name) {
      let cookieValue = null;
      if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          if (cookie.substring(0, name.length + 1) === (name + '=')) {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
          }
        }
      }
      return cookieValue;
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    function appendTranscript(speaker, text) {
      if (transcriptBox.querySelector('.italic')) {
        transcriptBox.innerHTML = '';
      }
      const div = document.createElement('div');
      div.className = speaker === 'user' 
        ? 'p-2.5 rounded-lg bg-blue-950/60 border border-blue-900 text-blue-200 self-end ml-12'
        : (speaker === 'system'
            ? 'p-2 rounded-lg bg-emerald-950/40 border border-emerald-800/50 text-emerald-300 text-xs my-1'
            : 'p-2.5 rounded-lg bg-slate-800/80 border border-slate-700 text-slate-200 mr-12');
      
      const label = speaker === 'user' ? 'أنت:' : (speaker === 'system' ? 'النظام:' : 'المساعدة الصوتية:');
      div.innerHTML = `<span class="font-bold block text-xs opacity-75 mb-1">${label}</span><span>${text}</span>`;
      transcriptBox.appendChild(div);
      transcriptBox.scrollTop = transcriptBox.scrollHeight;
    }

    function startMicVisualizer(mediaStream) {
      try {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        micSource = audioContext.createMediaStreamSource(mediaStream);
        micAnalyser = audioContext.createAnalyser();
        micAnalyser.fftSize = 256;
        micSource.connect(micAnalyser);
        micContainer.classList.remove('hidden');

        const dataArray = new Uint8Array(micAnalyser.frequencyBinCount);
        function updateLevel() {
          if (!micAnalyser) return;
          micAnalyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          const avg = sum / dataArray.length;
          const pct = Math.min(100, Math.round((avg / 128) * 100));
          micBar.style.width = pct + '%';
          micText.innerText = pct + '%';
          micAnimId = requestAnimationFrame(updateLevel);
        }
        updateLevel();
      } catch (e) {
        console.warn('Could not start mic visualizer:', e);
      }
    }

    function stopMicVisualizer() {
      if (micAnimId) cancelAnimationFrame(micAnimId);
      if (audioContext) audioContext.close();
      audioContext = null;
      micAnalyser = null;
      micSource = null;
      micContainer.classList.add('hidden');
      micBar.style.width = '0%';
    }

    async function startCall() {
      btnStart.disabled = true;
      btnStart.classList.add('opacity-40', 'pointer-events-none');
      callStatus.innerText = 'جاري طلب صلاحيات الاتصال والمفاتيح...';
      
      try {
        // 1. Fetch Tokens from Django
        const res = await fetch('/api/token/?t=' + Date.now());
        const data = await res.json();
        if (data.status !== 'success') {
          throw new Error('فشل جلب رموز الاتصال من الخادم');
        }

        callStatus.innerText = 'جاري الاتصال بـ LiveKit...';

        // 2. Connect to Centrifugo (App WebSockets)
        try {
          centrifugeClient = new Centrifuge(data.centrifugo_ws_url, {
            token: data.centrifugo_token
          });

          centrifugeClient.on('connecting', () => {
            cfStatusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-yellow-500"></span> Centrifugo: جاري الاتصال';
          });

          centrifugeClient.on('connected', () => {
            cfStatusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-500"></span> Centrifugo: متصل';
          });

          centrifugeClient.on('disconnected', () => {
            cfStatusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-red-500"></span> Centrifugo: منقطع';
          });

          currentSubscription = centrifugeClient.newSubscription(data.channel);
          currentSubscription.on('publication', (ctx) => {
            handleAgentEvent(ctx.data);
          });
          currentSubscription.subscribe();
          centrifugeClient.connect();
        } catch (cfErr) {
          console.warn('Centrifugo connection skipped:', cfErr);
        }

        // 3. Connect to LiveKit Room (WebRTC)
        livekitRoom = new LivekitClient.Room({
          adaptiveStream: true,
          dynacast: true,
        });

        livekitRoom.on(LivekitClient.RoomEvent.Connected, () => {
          lkStatusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-500"></span> LiveKit: متصل';
          callStatus.innerText = 'تم الانضمام للغرفة. جاري تشغيل المساعد الذكي وقاعدة المستندات...';
          subStatus.innerText = 'المساعد الصوتي ينضم الآن...';
        });

        livekitRoom.on(LivekitClient.RoomEvent.ParticipantConnected, (participant) => {
          console.log('[LiveKit] Participant connected:', participant.identity);
          if (participant.identity === 'pipecat-agent') {
            callStatus.innerText = 'المساعد متصل في الغرفة!';
            subStatus.innerText = 'تحدث الآن بصوتك، المساعد يستمع إليك ويجيب من مستنداتك';
          }
        });

        livekitRoom.on(LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {
          console.log('[LiveKit] Subscribed to track:', track.kind, participant.identity);
          if (track.kind === LivekitClient.Track.Kind.Audio) {
            const audioElement = track.attach();
            document.body.appendChild(audioElement);
            callStatus.innerText = 'المساعد متصل ويستمع إليك الآن';
            subStatus.innerText = 'تحدث بصوتك مباشرة عبر المايكروفون';
            orb.classList.add('agent-active');
          }
        });

        livekitRoom.on(LivekitClient.RoomEvent.Disconnected, () => {
          lkStatusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-gray-500"></span> LiveKit: غير متصل';
          cleanupCall();
        });

        // Connect and enable microphone
        await livekitRoom.connect(data.livekit_url, data.livekit_token);
        await livekitRoom.localParticipant.setMicrophoneEnabled(true, {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        });

        // Attach local mic to visualizer
        const localAudioTrack = livekitRoom.localParticipant.getTrackPublication(LivekitClient.Track.Source.Microphone);
        if (localAudioTrack && localAudioTrack.track && localAudioTrack.track.mediaStream) {
          startMicVisualizer(localAudioTrack.track.mediaStream);
        }

        btnMute.disabled = false;
        btnEnd.disabled = false;

      } catch (err) {
        console.error(err);
        alert('حدث خطأ أثناء بدء المكالمة: ' + err.message);
        cleanupCall();
      }
    }

    function handleAgentEvent(data) {
      if (data.event === 'agent_queued') {
        callStatus.innerText = data.message;
      } else if (data.event === 'agent_connected' || data.event === 'agent_ready' || data.event === 'agent_listening') {
        callStatus.innerText = 'المساعد متصل ويستمع إليك الآن';
        subStatus.innerText = 'تحدث بصوتك مباشرة عبر المايكروفون';
        orb.classList.add('agent-active');
      } else if (data.event === 'agent_speaking') {
        subStatus.innerText = 'المساعد يتحدث الآن...';
      } else if (data.event === 'agent_interrupted') {
        callStatus.innerText = 'المساعد يستمع إليك الآن';
        subStatus.innerText = 'المساعد استمع لمقاطعتك وتوقف عن الحديث...';
      } else if (data.event === 'agent_searching_rag') {
        subStatus.innerText = 'جاري البحث الدلالي في مستنداتك...';
        appendTranscript('system', '🔍 جاري البحث الدلالي في مستندات قاعدة المعرفة...');
      } else if (data.event === 'agent_action_executing') {
        subStatus.innerText = data.message;
        appendTranscript('system', `⚙️ ${data.message}`);
      } else if (data.event === 'transcription_user') {
        appendTranscript('user', data.message);
      } else if (data.event === 'transcription_agent') {
        appendTranscript('agent', data.message);
      } else if (data.event === 'agent_error') {
        callStatus.innerText = 'تنبيه: ' + data.message;
      }
    }

    async function toggleMute() {
      if (!livekitRoom) return;
      isMuted = !isMuted;
      await livekitRoom.localParticipant.setMicrophoneEnabled(!isMuted);
      document.getElementById('txt-mute').innerText = isMuted ? 'تشغيل المايك' : 'كتم المايك';
      btnMute.classList.toggle('bg-amber-600', isMuted);
    }

    async function endCall() {
      cleanupCall();
    }

    function cleanupCall() {
      stopMicVisualizer();
      if (livekitRoom) {
        livekitRoom.disconnect();
        livekitRoom = null;
      }
      if (centrifugeClient) {
        centrifugeClient.disconnect();
        centrifugeClient = null;
      }
      orb.classList.remove('agent-active');
      btnStart.disabled = false;
      btnStart.classList.remove('opacity-40', 'pointer-events-none');
      btnMute.disabled = true;
      btnEnd.disabled = true;
      callStatus.innerText = 'تم إنهاء المكالمة';
      subStatus.innerText = 'اضغط بدء المحادثة للاتصال مجدداً';
    }

    // ==================== Document Ingestion Handling ====================

    function handleFileSelect(e) {
      if (fileInput.files && fileInput.files.length > 0) {
        uploadLabel.innerText = fileInput.files[0].name;
        btnUpload.disabled = false;
      } else {
        uploadLabel.innerText = 'اختر ملفاً (PDF/DOCX/TXT)';
        btnUpload.disabled = true;
      }
    }

    async function loadDocuments() {
      try {
        const res = await fetch('/api/knowledge/documents/');
        const data = await res.json();
        if (data.status === 'success') {
          renderDocuments(data.documents);
        }
      } catch (err) {
        console.error('Error fetching documents:', err);
      }
    }

    function renderDocuments(docs) {
      if (!docs || docs.length === 0) {
        docsTbody.innerHTML = `
          <tr>
            <td colspan="5" class="text-center py-6 text-slate-500">
              لا توجد مستندات مرفوعة بعد. ارفع أول ملف لبدء الإجابة منه!
            </td>
          </tr>
        `;
        return;
      }

      docsTbody.innerHTML = docs.map(d => `
        <tr class="hover:bg-slate-800/30 transition">
          <td class="py-3 px-3 font-medium text-slate-200 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-slate-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            ${d.title}
          </td>
          <td class="py-3 px-3 text-slate-400 uppercase">${d.file_type}</td>
          <td class="py-3 px-3 text-indigo-400 font-semibold">${d.chunks_count} مقطع</td>
          <td class="py-3 px-3 text-slate-400">${d.created_at}</td>
          <td class="py-3 px-3 text-center">
            <button onclick="deleteDocument(${d.id})" class="text-rose-400 hover:text-rose-300 p-1.5 rounded-lg hover:bg-rose-950/40 transition">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </td>
        </tr>
      `).join('');
    }

    async function uploadDocument(e) {
      e.preventDefault();
      if (!fileInput.files || fileInput.files.length === 0) return;

      const file = fileInput.files[0];
      const formData = new FormData();
      formData.append('file', file);

      btnUpload.disabled = true;
      btnUpload.innerHTML = `
        <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
        </svg>
        جاري المعالجة والتضمين...
      `;

      uploadStatus.className = 'mt-4 p-3 rounded-xl text-xs bg-indigo-950/80 border border-indigo-800 text-indigo-300 flex items-center gap-2';
      uploadStatus.innerHTML = 'جاري استخراج النصوص وتوليد التضمينات الدلالية عبر Gemini...';
      uploadStatus.classList.remove('hidden');

      try {
        const res = await fetch('/api/knowledge/documents/upload/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCookie('csrftoken'),
          },
          body: formData,
        });
        const result = await res.json();
        if (result.status === 'success') {
          uploadStatus.className = 'mt-4 p-3 rounded-xl text-xs bg-emerald-950/80 border border-emerald-800 text-emerald-300 flex items-center gap-2';
          uploadStatus.innerHTML = result.message;
          fileInput.value = '';
          uploadLabel.innerText = 'اختر ملفاً (PDF/DOCX/TXT)';
          await loadDocuments();
        } else {
          uploadStatus.className = 'mt-4 p-3 rounded-xl text-xs bg-red-950/80 border border-red-800 text-red-300 flex items-center gap-2';
          uploadStatus.innerHTML = 'فشل الرفع: ' + (result.message || 'خطأ غير معروف');
        }
      } catch (err) {
        uploadStatus.className = 'mt-4 p-3 rounded-xl text-xs bg-red-950/80 border border-red-800 text-red-300 flex items-center gap-2';
        uploadStatus.innerHTML = 'خطأ في الاتصال بالخادم أثناء الرفع.';
      } finally {
        btnUpload.disabled = false;
        btnUpload.innerHTML = '<span>رفع ومعالجة</span>';
      }
    }

    async function deleteDocument(docId) {
      if (!confirm('هل أنت متأكد من رغبتك في حذف هذا المستند وحذف جميع مقاطعه الدلالية؟')) return;
      try {
        const res = await fetch(`/api/knowledge/documents/${docId}/delete/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCookie('csrftoken'),
          }
        });
        const result = await res.json();
        if (result.status === 'success') {
          await loadDocuments();
        } else {
          alert('فشل الحذف: ' + (result.message || 'خطأ غير معروف'));
        }
      } catch (err) {
        alert('حدث خطأ أثناء الاتصال بالخادم لحذف المستند.');
      }
    }


    // ==================== External FastMCP Server Handling ====================
    let currentMcpServer = null;

    const mcpModal = document.getElementById('mcp-modal');
    const mcpServerName = document.getElementById('mcp-server-name');
    const mcpServerUrl = document.getElementById('mcp-server-url');
    const mcpActiveBadge = document.getElementById('mcp-active-badge');
    const mcpStatusDot = document.getElementById('mcp-status-dot');
    const mcpLastSync = document.getElementById('mcp-last-sync');
    const btnToggleMcp = document.getElementById('btn-toggle-mcp');
    const mcpToolsCount = document.getElementById('mcp-tools-count');
    const mcpToolsContainer = document.getElementById('mcp-tools-container');
    const mcpSyncAlert = document.getElementById('mcp-sync-alert');

    async function loadMcpServer() {
      try {
        const res = await fetch('/api/agents/mcp/');
        const data = await res.json();
        if (data.status === 'success') {
          currentMcpServer = data.server;
          renderMcpServer(currentMcpServer);
        }
      } catch (err) {
        console.error('Error loading MCP server info:', err);
      }
    }

    function renderMcpServer(server) {
      const btnSync = document.getElementById('btn-sync-mcp');
      const btnSettingsLabel = document.getElementById('btn-mcp-settings-label');
      const btnDelete = document.getElementById('btn-delete-mcp');
      const modalBtnDelete = document.getElementById('modal-btn-delete-mcp');

      if (!server) {
        mcpServerName.innerText = 'لا يوجد خادم MCP مرتبط حالياً';
        mcpServerUrl.innerText = 'غير محدد';
        mcpLastSync.innerText = '';
        mcpStatusDot.className = 'w-2.5 h-2.5 rounded-full bg-slate-600';
        mcpActiveBadge.className = 'px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-800 border border-slate-700 text-slate-400';
        mcpActiveBadge.innerText = 'غير متصل';
        btnToggleMcp.classList.add('hidden');
        if (btnDelete) btnDelete.classList.add('hidden');
        if (modalBtnDelete) modalBtnDelete.classList.add('hidden');
        if (btnSettingsLabel) btnSettingsLabel.innerText = 'ربط خادم MCP';
        if (btnSync) btnSync.classList.add('hidden');

        mcpToolsCount.innerText = '0';
        mcpToolsContainer.innerHTML = `
          <div class="col-span-3 text-center py-8 text-slate-500 text-xs bg-slate-950/30 rounded-2xl border border-dashed border-slate-800 space-y-3">
            <p>لا يوجد خادم MCP مرتبط حالياً. يمكنك ربط خادمك الخارجي لتمكين المساعد الصوتي من استدعاء أدواتك أثناء المكالمات.</p>
            <button type="button" onclick="openMcpModal()" class="px-4 py-2 rounded-xl bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 border border-cyan-700/60 text-xs font-semibold transition inline-flex items-center gap-1.5">
              <span>⚡</span>
              <span>ربط خادم FastMCP الآن</span>
            </button>
          </div>
        `;
        return;
      }

      // Server is present
      btnToggleMcp.classList.remove('hidden');
      if (btnDelete) btnDelete.classList.remove('hidden');
      if (modalBtnDelete) modalBtnDelete.classList.remove('hidden');
      if (btnSettingsLabel) btnSettingsLabel.innerText = 'الإعدادات';
      if (btnSync) btnSync.classList.remove('hidden');

      mcpServerName.innerText = server.name;
      mcpServerUrl.innerText = server.server_url;
      mcpLastSync.innerText = server.last_synced_at ? `آخر مزامنة: ${server.last_synced_at}` : 'آخر مزامنة: لم تتم بعد';

      if (server.is_active) {
        mcpStatusDot.className = 'w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse';
        mcpActiveBadge.className = 'px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950 border border-emerald-800 text-emerald-300';
        mcpActiveBadge.innerText = 'مفعل للمكالمات';
        btnToggleMcp.innerText = 'تعطيل';
        btnToggleMcp.className = 'px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-medium transition';
      } else {
        mcpStatusDot.className = 'w-2.5 h-2.5 rounded-full bg-slate-500';
        mcpActiveBadge.className = 'px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-800 border border-slate-700 text-slate-400';
        mcpActiveBadge.innerText = 'معطل';
        btnToggleMcp.innerText = 'تفعيل';
        btnToggleMcp.className = 'px-3 py-1.5 rounded-xl bg-emerald-900/60 hover:bg-emerald-800/80 text-emerald-300 border border-emerald-700 text-xs font-medium transition';
      }

      const tools = server.cached_tools || [];
      mcpToolsCount.innerText = tools.length;
      if (tools.length === 0) {
        mcpToolsContainer.innerHTML = `
          <div class="col-span-3 text-center py-6 text-slate-500 text-xs bg-slate-950/30 rounded-2xl border border-dashed border-slate-800">
            لا توجد أدوات مكتشفة حتى الآن. اضغط على "فحص الاتصال وتحديث الأدوات" لقراءة دوال خادم FastMCP تلقائياً.
          </div>
        `;
      } else {
        mcpToolsContainer.innerHTML = tools.map(t => {
          const paramsList = t.parameters && t.parameters.properties ? Object.keys(t.parameters.properties) : [];
          const badges = paramsList.map(p => `<span class="px-1.5 py-0.5 rounded bg-slate-950/80 border border-slate-800 text-slate-400 font-mono text-[10px]">${p}</span>`).join(' ');
          return `
            <div class="p-3.5 rounded-2xl bg-slate-800/50 border border-slate-700/60 hover:border-cyan-500/40 transition shadow-sm space-y-2">
              <div class="flex items-center justify-between">
                <span class="font-mono font-bold text-cyan-400 text-xs flex items-center gap-1.5">
                  <span class="text-[10px]">⚡</span>
                  ${t.name}
                </span>
                <span class="text-[10px] px-2 py-0.5 rounded-full bg-cyan-950/60 border border-cyan-800/50 text-cyan-300 font-semibold">FastMCP</span>
              </div>
              <p class="text-slate-300 text-[11px] leading-relaxed line-clamp-2" title="${t.description}">${t.description || 'بدون وصف'}</p>
              ${badges ? `<div class="pt-1 flex flex-wrap gap-1 items-center"><span class="text-[10px] text-slate-500">المعاملات:</span> ${badges}</div>` : ''}
            </div>
          `;
        }).join('');
      }
    }

    async function syncMcpServer() {
      if (!currentMcpServer) {
        alert('يرجى ربط خادم MCP أولاً قبل إجراء الفحص.');
        return;
      }
      const btn = document.getElementById('btn-sync-mcp');
      const label = document.getElementById('sync-mcp-label');
      btn.disabled = true;
      label.innerText = 'جاري الاتصال واكتشاف الأدوات...';
      mcpSyncAlert.classList.add('hidden');

      try {
        const res = await fetch('/api/agents/mcp/sync/', {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        const data = await res.json();
        if (data.status === 'success') {
          currentMcpServer = data.server;
          renderMcpServer(currentMcpServer);
          mcpSyncAlert.className = 'mt-3 p-3 rounded-xl text-xs bg-emerald-950/80 border border-emerald-800 text-emerald-300 flex items-center gap-2';
          mcpSyncAlert.innerHTML = `<span>✅ ${data.message}</span>`;
          mcpSyncAlert.classList.remove('hidden');
        } else {
          mcpSyncAlert.className = 'mt-3 p-3 rounded-xl text-xs bg-rose-950/80 border border-rose-800 text-rose-300 flex items-center gap-2';
          mcpSyncAlert.innerHTML = `<span>❌ ${data.message}</span>`;
          mcpSyncAlert.classList.remove('hidden');
        }
      } catch (err) {
        mcpSyncAlert.className = 'mt-3 p-3 rounded-xl text-xs bg-rose-950/80 border border-rose-800 text-rose-300 flex items-center gap-2';
        mcpSyncAlert.innerHTML = `<span>❌ حدث خطأ في الاتصال بالخادم.</span>`;
        mcpSyncAlert.classList.remove('hidden');
      } finally {
        btn.disabled = false;
        label.innerText = 'فحص الاتصال وتحديث الأدوات';
      }
    }

    async function toggleMcpActive() {
      if (!currentMcpServer) return;
      try {
        const res = await fetch('/api/agents/mcp/toggle/', {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        const data = await res.json();
        if (data.status === 'success' && currentMcpServer) {
          currentMcpServer.is_active = data.is_active;
          renderMcpServer(currentMcpServer);
        }
      } catch (err) {
        alert('حدث خطأ أثناء تغيير حالة خادم MCP.');
      }
    }

    async function deleteMcpServer() {
      if (!confirm('هل أنت متأكد من رغبتك في حذف خادم MCP؟\nسيتم إزالة جميع الأدوات المرتبطة به ولن يتمكن المساعد الصوتي من استدعائها أثناء المكالمات.')) {
        return;
      }

      try {
        const res = await fetch('/api/agents/mcp/delete/', {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        const data = await res.json();
        if (data.status === 'success') {
          currentMcpServer = null;
          closeMcpModal();
          renderMcpServer(null);
          mcpSyncAlert.className = 'mt-3 p-3 rounded-xl text-xs bg-amber-950/80 border border-amber-800 text-amber-300 flex items-center gap-2';
          mcpSyncAlert.innerHTML = `<span>🗑️ ${data.message}</span>`;
          mcpSyncAlert.classList.remove('hidden');
        } else {
          alert('فشل حذف خادم MCP: ' + (data.message || ''));
        }
      } catch (err) {
        alert('حدث خطأ أثناء الاتصال بالخادم لحذف خادم MCP.');
      }
    }

    function openMcpModal() {
      const modalTitle = document.getElementById('modal-mcp-title');
      const modalBtnDelete = document.getElementById('modal-btn-delete-mcp');

      if (currentMcpServer) {
        if (modalTitle) modalTitle.innerHTML = '<span>⚙️</span> إعدادات خادم FastMCP الخارجي';
        document.getElementById('modal-mcp-name').value = currentMcpServer.name;
        document.getElementById('modal-mcp-url').value = currentMcpServer.server_url;
        document.getElementById('modal-mcp-token').value = currentMcpServer.auth_token || '';
        document.getElementById('modal-mcp-active').checked = currentMcpServer.is_active;
        if (modalBtnDelete) modalBtnDelete.classList.remove('hidden');
      } else {
        if (modalTitle) modalTitle.innerHTML = '<span>⚡</span> ربط خادم FastMCP خارجي جديد';
        document.getElementById('modal-mcp-name').value = 'خادم متجر خارجي (FastMCP)';
        document.getElementById('modal-mcp-url').value = 'http://mock-store:8002/sse';
        document.getElementById('modal-mcp-token').value = '';
        document.getElementById('modal-mcp-active').checked = true;
        if (modalBtnDelete) modalBtnDelete.classList.add('hidden');
      }
      mcpModal.classList.remove('hidden');
    }

    function closeMcpModal() {
      mcpModal.classList.add('hidden');
    }

    async function saveMcpSettings(e) {
      e.preventDefault();
      const name = document.getElementById('modal-mcp-name').value.trim();
      const server_url = document.getElementById('modal-mcp-url').value.trim();
      const auth_token = document.getElementById('modal-mcp-token').value.trim();
      const is_active = document.getElementById('modal-mcp-active').checked;

      const btn = document.getElementById('btn-save-mcp-settings');
      btn.disabled = true;
      btn.innerText = 'جاري الحفظ...';

      try {
        const res = await fetch('/api/agents/mcp/save/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: JSON.stringify({ name, server_url, auth_token, is_active })
        });
        const data = await res.json();
        if (data.status === 'success') {
          currentMcpServer = data.server;
          renderMcpServer(currentMcpServer);
          closeMcpModal();
          // Prompt auto sync if no cached tools yet
          if (!currentMcpServer.cached_tools || currentMcpServer.cached_tools.length === 0) {
            syncMcpServer();
          }
        } else {
          alert('فشل الحفظ: ' + (data.message || ''));
        }
      } catch (err) {
        alert('حدث خطأ أثناء حفظ الإعدادات.');
      } finally {
        btn.disabled = false;
        btn.innerText = 'حفظ التعديلات';
      }
    }

    // ==================== Agent Voice & Persona Profiles Handling ====================
    let userProfiles = [];
    let activeProfile = null;
    let googleVoices = [];

    const profileSelect = document.getElementById('profile-select');
    const fieldGender = document.getElementById('field-gender');
    const fieldDialect = document.getElementById('field-dialect');
    const fieldVoice = document.getElementById('field-voice');
    const fieldRole = document.getElementById('field-role');
    const fieldStyle = document.getElementById('field-style');
    const fieldCustom = document.getElementById('field-custom');
    const voiceTagBadge = document.getElementById('voice-tag-badge');
    const profileStatusMsg = document.getElementById('profile-status-msg');

    const profileModal = document.getElementById('profile-modal');
    const newProfVoice = document.getElementById('new-prof-voice');
    const newProfGender = document.getElementById('new-prof-gender');

    
    // Render Visual Personas Cards Grid
    function renderProfileCards() {
      const container = document.getElementById('personas-cards-grid');
      if (!container) return;

      if (!userProfiles || userProfiles.length === 0) {
        container.innerHTML = `
          <div class="col-span-2 text-center py-10 bg-white rounded-3xl border border-[#EAE3D9] text-[#8C827A] text-xs">
            لا توجد شخصيات مسجلة حالياً. اضغط على "+ إنشاء شخصية جديدة" للبدء.
          </div>
        `;
        return;
      }

      container.innerHTML = userProfiles.map(p => {
        const isActive = Boolean(p.is_active);
        const isFemale = p.gender === 'female';
        const avatarBg = isActive ? 'from-[#680E23] to-[#8C1633]' : 'from-[#78716C] to-[#57534E]';
        const avatarEmoji = isFemale ? '👩🏻‍💼' : '👨🏻‍💼';

        return `
          <div class="bg-white rounded-3xl p-5 border ${isActive ? 'border-2 border-[#D4AF37] shadow-lg shadow-[#680E23]/10 ring-2 ring-[#680E23]/10' : 'border border-[#EAE3D9] shadow-sm hover:border-[#C5A880]'} transition-all duration-300 flex flex-col justify-between gap-4">
            
            <!-- Card Header -->
            <div class="flex items-start justify-between gap-3">
              <div class="flex items-center gap-3">
                <div class="w-12 h-12 rounded-2xl bg-gradient-to-tr ${avatarBg} text-2xl flex items-center justify-center text-white shadow shrink-0">
                  ${avatarEmoji}
                </div>
                <div>
                  <h4 class="text-sm font-bold text-[#1C1917] flex items-center gap-2">
                    ${escapeHtml(p.name)}
                  </h4>
                  <p class="text-xs text-[#6E645D] font-medium mt-0.5">
                    ${escapeHtml(p.persona_role_display || p.persona_role)}
                  </p>
                </div>
              </div>

              <!-- Active Status Badge -->
              <div>
                ${isActive 
                  ? `<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-300 shadow-sm">
                       <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                       نشط للمكالمات
                     </span>`
                  : `<span class="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-semibold bg-[#FAF7F2] text-[#8C827A] border border-[#DDD5C7]">
                       غير مفعل
                     </span>`
                }
              </div>
            </div>

            <!-- Dialect & Voice Tags -->
            <div class="flex flex-wrap items-center gap-2 text-xs">
              <span class="px-2.5 py-1 rounded-lg bg-[#FAF0F2] text-[#680E23] font-semibold border border-[#E8CCD2] flex items-center gap-1">
                📍 ${escapeHtml(p.dialect_display || p.dialect)}
              </span>
              <span class="px-2.5 py-1 rounded-lg bg-[#FAF7F2] text-[#443D39] font-medium border border-[#EAE3D9] flex items-center gap-1 font-mono text-[11px]">
                🎙️ ${escapeHtml(p.voice_name)}
              </span>
              <span class="px-2.5 py-1 rounded-lg bg-[#FAF7F2] text-[#6E645D] border border-[#EAE3D9]">
                ✨ ${escapeHtml(p.speaking_style_display || p.speaking_style)}
              </span>
            </div>

            <!-- Stylized Soundwave Bar -->
            <div class="py-2 px-3.5 bg-[#FAF7F2] rounded-xl border border-[#EAE3D9] flex items-center justify-between gap-2">
              <span class="text-[10px] text-[#8C827A] font-medium">مخطط النبرة الصوتية:</span>
              <div class="flex items-center gap-1 h-4">
                <span class="w-1 bg-[#680E23] rounded-full ${isActive ? 'h-3 animate-pulse' : 'h-1.5'}"></span>
                <span class="w-1 bg-[#680E23] rounded-full ${isActive ? 'h-4 animate-pulse' : 'h-2'}"></span>
                <span class="w-1 bg-[#D4AF37] rounded-full ${isActive ? 'h-2 animate-pulse' : 'h-3'}"></span>
                <span class="w-1 bg-[#680E23] rounded-full ${isActive ? 'h-4 animate-pulse' : 'h-1.5'}"></span>
                <span class="w-1 bg-[#680E23] rounded-full ${isActive ? 'h-3 animate-pulse' : 'h-2.5'}"></span>
                <span class="w-1 bg-[#D4AF37] rounded-full ${isActive ? 'h-4 animate-pulse' : 'h-1'}"></span>
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="flex items-center justify-between gap-2 pt-2 border-t border-[#EAE3D9]/60">
              <div>
                ${isActive
                  ? `<span class="text-xs font-bold text-emerald-700 flex items-center gap-1">
                       ✅ الشخصية المعتمدة حالياً
                     </span>`
                  : `<button type="button" onclick="activateProfileById(${p.id})" class="px-3.5 py-1.5 rounded-xl bg-[#680E23] hover:bg-[#7E152F] text-white text-xs font-bold transition flex items-center gap-1.5 shadow-sm">
                       ⚡ تفعيل الآن للمكالمات
                     </button>`
                }
              </div>
              <div class="flex items-center gap-1.5">
                <button type="button" onclick="editProfileInStudio(${p.id})" class="px-3 py-1.5 rounded-xl bg-[#FAF7F2] hover:bg-[#F5EFE6] text-[#680E23] text-xs font-semibold border border-[#DDD5C7] transition">
                  ✏️ تعديل
                </button>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    async function activateProfileById(profileId) {
      try {
        const res = await fetch(`/api/agents/profiles/${profileId}/activate/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
          }
        });
        const data = await res.json();
        if (data.status === 'success') {
          await loadProfiles();
        } else {
          alert(data.message || 'حدث خطأ أثناء تفعيل البروفايل');
        }
      } catch (err) {
        console.error('Error activating profile:', err);
      }
    }

    function editProfileInStudio(profileId) {
      const profile = userProfiles.find(p => p.id === profileId);
      if (profile) {
        profileSelect.value = profileId;
        populateProfileForm(profile);
        const card = document.getElementById('profile-editor-card');
        if (card) {
          card.scrollIntoView({ behavior: 'smooth', block: 'center' });
          card.classList.add('ring-2', 'ring-[#680E23]');
          setTimeout(() => card.classList.remove('ring-2', 'ring-[#680E23]'), 1500);
        }
      }
    }

    async function loadProfiles() {
      try {
        const res = await fetch('/api/agents/profiles/');
        const data = await res.json();
        if (data.status === 'success') {
          userProfiles = data.profiles;
          activeProfile = data.active_profile;
          googleVoices = data.google_voices;

          renderProfileDropdown();
          renderProfileCards();
          syncGenderVoiceOptions();
          if (activeProfile) {
            populateProfileForm(activeProfile);
          }
        }
      } catch (err) {
        console.error('Error loading profiles:', err);
      }
    }

    function renderProfileDropdown() {
      if (!userProfiles || userProfiles.length === 0) {
        profileSelect.innerHTML = '<option value="">لا توجد بروفايلات</option>';
        return;
      }
      profileSelect.innerHTML = userProfiles.map(p => `
        <option value="${p.id}" ${p.is_active ? 'selected' : ''}>
          ${p.name} ${p.is_active ? '⭐ [نشط للمكالمات]' : ''}
        </option>
      `).join('');
    }

    function populateVoiceSelect(selectElem, targetGender, selectedVoice) {
      if (!googleVoices || googleVoices.length === 0) return;
      
      const filtered = targetGender 
        ? googleVoices.filter(v => v.gender === targetGender)
        : googleVoices;
      const other = targetGender
        ? googleVoices.filter(v => v.gender !== targetGender)
        : [];

      let html = '';
      if (filtered.length > 0) {
        html += `<optgroup label="أصوات (${targetGender === 'female' ? 'نسائية' : 'رجالية'})">`;
        filtered.forEach(v => {
          html += `<option value="${v.name}" ${v.name === selectedVoice ? 'selected' : ''}>${v.name} - ${v.style}</option>`;
        });
        html += '</optgroup>';
      }

      if (other.length > 0) {
        html += `<optgroup label="أصوات أخرى">`;
        other.forEach(v => {
          html += `<option value="${v.name}" ${v.name === selectedVoice ? 'selected' : ''}>${v.name} - ${v.style}</option>`;
        });
        html += '</optgroup>';
      }

      selectElem.innerHTML = html;
    }

    function syncGenderVoiceOptions() {
      const g = fieldGender.value;
      const currentVoice = fieldVoice.value || (activeProfile ? activeProfile.voice_name : 'Aoede');
      populateVoiceSelect(fieldVoice, g, currentVoice);
      updateVoiceTag();
    }

    function syncNewProfileVoices() {
      const g = newProfGender.value;
      populateVoiceSelect(newProfVoice, g, g === 'female' ? 'Aoede' : 'Puck');
    }

    function updateVoiceTag() {
      const selectedName = fieldVoice.value;
      const v = googleVoices.find(x => x.name === selectedName);
      if (v && voiceTagBadge) {
        voiceTagBadge.innerText = `${v.tag} | ${v.style.split('(')[0].trim()}`;
      }
    }

    function populateProfileForm(p) {
      fieldGender.value = p.gender;
      fieldDialect.value = p.dialect;
      populateVoiceSelect(fieldVoice, p.gender, p.voice_name);
      fieldRole.value = p.persona_role;
      fieldStyle.value = p.speaking_style;
      fieldCustom.value = p.custom_instructions || '';
      updateVoiceTag();
      profileStatusMsg.innerText = `البروفايل المطبق: "${p.name}" (${p.voice_name})`;
      profileStatusMsg.className = 'text-xs text-emerald-400 font-semibold';
    }

    async function handleProfileSelect(profileId) {
      if (!profileId) return;
      try {
        const res = await fetch(`/api/agents/profiles/${profileId}/activate/`, {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        const data = await res.json();
        if (data.status === 'success') {
          activeProfile = data.profile;
          userProfiles = userProfiles.map(p => ({ ...p, is_active: p.id === activeProfile.id }));
          renderProfileDropdown();
          renderProfileCards();
          populateProfileForm(activeProfile);
          profileStatusMsg.innerText = `✅ تم تفعيل بروفايل "${activeProfile.name}"! ستتحدث المساعدة بهذا الصوت واللهجة.`;
          profileStatusMsg.className = 'text-xs text-emerald-400 font-semibold';
        }
      } catch (err) {
        console.error('Error activating profile:', err);
      }
    }

    async function saveActiveProfileChanges() {
      if (!activeProfile) return;
      const btn = document.getElementById('btn-save-profile');
      btn.disabled = true;
      btn.innerText = 'جاري الحفظ...';

      const payload = {
        gender: fieldGender.value,
        dialect: fieldDialect.value,
        voice_name: fieldVoice.value,
        persona_role: fieldRole.value,
        speaking_style: fieldStyle.value,
        custom_instructions: fieldCustom.value.trim()
      };

      try {
        const res = await fetch(`/api/agents/profiles/${activeProfile.id}/update/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === 'success') {
          activeProfile = data.profile;
          userProfiles = userProfiles.map(p => p.id === activeProfile.id ? activeProfile : p);
          profileStatusMsg.innerText = `✅ تم حفظ وتطبيق إعدادات "${activeProfile.name}" بنجاح!`;
          profileStatusMsg.className = 'text-xs text-emerald-400 font-semibold';
        } else {
          profileStatusMsg.innerText = 'فشل الحفظ: ' + (data.message || '');
          profileStatusMsg.className = 'text-xs text-rose-400 font-semibold';
        }
      } catch (err) {
        profileStatusMsg.innerText = 'حدث خطأ أثناء حفظ البروفايل.';
        profileStatusMsg.className = 'text-xs text-rose-400 font-semibold';
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg> حفظ وتطبيق على المكالمات`;
      }
    }

    function openNewProfileModal() {
      document.getElementById('new-profile-form').reset();
      syncNewProfileVoices();
      profileModal.classList.remove('hidden');
    }

    function closeNewProfileModal() {
      profileModal.classList.add('hidden');
    }

    async function createNewProfile(e) {
      e.preventDefault();
      const name = document.getElementById('new-prof-name').value.trim();
      const gender = document.getElementById('new-prof-gender').value;
      const dialect = document.getElementById('new-prof-dialect').value;
      const voice_name = document.getElementById('new-prof-voice').value;
      const persona_role = document.getElementById('new-prof-role').value;
      const speaking_style = document.getElementById('new-prof-style').value;

      const btn = document.getElementById('btn-create-prof');
      btn.disabled = true;
      btn.innerText = 'جاري الحفظ...';

      try {
        const res = await fetch('/api/agents/profiles/create/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: JSON.stringify({
            name,
            gender,
            dialect,
            voice_name,
            persona_role,
            speaking_style,
            is_active: true
          })
        });
        const data = await res.json();
        if (data.status === 'success') {
          closeNewProfileModal();
          await loadProfiles();
        } else {
          alert('فشل إنشاء البروفايل: ' + (data.message || ''));
        }
      } catch (err) {
        alert('حدث خطأ في الاتصال بالخادم.');
      } finally {
        btn.disabled = false;
        btn.innerText = 'حفظ البروفايل';
      }
    }

    async function deleteCurrentProfile() {
      if (!activeProfile) return;
      if (userProfiles.length <= 1) {
        alert('لا يمكنك حذف البروفايل الوحيد لديك.');
        return;
      }
      if (!confirm(`هل أنت متأكد من حذف بروفايل "${activeProfile.name}"؟`)) return;

      try {
        const res = await fetch(`/api/agents/profiles/${activeProfile.id}/delete/`, {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        const data = await res.json();
        if (data.status === 'success') {
          await loadProfiles();
        } else {
          alert('فشل الحذف: ' + (data.message || ''));
        }
      } catch (err) {
        alert('حدث خطأ أثناء حذف البروفايل.');
      }
    }

    // ==========================================
    // Customer Memory Management Functions (Multi-Customer)
    // ==========================================
    let currentSelectedPhone = 'web_dashboard';
    let customerSearchTimer = null;

    function debounceCustomerSearch(query) {
      clearTimeout(customerSearchTimer);
      customerSearchTimer = setTimeout(() => {
        loadCustomersList(query);
      }, 300);
    }

    async function loadCustomersList(query = '') {
      try {
        const url = query ? `/api/crm/customers/?q=${encodeURIComponent(query)}` : '/api/crm/customers/';
        const res = await fetch(url);
        const data = await res.json();
        if (data.status !== 'success') return;

        const selectEl = document.getElementById('crm-customer-select');
        if (!selectEl) return;

        const customers = data.customers || [];
        let html = '<option value="web_dashboard">💻 web_dashboard (جلسة المتصفح)</option>';

        let hasSelectedInList = (currentSelectedPhone === 'web_dashboard');

        customers.forEach(c => {
          if (c.phone_number === 'web_dashboard') return;
          const isSel = (c.phone_number === currentSelectedPhone);
          if (isSel) hasSelectedInList = true;
          const displayName = c.customer_name ? `${c.phone_number} (${c.customer_name})` : c.phone_number;
          html += `<option value="${escapeHtml(c.phone_number)}" ${isSel ? 'selected' : ''}>📞 ${escapeHtml(displayName)}</option>`;
        });

        if (!hasSelectedInList && currentSelectedPhone && currentSelectedPhone !== 'web_dashboard') {
          html += `<option value="${escapeHtml(currentSelectedPhone)}" selected>📞 ${escapeHtml(currentSelectedPhone)}</option>`;
        }

        selectEl.innerHTML = html;
        selectEl.value = currentSelectedPhone;
      } catch (err) {
        console.error('Error loading customers list:', err);
      }
    }

    function onCustomerSelectChange(phone) {
      currentSelectedPhone = phone || 'web_dashboard';
      const badge = document.getElementById('crm-active-customer-badge');
      if (badge) badge.innerText = currentSelectedPhone;
      loadCustomerMemory(currentSelectedPhone);
    }

    async function loadCustomerMemory(phone) {
      const targetPhone = phone || currentSelectedPhone || 'web_dashboard';
      currentSelectedPhone = targetPhone;

      const badge = document.getElementById('crm-active-customer-badge');
      if (badge) badge.innerText = targetPhone;

      try {
        const res = await fetch(`/api/crm/memory/?phone=${encodeURIComponent(targetPhone)}`);
        const data = await res.json();
        if (data.status !== 'success') return;

        const memory = data.memory || {};
        const prof = memory.permanent_profile || {};
        const calls = data.recent_calls || [];

        // 1. Render Permanent Profile
        const permEl = document.getElementById('memory-permanent-content');
        if (!prof || Object.keys(prof).length === 0) {
          permEl.innerHTML = `
            <div class="text-center py-4 text-slate-500">
              لا توجد بيانات دائمة مسجلة لهذا الرقم بعد. سيتعلم المساعد اسمه وتفضيلاته تلقائياً أثناء المكالمات!
            </div>
          `;
        } else {
          let itemsHtml = '';
          if (prof.customer_name) {
            itemsHtml += `<div class="flex items-center gap-2"><span class="text-amber-400 font-semibold">👤 الاسم:</span> <span class="text-slate-100 font-bold">${escapeHtml(prof.customer_name)}</span></div>`;
          }
          if (prof.phone || memory.phone_number) {
            itemsHtml += `<div class="flex items-center gap-2"><span class="text-amber-400 font-semibold">📞 الهاتف:</span> <span class="text-slate-200 font-mono">${escapeHtml(prof.phone || memory.phone_number)}</span></div>`;
          }
          if (prof.address || prof.city) {
            itemsHtml += `<div class="flex items-center gap-2"><span class="text-amber-400 font-semibold">📍 العنوان:</span> <span class="text-slate-200">${escapeHtml(prof.address || prof.city)}</span></div>`;
          }
          if (prof.preferences && Array.isArray(prof.preferences) && prof.preferences.length > 0) {
            const tags = prof.preferences.map(p => `<span class="px-2 py-0.5 rounded-md bg-amber-950/60 border border-amber-800/80 text-amber-200 text-[10px]">${escapeHtml(p)}</span>`).join(' ');
            itemsHtml += `<div class="flex items-start gap-2 pt-1"><span class="text-amber-400 font-semibold">🏷️ التفضيلات:</span> <div class="flex flex-wrap gap-1">${tags}</div></div>`;
          }
          if (prof.notes) {
            itemsHtml += `<div class="flex items-start gap-2 pt-1 text-[11px] text-slate-400"><span class="text-amber-400 font-semibold">📝 ملاحظات:</span> <span>${escapeHtml(prof.notes)}</span></div>`;
          }
          permEl.innerHTML = itemsHtml || '<div class="text-slate-500">لا توجد تفاصيل محددة بعد.</div>';
        }

        // 2. Render Immediate Summary
        const immEl = document.getElementById('memory-immediate-content');
        const badgeEl = document.getElementById('memory-calls-badge');
        badgeEl.innerText = `${memory.total_calls_count || 0} مكالمات مسجلة`;

        if (memory.last_interaction_summary) {
          const timeStr = memory.last_interaction_at || 'مكالمة سابقة';
          immEl.innerHTML = `
            <div class="space-y-1.5">
              <div class="text-[10px] text-slate-400">📅 آخر تواصل: <span class="text-cyan-300 font-mono">${timeStr}</span></div>
              <p class="text-slate-200 leading-relaxed bg-slate-900/60 p-2.5 rounded-xl border border-slate-700/40">
                ${escapeHtml(memory.last_interaction_summary)}
              </p>
            </div>
          `;
        } else {
          immEl.innerHTML = `
            <div class="text-center py-4 text-slate-500">
              لا يوجد ملخص لمكالمة سابقة حتى الآن لهذا الرقم.
            </div>
          `;
        }

        // 3. Render Recent Calls
        const callsEl = document.getElementById('memory-recent-calls');
        if (!calls || calls.length === 0) {
          callsEl.innerHTML = '<div class="text-slate-500 text-center py-2">لا توجد مكالمات سابقة مسجلة لهذا الرقم.</div>';
        } else {
          callsEl.innerHTML = calls.map(c => {
            let dirBadge = '<span class="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950/80 border border-emerald-700/60 text-emerald-300 font-semibold">📞 واردة</span>';
            if (c.direction === 'outbound_ai') {
              dirBadge = '<span class="text-[10px] px-2 py-0.5 rounded-full bg-purple-950/80 border border-purple-700/60 text-purple-300 font-semibold">🤖 صادرة (AI)</span>';
            } else if (c.direction === 'outbound_agent') {
              dirBadge = '<span class="text-[10px] px-2 py-0.5 rounded-full bg-blue-950/80 border border-blue-700/60 text-blue-300 font-semibold">👤 صادرة (موظف)</span>';
            }
            const callerBadge = c.caller_phone ? `<span class="text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-700 font-mono text-amber-300">📱 ${escapeHtml(c.caller_phone)}</span>` : '';
            const destHtml = c.destination_phone ? `<span class="text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-700 font-mono text-cyan-300">🎯 ${escapeHtml(c.destination_phone)}</span>` : '';
            return `
            <div class="p-3 rounded-2xl bg-slate-800/40 border border-slate-700/40 flex flex-col md:flex-row md:items-center justify-between gap-2.5">
              <div class="space-y-1">
                <div class="flex flex-wrap items-center gap-2">
                  ${dirBadge}
                  ${callerBadge}
                  ${destHtml}
                  <span class="font-mono text-xs text-slate-300 font-semibold">${escapeHtml(c.room_name)}</span>
                  <span class="text-[10px] text-slate-500 font-mono">📅 ${c.started_at}</span>
                  <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">⏱️ ${c.duration_seconds} ثانية</span>
                </div>
                <p class="text-[11px] text-slate-300 mt-1">${escapeHtml(c.summary || (c.call_goal ? 'الهدف: ' + c.call_goal : 'مكالمة مكتملة بدون ملخص'))}</p>
              </div>
            </div>
            `;
          }).join('');
        }
      } catch (err) {
        console.error('Error loading customer memory:', err);
      }
    }

    async function resetCustomerMemory() {
      const targetPhone = currentSelectedPhone || 'web_dashboard';
      if (!confirm(`هل أنت متأكد من تصفير ذاكرة العميل للرقم (${targetPhone})؟ سيتم مسح البيانات الدائمة والملخص الخاص به.`)) return;
      try {
        const res = await fetch('/api/crm/memory/reset/', {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken') 
          },
          body: JSON.stringify({ phone: targetPhone })
        });
        const data = await res.json();
        if (data.status === 'success') {
          await loadCustomerMemory(targetPhone);
          await loadCustomersList();
        } else {
          alert('فشل تصفير الذاكرة: ' + (data.message || ''));
        }
      } catch (err) {
        alert('حدث خطأ أثناء تصفير الذاكرة.');
      }
    }

    // ==========================================
    // Employee WebRTC Directory Management
    // ==========================================
    let currentEmployees = [];

    async function loadEmployees() {
      const tbody = document.getElementById('employees-tbody');
      if (!tbody) return;
      try {
        const res = await fetch('/api/call-center/employees/');
        const data = await res.json();
        if (data.status !== 'success') return;

        currentEmployees = data.employees || [];
        if (currentEmployees.length === 0) {
          tbody.innerHTML = `
            <tr>
              <td colspan="6" class="text-center py-6 text-slate-500 text-xs">
                لا يوجد موظفون مسجلون بعد في النظام.
              </td>
            </tr>
          `;
          return;
        }

        const statusBadges = {
          'ready': '<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-800"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>متاح (Ready)</span>',
          'break': '<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-amber-950/80 text-amber-300 border border-amber-800"><span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>استراحة (Break)</span>',
          'busy': '<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-rose-950/80 text-rose-300 border border-rose-800"><span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span>مشغول (Busy)</span>',
          'offline': '<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-slate-800 text-slate-400 border border-slate-700">غير متصل</span>'
        };

        tbody.innerHTML = currentEmployees.map(emp => `
          <tr class="hover:bg-slate-800/30 transition">
            <td class="py-3 px-3 font-semibold text-slate-200 flex items-center gap-2">
              <span class="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs">👤</span>
              <span>${escapeHtml(emp.display_name)}</span>
            </td>
            <td class="py-3 px-3 text-center">
              <span class="font-mono font-bold text-cyan-300 bg-cyan-950/70 border border-cyan-800 px-2.5 py-1 rounded-lg text-sm shadow-sm">
                ${escapeHtml(emp.extension)}
              </span>
            </td>
            <td class="py-3 px-3 text-slate-300">${escapeHtml(emp.department || 'عام')}</td>
            <td class="py-3 px-3 text-center">
              ${statusBadges[emp.status] || statusBadges['offline']}
            </td>
            <td class="py-3 px-3">
              <span class="inline-flex items-center gap-1 text-[11px] text-teal-300 font-mono">
                <span class="w-1.5 h-1.5 rounded-full bg-teal-400"></span> WebRTC LiveKit
              </span>
            </td>
            <td class="py-3 px-3 text-center">
              <div class="flex items-center justify-center gap-1.5">
                <button 
                  type="button" 
                  onclick="dialTargetFromDashboard('${escapeHtml(emp.extension)}', '${escapeHtml(emp.display_name)}')"
                  class="px-2.5 py-1 rounded-lg bg-emerald-950/70 hover:bg-emerald-900 text-emerald-300 border border-emerald-700/80 text-[11px] font-bold transition inline-flex items-center gap-1 shadow-sm"
                  title="اتصال مباشر بالموظف عبر WebRTC"
                >
                  <span>📞 اتصال</span>
                </button>
                <button 
                  type="button" 
                  onclick="deleteEmployee(${emp.id}, '${escapeHtml(emp.display_name)}')"
                  class="p-1 rounded-lg hover:bg-rose-950/80 hover:text-rose-300 text-slate-500 transition"
                  title="حذف الموظف"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </td>
          </tr>
        `).join('');
      } catch (err) {
        console.error('Error loading employees:', err);
      }
    }

    // ==========================================
    // Call Queues & Routing Management Functions
    // ==========================================
    let currentCallQueues = [];

    async function loadQueues() {
      const tbody = document.getElementById('queues-tbody');
      if (!tbody) return;
      try {
        const res = await fetch('/api/call-center/queues/');
        const data = await res.json();
        if (data.status !== 'success') return;

        currentCallQueues = data.queues || [];
        if (currentCallQueues.length === 0) {
          tbody.innerHTML = `
            <tr>
              <td colspan="6" class="text-center py-6 text-slate-500 text-xs">
                لا توجد طوابير انتظار مسجلة بعد. اضغط "طابور جديد" لإنشاء طابور (مثل كود 200 للمبيعات أو 300 للدعم).
              </td>
            </tr>
          `;
          return;
        }

        tbody.innerHTML = currentCallQueues.map(q => {
          const membersHtml = (q.members && q.members.length > 0)
            ? q.members.map(m => {
                let badgeColor = 'bg-emerald-950/80 text-emerald-300 border-emerald-800';
                let dotColor = 'bg-emerald-400';
                let stateLabel = 'متاح';
                if (m.presence_state === 'RINGING') {
                  badgeColor = 'bg-amber-950/80 text-amber-300 border-amber-800';
                  dotColor = 'bg-amber-400 animate-ping';
                  stateLabel = 'يرن...';
                } else if (m.presence_state === 'BUSY') {
                  badgeColor = 'bg-rose-950/80 text-rose-300 border-rose-800';
                  dotColor = 'bg-rose-400';
                  stateLabel = 'مشغول';
                }
                return `
                  <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold ${badgeColor} border mr-1 mb-1">
                    <span class="w-1.5 h-1.5 rounded-full ${dotColor}"></span>
                    <span>${escapeHtml(m.sip_account_name || m.sip_username)}</span>
                    <span class="text-cyan-300 font-mono text-[9px] font-bold">[تحويلة ${escapeHtml(m.extension || '')}]</span>
                    <span class="opacity-75 font-mono text-[9px]">(${stateLabel})</span>
                  </span>
                `;
              }).join('')
            : '<span class="text-slate-500 text-[10px]">لا يوجد موظفون مسندون</span>';

          const waitingBadge = q.waiting_calls_count > 0
            ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-950 text-amber-300 border border-amber-700 animate-pulse">${q.waiting_calls_count} مكالمة</span>`
            : `<span class="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-slate-400">0</span>`;

          const strategyLabel = q.strategy === 'round_robin' 
            ? `رنين بالتناوب (${q.ring_timeout_seconds || 15}ث)` 
            : 'رنين متزامن للكل';

          return `
            <tr class="hover:bg-slate-800/30 transition">
              <td class="py-3 px-3">
                <span class="font-mono font-bold text-amber-400 bg-amber-950/60 px-2 py-1 rounded-lg border border-amber-800/80 text-sm">
                  ${escapeHtml(q.code)}
                </span>
              </td>
              <td class="py-3 px-3 font-semibold text-slate-200">
                ${escapeHtml(q.name)}
                ${q.hold_music_url ? '<span class="mr-1 text-[10px] text-cyan-400" title="موسيقى انتظار مخصصة">🎵</span>' : ''}
              </td>
              <td class="py-3 px-3 text-slate-300 font-mono text-[11px]">${strategyLabel}</td>
              <td class="py-3 px-3">
                <div class="flex flex-wrap items-center">${membersHtml}</div>
              </td>
              <td class="py-3 px-3 text-center">${waitingBadge}</td>
              <td class="py-3 px-3 text-center">
                <div class="flex items-center justify-center gap-1.5">
                  <button 
                    type="button" 
                    onclick="dialTargetFromDashboard('${escapeHtml(q.code)}', '${escapeHtml(q.name)}')"
                    class="px-2.5 py-1 rounded-lg bg-amber-950/70 hover:bg-amber-900 text-amber-300 border border-amber-700/80 text-[11px] font-bold transition inline-flex items-center gap-1 shadow-sm"
                    title="اتصال وتجربة الطابور عبر WebRTC"
                  >
                    <span>📞 اتصال بالطابور</span>
                  </button>
                  <button 
                    type="button" 
                    onclick="deleteQueue('${q.id}', '${escapeHtml(q.name)}')"
                    class="p-1 rounded-lg hover:bg-rose-950/80 hover:text-rose-300 text-slate-500 transition"
                    title="حذف الطابور"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          `;
        }).join('');
      } catch (err) {
        console.error('Error loading call queues:', err);
      }
    }

    function openNewQueueModal() {
      document.getElementById('new-queue-form').reset();
      document.getElementById('new-queue-error').classList.add('hidden');

      const membersListEl = document.getElementById('queue-members-list');
      if (currentEmployees && currentEmployees.length > 0) {
        membersListEl.innerHTML = currentEmployees.map(emp => `
          <label class="flex items-center gap-2 p-1.5 rounded-lg bg-slate-900/60 border border-slate-800 hover:bg-slate-800/40 cursor-pointer transition">
            <input type="checkbox" name="member_employee_ids" value="${emp.id}" class="rounded bg-slate-800 border-slate-700 text-amber-500 focus:ring-amber-500">
            <span class="text-slate-200 font-medium">${escapeHtml(emp.display_name)}</span>
            <span class="font-mono text-cyan-300 font-bold text-[11px] mr-1">[تحويلة: ${escapeHtml(emp.extension || '')}]</span>
            <span class="text-slate-400 text-[10px]">(${escapeHtml(emp.department || '')})</span>
          </label>
        `).join('');
      } else {
        membersListEl.innerHTML = `
          <span class="text-slate-500 text-[11px]">
            جاري مزامنة الموظفين من جدول التحويلات...
          </span>
        `;
      }

      document.getElementById('new-queue-modal').classList.remove('hidden');
    }

    function closeNewQueueModal() {
      document.getElementById('new-queue-modal').classList.add('hidden');
    }

    async function handleCreateQueue(e) {
      e.preventDefault();
      const btn = document.getElementById('btn-submit-queue');
      const errEl = document.getElementById('new-queue-error');
      const name = document.getElementById('queue-name').value.trim();
      const code = document.getElementById('queue-code').value.trim();
      const strategy = document.getElementById('queue-strategy').value;
      const ringTimeout = document.getElementById('queue-ring-timeout').value;
      const totalTimeout = document.getElementById('queue-total-timeout').value;

      btn.disabled = true;
      btn.innerText = 'جاري إنشاء الطابور وتخصيص الكود...';
      errEl.classList.add('hidden');

      const formData = new FormData();
      formData.append('name', name);
      formData.append('code', code);
      formData.append('strategy', strategy);
      formData.append('ring_timeout_seconds', ringTimeout);
      formData.append('total_timeout_seconds', totalTimeout);

      const musicFile = document.getElementById('queue-hold-music').files[0];
      if (musicFile) {
        formData.append('hold_music', musicFile);
      }

      const checkedMembers = document.querySelectorAll('input[name="member_employee_ids"]:checked');
      checkedMembers.forEach(cb => {
        formData.append('member_ids', cb.value);
      });

      try {
        const res = await fetch('/api/call-center/queues/create/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: formData
        });
        const data = await res.json();
        if (data.status === 'success') {
          closeNewQueueModal();
          await loadQueues();
        } else {
          errEl.innerText = data.message || 'فشل إنشاء الطابور';
          errEl.classList.remove('hidden');
        }
      } catch (err) {
        errEl.innerText = 'حدث خطأ أثناء الاتصال بالخادم.';
        errEl.classList.remove('hidden');
      } finally {
        btn.disabled = false;
        btn.innerText = 'حفظ الطابور وتفعيل الكود';
      }
    }

    async function deleteQueue(id, name) {
      if (!confirm(`هل أنت متأكد من حذف طابور "${name}"؟ سيتم إلغاء كود الطابور وتوجيه الاتصال.`)) return;
      try {
        const res = await fetch(`/api/call-center/queues/${id}/delete/`, {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        const data = await res.json();
        if (data.status === 'success') {
          await loadQueues();
        } else {
          alert('فشل الحذف: ' + (data.message || ''));
        }
      } catch (err) {
        alert('حدث خطأ أثناء حذف الطابور.');
      }
    }

    // ==========================================
    // Employee Directory & Modal Functions
    // ==========================================
    function openNewEmployeeModal() {
      const form = document.getElementById('new-employee-form');
      if (form) form.reset();
      const err = document.getElementById('new-employee-error');
      if (err) err.classList.add('hidden');
      const modal = document.getElementById('new-employee-modal');
      if (modal) modal.classList.remove('hidden');
    }

    function closeNewEmployeeModal() {
      const modal = document.getElementById('new-employee-modal');
      if (modal) modal.classList.add('hidden');
    }

    async function handleCreateEmployee(e) {
      e.preventDefault();
      const btn = document.getElementById('btn-submit-employee');
      const errEl = document.getElementById('new-employee-error');
      const name = document.getElementById('emp-name').value.trim();
      const ext = document.getElementById('emp-extension').value.trim();
      const dept = document.getElementById('emp-department').value.trim();
      const username = document.getElementById('emp-username').value.trim();
      const password = document.getElementById('emp-password').value.trim();

      btn.disabled = true;
      btn.innerText = 'جاري حفظ وإنشاء التحويلة...';
      errEl.classList.add('hidden');

      try {
        const res = await fetch('/api/call-center/employees/create/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: JSON.stringify({
            display_name: name,
            extension: ext,
            department: dept,
            username: username,
            password: password
          })
        });
        const data = await res.json();
        if (data.status === 'success') {
          closeNewEmployeeModal();
          await loadEmployees();
          await loadQueues();
        } else {
          errEl.innerText = data.message || 'حدث خطأ أثناء إضافة الموظف';
          errEl.classList.remove('hidden');
        }
      } catch (err) {
        errEl.innerText = 'فشل الاتصال بالخادم.';
        errEl.classList.remove('hidden');
      } finally {
        btn.disabled = false;
        btn.innerText = 'حفظ وإنشاء التحويلة';
      }
    }

    async function deleteEmployee(id, name) {
      if (!confirm(`هل أنت متأكد من حذف الموظف "${name}" وإلغاء تحويلته؟`)) return;
      try {
        const res = await fetch(`/api/call-center/employees/${id}/delete/`, {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        const data = await res.json();
        if (data.status === 'success') {
          await loadEmployees();
          await loadQueues();
        } else {
          alert('فشل الحذف: ' + (data.message || ''));
        }
      } catch (err) {
        alert('حدث خطأ أثناء حذف الموظف.');
      }
    }

    // ==========================================
    // Dashboard WebRTC Calling (Queues & Employees)
    // ==========================================
    let dashboardLivekitRoom = null;
    let dashboardAttachedAudio = null;
    let dashboardCurrentRoomName = null;

    async function dialTargetFromDashboard(target, targetName) {
      if (dashboardLivekitRoom) {
        alert('توجد مكالمة نشطة بالفعل في لوحة التحكم. يرجى إنهاؤها أولاً.');
        return;
      }

      const banner = document.getElementById('dashboard-active-call-banner');
      const callTitle = document.getElementById('dashboard-call-title');
      const callSub = document.getElementById('dashboard-call-sub');

      if (banner) banner.classList.remove('hidden');
      if (callTitle) callTitle.innerText = `جاري الاتصال بـ: ${targetName} [${target}]...`;
      if (callSub) callSub.innerText = 'يتم إنشاء غرفة WebRTC وتنبيه الموظفين عبر الشبكة الداخلية...';

      try {
        const res = await fetch('/api/call-center/calls/dial/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: JSON.stringify({ target: target })
        });
        const data = await res.json();

        if (data.status !== 'success') {
          alert(data.message || 'فشل بدء المكالمة');
          if (banner) banner.classList.add('hidden');
          return;
        }

        dashboardCurrentRoomName = data.room_name;
        const agentsInfo = (data.notified_agents !== undefined)
          ? `(تم تنبيه ${data.notified_agents} موظف متاح)`
          : '';

        if (callTitle) callTitle.innerText = `مكالمة جارية: ${data.target_name || targetName} [${data.target_number || target}]`;
        if (callSub) callSub.innerText = `متصل عبر WebRTC LiveKit ${agentsInfo} - بانتظار رد الموظف...`;

        dashboardLivekitRoom = new LivekitClient.Room({
          adaptiveStream: true,
          dynacast: true
        });

        dashboardLivekitRoom.on(LivekitClient.RoomEvent.ParticipantConnected, (p) => {
          if (callSub) callSub.innerText = `انضم للمكالمة: ${p.name || p.identity} ✅`;
        });

        dashboardLivekitRoom.on(LivekitClient.RoomEvent.ParticipantDisconnected, (p) => {
          console.log('[LiveKit Dashboard] Remote participant disconnected:', p.identity);
          endDashboardCall();
        });

        dashboardLivekitRoom.on(LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {
          if (track.kind === LivekitClient.Track.Kind.Audio) {
            if (dashboardAttachedAudio) dashboardAttachedAudio.remove();
            dashboardAttachedAudio = track.attach();
            document.body.appendChild(dashboardAttachedAudio);
          }
        });

        dashboardLivekitRoom.on(LivekitClient.RoomEvent.Disconnected, () => {
          if (banner) banner.classList.add('hidden');
          if (dashboardAttachedAudio) {
            dashboardAttachedAudio.remove();
            dashboardAttachedAudio = null;
          }
          dashboardLivekitRoom = null;
          dashboardCurrentRoomName = null;
        });

        await dashboardLivekitRoom.connect(data.livekit_url, data.livekit_token);
        await dashboardLivekitRoom.localParticipant.setMicrophoneEnabled(true);

      } catch (err) {
        console.error('Failed to dial from dashboard:', err);
        alert('حدث خطأ في الاتصال عبر WebRTC: ' + err.message);
        if (banner) banner.classList.add('hidden');
        if (dashboardLivekitRoom) {
          dashboardLivekitRoom.disconnect();
          dashboardLivekitRoom = null;
        }
        dashboardCurrentRoomName = null;
      }
    }

    async function endDashboardCall() {
      const banner = document.getElementById('dashboard-active-call-banner');
      if (banner) banner.classList.add('hidden');

      const roomToClose = dashboardCurrentRoomName;

      if (dashboardLivekitRoom) {
        try {
          await dashboardLivekitRoom.disconnect();
        } catch (e) {
          console.error(e);
        }
        dashboardLivekitRoom = null;
      }

      if (dashboardAttachedAudio) {
        dashboardAttachedAudio.remove();
        dashboardAttachedAudio = null;
      }

      dashboardCurrentRoomName = null;

      try {
        await fetch('/api/call-center/calls/hangup/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: JSON.stringify({ room_name: roomToClose })
        });
      } catch (e) {
        // ignore
      }
    }

    // ==================== Generic Outbound SIP Trunk & AI Calling JS ====================
    let currentOutboundTrunk = null;

    async function loadOutboundTrunk() {
      try {
        const res = await fetch('/api/telephony/trunk/');
        const data = await res.json();
        if (data.status !== 'success') return;

        const badge = document.getElementById('outbound-trunk-badge');
        const details = document.getElementById('outbound-trunk-details');

        if (data.has_trunk && data.trunk) {
          currentOutboundTrunk = data.trunk;
          badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-700/60";
          badge.innerHTML = "متصل وجاهز للاتصال";

          details.innerHTML = `
            <div class="space-y-1.5 pt-1">
              <div class="flex justify-between items-center"><span class="text-slate-400">الاسم:</span> <span class="font-bold text-slate-100">${escapeHtml(data.trunk.name)}</span></div>
              <div class="flex justify-between items-center"><span class="text-slate-400">الخادم:</span> <span class="font-mono text-cyan-300 text-[11px]">${escapeHtml(data.trunk.sip_host)}:${data.trunk.sip_port}</span></div>
              <div class="flex justify-between items-center"><span class="text-slate-400">البروتوكول:</span> <span class="text-amber-300 font-semibold">${data.trunk.transport}</span></div>
              <div class="flex justify-between items-center"><span class="text-slate-400">Caller ID:</span> <span class="font-mono text-emerald-300 font-semibold">${escapeHtml(data.trunk.caller_id || 'افتراضي')}</span></div>
              <div class="flex justify-between items-center"><span class="text-slate-400">معرف LiveKit:</span> <span class="font-mono text-[10px] text-purple-400">${data.trunk.livekit_outbound_trunk_id}</span></div>
            </div>
            <div class="pt-2 border-t border-slate-700/50 flex justify-end">
              <button type="button" onclick="handleDeleteOutboundTrunk(${data.trunk.id})" class="text-[11px] text-rose-400 hover:text-rose-300 font-semibold flex items-center gap-1">
                <span>حذف الجذع</span>
              </button>
            </div>
          `;

          // Populate form fields
          document.getElementById('outbound-name').value = data.trunk.name || '';
          document.getElementById('outbound-host').value = data.trunk.sip_host || '';
          document.getElementById('outbound-port').value = data.trunk.sip_port || 5060;
          document.getElementById('outbound-transport').value = data.trunk.transport || 'UDP';
          document.getElementById('outbound-username').value = data.trunk.auth_username || '';
          document.getElementById('outbound-caller-id').value = data.trunk.caller_id || '';
        } else {
          currentOutboundTrunk = null;
          badge.className = "px-2 py-0.5 rounded-full text-[10px] font-semibold bg-gray-800 text-gray-400 border border-gray-700";
          badge.innerText = "غير مهيأ";
          details.innerHTML = `
            <div class="text-slate-500 text-center py-4">
              لم يتم حفظ أي جذع SIP خارجي بعد. أدخل بيانات حساب Telnyx أو Twilio أو المزود الخاص بك لحفظه.
            </div>
          `;
        }
      } catch (err) {
        console.error('Error loading outbound trunk:', err);
      }
    }

    async function handleSaveOutboundTrunk(e) {
      e.preventDefault();
      const btn = document.getElementById('btn-save-outbound');
      const msg = document.getElementById('outbound-trunk-msg');
      msg.className = "hidden p-2.5 rounded-xl text-xs font-semibold";

      const payload = {
        name: document.getElementById('outbound-name').value.trim() || 'حساب المزود الخارجي (Generic SIP Trunk)',
        sip_host: document.getElementById('outbound-host').value.trim(),
        sip_port: parseInt(document.getElementById('outbound-port').value || 5060),
        transport: document.getElementById('outbound-transport').value,
        auth_username: document.getElementById('outbound-username').value.trim(),
        auth_password: document.getElementById('outbound-password').value.trim(),
        caller_id: document.getElementById('outbound-caller-id').value.trim(),
      };

      if (!payload.sip_host) {
        msg.className = "p-2.5 rounded-xl text-xs font-semibold bg-rose-950/80 border border-rose-800 text-rose-300";
        msg.innerText = "يرجى كتابة عنوان الخادم (SIP Host).";
        return;
      }

      btn.disabled = true;
      btn.innerHTML = '<span>جاري الربط مع LiveKit...</span>';

      try {
        const res = await fetch('/api/telephony/trunk/save/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === 'success') {
          msg.className = "p-2.5 rounded-xl text-xs font-semibold bg-emerald-950/80 border border-emerald-800 text-emerald-300";
          msg.innerText = data.message;
          await loadOutboundTrunk();
        } else {
          msg.className = "p-2.5 rounded-xl text-xs font-semibold bg-rose-950/80 border border-rose-800 text-rose-300";
          msg.innerText = data.message || "حدث خطأ أثناء حفظ الجذع.";
        }
      } catch (err) {
        msg.className = "p-2.5 rounded-xl text-xs font-semibold bg-rose-950/80 border border-rose-800 text-rose-300";
        msg.innerText = "فشل الاتصال بالخادم.";
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>حفظ وتفعيل الجذع الخارجي</span>';
      }
    }

    async function handleDeleteOutboundTrunk(id) {
      if (!confirm('هل أنت متأكد من حذف الجذع الخارجي؟ لن تتمكن من إجراء اتصالات صادرة حتى إعادة إعداده.')) return;
      try {
        const res = await fetch(`/api/telephony/trunk/${id}/delete/`, {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        const data = await res.json();
        if (data.status === 'success') {
          await loadOutboundTrunk();
        } else {
          alert('فشل الحذف: ' + (data.message || ''));
        }
      } catch (err) {
        alert('حدث خطأ أثناء حذف الجذع الخارجي.');
      }
    }

    async function loadOutboundGateways() {
      const select = document.getElementById('ai-call-gateway');
      if (!select) return;
      select.innerHTML = '<option value="auto:">المسار الافتراضي للنظام (تلقائي)</option>';
      try {
        const res = await fetch('/api/telephony/outbound-gateways/');
        const data = await res.json();
        if (data.status === 'success' && data.gateways) {
          data.gateways.forEach(g => {
            const val = `${g.type}:${g.id || ''}`;
            const isDef = g.is_default ? ' ⭐ (الافتراضي)' : '';
            const icon = g.type === 'pbx' ? '🏢' : '🌐';
            select.innerHTML += `<option value="${val}">${icon} ${escapeHtml(g.name)}${isDef}</option>`;
          });
          if (data.default_gateway) {
            select.value = `${data.default_gateway.type}:${data.default_gateway.id || ''}`;
          }
        }
      } catch (e) {
        console.error('Failed to load outbound gateways:', e);
      }
    }

    async function openNewAICallModal() {
      // Load available outbound gateways (Cloud Trunk + PBX Trunks)
      await loadOutboundGateways();

      // Populate profiles dropdown from API
      const select = document.getElementById('ai-call-profile');
      select.innerHTML = '<option value="">البروفايل النشط حالياً في النظام</option>';
      try {
        const res = await fetch('/api/agents/profiles/');
        const data = await res.json();
        if (data.status === 'success' && data.profiles) {
          data.profiles.forEach(p => {
            select.innerHTML += `<option value="${p.id}">${escapeHtml(p.name)} (${p.dialect_display})</option>`;
          });
        }
      } catch (e) {}

      document.getElementById('ai-call-error').classList.add('hidden');
      document.getElementById('ai-call-success').classList.add('hidden');
      document.getElementById('ai-call-modal').classList.remove('hidden');
      document.getElementById('ai-call-phone').focus();
    }

    function closeAICallModal() {
      document.getElementById('ai-call-modal').classList.add('hidden');
    }

    function applyGoalTemplate(type) {
      const area = document.getElementById('ai-call-goal');
      if (type === 'confirm_order') {
        area.value = "الاتصال بالعميل بلباقة لتأكيد تفاصيل الطلب رقم 1005 (قميص كاجوال وبنطلون جينز)، وسؤاله عن عنوان الشحن المناسب لتأكيد إرسال الشحنة اليوم.";
      } else if (type === 'survey') {
        area.value = "الاتصال بالعميل وسؤاله عن رأيه في تجربته الشرائية الأخيرة والمنتجات التي استلمها، وتسجيل أي ملاحظات أو شكاوى يذكرها.";
      } else if (type === 'reminder') {
        area.value = "تذكير العميل بموعد التسليم المحدد غداً بين الساعة 2 ظهراً و 5 مساءً، والتأكد من تواجده للاستلام.";
      }
    }

    async function handleTriggerAICall(e) {
      e.preventDefault();
      const phone = document.getElementById('ai-call-phone').value.trim();
      const profileId = document.getElementById('ai-call-profile').value;
      const callGoal = document.getElementById('ai-call-goal').value.trim();
      const gatewayVal = (document.getElementById('ai-call-gateway') && document.getElementById('ai-call-gateway').value) || 'auto:';
      const [gwType, gwId] = gatewayVal.split(':');
      const btn = document.getElementById('btn-submit-ai-call');
      const errEl = document.getElementById('ai-call-error');
      const succEl = document.getElementById('ai-call-success');

      errEl.classList.add('hidden');
      succEl.classList.add('hidden');

      if (!phone) {
        errEl.innerText = "يرجى إدخال رقم الهاتف.";
        errEl.classList.remove('hidden');
        return;
      }

      btn.disabled = true;
      btn.innerHTML = '<span>جاري طلب الرقم وتجهيز المساعد...</span>';

      try {
        const payload = {
          phone_number: phone,
          profile_id: profileId || null,
          call_goal: callGoal,
          gateway_type: gwType || 'auto',
          gateway_id: gwId ? parseInt(gwId) : null
        };

        const res = await fetch('/api/telephony/ai-call/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === 'success') {
          succEl.innerHTML = `
            <div><strong>✅ ${escapeHtml(data.message)}</strong></div>
            <div class="mt-1 text-[11px] text-emerald-200">الرقم: <span class="font-mono font-bold">${escapeHtml(data.destination_phone)}</span> | المسار: <span class="font-bold">${escapeHtml(data.gateway_used || 'الافتراضي')}</span> | الغرفة: <span class="font-mono">${escapeHtml(data.room_name)}</span></div>
          `;
          succEl.classList.remove('hidden');
          setTimeout(() => {
            loadCustomerMemory();
          }, 3000);
        } else {
          errEl.innerText = data.message || "فشل بدء المكالمة الصادرة.";
          errEl.classList.remove('hidden');
        }
      } catch (err) {
        errEl.innerText = "حدث خطأ في الاتصال بالخادم.";
        errEl.classList.remove('hidden');
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>📞 بدء الاتصال الآن</span>';
      }
    }

    // ==================== Inbound PBX Trunks (Issabel / Asterisk) JS ====================
    let currentPbxTrunks = [];

    async function loadPbxTrunks() {
      const grid = document.getElementById('pbx-trunks-grid');
      const countEl = document.getElementById('pbx-trunks-count');
      if (!grid) return;

      try {
        const res = await fetch('/api/telephony/pbx-trunks/');
        const data = await res.json();
        if (data.status !== 'success') return;

        currentPbxTrunks = data.trunks || [];
        if (countEl) countEl.innerText = currentPbxTrunks.length;

        if (currentPbxTrunks.length === 0) {
          grid.innerHTML = `
            <div class="col-span-full bg-slate-800/20 border border-slate-800 border-dashed rounded-3xl p-8 text-center space-y-3">
              <div class="text-3xl">🏢</div>
              <div class="text-slate-300 font-semibold text-sm">لا يوجد سنترال محلي مربوط حالياً</div>
              <p class="text-slate-500 text-xs max-w-md mx-auto">
                اضغط على زر "ربط سنترال Issabel / Asterisk جديد" لإنشاء جذع SIP والحصول على كود PEER Details الجاهز للصق في السنترال.
              </p>
              <button type="button" onclick="openNewPbxModal()" class="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs inline-flex items-center gap-1.5 shadow-md shadow-emerald-600/20">
                <span>➕ ربط أول سنترال</span>
              </button>
            </div>
          `;
          return;
        }

        grid.innerHTML = currentPbxTrunks.map(t => {
          const isIp = t.auth_mode === 'ip';
          const authBadge = isIp
            ? `<span class="px-2 py-0.5 rounded-md text-[10px] font-mono bg-cyan-950/80 text-cyan-300 border border-cyan-800">IP: ${escapeHtml(t.pbx_ip || 'غير محدد')}</span>`
            : `<span class="px-2 py-0.5 rounded-md text-[10px] font-mono bg-amber-950/80 text-amber-300 border border-amber-800">User: ${escapeHtml(t.auth_username || 'غير محدد')}</span>`;

          const destBadge = t.destination_type === 'ai'
            ? `<div class="flex items-center gap-1.5 text-xs text-purple-300 font-semibold"><span>🤖</span> <span>المساعد الذكي (Smart IVR)</span> ${t.target_profile_name ? `<span class="text-[10px] text-slate-400 font-normal">(${escapeHtml(t.target_profile_name)})</span>` : ''}</div>`
            : `<div class="flex items-center gap-1.5 text-xs text-amber-300 font-semibold"><span>👥</span> <span>طابور: ${escapeHtml(t.target_queue_name || 'غير محدد')} [${escapeHtml(t.target_queue_code || '')}]</span></div>`;

          let numDisplay = '';
          if (Array.isArray(t.inbound_numbers)) {
            numDisplay = t.inbound_numbers.join(', ');
          } else if (typeof t.inbound_numbers === 'string') {
            numDisplay = t.inbound_numbers.trim();
          }
          const numbersBadge = numDisplay
            ? `<span class="font-mono text-slate-300">${escapeHtml(numDisplay)}</span>`
            : `<span class="text-slate-500">جميع المكالمات الواردة</span>`;

          const bidiBadge = t.enable_outbound
            ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-cyan-950/80 text-cyan-300 border border-cyan-800" title="صادر ووارد">🔄 ${t.is_default_outbound ? 'ثنائي (افتراضي)' : 'ثنائي الاتجاه'}</span>`
            : `<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-800 text-slate-400">وارد فقط</span>`;

          return `
            <div class="bg-slate-800/40 border border-slate-700/50 hover:border-emerald-500/40 transition rounded-2xl p-4 flex flex-col justify-between space-y-4 shadow-lg">
              <div class="space-y-2.5">
                <div class="flex justify-between items-start">
                  <div>
                    <h3 class="font-bold text-slate-100 text-sm flex items-center gap-1.5">
                      <span>🏢</span>
                      <span>${escapeHtml(t.name)}</span>
                    </h3>
                    <div class="mt-1 flex items-center gap-1.5 flex-wrap">
                      ${authBadge}
                      ${bidiBadge}
                    </div>
                  </div>
                  <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold ${t.is_active ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800' : 'bg-slate-800 text-slate-400'}">
                    ${t.is_active ? '🟢 متصل' : '⚪ معطل'}
                  </span>
                </div>

                <div class="pt-2 border-t border-slate-800/80 space-y-1.5 text-xs">
                  <div class="flex justify-between items-center text-[11px]">
                    <span class="text-slate-400">الوجهة:</span>
                    ${destBadge}
                  </div>
                  <div class="flex justify-between items-center text-[11px]">
                    <span class="text-slate-400">الأرقام / DIDs:</span>
                    ${numbersBadge}
                  </div>
                  <div class="flex justify-between items-center text-[10px] font-mono text-slate-500">
                    <span>LiveKit Trunk:</span>
                    <span class="truncate max-w-[120px]" title="${escapeHtml(t.livekit_trunk_id || '')}">${escapeHtml(t.livekit_trunk_id ? t.livekit_trunk_id.substring(0, 15) + '...' : 'غير مزامن')}</span>
                  </div>
                  ${t.enable_outbound && t.livekit_outbound_trunk_id ? `
                  <div class="flex justify-between items-center text-[10px] font-mono text-cyan-400/80">
                    <span>LK Outbound:</span>
                    <span class="truncate max-w-[120px]" title="${escapeHtml(t.livekit_outbound_trunk_id)}">${escapeHtml(t.livekit_outbound_trunk_id.substring(0, 15) + '...')}</span>
                  </div>
                  ` : ''}
                </div>
              </div>

              <div class="pt-2 border-t border-slate-700/50 flex items-center justify-between gap-2">
                <button 
                  type="button" 
                  onclick="showIssabelConfigModal(${t.id})" 
                  class="px-3 py-1.5 rounded-xl bg-emerald-950/80 hover:bg-emerald-900 text-emerald-300 border border-emerald-700/80 text-[11px] font-bold transition flex items-center gap-1 shadow-sm"
                  title="عرض كود الإعداد للسنترال"
                >
                  <span>📋 كود Issabel</span>
                </button>
                <button 
                  type="button" 
                  onclick="handleDeletePbxTrunk(${t.id}, '${escapeHtml(t.name)}')" 
                  class="p-1.5 rounded-xl hover:bg-rose-950/80 text-slate-500 hover:text-rose-300 transition"
                  title="حذف الربط"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          `;
        }).join('');

      } catch (err) {
        console.error('Error loading PBX trunks:', err);
      }
    }

    async function openNewPbxModal() {
      const form = document.getElementById('new-pbx-form');
      if (form) form.reset();

      const err = document.getElementById('pbx-modal-error');
      const succ = document.getElementById('pbx-modal-success');
      if (err) err.classList.add('hidden');
      if (succ) succ.classList.add('hidden');

      const outbCheck = document.getElementById('pbx-enable-outbound');
      if (outbCheck) outbCheck.checked = true;
      const portInput = document.getElementById('pbx-outbound-port');
      if (portInput) portInput.value = 5060;
      const transInput = document.getElementById('pbx-outbound-transport');
      if (transInput) transInput.value = 'UDP';
      const defCheck = document.getElementById('pbx-is-default-outbound');
      if (defCheck) defCheck.checked = false;
      togglePbxOutboundOptions();

      onPbxAuthModeChange();
      onPbxDestinationChange();

      // Populate Profiles dropdown
      const profSelect = document.getElementById('pbx-target-profile');
      if (profSelect) {
        profSelect.innerHTML = '<option value="">البروفايل النشط حالياً في النظام</option>';
        try {
          const res = await fetch('/api/agents/profiles/');
          const data = await res.json();
          if (data.status === 'success' && data.profiles) {
            data.profiles.forEach(p => {
              profSelect.innerHTML += `<option value="${p.id}">${escapeHtml(p.name)} (${escapeHtml(p.dialect_display || '')})</option>`;
            });
          }
        } catch (e) {}
      }

      // Populate Queues dropdown
      const queueSelect = document.getElementById('pbx-target-queue');
      if (queueSelect) {
        queueSelect.innerHTML = '<option value="">اختر طابور الانتظار...</option>';
        if (currentCallQueues && currentCallQueues.length > 0) {
          currentCallQueues.forEach(q => {
            queueSelect.innerHTML += `<option value="${q.id}">[${escapeHtml(q.code)}] ${escapeHtml(q.name)}</option>`;
          });
        }
      }

      const modal = document.getElementById('new-pbx-modal');
      if (modal) modal.classList.remove('hidden');
    }

    function closeNewPbxModal() {
      const modal = document.getElementById('new-pbx-modal');
      if (modal) modal.classList.add('hidden');
    }

    function togglePbxOutboundOptions() {
      const check = document.getElementById('pbx-enable-outbound');
      const opts = document.getElementById('pbx-outbound-options');
      if (opts && check) {
        if (check.checked) {
          opts.classList.remove('hidden');
        } else {
          opts.classList.add('hidden');
        }
      }
    }

    function onPbxAuthModeChange() {
      const mode = document.getElementById('pbx-auth-mode').value;
      const ipGroup = document.getElementById('pbx-ip-group');
      const credsGroup = document.getElementById('pbx-creds-group');
      const ipInput = document.getElementById('pbx-ip');
      const userInput = document.getElementById('pbx-auth-username');
      const passInput = document.getElementById('pbx-auth-password');

      if (mode === 'ip') {
        ipGroup.classList.remove('hidden');
        credsGroup.classList.add('hidden');
        if (ipInput) ipInput.required = true;
        if (userInput) userInput.required = false;
        if (passInput) passInput.required = false;
      } else {
        ipGroup.classList.add('hidden');
        credsGroup.classList.remove('hidden');
        if (ipInput) ipInput.required = false;
        if (userInput) userInput.required = true;
        if (passInput) passInput.required = true;
      }
    }

    function onPbxDestinationChange() {
      const dest = document.getElementById('pbx-destination-type').value;
      const aiGroup = document.getElementById('pbx-ai-group');
      const queueGroup = document.getElementById('pbx-queue-group');
      const queueSelect = document.getElementById('pbx-target-queue');

      if (dest === 'ai') {
        aiGroup.classList.remove('hidden');
        queueGroup.classList.add('hidden');
        if (queueSelect) queueSelect.required = false;
      } else {
        aiGroup.classList.add('hidden');
        queueGroup.classList.remove('hidden');
        if (queueSelect) queueSelect.required = true;
      }
    }

    async function handleSavePbxTrunk(e) {
      e.preventDefault();
      const btn = document.getElementById('btn-submit-pbx');
      const errEl = document.getElementById('pbx-modal-error');
      const succEl = document.getElementById('pbx-modal-success');

      errEl.classList.add('hidden');
      succEl.classList.add('hidden');

      const name = document.getElementById('pbx-name').value.trim();
      const authMode = document.getElementById('pbx-auth-mode').value;
      const pbxIp = document.getElementById('pbx-ip').value.trim();
      const authUsername = document.getElementById('pbx-auth-username').value.trim();
      const authPassword = document.getElementById('pbx-auth-password').value.trim();
      const destinationType = document.getElementById('pbx-destination-type').value;
      const targetProfileId = document.getElementById('pbx-target-profile').value;
      const targetQueueId = document.getElementById('pbx-target-queue').value;
      const inboundNumbers = document.getElementById('pbx-inbound-numbers').value.trim();

      const enableOutbound = document.getElementById('pbx-enable-outbound') ? document.getElementById('pbx-enable-outbound').checked : true;
      const outboundPort = document.getElementById('pbx-outbound-port') ? (parseInt(document.getElementById('pbx-outbound-port').value) || 5060) : 5060;
      const outboundTransport = document.getElementById('pbx-outbound-transport') ? document.getElementById('pbx-outbound-transport').value : 'UDP';
      const isDefaultOutbound = document.getElementById('pbx-is-default-outbound') ? document.getElementById('pbx-is-default-outbound').checked : false;

      btn.disabled = true;
      btn.innerHTML = '<span>جاري إنشاء الجذع والمزامنة مع LiveKit...</span>';

      const payload = {
        name: name,
        auth_mode: authMode,
        pbx_ip: pbxIp,
        auth_username: authUsername,
        auth_password: authPassword,
        destination_type: destinationType,
        target_profile_id: targetProfileId || null,
        target_queue_id: targetQueueId || null,
        inbound_numbers: inboundNumbers,
        enable_outbound: enableOutbound,
        outbound_port: outboundPort,
        outbound_transport: outboundTransport,
        is_default_outbound: isDefaultOutbound
      };

      try {
        const res = await fetch('/api/telephony/pbx-trunks/save/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === 'success') {
          succEl.innerText = data.message || 'تم إنشاء الجذع وربطه بنجاح!';
          succEl.classList.remove('hidden');
          setTimeout(async () => {
            closeNewPbxModal();
            await loadPbxTrunks();
            if (data.trunk && data.trunk.id) {
              showIssabelConfigModal(data.trunk.id);
            }
          }, 800);
        } else {
          errEl.innerText = data.message || 'فشل إنشاء السنترال.';
          errEl.classList.remove('hidden');
        }
      } catch (err) {
        errEl.innerText = 'حدث خطأ أثناء الاتصال بالخادم.';
        errEl.classList.remove('hidden');
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>💾 إنشاء وتفعيل في LiveKit</span>';
      }
    }

    async function handleDeletePbxTrunk(id, name) {
      if (!confirm(`هل أنت متأكد من حذف سنترال "${name}"؟ سيتم إيقاف الـ SIP Trunk وحذف قاعدة التوجيه في LiveKit.`)) return;
      try {
        const res = await fetch(`/api/telephony/pbx-trunks/${id}/delete/`, {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        const data = await res.json();
        if (data.status === 'success') {
          await loadPbxTrunks();
        } else {
          alert('فشل الحذف: ' + (data.message || ''));
        }
      } catch (err) {
        alert('حدث خطأ أثناء حذف السنترال.');
      }
    }

    function showIssabelConfigModal(trunkId) {
      const trunk = currentPbxTrunks.find(t => t.id === trunkId);
      if (!trunk) return;

      const titleEl = document.getElementById('issabel-modal-title');
      const peerEl = document.getElementById('issabel-peer-content');
      const userEl = document.getElementById('issabel-user-content');
      const userBox = document.getElementById('issabel-user-box');
      const regBox = document.getElementById('issabel-register-box');
      const regEl = document.getElementById('issabel-register-content');

      if (titleEl) titleEl.innerText = `كود إعداد السنترال: ${trunk.name}`;
      if (peerEl) peerEl.innerText = (trunk.issabel_config && trunk.issabel_config.peer_details) || '';

      if (userEl) {
        const userDetails = (trunk.issabel_config && trunk.issabel_config.user_details) || '';
        userEl.innerText = userDetails;
        if (userBox) {
          if (userDetails.trim()) {
            userBox.classList.remove('hidden');
          } else {
            userBox.classList.add('hidden');
          }
        }
      }

      if (trunk.issabel_config && trunk.issabel_config.register_string && trunk.issabel_config.register_string.trim()) {
        if (regBox) regBox.classList.remove('hidden');
        if (regEl) regEl.innerText = trunk.issabel_config.register_string;
      } else {
        if (regBox) regBox.classList.add('hidden');
      }

      const modal = document.getElementById('issabel-code-modal');
      if (modal) modal.classList.remove('hidden');
    }

    function closeIssabelModal() {
      const modal = document.getElementById('issabel-code-modal');
      if (modal) modal.classList.add('hidden');
    }

    function copyIssabelSnippet(elementId, btn) {
      const text = document.getElementById(elementId).innerText;
      navigator.clipboard.writeText(text).then(() => {
        const originalText = btn.innerHTML;
        btn.innerHTML = '<span>✅ تم النسخ!</span>';
        setTimeout(() => {
          btn.innerHTML = originalText;
        }, 2000);
      });
    }

    // Initialize lists on load
    loadDocuments();
    loadProfiles();
    loadMcpServer();
    loadCustomersList();
    loadCustomerMemory();
    loadEmployees();
    loadQueues();
    loadOutboundTrunk();
    loadPbxTrunks();

    // Periodic polling to update agent presence states & queue waiting counts
    setInterval(loadQueues, 8000);
    setInterval(loadEmployees, 8000);
  
  