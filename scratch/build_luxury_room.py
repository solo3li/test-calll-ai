import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r'django_app/voice_assistant/templates/voice_assistant/room.html.bak', 'r', encoding='utf-8') as f:
    orig = f.read()

lines = orig.splitlines()

# Extract JavaScript block
script_match = re.search(r'<script>(.*)</script>\s*</body>', orig, re.DOTALL)
if not script_match:
    raise ValueError("Could not find <script> block in room.html.bak")
orig_js = script_match.group(1)

def beautify(c):
    # Colors
    c = c.replace('bg-slate-950', 'bg-[#FAF7F2]')
    c = c.replace('bg-slate-900/90', 'bg-white shadow-[0_4px_25px_-3px_rgba(104,14,35,0.06)] border border-[#EAE3D9]')
    c = c.replace('bg-slate-900/80', 'bg-white shadow-[0_4px_25px_-3px_rgba(104,14,35,0.06)] border border-[#EAE3D9]')
    c = c.replace('bg-slate-900/70', 'bg-white border border-[#EAE3D9]')
    c = c.replace('bg-slate-900', 'bg-white border border-[#EAE3D9] shadow-sm')
    c = c.replace('bg-slate-800/80', 'bg-[#FAF7F2] border border-[#E8E0D5]')
    c = c.replace('bg-slate-800/70', 'bg-[#FAF7F2] border border-[#E8E0D5]')
    c = c.replace('bg-slate-800/60', 'bg-[#FAF7F2] border border-[#E8E0D5]')
    c = c.replace('bg-slate-800', 'bg-[#F5EFE6]')
    c = c.replace('bg-slate-700', 'bg-[#EAE3D9]')
    
    # Borders
    c = c.replace('border-slate-800/80', 'border-[#EAE3D9]')
    c = c.replace('border-slate-800', 'border-[#EAE3D9]')
    c = c.replace('border-slate-700/60', 'border-[#DDD5C7]')
    c = c.replace('border-slate-700', 'border-[#DDD5C7]')
    
    # Texts
    c = c.replace('text-slate-100', 'text-[#1C1917]')
    c = c.replace('text-slate-200', 'text-[#2D2825]')
    c = c.replace('text-slate-300', 'text-[#443D39]')
    c = c.replace('text-slate-400', 'text-[#6E645D]')
    c = c.replace('text-slate-500', 'text-[#8C827A]')
    c = c.replace('text-slate-600', 'text-[#A3988F]')
    
    # Primary Buttons
    c = c.replace('bg-purple-600', 'bg-[#680E23]')
    c = c.replace('hover:bg-purple-500', 'hover:bg-[#7E152F]')
    c = c.replace('bg-blue-600', 'bg-[#680E23]')
    c = c.replace('hover:bg-blue-500', 'hover:bg-[#7E152F]')
    c = c.replace('bg-indigo-600', 'bg-[#680E23]')
    c = c.replace('hover:bg-indigo-500', 'hover:bg-[#7E152F]')
    c = c.replace('bg-cyan-600', 'bg-[#680E23]')
    c = c.replace('hover:bg-cyan-500', 'hover:bg-[#7E152F]')
    
    # Focus rings
    c = c.replace('focus:border-purple-500', 'focus:border-[#680E23] focus:ring-[#680E23]')
    c = c.replace('focus:border-blue-500', 'focus:border-[#680E23] focus:ring-[#680E23]')
    c = c.replace('focus:border-indigo-500', 'focus:border-[#680E23] focus:ring-[#680E23]')
    
    # Text colors
    c = c.replace('text-purple-400', 'text-[#680E23]')
    c = c.replace('text-indigo-400', 'text-[#680E23]')
    c = c.replace('text-blue-400', 'text-[#680E23]')
    c = c.replace('text-purple-300', 'text-[#680E23]')
    
    # Notice boxes
    c = c.replace('bg-indigo-950/40 border border-indigo-900/60 text-indigo-200', 'bg-[#FAF0F2] border border-[#E8CCD2] text-[#5A0E1F]')
    c = c.replace('bg-purple-950/80 text-purple-300 border border-purple-800', 'bg-[#FAF0F2] text-[#680E23] border border-[#E8CCD2]')
    c = c.replace('bg-blue-950/80 text-blue-300 border border-blue-800', 'bg-[#FAF0F2] text-[#680E23] border border-[#E8CCD2]')
    
    # Table headers
    c = c.replace('thead class="text-xs text-slate-400 bg-slate-800/50"', 'thead class="text-xs text-[#680E23] bg-[#F5EFE6] font-semibold"')
    c = c.replace('text-xs text-slate-400 uppercase bg-slate-800/50', 'text-xs text-[#680E23] bg-[#F5EFE6] font-semibold')
    
    return c

# Extract subsections from original lines
voice_room_html = beautify("\n".join(lines[69:139]))
personas_html = beautify("\n".join(lines[140:244]))
modal_profile_html = beautify("\n".join(lines[246:320]))
rag_html = beautify("\n".join(lines[321:381]))
mcp_html = beautify("\n".join(lines[382:482]))
crm_html = beautify("\n".join(lines[483:599]))
employees_html = beautify("\n".join(lines[600:666]))
queues_html = beautify("\n".join(lines[667:715]))
outbound_html = beautify("\n".join(lines[716:808]))
pbx_html = beautify("\n".join(lines[809:843]))
other_modals_html = beautify("\n".join(lines[844:1276]))

# Refine Voice Room Visualizer Orb for the luxury look
voice_room_html = voice_room_html.replace(
    'class="w-32 h-32 rounded-full bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 flex items-center justify-center transition-all duration-300 shadow-xl shadow-blue-500/10"',
    'class="w-36 h-36 rounded-full luxury-voice-orb flex items-center justify-center transition-all duration-500 shadow-2xl cursor-pointer relative"'
)

# New HTML Document Template
new_html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
  <meta http-equiv="Pragma" content="no-cache" />
  <meta http-equiv="Expires" content="0" />
  <title>المساعد الصوتي الذكي | Enterprise Voice AI</title>
  
  <!-- Google Fonts: Tajawal (Arabic) & Inter (English) -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Tajawal:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  
  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  
  <!-- Centrifuge JS Client (WebSockets / App Events) -->
  <script src="https://unpkg.com/centrifuge@5.0.1/dist/centrifuge.js"></script>
  
  <!-- LiveKit Client JS (WebRTC Audio) -->
  <script src="https://cdn.jsdelivr.net/npm/livekit-client/dist/livekit-client.umd.min.js"></script>

  <style>
    :root {{
      --bg-canvas: #FAF7F2;
      --bg-surface: #F5EFE6;
      --bg-card: #FFFFFF;
      --burgundy-primary: #680E23;
      --burgundy-dark: #4A0817;
      --burgundy-accent: #841832;
      --gold-accent: #C5A880;
      --gold-border: #E8DAC6;
      --border-color: #EAE3D9;
      --text-dark: #1C1917;
    }}

    html[dir="rtl"] body {{
      font-family: 'Tajawal', sans-serif;
    }}
    html[dir="ltr"] body {{
      font-family: 'Inter', sans-serif;
    }}

    /* Luxury Acoustic Voice Orb Animation */
    .luxury-voice-orb {{
      background: radial-gradient(circle at 35% 35%, #9E1C38 0%, #680E23 55%, #420814 100%);
      border: 3px solid #D4AF37;
      box-shadow: 0 0 35px rgba(104, 14, 35, 0.35), 0 0 15px rgba(212, 175, 55, 0.25);
    }}

    @keyframes luxury-pulse {{
      0%, 100% {{
        transform: scale(1);
        box-shadow: 0 0 35px rgba(104, 14, 35, 0.35), 0 0 15px rgba(212, 175, 55, 0.25);
      }}
      50% {{
        transform: scale(1.06);
        box-shadow: 0 0 55px rgba(104, 14, 35, 0.65), 0 0 25px rgba(212, 175, 55, 0.55);
      }}
    }}

    .agent-active {{
      animation: luxury-pulse 2.2s infinite ease-in-out;
    }}

    /* SPA Tabs Animation */
    .tab-panel {{
      display: none;
      animation: fadeIn 0.25s ease-in-out forwards;
    }}
    .tab-panel.active {{
      display: block;
    }}

    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(6px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* Collapsible Sidebar States */
    .sidebar-expanded {{
      width: 16.5rem;
    }}
    .sidebar-collapsed {{
      width: 4.75rem;
    }}
    .sidebar-collapsed .nav-text,
    .sidebar-collapsed .brand-text {{
      display: none;
    }}
    .sidebar-collapsed .nav-item {{
      justify-content: center;
      padding-left: 0;
      padding-right: 0;
    }}

    /* Custom Luxury Scrollbar */
    ::-webkit-scrollbar {{
      width: 6px;
      height: 6px;
    }}
    ::-webkit-scrollbar-track {{
      background: #FAF7F2;
    }}
    ::-webkit-scrollbar-thumb {{
      background: #D5C7B5;
      border-radius: 9999px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
      background: #680E23;
    }}
  </style>
</head>
<body class="bg-[#FAF7F2] text-[#1C1917] min-h-screen flex flex-col md:flex-row antialiased">

  <!-- ==================== Luxury Burgundy Sidebar ==================== -->
  <aside id="sidebar" class="bg-gradient-to-b from-[#4A0817] via-[#680E23] to-[#3B0612] text-white flex flex-col justify-between transition-all duration-300 z-30 shadow-2xl shrink-0 sidebar-expanded border-l md:border-l-0 md:border-e border-[#5A0E1F]">
    
    <!-- Top Brand & Toggle -->
    <div>
      <div class="h-16 px-4 flex items-center justify-between border-b border-white/10">
        <div class="flex items-center gap-3 overflow-hidden cursor-pointer" onclick="switchTab('voice')">
          <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#D4AF37] to-[#C5A880] p-0.5 shadow-md flex items-center justify-center shrink-0">
            <div class="w-full h-full bg-[#4A0817] rounded-[10px] flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-[#D4AF37]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                <line x1="12" x2="12" y1="19" y2="22"/>
              </svg>
            </div>
          </div>
          <div class="brand-text">
            <h1 class="text-sm font-bold text-white tracking-wide" data-i18n="app_title">المساعد الصوتي الذكي</h1>
            <p class="text-[10px] text-[#EADBC8] font-medium" data-i18n="app_subtitle">منظومة الذكاء الاصطناعي</p>
          </div>
        </div>
        
        <!-- Toggle Collapse Button -->
        <button type="button" onclick="toggleSidebar()" class="text-[#EADBC8] hover:text-white p-1.5 rounded-lg hover:bg-white/10 transition" title="طي/توسيع القائمة">
          <svg id="sidebar-toggle-icon" xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 transition-transform duration-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        </button>
      </div>

      <!-- Navigation Links -->
      <nav class="p-3 space-y-1 text-xs font-semibold">
        <!-- 1. Voice Room -->
        <button type="button" onclick="switchTab('voice')" id="nav-btn-voice" class="nav-item w-full flex items-center gap-3 px-3.5 py-3 rounded-xl transition text-start bg-white/15 text-white shadow-sm border border-[#D4AF37]/30">
          <span class="text-base shrink-0">🎙️</span>
          <span class="nav-text" data-i18n="nav_voice">غرفة المساعد الصوتي</span>
        </button>

        <!-- 2. Personas -->
        <button type="button" onclick="switchTab('personas')" id="nav-btn-personas" class="nav-item w-full flex items-center gap-3 px-3.5 py-3 rounded-xl transition text-start text-[#EADBC8] hover:text-white hover:bg-white/10">
          <span class="text-base shrink-0">🎭</span>
          <span class="nav-text" data-i18n="nav_personas">الشخصيات واللهجات</span>
        </button>

        <!-- 3. RAG -->
        <button type="button" onclick="switchTab('rag')" id="nav-btn-rag" class="nav-item w-full flex items-center gap-3 px-3.5 py-3 rounded-xl transition text-start text-[#EADBC8] hover:text-white hover:bg-white/10">
          <span class="text-base shrink-0">📚</span>
          <span class="nav-text" data-i18n="nav_rag">قاعدة المعرفة RAG</span>
        </button>

        <!-- 4. Call Center -->
        <button type="button" onclick="switchTab('callcenter')" id="nav-btn-callcenter" class="nav-item w-full flex items-center gap-3 px-3.5 py-3 rounded-xl transition text-start text-[#EADBC8] hover:text-white hover:bg-white/10">
          <span class="text-base shrink-0">🎧</span>
          <span class="nav-text" data-i18n="nav_callcenter">مركز الاتصالات والطوابير</span>
        </button>

        <!-- 5. Telephony -->
        <button type="button" onclick="switchTab('telephony')" id="nav-btn-telephony" class="nav-item w-full flex items-center gap-3 px-3.5 py-3 rounded-xl transition text-start text-[#EADBC8] hover:text-white hover:bg-white/10">
          <span class="text-base shrink-0">📞</span>
          <span class="nav-text" data-i18n="nav_telephony">الربط الهاتفي والسنترال</span>
        </button>

        <!-- 6. CRM -->
        <button type="button" onclick="switchTab('crm')" id="nav-btn-crm" class="nav-item w-full flex items-center gap-3 px-3.5 py-3 rounded-xl transition text-start text-[#EADBC8] hover:text-white hover:bg-white/10">
          <span class="text-base shrink-0">🧠</span>
          <span class="nav-text" data-i18n="nav_crm">ذاكرة وسجل العملاء</span>
        </button>

        <!-- 7. Store MCP -->
        <button type="button" onclick="switchTab('store')" id="nav-btn-store" class="nav-item w-full flex items-center gap-3 px-3.5 py-3 rounded-xl transition text-start text-[#EADBC8] hover:text-white hover:bg-white/10">
          <span class="text-base shrink-0">🛍️</span>
          <span class="nav-text" data-i18n="nav_store">متجر وأدوات MCP</span>
        </button>
      </nav>
    </div>

    <!-- Sidebar Bottom Profile / Status -->
    <div class="p-3 border-t border-white/10 space-y-2">
      <div class="flex items-center gap-2.5 px-2 py-1.5 rounded-xl bg-white/5">
        <div class="w-8 h-8 rounded-full bg-[#D4AF37] text-[#4A0817] font-bold flex items-center justify-center text-xs shrink-0 shadow">
          100
        </div>
        <div class="brand-text overflow-hidden text-xs">
          <p class="font-bold text-white truncate">{{{{ request.user.username }}}}</p>
          <span class="text-[10px] text-[#EADBC8] block" data-i18n="role_admin">مدير النظام (Super Admin)</span>
        </div>
      </div>
      
      <div class="flex justify-between items-center px-1 text-xs">
        <a href="/admin/" target="_blank" class="text-[#EADBC8] hover:text-white flex items-center gap-1 transition text-[11px]" data-i18n="btn_django_admin">
          ⚙️ لوحة الإدارة
        </a>
        <a href="{{% url 'voice_assistant:logout' %}}" class="text-rose-300 hover:text-rose-100 flex items-center gap-1 transition text-[11px]" data-i18n="btn_logout">
          🚪 خروج
        </a>
      </div>
    </div>
  </aside>

  <!-- ==================== Main App Workspace ==================== -->
  <div id="main-wrapper" class="flex-1 flex flex-col min-w-0 min-h-screen">
    
    <!-- Top Luxury Header -->
    <header class="sticky top-0 z-20 bg-white/90 backdrop-blur border-b border-[#EAE3D9] px-6 py-3.5 flex flex-wrap items-center justify-between gap-4 shadow-sm">
      <div class="flex items-center gap-3">
        <!-- Section Title Breadcrumb -->
        <h2 id="current-section-title" class="text-base font-bold text-[#680E23] flex items-center gap-2">
          🎙️ <span data-i18n="nav_voice">غرفة المساعد الصوتي</span>
        </h2>
      </div>

      <!-- Live Service Status Badges -->
      <div class="flex flex-wrap items-center gap-3 text-xs">
        <span id="livekit-status" class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#FAF7F2] border border-[#EAE3D9] text-[#6E645D] font-medium shadow-sm">
          <span class="w-2 h-2 rounded-full bg-slate-400"></span> LiveKit: جاري التحقق...
        </span>
        <span id="centrifugo-status" class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#FAF7F2] border border-[#EAE3D9] text-[#6E645D] font-medium shadow-sm">
          <span class="w-2 h-2 rounded-full bg-slate-400"></span> Centrifugo: جاري التحقق...
        </span>

        <!-- Bilingual Switcher Toggle Button -->
        <button type="button" onclick="toggleLanguage()" id="lang-switch-btn" class="px-3.5 py-1.5 rounded-full bg-[#FAF0F2] border border-[#E8CCD2] text-[#680E23] text-xs font-bold hover:bg-[#F3E2E6] transition flex items-center gap-1.5 shadow-sm">
          🌐 <span id="lang-text">English</span>
        </button>
      </div>
    </header>

    <!-- Content Workspace -->
    <main class="flex-1 p-6 max-w-6xl w-full mx-auto space-y-6">

      <!-- ==================== Tab 1: Voice Room ==================== -->
      <div id="tab-voice" class="tab-panel active space-y-6">
        
        <!-- Luxury Metrics Row -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
          <div class="bg-white p-4 rounded-2xl border border-[#EAE3D9] shadow-sm flex items-center gap-3.5">
            <div class="w-10 h-10 rounded-xl bg-[#FAF0F2] text-[#680E23] flex items-center justify-center text-lg">📞</div>
            <div>
              <p class="text-[#8C827A] font-medium" data-i18n="metric_calls">المكالمات النشطة</p>
              <h4 class="text-lg font-bold text-[#1C1917]">1</h4>
            </div>
          </div>
          <div class="bg-white p-4 rounded-2xl border border-[#EAE3D9] shadow-sm flex items-center gap-3.5">
            <div class="w-10 h-10 rounded-xl bg-[#FAF0F2] text-[#680E23] flex items-center justify-center text-lg">⚡</div>
            <div>
              <p class="text-[#8C827A] font-medium" data-i18n="metric_latency">زمن استجابة الـ AI</p>
              <h4 class="text-lg font-bold text-[#1C1917]">380ms</h4>
            </div>
          </div>
          <div class="bg-white p-4 rounded-2xl border border-[#EAE3D9] shadow-sm flex items-center gap-3.5">
            <div class="w-10 h-10 rounded-xl bg-[#FAF0F2] text-[#680E23] flex items-center justify-center text-lg">📚</div>
            <div>
              <p class="text-[#8C827A] font-medium" data-i18n="metric_rag">فهرس المعرفة</p>
              <h4 class="text-lg font-bold text-emerald-700" data-i18n="metric_rag_status">متصل ومحدث</h4>
            </div>
          </div>
          <div class="bg-white p-4 rounded-2xl border border-[#EAE3D9] shadow-sm flex items-center gap-3.5">
            <div class="w-10 h-10 rounded-xl bg-[#FAF0F2] text-[#680E23] flex items-center justify-center text-lg">👥</div>
            <div>
              <p class="text-[#8C827A] font-medium" data-i18n="metric_queue">جاهزية الطوابير</p>
              <h4 class="text-lg font-bold text-emerald-700">100%</h4>
            </div>
          </div>
        </div>

        <!-- Voice Room Content (Orb, Controls, Subtitles) -->
        <div class="bg-white p-6 md:p-8 rounded-3xl border border-[#EAE3D9] shadow-[0_4px_25px_-3px_rgba(104,14,35,0.06)] space-y-6">
          {voice_room_html}
        </div>
      </div>

      <!-- ==================== Tab 2: Personas Studio ==================== -->
      <div id="tab-personas" class="tab-panel space-y-6">
        {personas_html}
      </div>

      <!-- ==================== Tab 3: Knowledge Base RAG ==================== -->
      <div id="tab-rag" class="tab-panel space-y-6">
        {rag_html}
      </div>

      <!-- ==================== Tab 4: Call Center & Queues ==================== -->
      <div id="tab-callcenter" class="tab-panel space-y-6">
        {employees_html}
        {queues_html}
      </div>

      <!-- ==================== Tab 5: Telephony & PBX ==================== -->
      <div id="tab-telephony" class="tab-panel space-y-6">
        {outbound_html}
        {pbx_html}
      </div>

      <!-- ==================== Tab 6: Customer CRM & Memory ==================== -->
      <div id="tab-crm" class="tab-panel space-y-6">
        {crm_html}
      </div>

      <!-- ==================== Tab 7: Store & Tools MCP ==================== -->
      <div id="tab-store" class="tab-panel space-y-6">
        {mcp_html}
      </div>

      <!-- Modals Container -->
      <div id="modals-root">
        {modal_profile_html}
        {other_modals_html}
      </div>

    </main>
  </div>

  <!-- ==================== Floating Persistent Voice Bar ==================== -->
  <div id="floating-voice-bar" class="fixed bottom-6 start-1/2 -translate-x-1/2 z-40 bg-white/95 backdrop-blur-md border-2 border-[#C5A880] shadow-[0_12px_40px_rgba(104,14,35,0.22)] rounded-full px-5 py-2.5 flex items-center gap-4 transition-all duration-300 transform scale-95 opacity-0 pointer-events-none">
    <div class="flex items-center gap-2.5">
      <div id="floating-orb" class="w-9 h-9 rounded-full luxury-voice-orb flex items-center justify-center shrink-0">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-[#D4AF37]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        </svg>
      </div>
      <div class="text-xs">
        <p id="floating-status" class="font-bold text-[#680E23]">المساعد الصوتي قيد التشغيل</p>
        <span class="text-[10px] text-[#8C827A]" data-i18n="floating_hint">محادثة مستمرة عبر LiveKit</span>
      </div>
    </div>

    <div class="h-6 w-px bg-[#EAE3D9]"></div>

    <div class="flex items-center gap-2">
      <button type="button" onclick="toggleMute()" id="floating-btn-mute" class="p-2 rounded-full bg-[#FAF7F2] hover:bg-[#F5EFE6] text-[#680E23] border border-[#DDD5C7] transition" title="كتم/تفعيل المايك">
        🎤
      </button>
      <button type="button" onclick="endCall()" id="floating-btn-end" class="p-2 rounded-full bg-rose-100 hover:bg-rose-200 text-rose-800 border border-rose-300 transition" title="إنهاء المكالمة">
        🛑
      </button>
      <button type="button" onclick="switchTab('voice')" class="px-3 py-1.5 rounded-full bg-[#680E23] hover:bg-[#7E152F] text-white text-xs font-bold transition flex items-center gap-1">
        <span data-i18n="btn_full_room">غرفة الصوت</span> ↗
      </button>
    </div>
  </div>

  <!-- ==================== Original Scripts + Luxury UI Orchestrator ==================== -->
  <script>
    // Bilingual Localization Dictionary
    const I18N = {{
      ar: {{
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
      }},
      en: {{
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
      }}
    }};

    let currentLanguage = localStorage.getItem('voice_app_lang') || 'ar';
    let activeTabId = 'voice';

    function applyLanguage(lang) {{
      currentLanguage = lang;
      localStorage.setItem('voice_app_lang', lang);
      const isRtl = lang === 'ar';
      
      document.documentElement.dir = isRtl ? 'rtl' : 'ltr';
      document.documentElement.lang = lang;
      
      // Update lang switch button text
      const langText = document.getElementById('lang-text');
      if (langText) {{
        langText.innerText = I18N[lang].switch_to;
      }}

      // Update all elements with data-i18n
      document.querySelectorAll('[data-i18n]').forEach(el => {{
        const key = el.getAttribute('data-i18n');
        if (I18N[lang] && I18N[lang][key]) {{
          el.innerText = I18N[lang][key];
        }}
      }});

      // Update current section title
      updateHeaderTitle();
    }}

    function toggleLanguage() {{
      const nextLang = currentLanguage === 'ar' ? 'en' : 'ar';
      applyLanguage(nextLang);
    }}

    function updateHeaderTitle() {{
      const titleEl = document.querySelector('#current-section-title span');
      if (titleEl) {{
        const key = 'nav_' + activeTabId;
        if (I18N[currentLanguage] && I18N[currentLanguage][key]) {{
          titleEl.innerText = I18N[currentLanguage][key];
        }}
      }}
    }}

    // SPA Tab Switching Logic
    function switchTab(tabId) {{
      activeTabId = tabId;
      
      // Hide all panels
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      
      // Show selected panel
      const target = document.getElementById('tab-' + tabId);
      if (target) {{
        target.classList.add('active');
      }}

      // Update sidebar nav active styling
      document.querySelectorAll('.nav-item').forEach(btn => {{
        btn.classList.remove('bg-white/15', 'text-white', 'border', 'border-[#D4AF37]/30');
        btn.classList.add('text-[#EADBC8]');
      }});
      
      const activeNavBtn = document.getElementById('nav-btn-' + tabId);
      if (activeNavBtn) {{
        activeNavBtn.classList.add('bg-white/15', 'text-white', 'border', 'border-[#D4AF37]/30');
        activeNavBtn.classList.remove('text-[#EADBC8]');
      }}

      updateHeaderTitle();
      syncFloatingVoiceBar();
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}

    // Sidebar Collapse / Expand
    function toggleSidebar() {{
      const sidebar = document.getElementById('sidebar');
      const icon = document.getElementById('sidebar-toggle-icon');
      if (!sidebar) return;

      const isExpanded = sidebar.classList.contains('sidebar-expanded');
      if (isExpanded) {{
        sidebar.classList.remove('sidebar-expanded');
        sidebar.classList.add('sidebar-collapsed');
        if (icon) icon.classList.add('rotate-180');
      }} else {{
        sidebar.classList.remove('sidebar-collapsed');
        sidebar.classList.add('sidebar-expanded');
        if (icon) icon.classList.remove('rotate-180');
      }}
    }}

    // Sync Floating Voice Widget when browsing other sections
    function syncFloatingVoiceBar() {{
      const floatingBar = document.getElementById('floating-voice-bar');
      if (!floatingBar) return;

      // Show floating bar only if we are outside the voice room AND call is active
      const isVoiceRoom = activeTabId === 'voice';
      const isCallActive = (livekitRoom && livekitRoom.state === 'connected') || (btnEnd && !btnEnd.disabled);

      if (!isVoiceRoom && isCallActive) {{
        floatingBar.classList.remove('opacity-0', 'pointer-events-none', 'scale-95');
        floatingBar.classList.add('opacity-100', 'pointer-events-auto', 'scale-100');
        
        const floatingStatus = document.getElementById('floating-status');
        const mainCallStatus = document.getElementById('call-status');
        if (floatingStatus && mainCallStatus) {{
          floatingStatus.innerText = mainCallStatus.innerText;
        }}
      }} else {{
        floatingBar.classList.add('opacity-0', 'pointer-events-none', 'scale-95');
        floatingBar.classList.remove('opacity-100', 'pointer-events-auto', 'scale-100');
      }}
    }}

    // Periodically check floating voice bar state
    setInterval(syncFloatingVoiceBar, 1000);

    // Apply saved language on page boot
    document.addEventListener('DOMContentLoaded', () => {{
      applyLanguage(currentLanguage);
    }});

    // ==================== ORIGINAL ENGINE JAVASCRIPT ====================
    {orig_js}
  </script>
</body>
</html>
"""

# Write the new generated file to django_app/voice_assistant/templates/voice_assistant/room.html
with open(r'django_app/voice_assistant/templates/voice_assistant/room.html', 'w', encoding='utf-8') as f:
    f.write(new_html)

print("Successfully built luxury off-white & burgundy room.html!")
