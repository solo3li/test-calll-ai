import re
import json
import asyncio
import logging
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone

from .models import AgentProfile, UserMCPServer, SystemSetting

logger = logging.getLogger(__name__)

GOOGLE_VOICES = [
    {"name": "Aoede", "gender": "female", "style": "Brisk (نشيطة وسريعة)", "tag": "افتراضي"},
    {"name": "Kore", "gender": "female", "style": "Firm (واثقة وحازمة)", "tag": "رسمي"},
    {"name": "Leda", "gender": "female", "style": "Youthful (شابة وودودة)", "tag": "ودود"},
    {"name": "Fenrir", "gender": "male", "style": "Deep (عميق وهادئ)", "tag": "رسمي"},
    {"name": "Puck", "gender": "male", "style": "Cheerful (مرح وحيوي)", "tag": "حيوي"},
    {"name": "Charon", "gender": "male", "style": "Calm (هادئ ووقور)", "tag": "هادئ"},
    {"name": "Callisto", "gender": "female", "style": "Warm (دافئة ومريحة)", "tag": "دافئ"},
    {"name": "Sulafat", "gender": "female", "style": "Gentle (رقيقة وواضحة)", "tag": "رقيق"},
    {"name": "Zubenelgenubi", "gender": "male", "style": "Casual (تلقائي وعادي)", "tag": "تلقائي"},
    {"name": "Sadachbia", "gender": "male", "style": "Lively (حيوي ومتفاعل)", "tag": "حيوي"},
    {"name": "Zephyr", "gender": "male", "style": "Bright (منعش ومشرق)", "tag": "منعش"},
]

def verify_internal_api_key(request) -> bool:
    """Validate internal request from AI agent service."""
    expected_key = getattr(settings, 'INTERNAL_API_KEY', 'default-internal-secret-key-12345')
    auth_header = request.headers.get('X-Internal-API-Key') or request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ', 1)[1].strip()
    else:
        token = auth_header.strip()
    return token == expected_key or request.user.is_authenticated

# ==================== Agent Profiles Management ====================

@login_required(login_url='/login/')
def list_profiles(request):
    """List all agent profiles for user, active profile, and options metadata."""
    profiles = list(AgentProfile.objects.filter(user=request.user))
    if not profiles:
        default_prof = AgentProfile.objects.create(
            user=request.user,
            name="نورهان - خدمة عملاء مصرية",
            voice_name="Aoede",
            gender="female",
            dialect="egyptian",
            persona_role="customer_support",
            speaking_style="friendly",
            is_active=True
        )
        profiles = [default_prof]

    active_p = next((p for p in profiles if p.is_active), profiles[0])

    return JsonResponse({
        "status": "success",
        "profiles": [p.to_dict() for p in profiles],
        "active_profile": active_p.to_dict(),
        "google_voices": GOOGLE_VOICES,
        "dialects": [{"id": d[0], "label": d[1]} for d in AgentProfile.DIALECT_CHOICES],
        "roles": [{"id": r[0], "label": r[1]} for r in AgentProfile.ROLE_CHOICES],
        "styles": [{"id": s[0], "label": s[1]} for s in AgentProfile.STYLE_CHOICES],
        "genders": [{"id": g[0], "label": g[1]} for g in AgentProfile.GENDER_CHOICES],
    })

@login_required(login_url='/login/')
def create_profile(request):
    """Create a new agent persona profile for user."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        name = data.get('name', '').strip() or 'بروفايل مخصص'
        voice_name = data.get('voice_name', 'Aoede').strip()
        gender = data.get('gender', 'female')
        dialect = data.get('dialect', 'egyptian')
        persona_role = data.get('persona_role', 'customer_support')
        speaking_style = data.get('speaking_style', 'friendly')
        custom_instructions = data.get('custom_instructions', '').strip()
        is_active = bool(data.get('is_active', True))

        profile = AgentProfile.objects.create(
            user=request.user,
            name=name,
            voice_name=voice_name,
            gender=gender,
            dialect=dialect,
            persona_role=persona_role,
            speaking_style=speaking_style,
            custom_instructions=custom_instructions,
            is_active=is_active
        )
        return JsonResponse({
            "status": "success",
            "message": f"تم حفظ البروفايل '{profile.name}' بنجاح.",
            "profile": profile.to_dict()
        }, status=201)
    except Exception as e:
        logger.error(f"Error creating agent profile: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=400)

@login_required(login_url='/login/')
def update_profile(request, profile_id):
    """Update an existing agent persona profile."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    profile = get_object_or_404(AgentProfile, id=profile_id, user=request.user)
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        if 'name' in data and data['name'].strip():
            profile.name = data['name'].strip()
        if 'voice_name' in data and data['voice_name'].strip():
            profile.voice_name = data['voice_name'].strip()
        if 'gender' in data:
            profile.gender = data['gender']
        if 'dialect' in data:
            profile.dialect = data['dialect']
        if 'persona_role' in data:
            profile.persona_role = data['persona_role']
        if 'speaking_style' in data:
            profile.speaking_style = data['speaking_style']
        if 'custom_instructions' in data:
            profile.custom_instructions = data['custom_instructions'].strip()
        if 'is_active' in data:
            profile.is_active = bool(data['is_active'])

        profile.save()
        return JsonResponse({
            "status": "success",
            "message": f"تم تحديث البروفايل '{profile.name}' بنجاح.",
            "profile": profile.to_dict()
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)

@login_required(login_url='/login/')
def activate_profile(request, profile_id):
    """Set a specific profile as the active one for future calls."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    profile = get_object_or_404(AgentProfile, id=profile_id, user=request.user)
    profile.is_active = True
    profile.save()
    return JsonResponse({
        "status": "success",
        "message": f"تم تفعيل البروفايل '{profile.name}' للمكالمات القادمة.",
        "profile": profile.to_dict()
    })

@login_required(login_url='/login/')
def delete_profile(request, profile_id):
    """Delete an agent persona profile."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    profile = get_object_or_404(AgentProfile, id=profile_id, user=request.user)
    was_active = profile.is_active
    name = profile.name
    profile.delete()

    if was_active:
        fallback = AgentProfile.objects.filter(user=request.user).first()
        if fallback:
            fallback.is_active = True
            fallback.save()

    return JsonResponse({"status": "success", "message": f"تم حذف البروفايل '{name}' بنجاح."})

# ==================== User Custom Actions ====================

# ==================== User External MCP Server ====================

async def _fetch_mcp_tools_async(url: str, auth_token: str = ""):
    """Connect to MCP SSE server, perform handshake, and list tools."""
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    async with sse_client(url, headers=headers) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tool_list = await session.list_tools()
            tools = []
            for t in tool_list.tools:
                schema = getattr(t, 'input_schema', None) or getattr(t, 'inputSchema', None) or {}
                tools.append({
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": schema
                })
            return tools

def fetch_mcp_tools_sync(url: str, auth_token: str = "", timeout: float = 6.0):
    """Fetch tool list from an external MCP SSE server synchronously with timeout."""
    async def _run():
        return await asyncio.wait_for(_fetch_mcp_tools_async(url, auth_token), timeout=timeout)
    return asyncio.run(_run())

@login_required(login_url='/login/')
def get_mcp_server(request):
    """Get the current user's MCP servers list and aggregated statistics."""
    servers = list(UserMCPServer.objects.filter(user=request.user).order_by('-created_at'))
    if not servers:
        # Create default store MCP server if none exists
        default_server = UserMCPServer.objects.create(
            user=request.user,
            name="خادم المتجر الرئيسي (FastMCP)",
            server_url="http://mock-store:8002/sse",
            is_active=True
        )
        try:
            tools = fetch_mcp_tools_sync(default_server.server_url, default_server.auth_token)
            default_server.cached_tools = tools
            default_server.last_synced_at = timezone.now()
            default_server.save()
        except Exception as e:
            logger.warning(f"Initial MCP sync failed: {e}")
        servers = [default_server]

    server_list = [s.to_dict() for s in servers]
    active_count = sum(1 for s in servers if s.is_active)
    total_tools = sum(len(s.cached_tools or []) for s in servers if s.is_active)

    return JsonResponse({
        "status": "success",
        "servers": server_list,
        "server": server_list[0] if server_list else None,
        "total_servers": len(servers),
        "active_servers": active_count,
        "total_tools": total_tools
    })

@login_required(login_url='/login/')
def save_mcp_server(request):
    """Create or update an MCP server configuration and trigger an automatic handshake sync."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        server_id = data.get('id') or data.get('server_id')
        name = data.get('name', '').strip() or 'خادم FastMCP'
        server_url = data.get('server_url', '').strip()
        auth_token = data.get('auth_token', '').strip()
        is_active = bool(data.get('is_active', True))

        if not server_url:
            return JsonResponse({"status": "error", "message": "رابط الخادم مطلوب."}, status=400)

        if server_id:
            server = get_object_or_404(UserMCPServer, id=server_id, user=request.user)
            server.name = name
            server.server_url = server_url
            server.auth_token = auth_token
            server.is_active = is_active
        else:
            server = UserMCPServer.objects.create(
                user=request.user,
                name=name,
                server_url=server_url,
                auth_token=auth_token,
                is_active=is_active
            )

        try:
            tools = fetch_mcp_tools_sync(server_url, auth_token, timeout=5.0)
            server.cached_tools = tools
            server.last_synced_at = timezone.now()
            sync_msg = f"تم الاتصال واكتشاف {len(tools)} أداة بنجاح."
        except Exception as sync_err:
            sync_msg = f"تم حفظ الرابط، ولكن تعذر الاتصال بالخادم: {sync_err}"

        server.save()
        return JsonResponse({
            "status": "success",
            "message": f"تم حفظ إعدادات MCP بنجاح. {sync_msg}",
            "server": server.to_dict()
        })
    except Exception as e:
        logger.error(f"Error saving MCP server: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=400)

@login_required(login_url='/login/')
def sync_mcp_server(request):
    """Trigger an on-demand re-sync of MCP tools from remote server(s)."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body) if (request.body and request.content_type == 'application/json') else request.POST
    except Exception:
        data = {}

    server_id = data.get('id') or data.get('server_id') or request.GET.get('id')
    if server_id:
        server = get_object_or_404(UserMCPServer, id=server_id, user=request.user)
        try:
            tools = fetch_mcp_tools_sync(server.server_url, server.auth_token, timeout=8.0)
            server.cached_tools = tools
            server.last_synced_at = timezone.now()
            server.save()
            return JsonResponse({
                "status": "success",
                "message": f"تم تحديث أدوات '{server.name}' بنجاح. تم اكتشاف {len(tools)} أداة.",
                "server": server.to_dict()
            })
        except Exception as e:
            logger.error(f"Failed to sync MCP tools from {server.server_url}: {e}")
            return JsonResponse({
                "status": "error",
                "message": f"فشل الاتصال بخادم '{server.name}': {str(e)}"
            }, status=502)
    else:
        # Sync all active servers for user
        servers = UserMCPServer.objects.filter(user=request.user)
        if not servers.exists():
            return JsonResponse({"status": "error", "message": "لا يوجد خادم MCP مسجل."}, status=404)
        total_discovered = 0
        errors = []
        for s in servers:
            try:
                tools = fetch_mcp_tools_sync(s.server_url, s.auth_token, timeout=6.0)
                s.cached_tools = tools
                s.last_synced_at = timezone.now()
                s.save()
                total_discovered += len(tools)
            except Exception as e:
                errors.append(f"{s.name}: {e}")
        
        msg = f"تم تحديث الأدوات بنجاح. إجمالي الأدوات المكتشفة: {total_discovered} أداة."
        if errors:
            msg += f" (تعذر الاتصال بـ: {', '.join(errors)})"
        return JsonResponse({
            "status": "success",
            "message": msg,
            "servers": [s.to_dict() for s in UserMCPServer.objects.filter(user=request.user)]
        })

@login_required(login_url='/login/')
def toggle_mcp_server(request):
    """Toggle whether a specific MCP server is enabled for voice calls."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body) if (request.body and request.content_type == 'application/json') else request.POST
    except Exception:
        data = {}

    server_id = data.get('id') or data.get('server_id') or request.GET.get('id')
    if server_id:
        server = get_object_or_404(UserMCPServer, id=server_id, user=request.user)
    else:
        server = UserMCPServer.objects.filter(user=request.user).first()

    if not server:
        return JsonResponse({"status": "error", "message": "لا يوجد خادم مسجل."}, status=404)

    server.is_active = not server.is_active
    server.save()
    status_str = "تفعيل" if server.is_active else "تعطيل"
    return JsonResponse({
        "status": "success",
        "message": f"تم {status_str} خادم '{server.name}' بنجاح.",
        "is_active": server.is_active,
        "server": server.to_dict()
    })

@login_required(login_url='/login/')
def delete_mcp_server(request):
    """Delete a specific MCP server configuration."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body) if (request.body and request.content_type == 'application/json') else request.POST
    except Exception:
        data = {}

    server_id = data.get('id') or data.get('server_id') or request.GET.get('id')
    if server_id:
        server = get_object_or_404(UserMCPServer, id=server_id, user=request.user)
        server_name = server.name
        server.delete()
        return JsonResponse({"status": "success", "message": f"تم حذف خادم '{server_name}' بنجاح."})
    else:
        server = UserMCPServer.objects.filter(user=request.user).first()
        if server:
            server_name = server.name
            server.delete()
            return JsonResponse({"status": "success", "message": f"تم حذف خادم '{server_name}' بنجاح."})
        return JsonResponse({"status": "error", "message": "لا يوجد خادم لحذفه."}, status=404)

# ==================== Internal AI Agent Bootstrap API ====================

@csrf_exempt
def api_internal_agent_bootstrap(request):
    """
    Consolidated internal bootstrap API for AI Voice Agent session.
    Fetches active profile, custom HTTP actions, MCP servers, and customer memory in a single fast call.
    Accepts: { user_id: int }
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    if not verify_internal_api_key(request):
        return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
        user_id = data.get('user_id')
        user = User.objects.filter(id=user_id).first() if user_id else None
        if not user:
            user = User.objects.first()
        if not user:
            return JsonResponse({"status": "error", "message": "No valid user found"}, status=404)

        # 1. Agent Profile
        profile = AgentProfile.objects.filter(user=user, is_active=True).first()
        profile_data = profile.to_dict() if profile else {
            "name": "البروفايل الافتراضي",
            "voice_name": "Aoede",
            "gender": "female",
            "dialect": "egyptian",
            "persona_role": "customer_support",
            "speaking_style": "friendly",
            "custom_instructions": "",
            "is_active": True
        }

        # 2. External FastMCP Servers
        mcp_servers = UserMCPServer.objects.filter(user=user, is_active=True)
        mcp_list = [s.to_dict() for s in mcp_servers]

        # 2.1 Inherit Partner Shared MCP Server if user is a sub-client
        partner_info = None
        try:
            from partners.models import PartnerClientRelationship
            partner_rel = PartnerClientRelationship.objects.select_related('partner').filter(
                client=user,
                partner__status='approved'
            ).first()
            if partner_rel and partner_rel.partner:
                partner = partner_rel.partner
                partner_info = {
                    "partner_id": partner.id,
                    "partner_code": partner.partner_code,
                    "custom_rate": float(partner.custom_rate_per_minute),
                    "client_id": user.id,
                    "external_reference": partner_rel.external_reference,
                }
                if partner.shared_mcp_server and partner.shared_mcp_server.is_active:
                    shared_dict = partner.shared_mcp_server.to_dict()
                    shared_dict['is_partner_inherited'] = True
                    shared_dict['client_id'] = user.id
                    if not any(s['id'] == shared_dict['id'] for s in mcp_list):
                        mcp_list.append(shared_dict)
        except Exception:
            pass

        # 3. Customer Memory (Lazy import to avoid circular dependency)
        from crm.models import CustomerMemory
        caller_phone = str(data.get('caller_phone') or 'web_dashboard').strip()
        memory = CustomerMemory.objects.filter(user=user, phone_number=caller_phone).first()
        if not memory and caller_phone != 'web_dashboard' and len(caller_phone) >= 7:
            memory = CustomerMemory.objects.filter(user=user, phone_number__endswith=caller_phone[-8:]).first()
        memory_data = memory.to_dict() if memory else {
            "phone_number": caller_phone,
            "customer_name": "",
            "permanent_profile": {},
            "last_interaction_summary": "",
            "total_calls_count": 0
        }

        # 4. Active Call Queues for this tenant/user
        from call_center.models import CallQueue
        queues = CallQueue.objects.filter(user=user, is_active=True).order_by('code')
        queues_list = [
            {
                "id": q.id,
                "name": q.name,
                "code": q.code,
                "description": q.description or "",
                "strategy": q.strategy,
                "ring_timeout_seconds": q.ring_timeout_seconds,
                "total_timeout_seconds": q.total_timeout_seconds,
                "members_count": q.memberships.filter(is_active=True).count()
            }
            for q in queues
        ]

        return JsonResponse({
            "status": "success",
            "user_id": user.id,
            "gemini_api_key": SystemSetting.get_gemini_api_key(),
            "profile": profile_data,
            "mcp_servers": mcp_list,
            "customer_memory": memory_data,
            "partner_info": partner_info,
            "call_queues": queues_list
        })

    except Exception as e:
        logger.error(f"Error in api_internal_agent_bootstrap: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
