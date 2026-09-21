import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r'django_app/voice_assistant/templates/voice_assistant/room.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace the inner HTML of #tab-personas with a rich cards grid + editor studio
old_tab_personas_pattern = re.compile(r'<div id="tab-personas" class="tab-panel space-y-6">.*?</div>\s*<!-- ==================== Tab 3', re.DOTALL)

new_tab_personas_html = """<div id="tab-personas" class="tab-panel space-y-6">
        
        <!-- Header & Action Bar -->
        <div class="bg-white p-6 rounded-3xl border border-[#EAE3D9] shadow-sm flex flex-wrap justify-between items-center gap-4">
          <div class="flex items-center gap-3">
            <div class="w-12 h-12 rounded-2xl bg-gradient-to-tr from-[#680E23] to-[#8C1633] flex items-center justify-center text-2xl text-white shadow-md shadow-[#680E23]/20">
              🎭
            </div>
            <div>
              <h2 class="text-lg font-bold text-[#1C1917] flex items-center gap-2">
                <span data-i18n="personas_title">إدارة الشخصيات واللهجات وأصوات الذكاء الاصطناعي</span>
              </h2>
              <p class="text-xs text-[#6E645D]" data-i18n="personas_subtitle">
                اختر من بين الشخصيات المتاحة لتفعيلها فوراً في المكالمات الحية، أو خصص النبرة واللهجة والصوت
              </p>
            </div>
          </div>

          <div class="flex items-center gap-3">
            <button type="button" onclick="openNewProfileModal()" class="px-4 py-2.5 rounded-xl bg-[#680E23] hover:bg-[#7E152F] text-white text-xs font-bold transition flex items-center gap-2 shadow-md shadow-[#680E23]/20">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
              <span data-i18n="btn_new_persona">+ إنشاء شخصية جديدة</span>
            </button>
          </div>
        </div>

        <!-- Visual Personas Cards Grid (Interactive Cards from second design) -->
        <div>
          <div class="flex justify-between items-center mb-3">
            <h3 class="text-xs font-bold text-[#680E23] flex items-center gap-1.5 uppercase tracking-wide">
              <span>🌟</span>
              <span data-i18n="personas_catalog">الشخصيات المتاحة للمحادثات (Available AI Personas)</span>
            </h3>
            <span class="text-[11px] text-[#8C827A]" data-i18n="personas_click_hint">اضغط "تفعيل للمكالمات" لاختيار الشخصية المعتمدة للمساعد</span>
          </div>

          <div id="personas-cards-grid" class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="col-span-2 text-center py-10 text-[#8C827A] bg-white rounded-3xl border border-[#EAE3D9]">
              جاري تحميل كروت الشخصيات...
            </div>
          </div>
        </div>

        <!-- Customization Studio & Profile Details Editor -->
        <div id="profile-editor-card" class="bg-white rounded-3xl p-6 border border-[#EAE3D9] shadow-sm space-y-5 transition-all duration-300">
          <div class="flex flex-wrap justify-between items-center gap-3 pb-4 border-b border-[#EAE3D9]">
            <div class="flex items-center gap-2.5">
              <div class="w-8 h-8 rounded-xl bg-[#FAF0F2] text-[#680E23] flex items-center justify-center text-sm font-bold">
                ⚙️
              </div>
              <div>
                <h3 class="text-sm font-bold text-[#1C1917]" data-i18n="studio_title">استوديو تخصيص الشخصية المحددة</h3>
                <p class="text-[11px] text-[#8C827A]" data-i18n="studio_subtitle">تعديل الخامة الصوتية من Google (30 خامة)، الدور، والتعليمات البرمجية</p>
              </div>
            </div>

            <!-- Profile Selector Dropdown (Preserved for compatibility) -->
            <div class="flex items-center gap-2">
              <span class="text-xs text-[#6E645D]" data-i18n="label_selected_profile">الشخصية الحالية:</span>
              <select id="profile-select" onchange="handleProfileSelect(this.value)" class="px-3 py-1.5 rounded-xl bg-[#FAF7F2] border border-[#DDD5C7] text-xs font-semibold text-[#1C1917] focus:outline-none focus:border-[#680E23] focus:ring-[#680E23]">
                <option value="">جاري تحميل البروفايلات...</option>
              </select>
            </div>
          </div>

          <!-- Current Profile Summary / Editor Fields -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
            <!-- Gender & Dialect -->
            <div class="bg-[#FAF7F2] border border-[#EAE3D9] rounded-2xl p-3.5 space-y-2">
              <label class="block font-semibold text-[#443D39]" data-i18n="field_gender_dialect">النوع واللهجة</label>
              <div class="grid grid-cols-2 gap-2">
                <select id="field-gender" onchange="syncGenderVoiceOptions()" class="w-full px-2.5 py-1.5 bg-white border border-[#DDD5C7] rounded-lg text-[#1C1917]">
                  <option value="female">أنثى (بنت)</option>
                  <option value="male">ذكر (شاب)</option>
                </select>
                <select id="field-dialect" class="w-full px-2.5 py-1.5 bg-white border border-[#DDD5C7] rounded-lg text-[#1C1917]">
                  <option value="egyptian">مصرية عامية</option>
                  <option value="saudi">سعودية / خليجية</option>
                  <option value="levantine">شامية</option>
                  <option value="fusha">فصحى معاصرة</option>
                  <option value="english">English</option>
                </select>
              </div>
            </div>

            <!-- Google Voice Selector -->
            <div class="bg-[#FAF7F2] border border-[#EAE3D9] rounded-2xl p-3.5 space-y-2">
              <div class="flex justify-between items-center">
                <label class="font-semibold text-[#443D39]" data-i18n="field_google_voice">صوت Google الرسمي</label>
                <span id="voice-tag-badge" class="text-[10px] px-2 py-0.5 rounded-full bg-[#FAF0F2] text-[#680E23] border border-[#E8CCD2]">طبيعي وهادئ</span>
              </div>
              <select id="field-voice" onchange="updateVoiceTag()" class="w-full px-2.5 py-1.5 bg-white border border-[#DDD5C7] rounded-lg text-[#1C1917] font-mono text-xs">
              </select>
            </div>

            <!-- Persona Role -->
            <div class="bg-[#FAF7F2] border border-[#EAE3D9] rounded-2xl p-3.5 space-y-2">
              <label class="block font-semibold text-[#443D39]" data-i18n="field_role">الدور والشخصية</label>
              <select id="field-role" class="w-full px-2.5 py-1.5 bg-white border border-[#DDD5C7] rounded-lg text-[#1C1917]">
                <option value="customer_support">خدمة عملاء ومبيعات المتجر</option>
                <option value="sales_advisor">مستشار تسويق ومبيعات شاطر</option>
                <option value="personal_assistant">مساعد شخصي ذكي وودود</option>
                <option value="technical_consultant">مستشار فني ورسمي</option>
              </select>
            </div>

            <!-- Speaking Style & Pacing -->
            <div class="bg-[#FAF7F2] border border-[#EAE3D9] rounded-2xl p-3.5 space-y-2">
              <label class="block font-semibold text-[#443D39]" data-i18n="field_style">أسلوب الإلقاء والنبرة</label>
              <select id="field-style" class="w-full px-2.5 py-1.5 bg-white border border-[#DDD5C7] rounded-lg text-[#1C1917]">
                <option value="friendly">ودود ولطيف ومرح</option>
                <option value="formal">رسمي وهادئ ورصين</option>
                <option value="concise">مباشر وسريع وموجز</option>
                <option value="enthusiastic">حماسي وتشجيعي</option>
              </select>
            </div>
          </div>

          <!-- Custom Instructions & Action Buttons -->
          <div class="space-y-2 text-xs">
            <label class="block font-semibold text-[#443D39]" data-i18n="field_custom_instructions">تعليمات وتوجيهات خاصة إضافية للشخصية (Custom Prompt Instructions - اختياري):</label>
            <textarea id="field-custom" rows="2" placeholder="مثال: ناديني دائماً بـ 'يا باشا'، وركز على تشجيعي لتجربة المنتجات الجديدة..." class="w-full px-3 py-2 bg-[#FAF7F2] border border-[#DDD5C7] rounded-xl text-[#1C1917] focus:outline-none focus:border-[#680E23] focus:ring-[#680E23]"></textarea>
          </div>

          <div class="flex flex-wrap justify-between items-center gap-3 pt-3 border-t border-[#EAE3D9]">
            <div id="profile-status-msg" class="text-xs text-[#6E645D]"></div>
            <div class="flex items-center gap-2">
              <button type="button" onclick="saveActiveProfileChanges()" id="btn-save-profile" class="px-4 py-2 rounded-xl bg-[#680E23] hover:bg-[#7E152F] text-white text-xs font-bold transition flex items-center gap-1.5 shadow-md shadow-[#680E23]/20">
                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                <span data-i18n="btn_save_profile">حفظ وتطبيق على المكالمات</span>
              </button>
              <button type="button" onclick="deleteCurrentProfile()" id="btn-delete-profile" class="px-3.5 py-2 rounded-xl bg-[#F5EFE6] hover:bg-rose-50 hover:text-rose-700 text-[#6E645D] text-xs font-semibold border border-[#DDD5C7] transition">
                <span data-i18n="btn_delete_profile">حذف البروفايل</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- ==================== Tab 3"""

content = old_tab_personas_pattern.sub(new_tab_personas_html, content)

# 2. Add renderProfileCards and activateProfileById in JavaScript
js_enhancement = """
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
"""

# Insert renderProfileCards call inside loadProfiles
content = content.replace('renderProfileDropdown();', 'renderProfileDropdown();\n          renderProfileCards();')

# Insert the functions before loadProfiles
content = content.replace('async function loadProfiles() {', js_enhancement + '\n    async function loadProfiles() {')

with open(r'django_app/voice_assistant/templates/voice_assistant/room.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied rich personas cards grid and studio successfully.")
