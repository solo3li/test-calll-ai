"""Dynamic system instruction builder for Voice AI Agent."""
from typing import Dict, Any, List, Optional
from .dialects import DIALECT_RULES_MAP
from .verbosity import VERBOSITY_INSTRUCTIONS


def build_dynamic_system_instruction(
    profile: Dict[str, Any],
    memory_card: str = "",
    queue_context: Optional[Dict[str, Any]] = None,
    outbound_context: Optional[Dict[str, Any]] = None,
    call_queues: Optional[List[Dict[str, Any]]] = None
) -> str:
    """Construct dynamic prompt incorporating dialect, gender, role, style, memory, queue fallback context, outbound context, and strict guardrails."""
    gender = profile.get("gender", "female")
    dialect = profile.get("dialect", "egyptian")
    role = profile.get("persona_role", "customer_support")
    style = profile.get("speaking_style", "friendly")
    verbosity = profile.get("verbosity", "balanced")
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

    # 2. Dialect rules
    dialect_rules = DIALECT_RULES_MAP.get(dialect, DIALECT_RULES_MAP["egyptian"])

    # 3. Role & Persona
    role_map = {
        "customer_support": "دورك هو ممثل خدمة عملاء محترف لمتجر المستخدم: تساعد في الرد على استفسارات المنتجات وتتبع الشحنات وحل المشكلات بلباقة وسرعة.",
        "sales_advisor": "دورك هو مستشار مبيعات خبير وشاطر: تشرح مزايا ومواصفات المنتجات بأسلوب مقنع وجذاب وتشجع العميل بلطف على إتمام الشراء.",
        "personal_assistant": "دورك هو مساعد شخصي ذكي وودود: تنظم الأمور وتجيب على الأسئلة بوضوح ومرونة وسرعة.",
        "technical_consultant": "دورك هو مستشار فني ورسمي: تقدم إجابات دقيقة واحترافية وتركز على التفاصيل والمواصفات بحرفية عالية."
    }
    if role in role_map:
        role_text = role_map[role]
    elif role and str(role).strip():
        role_text = f"الدور والشخصية المحددة لك بدقة: {str(role).strip()}"
    else:
        role_text = role_map["customer_support"]

    # 4. Speaking style & Tone
    style_map = {
        "friendly": "أسلوب الإلقاء: ودود ولطيف ومرح، يبعث على الراحة والابتسامة في الحديث.",
        "formal": "أسلوب الإلقاء: رسمي ومهني وجاد، خالٍ من المزاح المفرط، ويركز على الوقار والاحترام.",
        "concise": "أسلوب الإلقاء: مباشر وسريع وموجز، يقدم الإجابة بكلمات قليلة ومفيدة دون مقدمات طويلة.",
        "enthusiastic": "أسلوب الإلقاء: حماسي ونشيط ومتفائل، يظهر طاقة إيجابية عالية في الرد."
    }
    if style in style_map:
        style_text = style_map[style]
    elif style and str(style).strip():
        style_text = f"أسلوب الإلقاء والنبرة المطلوب منك الالتزام التام بها: {str(style).strip()}"
    else:
        style_text = style_map["friendly"]

    custom_text = f"\nتعليمات خاصة إضافية من المستخدم:\n{custom}\n" if custom else ""

    # 5. Verbosity
    verbosity_instruction = VERBOSITY_INSTRUCTIONS.get(verbosity, VERBOSITY_INSTRUCTIONS["balanced"])

    # 6. Memory context
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
6. الاعتذار الإجباري الصارم: لو سألك عن أي حاجة عامة ملهاش أداة ولا موجودة في المستندات ولا تخص طوابير وأقسام الدعم المتاحة (زي أسئلة عامة خارج الشغل): اعتذر فوراً بصيغة الاعتذار المحددة أعلاه، وممنوع تفتي أو تخمن.{custom_text}
{verbosity_instruction}{memory_text}"""

    queues_instruction = ""
    if call_queues:
        q_lines = []
        for q in call_queues:
            desc = f" - اختصاصاته وشروط التحويل إليه: {q['description']}" if q.get("description") else ""
            q_lines.append(f"- قسم {q['name']} [كود التحويل: {q['code']}]{desc}")
        q_list_str = "\n".join(q_lines)
        queues_instruction = (
            f"\n\nطوابير وأقسام خدمة العملاء المتاحة حصراً في شركتك للتحويل إليها:\n{q_list_str}\n"
            f"قواعد التحويل الإلزامية الصارمة:\n"
            f"1. إذا طلب العميل التحدث مع موظف بشري أو خدمة العملاء أو قسم معين:\n"
            f"   - طابق مشكلة العميل واحتياجه بدقة مع اختصاصات ووصف كل طابور أعلاه، واستدعِ فوراً أداة 'transfer_to_queue' بكود الطابور الأنسب.\n"
            f"   - إذا طلب العميل التحويل بشكل عام دون تحديد قسم أو مشكلة، اسأله بلباقة واختصار (مثال: 'تحت أمرك يا فندم، تحب أحولك لأي قسم بالتحديد، أو إيه طبيعة المشكلة عشان أوجهك للقسم المختص؟'). وإذا أصر العميل على التحويل أو كان هناك قسم دعم عام، حوله فوراً إليه.\n"
            f"2. عند التحويل، استدعِ فوراً أداة 'transfer_to_queue'. انطق جملة واحدة فقط طبيعية وموجزة تؤكد التحويل للعميل (مثال: 'حاضر يا فندم، هحول حضرتك حالا لقسم [الاسم]، ثواني معايا...')، وممنوع نهائياً قراءة أي معطيات تقنية أو تكرار الكلام.\n"
            f"3. ممنوع نهائياً اختراع أو ذكر أي أقسام أو أرقام طوابير غير الموجودة في القائمة أعلاه، وممنوع رفض طلب التحويل إذا كان العميل يطلب التواصل مع موظف أو قسم متاح في القائمة أعلاه."
        )

    return (outbound_header + fallback_header + prompt + queues_instruction).strip()
