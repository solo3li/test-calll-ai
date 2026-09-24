import asyncio
import os
import sys
import time
import datetime
import json
import logging
import signal
import requests
import redis.asyncio as aioredis
from dotenv import load_dotenv
from google import genai
from google.genai import types
from livekit import api, rtc
from queue_manager import run_queue_session

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("VoiceAgentDaemon")

LIVEKIT_INTERNAL_URL = os.getenv("LIVEKIT_INTERNAL_URL", "ws://livekit:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "secretkey1234567890abcdef")
CENTRIFUGO_HTTP_API_URL = os.getenv("CENTRIFUGO_HTTP_API_URL", "http://centrifugo:8000/api")
CENTRIFUGO_API_KEY = os.getenv("CENTRIFUGO_API_KEY", "centrifugo_api_key_1234567890")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://django:8000")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "voice-internal-secret-token-key-12345")

def notify_centrifugo(channel: str, event: str, message: str = "", extra: dict = None):
    """Notify web client via Centrifugo WebSocket channel."""
    try:
        url = f"{CENTRIFUGO_HTTP_API_URL}/publish"
        if isinstance(event, dict):
            extra_data = event
            event_name = extra_data.get("event", "notification")
            msg = extra_data.get("message", message or "")
        else:
            event_name = event
            msg = message or ""
            extra_data = extra or {}

        payload = {
            "channel": channel,
            "data": {
                "event": event_name,
                "message": msg,
                "timestamp": time.time(),
                **extra_data
            }
        }
        headers = {
            "Authorization": f"apikey {CENTRIFUGO_API_KEY}",
            "Content-Type": "application/json"
        }
        requests.post(url, json=payload, headers=headers, timeout=2)
    except Exception as e:
        logger.warning(f"Could not notify Centrifugo: {e}")

def fetch_agent_bootstrap_sync(user_id: int, caller_phone: str = "web_dashboard") -> dict:
    """Fetch complete agent bootstrap bundle (profile, mcp, memory) via Django API."""
    if not user_id:
        return {}
    try:
        url = f"{DJANGO_API_URL}/api/agents/internal/bootstrap/"
        headers = {
            "X-Internal-API-Key": INTERNAL_API_KEY,
            "Content-Type": "application/json"
        }
        res = requests.post(url, json={"user_id": user_id, "caller_phone": caller_phone}, headers=headers, timeout=5)
        if res.status_code == 200:
            return res.json()
        logger.error(f"Bootstrap API error ({res.status_code}): {res.text}")
        return {}
    except Exception as e:
        logger.error(f"Failed to fetch bootstrap from Django API: {e}")
        return {}

def query_knowledge_base_sync(query: str, user_id: int, genai_client=None, top_k: int = 4) -> str:
    """Query user's documents semantically via Django Knowledge RAG API."""
    if not user_id:
        return "لا توجد مستندات مرفوعة لهذا المستخدم."
    try:
        url = f"{DJANGO_API_URL}/api/knowledge/internal/rag/"
        headers = {
            "X-Internal-API-Key": INTERNAL_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "user_id": user_id,
            "query": query,
            "top_k": top_k
        }
        res = requests.post(url, json=payload, headers=headers, timeout=6)
        if res.status_code == 200:
            data = res.json()
            return data.get("text", "لم يتم العثور على أي معلومات متعلقة بهذا السؤال في المستندات المرفوعة.")
        else:
            logger.error(f"Knowledge RAG API error ({res.status_code}): {res.text}")
            return "حدث خطأ أثناء البحث في المستندات عبر الواجهة البرمجية."
    except Exception as e:
        logger.error(f"Failed to query knowledge API: {e}", exc_info=True)
        return f"حدث خطأ أثناء البحث في المستندات: {e}"

def parse_mcp_servers_from_bootstrap(bootstrap: dict) -> list:
    """Extract and format active MCP servers from bootstrap dictionary."""
    servers = bootstrap.get("mcp_servers", []) if bootstrap else []
    clean_servers = []
    for s in servers:
        if not s or not s.get("is_active", True):
            continue
        tools = s.get("cached_tools", [])
        if isinstance(tools, str):
            try:
                tools = json.loads(tools)
            except Exception:
                tools = []
        clean_servers.append({
            "server_url": s.get("server_url", ""),
            "auth_token": s.get("auth_token", ""),
            "tools": tools or [],
            "name": s.get("name", "خادم MCP")
        })
    return clean_servers

def parse_customer_memory_from_bootstrap(bootstrap: dict, caller_phone: str = "web_dashboard") -> dict:
    """Extract and format customer memory from bootstrap dictionary."""
    if not bootstrap:
        return {"phone_number": caller_phone, "permanent_profile": {}, "last_interaction_summary": "", "card_text": "", "total_calls_count": 0}
    mem = bootstrap.get("customer_memory", {})
    prof = mem.get("permanent_profile") or {}
    if isinstance(prof, str):
        try:
            prof = json.loads(prof)
        except Exception:
            prof = {}
    summary = mem.get("last_interaction_summary", "")

    parts = []
    if prof:
        items = []
        if prof.get("customer_name"):
            items.append(f"اسم العميل المفضل: {prof['customer_name']}")
        phone_val = caller_phone if caller_phone != 'web_dashboard' else prof.get("phone")
        if phone_val:
            items.append(f"الهاتف: {phone_val}")
        if prof.get("city") or prof.get("address"):
            items.append(f"العنوان/المدينة: {prof.get('city') or prof.get('address')}")
        if prof.get("preferences"):
            prefs = prof['preferences']
            if isinstance(prefs, list):
                prefs = "، ".join(str(p) for p in prefs)
            items.append(f"تفضيلات واهتمامات العميل: {prefs}")
        if prof.get("notes"):
            items.append(f"ملاحظات هامة: {prof['notes']}")
        if items:
            parts.append("البيانات الدائمة للعميل:\n- " + "\n- ".join(items))

    if summary:
        parts.append(f"الذاكرة اللحظية من آخر تواصل:\n{summary}")

    card_text = ""
    if parts:
        phone_label = f" ({caller_phone})" if caller_phone and caller_phone != 'web_dashboard' else ""
        card_text = f"ذاكرة وسياق العميل{phone_label} من المكالمات السابقة (استخدمها بذكاء وعفوية للتذكر والترحيب بالمتابعة):\n" + "\n\n".join(parts)

    return {
        "phone_number": caller_phone,
        "permanent_profile": prof,
        "last_interaction_summary": summary,
        "card_text": card_text,
        "total_calls_count": mem.get("total_calls_count", 0)
    }

def parse_active_profile_from_bootstrap(bootstrap: dict) -> dict:
    """Extract active profile from bootstrap dictionary with fallbacks."""
    default_profile = {
        "name": "نورهان - خدمة عملاء مصرية",
        "voice_name": "Aoede",
        "gender": "female",
        "dialect": "egyptian",
        "persona_role": "customer_support",
        "speaking_style": "friendly",
        "custom_instructions": ""
    }
    if not bootstrap:
        return default_profile
    prof = bootstrap.get("profile")
    if prof and isinstance(prof, dict):
        return {
            "voice_name": prof.get("voice_name") or "Aoede",
            "gender": prof.get("gender") or "female",
            "dialect": prof.get("dialect") or "egyptian",
            "persona_role": prof.get("persona_role") or "customer_support",
            "speaking_style": prof.get("speaking_style") or "friendly",
            "custom_instructions": prof.get("custom_instructions") or "",
            "name": prof.get("name") or "المساعد"
        }
    return default_profile

def fetch_user_mcp_servers_sync(user_id: int, bootstrap: dict = None) -> list:
    """Fetch all active external MCP servers and cached tools for user via Django API."""
    if bootstrap is not None:
        return parse_mcp_servers_from_bootstrap(bootstrap)
    if not user_id:
        return []
    try:
        b = fetch_agent_bootstrap_sync(user_id)
        return parse_mcp_servers_from_bootstrap(b)
    except Exception as e:
        logger.error(f"Error fetching MCP servers for user {user_id}: {e}")
        return []

# Backwards compatibility alias
fetch_user_mcp_server_sync = fetch_user_mcp_servers_sync

async def execute_mcp_tool_call(server_url: str, auth_token: str, tool_name: str, arguments: dict) -> str:
    """Execute tool call on external MCP SSE server with strict timeout and fallback."""
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    logger.info(f"Connecting to MCP SSE at {server_url} to call '{tool_name}' with {arguments}")
    try:
        async def _call():
            async with sse_client(server_url, headers=headers) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments=arguments)
                    out_texts = []
                    for c in result.content:
                        if hasattr(c, "text"):
                            out_texts.append(c.text)
                        else:
                            out_texts.append(str(c))
                    return "\n".join(out_texts) if out_texts else "{}"

        return await asyncio.wait_for(_call(), timeout=4.0)
    except asyncio.TimeoutError:
        logger.warning(f"MCP tool '{tool_name}' timed out after 4.0s")
        return "عذراً، استغرق نظام المتجر وقتاً أطول من المتوقع للرد."
    except Exception as ex:
        logger.error(f"Error calling MCP tool '{tool_name}' on {server_url}: {ex}", exc_info=True)
        return f"حدث خطأ أثناء الاتصال بنظام المتجر: {str(ex)}"

def fetch_user_active_profile_sync(user_id: int, bootstrap: dict = None) -> dict:
    """Fetch active agent profile for user via Django API."""
    if bootstrap is not None:
        return parse_active_profile_from_bootstrap(bootstrap)
    if not user_id:
        return parse_active_profile_from_bootstrap({})
    try:
        b = fetch_agent_bootstrap_sync(user_id)
        return parse_active_profile_from_bootstrap(b)
    except Exception as e:
        logger.error(f"Error fetching active profile for user {user_id}: {e}")
        return parse_active_profile_from_bootstrap({})

def fetch_customer_memory_sync(user_id: int, caller_phone: str = "web_dashboard", bootstrap: dict = None) -> dict:
    """Fetch customer memory (permanent profile + immediate summary) for a specific phone number via Django API."""
    if bootstrap is not None:
        return parse_customer_memory_from_bootstrap(bootstrap, caller_phone)
    if not user_id:
        return parse_customer_memory_from_bootstrap({}, caller_phone)
    try:
        b = fetch_agent_bootstrap_sync(user_id, caller_phone)
        return parse_customer_memory_from_bootstrap(b, caller_phone)
    except Exception as e:
        logger.error(f"Error fetching customer memory for user {user_id} ({caller_phone}): {e}")
        return {"phone_number": caller_phone, "permanent_profile": {}, "last_interaction_summary": "", "card_text": "", "total_calls_count": 0}

def save_call_session_and_update_memory_sync(user_id: int, room_name: str, started_at: float, transcript_text: str, summary: str, updated_profile: dict, caller_phone: str = "web_dashboard", outbound_context: dict = None):
    """Persist completed CallSession and update CustomerMemory for (user, caller_phone) via Django CRM API."""
    if not user_id:
        return
    try:
        now_ts = time.time()
        duration = max(0, int(now_ts - started_at))

        direction = 'inbound'
        destination_phone = ''
        call_goal = ''
        if outbound_context:
            if outbound_context.get("is_outbound_ai"):
                direction = 'outbound_ai'
            elif outbound_context.get("direction"):
                direction = outbound_context.get("direction")
            destination_phone = str(outbound_context.get("destination_phone") or "")
            call_goal = str(outbound_context.get("call_goal") or "")

        url = f"{DJANGO_API_URL}/api/crm/internal/complete-call/"
        headers = {
            "X-Internal-API-Key": INTERNAL_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "user_id": user_id,
            "room_name": room_name,
            "caller_phone": caller_phone,
            "started_at": started_at,
            "duration_seconds": duration,
            "direction": direction,
            "destination_phone": destination_phone,
            "call_goal": call_goal,
            "transcript_text": transcript_text,
            "summary": summary,
            "permanent_profile": updated_profile
        }
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        if res.status_code == 200:
            logger.info(f"Successfully saved CallSession & CustomerMemory via Django CRM API for ({user_id}, {caller_phone})")
        else:
            logger.error(f"Error saving CallSession via CRM API ({res.status_code}): {res.text}")
    except Exception as e:
        logger.error(f"Failed to save call session via Django API: {e}", exc_info=True)

async def distill_and_update_memory(user_id: int, room_name: str, started_at: float, messages: list[dict], current_profile: dict, caller_phone: str = "web_dashboard", genai_client = None, outbound_context: dict = None):
    """Background task to extract permanent profile facts and distill short-term episode summary."""
    try:
        user_msgs = [m for m in messages if m.get("speaker") == "user"]
        if not user_msgs or len(messages) < 2:
            logger.info(f"Call in room {room_name} had insufficient speech turns ({len(messages)}). Skipping memory distillation.")
            return

        lines = []
        for m in messages:
            speaker_label = "العميل" if m.get("speaker") == "user" else "المساعد"
            lines.append(f"{speaker_label}: {m.get('text', '')}")
        transcript_text = "\n".join(lines)

        distillation_prompt = f"""أنت محلل ذكاء اصطناعي متخصص في استخلاص ذاكرة العملاء لمساعد صوتي ذكي.
المطلوب منك تحليل نص هذه المكالمة الصوتية واستخراج نقطتين فقط بدقة وإيجاز شديد:
1. "summary": ملخص دقيق ومركز جداً في سطرين فقط (لا يتعدى 50 كلمة) لما دار في المكالمة، والأسئلة أو المنتجات التي سأل عنها، وما إذا كان هناك أي أمر معلق يحتاج متابعة في المكالمة القادمة.
2. "new_permanent_facts": أي حقائق دائمة جديدة ذكرها العميل صراحةً (اسمه، هاتفه، عنوانه/مدينته، اهتمامات وتفضيلات محددة بالمنتجات، ملاحظات). إذا لم يذكر أي حقيقة جديدة، اترك الحقل فارغاً.

البروفايل الدائم الحالي للعميل:
{json.dumps(current_profile, ensure_ascii=False)}

نص المكالمة:
{transcript_text}

أجب بصيغة JSON فقط بهذا الشكل:
{{
  "summary": "...",
  "new_permanent_facts": {{
    "customer_name": "...",
    "phone": "...",
    "address": "...",
    "preferences": ["..."],
    "notes": "..."
  }}
}}"""

        response = await genai_client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=distillation_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        resp_text = response.text or "{}"
        data = json.loads(resp_text)
        summary = data.get("summary", "").strip()
        new_facts = data.get("new_permanent_facts", {})

        updated_profile = dict(current_profile or {})
        if new_facts and isinstance(new_facts, dict):
            for k in ["customer_name", "phone", "address", "notes"]:
                val = new_facts.get(k)
                if val and str(val).strip() and str(val).strip().lower() not in ["null", "none", "..."]:
                    updated_profile[k] = str(val).strip()

            if new_facts.get("preferences") and isinstance(new_facts["preferences"], list):
                existing_prefs = list(updated_profile.get("preferences") or [])
                for p in new_facts["preferences"]:
                    p_str = str(p).strip()
                    if p_str and p_str not in existing_prefs:
                        existing_prefs.append(p_str)
                updated_profile["preferences"] = existing_prefs[:6]

        # Dynamic binding: if caller was anonymous/web but explicitly stated their phone number in the call
        extracted_phone = updated_profile.get("phone")
        final_phone = caller_phone
        if extracted_phone and str(extracted_phone).strip() and caller_phone in ['web_dashboard', 'anonymous', 'unknown', '']:
            final_phone = str(extracted_phone).strip()
            logger.info(f"Dynamically bound call in room {room_name} to extracted phone '{final_phone}'")

        logger.info(f"Distillation complete for ({user_id}, {final_phone}). Summary: {summary[:80]}...")

        await asyncio.to_thread(
            save_call_session_and_update_memory_sync,
            user_id,
            room_name,
            started_at,
            transcript_text,
            summary,
            updated_profile,
            final_phone,
            outbound_context
        )
    except Exception as e:
        logger.error(f"Error in distill_and_update_memory for user {user_id}: {e}", exc_info=True)

def build_dynamic_system_instruction(profile: dict, memory_card: str = "", queue_context: dict = None, outbound_context: dict = None) -> str:
    """Construct dynamic prompt incorporating dialect, gender, role, style, memory, queue fallback context, outbound context, and strict guardrails."""
    gender = profile.get("gender", "female")
    dialect = profile.get("dialect", "egyptian")
    role = profile.get("persona_role", "customer_support")
    style = profile.get("speaking_style", "friendly")
    custom = (profile.get("custom_instructions") or "").strip()
    name = profile.get("name", "المساعد")

    outbound_header = ""
    if outbound_context and outbound_context.get("is_outbound_ai"):
        goal = (outbound_context.get("call_goal") or "التواصل مع العميل والرد على استفساراته").strip()
        dest = outbound_context.get("destination_phone") or ""
        outbound_header = (
            f"[توجيه فوري ذو أولوية عليا - مكالمة هاتفية صادرة للعميل]:\n"
            f"أنت المساعد الصوتي الذكي وتتصل هاتفياً بالعميل على رقم هاتفه ({dest}).\n"
            f"الهدف المطلوب تحقيقه في هذه المكالمة الصادرة:\n\"{goal}\"\n\n"
            f"تعليمات هامة عند فتح العميل للخط:\n"
            f"1. بادر فوراً بالترحيب بالعميل بلباقة وعرف باسمك واشرح سبب اتصالك مباشرة وفقاً للهدف المحدد أعلاه.\n"
            f"2. استمع لرد العميل وتجاوب معه بمرونة واستخدم الأدوات المناسبة للإجابة على استفساراته أو تسجيل طلباته.\n\n"
        )

    fallback_header = ""
    if queue_context and queue_context.get("is_fallback"):
        q_name = queue_context.get("queue_name", "طابور الخدمة")
        q_time = queue_context.get("wait_seconds", 60)
        fallback_header = (
            f"[توجيه فوري ذو أولوية عليا للمساعد]: العميل انتظر في '{q_name}' لمدة {q_time} ثانية دون رد من الموظفين لانشغالهم. "
            f"يجب أن تبدأ حديثك فوراً بالاعتذار بلطف واختصار عن مدة الانتظار، وطمأنته بأنك المساعد الذكي وجاهز لخدمته والرد على كل استفساراته أو تسجيل بياناته ليتواصل معه ممثلو {q_name} لاحقاً.\n\n"
        )

    # 1. Gender & pronouns
    if gender == "male":
        identity_gender = "أنت مساعد ذكي وصوتك وهوية حديثك رجل / شاب، وتتحدث دائماً بصيغة المذكر عن نفسك (زي: 'أنا جاهز ومستعد أساعدك'، 'أنا هفحصلك الأوردر حالا')."
    else:
        identity_gender = "أنتِ مساعدة ذكية وصوتك وهوية حديثك بنت / أنثى، وتتحدثين دائماً بصيغة المؤنث عن نفسك (زي: 'أنا جاهزة ومستعدة أساعدك'، 'أنا هفحصلك الأوردر حالا')."

    # 2. Dialect rules & explicit apology text
    if dialect == "saudi":
        dialect_rules = (
            "التحدث باللهجة السعودية والخليجية الدارجة فقط: كل كلامك بدون أي استثناء يكون باللهجة السعودية اللطيفة الطبيعية "
            "(زي: 'يا هلا والله ومسهلا'، 'أبشر طال عمرك'، 'سمّ آمرني'، 'على هالخشم'، 'ولا يهمك'). ممنوع منعاً باتاً الفصحى أو لهجات أخرى.\n"
            "صيغة الاعتذار الإلزامية: 'عذراً طال عمرك، أنا متخصص في مساعدة متجرك ومستنداتك بس، وما أقدر أفيدك في أسئلة خارج نطاقهم.'"
        )
    elif dialect == "levantine":
        dialect_rules = (
            "التحدث باللهجة الشامية اللطيفة المحببة فقط: كل كلامك يكون باللهجة الشامية الدارجة العفوية "
            "(زي: 'يا هلا فيك'، 'تكرم عينك'، 'على راسي'، 'كيف فيني ساعدك اليوم؟'). ممنوع منعاً باتاً الفصحى أو لهجات أخرى.\n"
            "صيغة الاعتذار الإلزامية: 'بعتذر منك كتير، أنا مخصص لمساعدتك بالمتجر ومستنداتك بس، وما بقدر جاوب على شي براتهن.'"
        )
    elif dialect == "fusha":
        dialect_rules = (
            "التحدث باللغة العربية الفصحى المعاصرة: تحدث بلغة عربية فصحى أنيقة وميسرة وسلسة وواضحة جداً.\n"
            "صيغة الاعتذار الإلزامية: 'أعتذر منك يا سيدي، أنا مخصص حصرياً لمساعدتك في متجرك ومستنداتك، ولا يمكنني الإجابة عن أسئلة خارج نطاقهما.'"
        )
    elif dialect == "english":
        dialect_rules = (
            "Speak exclusively in natural, professional English.\n"
            "Mandatory apology: 'I apologize, I am designated exclusively to assist with your store and uploaded documents, and cannot answer topics outside this scope.'"
        )
    else: # egyptian default
        dialect_rules = (
            "التحدث باللهجة المصرية العامية فقط: كل كلامك بدون أي استثناء لازم يكون باللهجة المصرية الدارجة الطبيعية "
            "(زي: 'أهلاً بيك يا فندم'، 'إزيك عامل إيه؟'، 'أنا تمام أهو معاك'، 'تحت أمرك'، 'عيني حاضر'). ممنوع منعاً باتاً الفصحى أو أي لهجة تانية.\n"
            "صيغة الاعتذار الإلزامية: 'معلش يا فندم، أنا متخصصة في مساعدة متجرك ومستنداتك بس، ومقدرش أجاوبك على أسئلة برة نطاقهم.'"
        )

    # 3. Role
    role_map = {
        "customer_support": "دورك هو ممثل خدمة عملاء محترف لمتجر المستخدم: تساعد في الرد على استفسارات المنتجات وتتبع الشحنات وحل المشكلات بلباقة وسرعة.",
        "sales_advisor": "دورك هو مستشار مبيعات خبير وشاطر: تشرح مزايا ومواصفات المنتجات بأسلوب مقنع وجذاب وتشجع العميل بلطف على إتمام الشراء.",
        "personal_assistant": "دورك هو مساعد شخصي ذكي وودود: تنظم الأمور وتجيب على الأسئلة بوضوح ومرونة وسرعة.",
        "technical_consultant": "دورك هو مستشار فني ورسمي: تقدم إجابات دقيقة واحترافية وتركز على التفاصيل والمواصفات بحرفية عالية."
    }
    role_text = role_map.get(role, role_map["customer_support"])

    # 4. Speaking style
    style_map = {
        "friendly": "أسلوب الإلقاء: ودود ولطيف ومرح، يبعث على الراحة والابتسامة في الحديث.",
        "formal": "أسلوب الإلقاء: رسمي ومهني وجاد، خالٍ من المزاح المفرط، ويركز على الوقار والاحترام.",
        "concise": "أسلوب الإلقاء: مباشر وسريع وموجز، يقدم الإجابة بكلمات قليلة ومفيدة دون مقدمات طويلة.",
        "enthusiastic": "أسلوب الإلقاء: حماسي ونشيط ومتفائل، يظهر طاقة إيجابية عالية في الرد."
    }
    style_text = style_map.get(style, style_map["friendly"])

    custom_text = f"\nتعليمات خاصة إضافية من المستخدم:\n{custom}\n" if custom else ""

    memory_text = f"\n8. {memory_card}\nتوجيه للمساعد: وظف الذاكرة السابقة بشكل طبيعي وعفوي في بداية الحديث للتذكير والتواصل الذكي دون قراءتها كقائمة رسمية.\n" if memory_card else ""

    prompt = f"""أنت مسجل في النظام كبروفايل: {name}.
{identity_gender}
{role_text}
{style_text}

قواعد أساسية صارمة ملزمة لا تقبل الاستثناء:
1. {dialect_rules}
2. التحيات والمجاملات الخفيفة: تبادل التحيات بلباقة واختصار حسب اللهجة المحددة.
3. أدوات المتجر والـ API: عندما يسألك المستخدم عن المنتجات، الأسعار، الطلبات، أو يطلب عمل أوردر، استدعِ فوراً الأداة المناسبة المتاحة لديك (مثل search_store_products أو get_order_status أو create_store_order).
4. أدوات المستندات (RAG): لما يسألك عن أي معلومة تخص مستنداته أو ملفاته المرفوعة، استدعِ أداة search_knowledge_base.
5. الإجابة من نتائج الأدوات: لخص نتائج الأداة للمستخدم بأسلوبك ولهجتك المحددة، بوضوح وأرقام دقيقة ومباشرة.
6. الاعتذار الإجباري الصارم: لو سألك عن أي حاجة عامة ملهاش أداة ولا موجودة في المستندات (زي أسئلة عامة خارج الشغل): اعتذر فوراً بصيغة الاعتذار المحددة أعلاه، وممنوع تفتي أو تخمن.{custom_text}
7. الإيجاز: كلامك يكون مفيداً وموجزاً وعلى قد السؤال بالظبط.{memory_text}"""
    return (outbound_header + fallback_header + prompt).strip()

async def run_agent_session(room_name: str, user_id: int = None, caller_phone: str = "web_dashboard", profile_data: dict = None, queue_context: dict = None, outbound_context: dict = None):
    channel_name = f"rooms:{room_name}"
    logger.info(f"Starting Gemini Live Voice Agent session for room: {room_name} (user_id={user_id}, caller_phone={caller_phone})")
    notify_centrifugo(channel_name, "agent_starting", "جاري تهيئة المساعدة الصوتية وتجهيز قاعدة المستندات والإجراءات...")

    # 1. Create LiveKit Access Token for Agent
    token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET) \
        .with_identity("pipecat-agent") \
        .with_name("Gemini Voice Assistant") \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        ))
    agent_jwt = token.to_jwt()

    # 2. Connect to LiveKit Room
    room = rtc.Room()
    try:
        await room.connect(LIVEKIT_INTERNAL_URL, agent_jwt)
        logger.info(f"Connected to LiveKit room '{room_name}'")
    except Exception as e:
        logger.error(f"Failed to connect to LiveKit: {e}")
        notify_centrifugo(channel_name, "agent_error", f"فشل الاتصال بخادم LiveKit: {e}")
        return

    # 3. Prepare Local Audio Track (Agent output: 24kHz mono)
    audio_source = rtc.AudioSource(sample_rate=24000, num_channels=1)
    audio_track = rtc.LocalAudioTrack.create_audio_track("agent-audio", audio_source)
    publish_options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
    await room.local_participant.publish_track(audio_track, publish_options)
    logger.info(f"Published agent audio track to room '{room_name}'")

    # 4. Fetch unified Bootstrap bundle ONCE (profile, mcp_servers, customer_memory, gemini_api_key)
    bootstrap = {}
    if user_id:
        bootstrap = await asyncio.to_thread(fetch_agent_bootstrap_sync, user_id, caller_phone)

    # 4.1 Resolve active Gemini API key: prioritize Django SystemSetting from bootstrap, fallback to .env
    active_api_key = (bootstrap.get("gemini_api_key") or "").strip() or GEMINI_API_KEY
    if not active_api_key or active_api_key.startswith("your_"):
        err = "GEMINI_API_KEY is not configured in Django Admin (SystemSetting) or .env"
        logger.error(err)
        notify_centrifugo(channel_name, "agent_error", err)
        await room.disconnect()
        return

    client = genai.Client(api_key=active_api_key)

    # 4.1 Parse MCP Tools dynamically from unified bootstrap
    mcp_servers_list = parse_mcp_servers_from_bootstrap(bootstrap) if user_id else []
    mcp_tools = {}
    for s in mcp_servers_list:
        s_url = s.get("server_url")
        s_token = s.get("auth_token", "")
        s_name = s.get("name", "FastMCP")
        for t in s.get("tools", []):
            t_name = t.get("name")
            if not t_name:
                continue
            mcp_tools[t_name] = {
                "server_url": s_url,
                "auth_token": s_token,
                "server_name": s_name,
                "description": t.get("description", ""),
                "parameters": t.get("parameters")
            }

    # 4.2 Parse Customer Memory dynamically from unified bootstrap
    memory_data = parse_customer_memory_from_bootstrap(bootstrap, caller_phone) if user_id else {}
    memory_card_text = memory_data.get("card_text", "")
    if memory_card_text:
        logger.info(f"Loaded customer memory for user {user_id} [phone={caller_phone}] ({len(memory_card_text)} chars)")

    # 4.3 Resolve Active Profile dynamically from unified bootstrap
    active_profile = None
    if profile_data and isinstance(profile_data, dict):
        active_profile = profile_data
    elif user_id:
        active_profile = parse_active_profile_from_bootstrap(bootstrap)

    if not active_profile:
        active_profile = parse_active_profile_from_bootstrap({})

    chosen_voice = active_profile.get("voice_name") or "Aoede"
    logger.info(f"Using Google voice '{chosen_voice}', dialect '{active_profile.get('dialect')}', gender '{active_profile.get('gender')}' for user {user_id}")

    speech_config = types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                voice_name=chosen_voice
            )
        )
    )

    rag_decl = {
        "name": "search_knowledge_base",
        "description": "البحث في المستندات والملفات المرفقة الخاصة بالمستخدم للإجابة عن أسئلته واستفساراته وحقائقه المطلوبة.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "نص السؤال أو الاستفسار أو الكلمات المفتاحية للبحث عنها في المستندات"
                }
            },
            "required": ["query"]
        }
    }

    func_decls = [rag_decl]

    # Add external MCP tools from all active servers
    for t_name, t_info in mcp_tools.items():
        decl = {
            "name": t_name,
            "description": t_info.get("description", "")
        }
        params = t_info.get("parameters")
        if params and isinstance(params, dict) and params.get("properties"):
            decl["parameters"] = params
        func_decls.append(decl)
    if mcp_tools:
        logger.info(f"Loaded {len(mcp_tools)} total MCP tools across {len(mcp_servers_list)} active servers: {list(mcp_tools.keys())}")

    tools = [{"function_declarations": func_decls}]

    system_instruction_text = build_dynamic_system_instruction(active_profile, memory_card_text, queue_context=queue_context, outbound_context=outbound_context)
    logger.info(f"Dynamic system instruction compiled (length={len(system_instruction_text)} chars)")

    live_config = types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO],
        speech_config=speech_config,
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        tools=tools,
        system_instruction=types.Content(
            parts=[types.Part(text=system_instruction_text)]
        )
    )

    in_audio_queue = asyncio.Queue()
    out_audio_queue = asyncio.Queue()
    stop_event = asyncio.Event()

    call_started_at = time.time()
    call_dialogue_turns = []

    state = {
        "is_agent_speaking": False,
        "turn_complete": True,
        "agent_last_audio_time": 0.0,
        "interrupted": False,
    }

    subscribed_sids = set()

    def subscribe_track(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        sid = publication.sid or (track.sid if track else None)
        if not sid or sid in subscribed_sids:
            return
        if track and track.kind == rtc.TrackKind.KIND_AUDIO:
            subscribed_sids.add(sid)
            logger.info(f"Subscribing to audio track {sid} from participant {participant.identity}")
            audio_stream = rtc.AudioStream(track, sample_rate=16000, num_channels=1)
            asyncio.create_task(stream_user_audio_to_queue(audio_stream, in_audio_queue, stop_event, participant.identity))

    @room.on("track_published")
    def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        publication.set_subscribed(True)
        if publication.track:
            subscribe_track(publication.track, publication, participant)

    @room.on("track_subscribed")
    def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        subscribe_track(track, publication, participant)

    for participant in room.remote_participants.values():
        for publication in participant.track_publications.values():
            publication.set_subscribed(True)
            if publication.track:
                subscribe_track(publication.track, publication, participant)

    @room.on("participant_disconnected")
    def on_participant_disconnected(participant: rtc.RemoteParticipant):
        logger.info(f"Participant disconnected: {participant.identity} from room {room_name}")
        remaining_humans = [p for p in room.remote_participants.values() if p.identity != "pipecat-agent"]
        if not remaining_humans:
            logger.info(f"No human participants left in room '{room_name}'. Terminating agent session.")
            stop_event.set()

    # 5. Connect to Gemini Live Session
    try:
        logger.info(f"Connecting to Gemini Live API (gemini-3.1-flash-live-preview) for room {room_name}...")
        async with client.aio.live.connect(model="gemini-3.1-flash-live-preview", config=live_config) as session:
            logger.info(f"Gemini Live session connected for room '{room_name}'!")
            notify_centrifugo(channel_name, "agent_ready", "المساعدة الصوتية وقاعدة المستندات جاهزة للاستماع إليك الآن!")

            # Outbound AI proactive greeting trigger
            greeting_triggered = False
            async def trigger_outbound_greeting():
                nonlocal greeting_triggered
                for _ in range(40):
                    if stop_event.is_set() or greeting_triggered:
                        return
                    humans = [p for p in room.remote_participants.values() if p.identity != "pipecat-agent"]
                    if humans:
                        await asyncio.sleep(1.0)
                        if not greeting_triggered and not stop_event.is_set():
                            greeting_triggered = True
                            logger.info(f"Human customer detected in outbound room {room_name}. Triggering initial greeting.")
                            try:
                                await session.send_client_content(
                                    turns=[
                                        types.Content(
                                            role="user",
                                            parts=[types.Part(text="العميل فتح الخط وقام بالرد للتو. ابدأ بالتحية فوراً وعرف باسمك واشرح سبب اتصالك وفقاً للهدف المحدد.")]
                                        )
                                    ],
                                    turn_complete=True
                                )
                            except Exception as ge:
                                logger.warning(f"Error triggering outbound greeting: {ge}")
                        return
                    await asyncio.sleep(0.5)

            if outbound_context and outbound_context.get("is_outbound_ai"):
                asyncio.create_task(trigger_outbound_greeting())

            # Worker 1: Stream user PCM audio frames to Gemini Live (continuous full-duplex streaming)
            async def send_audio_worker():
                buffer = bytearray()
                CHUNK_SIZE = 1280  # 40ms at 16kHz 16-bit mono

                while not stop_event.is_set():
                    try:
                        chunk = await asyncio.wait_for(in_audio_queue.get(), timeout=0.05)
                        buffer.extend(chunk)

                        while len(buffer) >= CHUNK_SIZE:
                            to_send = bytes(buffer[:CHUNK_SIZE])
                            del buffer[:CHUNK_SIZE]
                            await session.send_realtime_input(
                                audio=types.Blob(data=to_send, mime_type="audio/pcm;rate=16000")
                            )

                    except asyncio.TimeoutError:
                        if buffer:
                            to_send = bytes(buffer)
                            buffer.clear()
                            try:
                                await session.send_realtime_input(
                                    audio=types.Blob(data=to_send, mime_type="audio/pcm;rate=16000")
                                )
                            except Exception:
                                pass
                    except Exception as ex:
                        if not stop_event.is_set():
                            logger.error(f"Error sending audio to Gemini: {ex}")
                            await asyncio.sleep(0.05)

            # Worker 2: Receive audio, transcripts & handle tool calls from Gemini Live across multiple turns
            async def receive_audio_worker():
                while not stop_event.is_set():
                    try:
                        async for response in session.receive():
                            if stop_event.is_set():
                                break

                            # Handle Tool Calls (RAG Search & Custom Actions)
                            if response.tool_call:
                                logger.info(f"Gemini requested tool call in room {room_name}: {response.tool_call}")
                                function_responses = []
                                for fc in response.tool_call.function_calls:
                                    if fc.name == "search_knowledge_base":
                                        notify_centrifugo(channel_name, "agent_searching_rag", "جاري البحث الدلالي في مستنداتك...")
                                        query_text = fc.args.get("query", "") if fc.args else ""
                                        logger.info(f"Executing search_knowledge_base for user_id={user_id}, query='{query_text}'")
                                        search_result = await asyncio.to_thread(
                                            query_knowledge_base_sync, query_text, user_id, client
                                        )
                                        logger.info(f"Search result retrieved: {search_result[:100]}...")
                                        function_responses.append(types.FunctionResponse(
                                            id=fc.id,
                                            name=fc.name,
                                            response={"result": search_result}
                                        ))
                                    elif fc.name in mcp_tools:
                                        mcp_info = mcp_tools[fc.name]
                                        desc = mcp_info["description"][:30] if mcp_info["description"] else fc.name
                                        s_name = mcp_info.get("server_name", "FastMCP")
                                        notify_centrifugo(channel_name, "agent_action_executing", f"جاري استدعاء أداة {s_name}: {desc}...")
                                        act_args = dict(fc.args or {})
                                        logger.info(f"Executing MCP tool '{fc.name}' with args {act_args} on [{s_name}] {mcp_info['server_url']}")
                                        action_result = await execute_mcp_tool_call(
                                            mcp_info["server_url"],
                                            mcp_info["auth_token"],
                                            fc.name,
                                            act_args
                                        )
                                        logger.info(f"MCP tool '{fc.name}' response: {action_result[:150]}")
                                        function_responses.append(types.FunctionResponse(
                                            id=fc.id,
                                            name=fc.name,
                                            response={"result": action_result}
                                        ))
                                    else:
                                        logger.warning(f"Unknown tool requested by Gemini: {fc.name}")
                                        function_responses.append(types.FunctionResponse(
                                            id=fc.id,
                                            name=fc.name,
                                            response={"result": "عذراً، هذه الأداة غير معرفة."}
                                        ))
                                await session.send_tool_response(function_responses=function_responses)
                                continue

                            content = response.server_content
                            if not content:
                                continue

                            # Interruption handling (Barge-in triggered by Gemini Live)
                            if content.interrupted:
                                logger.info(f"Gemini playback interrupted by user in room {room_name}")
                                state["interrupted"] = True
                                state["is_agent_speaking"] = False
                                state["turn_complete"] = True
                                while not out_audio_queue.empty():
                                    try:
                                        out_audio_queue.get_nowait()
                                    except asyncio.QueueEmpty:
                                        break
                                notify_centrifugo(channel_name, "agent_interrupted", "المساعد استمع لمقاطعتك...")
                                continue

                            # Transcriptions
                            if content.input_transcription and content.input_transcription.text:
                                user_text = content.input_transcription.text.strip()
                                logger.info(f"[{room_name}] User: {user_text}")
                                call_dialogue_turns.append({"speaker": "user", "text": user_text})
                                notify_centrifugo(channel_name, "transcription_user", user_text, {"speaker": "user"})

                            if content.output_transcription and content.output_transcription.text:
                                bot_text = content.output_transcription.text.strip()
                                logger.info(f"[{room_name}] Gemini: {bot_text}")
                                call_dialogue_turns.append({"speaker": "agent", "text": bot_text})
                                notify_centrifugo(channel_name, "transcription_agent", bot_text, {"speaker": "agent"})

                            # Audio response from Gemini
                            if content.model_turn:
                                if not state["is_agent_speaking"]:
                                    state["is_agent_speaking"] = True
                                    notify_centrifugo(channel_name, "agent_speaking", "المساعدة تتحدث الآن...")
                                state["turn_complete"] = False
                                state["agent_last_audio_time"] = time.time()
                                for part in content.model_turn.parts:
                                    if part.inline_data and part.inline_data.data:
                                        await out_audio_queue.put(part.inline_data.data)

                            if content.turn_complete:
                                logger.info(f"Gemini model turn complete for room {room_name}")
                                state["turn_complete"] = True

                    except asyncio.CancelledError:
                        break
                    except Exception as ex:
                        if not stop_event.is_set():
                            logger.error(f"Error receiving from Gemini Live in room {room_name}: {ex}")
                            await asyncio.sleep(0.1)

            # Worker 3: Audio Pacer (paces output to LiveKit track in smooth 20ms frames)
            async def audio_pacer_worker():
                FRAME_SAMPLES = 480  # 20ms at 24kHz
                FRAME_BYTES = 960
                buffer = bytearray()

                while not stop_event.is_set():
                    try:
                        # If barge-in interruption occurred, dump local buffer immediately
                        if state.get("interrupted"):
                            buffer.clear()
                            state["interrupted"] = False

                        while len(buffer) < FRAME_BYTES:
                            chunk = await asyncio.wait_for(out_audio_queue.get(), timeout=0.02)
                            if state.get("interrupted"):
                                buffer.clear()
                                state["interrupted"] = False
                                break
                            buffer.extend(chunk)

                        if state.get("interrupted"):
                            buffer.clear()
                            state["interrupted"] = False
                            continue

                        if len(buffer) < FRAME_BYTES:
                            continue

                        frame_bytes = bytes(buffer[:FRAME_BYTES])
                        del buffer[:FRAME_BYTES]

                        frame = rtc.AudioFrame(
                            data=frame_bytes,
                            sample_rate=24000,
                            num_channels=1,
                            samples_per_channel=FRAME_SAMPLES
                        )
                        await audio_source.capture_frame(frame)
                        state["agent_last_audio_time"] = time.time()
                        await asyncio.sleep(0.019)
                    except asyncio.TimeoutError:
                        if state.get("interrupted"):
                            buffer.clear()
                            state["interrupted"] = False
                            continue

                        if buffer:
                            pad = FRAME_BYTES - len(buffer)
                            frame_bytes = bytes(buffer + b'\x00' * pad)
                            buffer.clear()
                            frame = rtc.AudioFrame(
                                data=frame_bytes,
                                sample_rate=24000,
                                num_channels=1,
                                samples_per_channel=FRAME_SAMPLES
                            )
                            await audio_source.capture_frame(frame)
                            state["agent_last_audio_time"] = time.time()
                        else:
                            # If queue and buffer are empty and turn is complete and 250ms have passed:
                            if state["is_agent_speaking"] and state.get("turn_complete", True) and (time.time() - state["agent_last_audio_time"] > 0.25):
                                state["is_agent_speaking"] = False
                                logger.info(f"Agent playback finished for room {room_name}. Mic listening active.")
                                notify_centrifugo(channel_name, "agent_listening", "المساعدة تستمع إليكِ الآن...")
                        continue
                    except Exception as ex:
                        if not stop_event.is_set():
                            logger.error(f"Error in audio pacer for room {room_name}: {ex}")
                        break

            sender_task = asyncio.create_task(send_audio_worker())
            receiver_task = asyncio.create_task(receive_audio_worker())
            pacer_task = asyncio.create_task(audio_pacer_worker())

            await stop_event.wait()
            sender_task.cancel()
            receiver_task.cancel()
            pacer_task.cancel()

    except Exception as e:
        logger.error(f"Gemini Live session error in room {room_name}: {e}")
        notify_centrifugo(channel_name, "agent_error", f"خطأ في جلسة Gemini Live: {e}")
    finally:
        logger.info(f"Cleaning up and disconnecting from room '{room_name}'...")
        await room.disconnect()
        notify_centrifugo(channel_name, "agent_disconnected", "تم إنهاء جلسة المساعدة الصوتية.")
        if user_id and call_dialogue_turns:
            logger.info(f"Triggering background memory distillation for user {user_id} [phone={caller_phone}] with {len(call_dialogue_turns)} turns.")
            asyncio.create_task(
                distill_and_update_memory(
                    user_id=user_id,
                    caller_phone=caller_phone,
                    room_name=room_name,
                    started_at=call_started_at,
                    messages=list(call_dialogue_turns),
                    current_profile=dict(memory_data.get("permanent_profile", {}) if memory_data else {}),
                    genai_client=client,
                    outbound_context=outbound_context
                )
            )

async def stream_user_audio_to_queue(audio_stream: rtc.AudioStream, queue: asyncio.Queue, stop_event: asyncio.Event, identity: str):
    """Read user audio frames from LiveKit stream and push to queue."""
    logger.info(f"Started reading audio frames from participant: {identity}")
    try:
        async for frame_event in audio_stream:
            if stop_event.is_set():
                break
            frame: rtc.AudioFrame = frame_event.frame
            queue.put_nowait(bytes(frame.data))
    except Exception as e:
        logger.debug(f"Audio stream for {identity} ended: {e}")

async def handle_webrtc_transfer_session(data: dict):
    """
    Handle WebRTC Call Transfer:
    1. Connect hold audio bot to room so the customer hears pleasant hold music.
    2. Ring target employee or queue.
    3. If target answers within 15s -> bot disconnects and target connects to customer.
    4. If target does NOT answer -> Ring back to original employee so customer is not lost.
    """
    room_name = data.get("room_name")
    from_user = str(data.get("from_user", ""))
    from_name = data.get("from_name", f"موظف {from_user}")
    from_employee_id = data.get("from_employee_id")
    target = str(data.get("target", ""))
    target_type = data.get("target_type", "employee")
    target_id = data.get("target_id")
    target_name = data.get("target_name", f"تحويلة {target}")

    logger.info(f"[TRANSFER SESSION] Starting transfer for room '{room_name}': '{from_name}' ({from_user}) -> '{target_name}' ({target})")

    # 1. Connect hold audio bot to room
    token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET) \
        .with_identity("transfer-bot") \
        .with_name("نغمة الانتظار - تحويل المكالمة") \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        ))
    bot_jwt = token.to_jwt()

    room = rtc.Room()
    stop_hold_event = asyncio.Event()
    hold_playback_task = None

    try:
        await room.connect(LIVEKIT_INTERNAL_URL, bot_jwt)
        logger.info(f"[TRANSFER SESSION] Transfer bot connected to room '{room_name}' to play hold music")

        audio_source = rtc.AudioSource(sample_rate=24000, num_channels=1)
        audio_track = rtc.LocalAudioTrack.create_audio_track("transfer-hold-audio", audio_source)
        publish_options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
        await room.local_participant.publish_track(audio_track, publish_options)

        from queue_manager import HOLD_CHIME_FRAMES, play_hold_audio_loop
        hold_playback_task = asyncio.create_task(play_hold_audio_loop(audio_source, stop_hold_event, HOLD_CHIME_FRAMES))
    except Exception as e:
        logger.error(f"[TRANSFER SESSION] Error connecting transfer hold bot: {e}")

    # 2. Ring target employee or queue
    channels_to_notify = []
    if target_type == "queue":
        channels_to_notify.append("queues:broadcast")
    else:
        if target_id:
            channels_to_notify.append(f"employee:{target_id}")
        if target:
            channels_to_notify.append(f"employee:{target}")

    for ch in channels_to_notify:
        notify_centrifugo(
            ch,
            "incoming_call",
            f"مكالمة محولة من {from_name} ({from_user})",
            {
                "room_name": room_name,
                "call_id": room_name,
                "caller_name": f"محولة من {from_name} ({from_user})",
                "caller_extension": from_user,
                "caller_department": "مكالمة محولة",
                "call_type": "transfer",
                "original_employee_id": from_employee_id,
                "original_extension": from_user
            }
        )

    # 3. Wait up to 15s for target to answer
    timeout_seconds = 15
    start_time = time.time()
    target_answered = False

    while (time.time() - start_time) < timeout_seconds:
        remote_parts = list(room.remote_participants.values())
        # Check if customer hung up
        customer_present = any(
            not p.identity.startswith("transfer-")
            and not p.identity.startswith("queue-")
            and p.identity != f"employee_{from_employee_id}_{from_user}"
            for p in remote_parts
        )
        if room.connection_state == rtc.ConnectionState.CONN_CONNECTED and not customer_present and len(remote_parts) == 0:
            logger.info(f"[TRANSFER SESSION] Customer left room '{room_name}'. Ending transfer.")
            break

        # Check if target employee answered
        for p in remote_parts:
            if (target_id and p.identity.startswith(f"employee_{target_id}_")) or (target and p.identity.endswith(f"_{target}")):
                logger.info(f"[TRANSFER SESSION] Target employee answered and joined room '{room_name}' (identity={p.identity})!")
                target_answered = True
                break

        if target_answered:
            break

        await asyncio.sleep(0.5)

    # 4. If target answered -> disconnect hold bot cleanly
    if target_answered:
        logger.info(f"[TRANSFER SESSION] Transfer completed successfully to '{target}' in room '{room_name}'.")
        stop_hold_event.set()
        if hold_playback_task:
            hold_playback_task.cancel()
        try:
            await room.disconnect()
        except Exception:
            pass
        return

    # 5. If target did NOT answer -> Ring Back to Original Employee!
    logger.info(f"[TRANSFER SESSION] Target '{target}' did not answer within {timeout_seconds}s. Initiating RING-BACK to '{from_name}' ({from_user}).")

    # Cancel ringing on target employee
    for ch in channels_to_notify:
        notify_centrifugo(
            ch,
            "call_ended",
            "انتهت مهلة تحويل المكالمة",
            {"room_name": room_name, "ended_by": "timeout"}
        )

    # Check if customer is still in room before ringing back
    remote_parts = list(room.remote_participants.values())
    customer_present = any(
        not p.identity.startswith("transfer-")
        and not p.identity.startswith("queue-")
        for p in remote_parts
    )
    if not customer_present:
        logger.info(f"[TRANSFER SESSION] Customer already left room '{room_name}'. Ending transfer.")
        stop_hold_event.set()
        if hold_playback_task:
            hold_playback_task.cancel()
        try:
            await room.disconnect()
        except Exception:
            pass
        return

    # Send Ring Back notification to original employee
    ring_back_channels = []
    if from_employee_id:
        ring_back_channels.append(f"employee:{from_employee_id}")
    if from_user:
        ring_back_channels.append(f"employee:{from_user}")

    for ch in ring_back_channels:
        notify_centrifugo(
            ch,
            "incoming_call",
            f"استرجاع: {target_name} لم يرد على التحويل",
            {
                "room_name": room_name,
                "call_id": room_name,
                "caller_name": f"استرجاع: لم يرد {target_name} ({target})",
                "caller_extension": str(target),
                "caller_department": "فشل التحويل",
                "call_type": "ring_back"
            }
        )

    # Wait for original employee to re-join (up to 20s)
    rb_start = time.time()
    while (time.time() - rb_start) < 20:
        remote_parts = list(room.remote_participants.values())
        if any(
            (from_employee_id and p.identity.startswith(f"employee_{from_employee_id}_"))
            or (from_user and p.identity.endswith(f"_{from_user}"))
            for p in remote_parts
        ):
            logger.info(f"[TRANSFER SESSION] Original employee '{from_name}' re-joined room '{room_name}' after ring back!")
            break
        await asyncio.sleep(0.5)

    # Cleanup bot
    stop_hold_event.set()
    if hold_playback_task:
        hold_playback_task.cancel()
    try:
        await room.disconnect()
    except Exception:
        pass
    logger.info(f"[TRANSFER SESSION] Transfer session finished for room '{room_name}'.")

async def transfer_events_worker(r: aioredis.Redis, shutdown_event: asyncio.Event):
    logger.info("Starting Transfer Events Background Worker in agent service...")
    while not shutdown_event.is_set():
        try:
            item = await r.brpop("transfer_events", timeout=1.0)
            if not item:
                continue
            _, raw_ev = item
            data = json.loads(raw_ev)
            from_user = data.get("from_user")
            target = data.get("target")
            real_target_user = data.get("real_target_user") or target
            call_id = data.get("call_id")
            room_name = data.get("room_name")

            # Resolve active room of from_user or call_id if not explicitly provided
            if not room_name and from_user:
                r_val = await r.get(f"agent_room:{from_user}")
                if r_val:
                    room_name = r_val.decode() if isinstance(r_val, bytes) else str(r_val)

            if not room_name and call_id:
                r_val = await r.get(f"call_room:{call_id}")
                if r_val:
                    room_name = r_val.decode() if isinstance(r_val, bytes) else str(r_val)

            if not room_name:
                logger.warning(f"[TRANSFER WORKER] Could not find active room for from_user '{from_user}'")
                continue

            data["room_name"] = room_name

            # Spawn transfer session with hold music and ring-back
            asyncio.create_task(handle_webrtc_transfer_session(data))

        except asyncio.CancelledError:
            break
        except Exception as ex:
            logger.error(f"Error in transfer worker: {ex}")
            await asyncio.sleep(1)

async def main():

    logger.info("Starting Standalone Voice Agent Service (Decoupled Modular Architecture via Django API)...")
    logger.info(f"LiveKit Internal URL: {LIVEKIT_INTERNAL_URL}")
    logger.info(f"Centrifugo API URL: {CENTRIFUGO_HTTP_API_URL}")
    logger.info(f"Redis URL: {REDIS_URL}")
    logger.info(f"Django API URL: {DJANGO_API_URL}")

    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    active_sessions: dict[str, asyncio.Task] = {}

    shutdown_event = asyncio.Event()

    def handle_signal():
        logger.info("Received termination signal. Shutting down agent daemon...")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            pass

    transfer_task = asyncio.create_task(transfer_events_worker(r, shutdown_event))

    while not shutdown_event.is_set():
        try:
            # Non-blocking pop with 1s timeout
            item = await r.brpop("agent_jobs", timeout=1.0)
            if item:
                _, raw_data = item
                raw_data = raw_data.strip()
                if not raw_data:
                    continue

                room_name = raw_data
                user_id = None
                profile_data = None
                is_queue = False
                queue_data = None
                is_outbound_ai = False
                call_goal = None
                destination_phone = None
                caller_phone = "web_dashboard"
                try:
                    parsed = json.loads(raw_data)
                    room_name = parsed.get("room_name", raw_data)
                    user_id = parsed.get("user_id")
                    caller_phone = parsed.get("caller_phone") or "web_dashboard"
                    profile_data = parsed.get("profile")
                    is_queue = parsed.get("is_queue", False)
                    queue_data = parsed.get("queue_data")
                    is_outbound_ai = parsed.get("is_outbound_ai", False)
                    call_goal = parsed.get("call_goal")
                    destination_phone = parsed.get("destination_phone")
                    if is_outbound_ai and destination_phone:
                        caller_phone = destination_phone
                except Exception:
                    pass

                room_name = room_name.strip()
                if not room_name:
                    continue

                # Defensive check: Do not dispatch AI agent for direct human-to-human calls
                if room_name.startswith("call_ext_") or room_name.startswith("call_tr_") or room_name.startswith("call_rst_") or room_name.startswith("pstn_out_"):
                    logger.info(f"Skipping direct human call room '{room_name}' in agent dispatcher.")
                    continue

                # Check if session is already running for this room
                if room_name in active_sessions and not active_sessions[room_name].done():
                    logger.info(f"Session for room '{room_name}' is already running. Skipping duplicate dispatch.")
                    continue

                logger.info(f"Received new dispatch for room: {room_name} (user_id={user_id}, caller_phone={caller_phone}, is_queue={is_queue}, is_outbound_ai={is_outbound_ai})")

                def make_cleanup(rm):
                    def _cleanup(fut):
                        logger.info(f"Session task finished for room: {rm}")
                        active_sessions.pop(rm, None)
                    return _cleanup

                outbound_ctx = None
                if is_outbound_ai:
                    outbound_ctx = {
                        "is_outbound_ai": True,
                        "call_goal": call_goal,
                        "destination_phone": destination_phone
                    }

                if is_queue:
                    task = asyncio.create_task(run_queue_session(
                        room_name=room_name,
                        user_id=user_id,
                        caller_phone=caller_phone,
                        queue_data=queue_data,
                        profile_data=profile_data,
                        livekit_url=LIVEKIT_INTERNAL_URL,
                        api_key=LIVEKIT_API_KEY,
                        api_secret=LIVEKIT_API_SECRET,
                        redis_client=r,
                        notify_func=notify_centrifugo,
                        fallback_agent_func=run_agent_session
                    ))
                else:
                    task = asyncio.create_task(run_agent_session(
                        room_name,
                        user_id=user_id,
                        caller_phone=caller_phone,
                        profile_data=profile_data,
                        outbound_context=outbound_ctx
                    ))

                task.add_done_callback(make_cleanup(room_name))
                active_sessions[room_name] = task

            # Periodically prune any finished tasks
            for rm, t in list(active_sessions.items()):
                if t.done():
                    active_sessions.pop(rm, None)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in agent dispatcher loop: {e}")
            await asyncio.sleep(1)

    logger.info("Stopping all active agent sessions...")
    for rm, t in active_sessions.items():
        t.cancel()
    if active_sessions:
        await asyncio.gather(*active_sessions.values(), return_exceptions=True)
    await r.aclose()
    logger.info("Agent service stopped gracefully.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
