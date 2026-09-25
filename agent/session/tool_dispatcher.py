"""Tool declaration and execution dispatcher for Gemini Live sessions."""
from typing import Dict, Any, List, Optional, Tuple
from google.genai import types
from agent.config import logger
from agent.clients.centrifugo_client import notify_centrifugo_async
from agent.clients.django_client import query_knowledge_base_async
from agent.clients.mcp_client import execute_mcp_tool_call


def build_gemini_tools(mcp_tools: Dict[str, Any], call_queues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build the function declarations list for Gemini Live connect config."""
    rag_decl = {
        "name": "search_knowledge_base",
        "description": (
            "البحث الدلالي الذكي في قاعدة المعرفة والمستندات والبيانات المعتمدة للمؤسسة أو النشاط للإجابة على استفسارات المتصل بدقة وموثوقية."
        ),
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
        logger.info(f"Loaded {len(mcp_tools)} total MCP tools: {list(mcp_tools.keys())}")

    # Add tenant call_queues transfer tool if tenant has active queues
    if call_queues:
        q_codes = [str(q["code"]) for q in call_queues]
        q_desc_parts = []
        for q in call_queues:
            detail = f" [الاختصاص: {q['description']}]" if q.get("description") else ""
            q_desc_parts.append(f"{q['name']} ({q['code']}){detail}")
        q_descriptions = " | ".join(q_desc_parts)
        transfer_decl = {
            "name": "transfer_to_queue",
            "description": f"تحويل المكالمة الجارية إلى أحد طوابير الموظفين البشريين التابعة للمؤسسة. الأقسام واختصاصاتها: [{q_descriptions}]. تحذير: ممنوع استدعاء هذه الأداة فوراً عند أول طلب تحويل. يجب أولاً استيضاح سبب التحويل وفهم المشكلة من العميل لمحاولة مساعدته، ولا يتم استدعاء الأداة إلا بعد إصراره أو بعد معرفة المشكلة، ويجب كتابة ملخص ما قاله العميل كاملاً في حقل reason.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "queue_code": {
                        "type": "STRING",
                        "description": f"كود الطابور المراد التحويل إليه حصراً من بين: {q_codes}"
                    },
                    "reason": {
                        "type": "STRING",
                        "description": "ملخص وافٍ لسبب التحويل وما قاله العميل والمشكلة لتمريره لممثلي القسم"
                    }
                },
                "required": ["queue_code"]
            }
        }
        func_decls.append(transfer_decl)
        logger.info(f"Loaded transfer_to_queue tool with {len(call_queues)} tenant queues: {q_codes}")

    return [{"function_declarations": func_decls}]


async def handle_gemini_tool_call(
    fc,
    user_id: Optional[int],
    room_name: str,
    channel_name: str,
    mcp_tools: Dict[str, Any],
    call_queues: List[Dict[str, Any]],
    genai_client = None
) -> Tuple[types.FunctionResponse, Optional[Dict[str, Any]]]:
    """Execute a single function call from Gemini Live and return (response, pending_transfer)."""
    pending_transfer = None

    if fc.name == "search_knowledge_base":
        await notify_centrifugo_async(channel_name, "agent_searching_rag", "جاري البحث الدلالي في مستنداتك...")
        query_text = fc.args.get("query", "") if fc.args else ""
        logger.info(f"Executing search_knowledge_base for user_id={user_id}, query='{query_text}'")
        search_result = await query_knowledge_base_async(query_text, user_id, genai_client)
        logger.info(f"Search result retrieved: {search_result[:100]}...")
        return types.FunctionResponse(
            id=fc.id,
            name=fc.name,
            response={"result": search_result}
        ), None

    elif fc.name in mcp_tools:
        mcp_info = mcp_tools[fc.name]
        desc = mcp_info["description"][:30] if mcp_info.get("description") else fc.name
        s_name = mcp_info.get("server_name", "FastMCP")
        await notify_centrifugo_async(channel_name, "agent_action_executing", f"جاري استدعاء أداة {s_name}: {desc}...")
        act_args = dict(fc.args or {})
        logger.info(f"Executing MCP tool '{fc.name}' with args {act_args} on [{s_name}] {mcp_info.get('server_url')}")
        action_result = await execute_mcp_tool_call(
            mcp_info["server_url"],
            mcp_info["auth_token"],
            fc.name,
            act_args
        )
        logger.info(f"MCP tool '{fc.name}' response: {action_result[:150]}")
        return types.FunctionResponse(
            id=fc.id,
            name=fc.name,
            response={"result": action_result}
        ), None

    elif fc.name == "transfer_to_queue":
        q_code = str(fc.args.get("queue_code", "")).strip() if fc.args else ""
        reason = str(fc.args.get("reason", "")).strip() if fc.args else ""
        matched_q = next((q for q in call_queues if str(q.get("code")) == q_code), None)
        q_name = matched_q.get("name", "القسم المطلوب") if matched_q else f"طابور {q_code}"
        logger.info(f"AI requested transfer_to_queue in room {room_name}: queue_code={q_code}, queue_name={q_name}, reason={reason}")

        await notify_centrifugo_async(channel_name, "agent_transferring", f"جاري تحويلك إلى {q_name}...")
        pending_transfer = {
            "queue_code": q_code,
            "queue_name": q_name,
            "reason": reason
        }
        return types.FunctionResponse(
            id=fc.id,
            name=fc.name,
            response={
                "status": "success",
                "target_queue": q_name
            }
        ), pending_transfer

    else:
        logger.warning(f"Unknown tool requested by Gemini: {fc.name}")
        return types.FunctionResponse(
            id=fc.id,
            name=fc.name,
            response={"result": "عذراً، هذه الأداة غير معرفة."}
        ), None
