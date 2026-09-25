"""
OpenAPI 3.1 Specification for Direct Platform User Developer API (/api/v1/).
Supports bilingual Arabic ('ar') and English ('en') with complete schemas,
endpoint summaries, realistic examples, and security definitions.
"""

def get_user_openapi_spec(server_url: str = "/api/v1", lang: str = "ar") -> dict:
    lang = "en" if lang.lower() == "en" else "ar"
    is_ar = (lang == "ar")

    info = {
        "title": "واجهة برمجة تطبيقات المساعد الصوتي (Developer Voice API)" if is_ar else "Voice AI Developer API (Platform REST Reference)",
        "version": "1.0.0",
        "description": (
            "دليل تكامل واجهات المطورين المباشرة (Direct Developer API). "
            "يتيح لك هذا الـ API ربط وتضمين المساعد الصوتي الذكي داخل موقعك أو تطبيقك أو نظامك الخاص مباشرة "
            "باستخدام مفتاح الـ API الشخصي الخاص بك (X-API-Key). "
            "تتم إدارة الموارد التابعة لحسابك (الشخصيات، المستندات، خوادم FastMCP، الموظفين، واستخراج توكنات WebRTC لبدء المكالمات الحية) بكل سلاسة."
            if is_ar else
            "Direct Developer Integration Guide for Platform Users. "
            "This API enables you to embed intelligent, dialect-aware conversational voice AI directly into your apps and web services "
            "using your personal API key (X-API-Key). "
            "Effortlessly manage your voice personas, CRM customer memories, FastMCP servers, and issue ephemeral WebRTC LiveKit tokens for live calling."
        ),
        "contact": {
            "name": "فريق دعم المطورين" if is_ar else "Developer API Support",
            "url": "https://localhost/api/v1/docs/"
        }
    }

    tags_ar = [
        {"name": "1. الحساب والرصيد (Account & Balance)", "description": "استعراض تفاصيل الحساب، الرصيد المالي الحالي بالدولار، والشخصية المفعلة وإحصائيات النظام."},
        {"name": "2. الصوت واللهجات والشخصيات", "description": "إدارة بروفايلات الذكاء الاصطناعي، اللهجات (سعودي، مصري، شامي، فصحى)، وتفعيل الشخصيات."},
        {"name": "3. ذاكرة وسياق العملاء CRM", "description": "سجلات الذاكرة التراكمية، ملاحظات المكالمات، والاستعلام برقم هاتف المتصل."},
        {"name": "4. قواعد المعرفة والاستعلام الدلالي RAG", "description": "رفع المستندات وفهرستها دلالياً بالمتجهات (pgvector) والبحث الذكي عبر Gemini."},
        {"name": "5. خوادم FastMCP والأدوات الحية", "description": "ربط خوادم FastMCP الخارجية عبر بروتوكول SSE ومزامنة أدوات الذكاء الاصطناعي."},
        {"name": "6. السنترالات والخطوط والأرقام", "description": "ربط سنترالات PBX (Issabel)، خطوط SIP الصادرة، وربط أرقام الـ DIDs."},
        {"name": "7. دليل الموظفين والتحويلات", "description": "إدارة الموظفين والتحويلات الداخلية للعميل وحالات التوفر (Ready, Busy, Offline)."},
        {"name": "8. طوابير الانتظار والكول سنتر", "description": "طوابير الكول سنتر واستراتيجيات التوزيع (Round Robin) وإدارة الأعضاء."},
        {"name": "9. بدء مكالمة WebRTC", "description": "إصدار توكنات LiveKit المشفرة لبدء المكالمة الصوتية الفورية في المتصفح أو التطبيق."},
        {"name": "10. حملات الاتصال والعملاء (Campaigns)", "description": "إنشاء وإدارة حملات الاتصال الآلي الصادرة وجدولة الاتصال المتوازي عبر Inngest."},
        {"name": "11. سجلات المكالمات والفوترة", "description": "استعراض سجلات المكالمات CDR، الدقائق المفوترة، تكلفة المكالمة، وملخصات المحادثة."},
        {"name": "12. إشعارات الويبهوك", "description": "استقبال إشعارات انتهاء المكالمات والتحقق البرمجي من الأحداث الموقعة."}
    ]

    tags_en = [
        {"name": "1. Account & Balance", "description": "Retrieve account details, available wallet balance, and active persona status."},
        {"name": "2. Voice Profiles & Personas", "description": "Create and manage AI agent personalities, dialects, and activation."},
        {"name": "3. Customer CRM & Context Memory", "description": "Cumulative caller history, CRM customer memory, phone lookups, and notes."},
        {"name": "4. Knowledge Base & Semantic RAG", "description": "Document ingestion, pgvector semantic indexing, and RAG knowledge search."},
        {"name": "5. FastMCP Servers & Live Tools", "description": "Connect external FastMCP SSE servers and synchronize live AI tools."},
        {"name": "6. Telephony, PBX & DIDs", "description": "PBX trunks (Issabel), outbound SIP endpoints, and DID phone number mapping."},
        {"name": "7. Employee Directory & Extensions", "description": "Staff directory, internal SIP extensions, call transfers, and agent availability status."},
        {"name": "8. Call Queues & Routing", "description": "Call center queues, routing strategies (Round Robin), and queue membership."},
        {"name": "9. WebRTC Voice Sessions", "description": "Issuing encrypted LiveKit access tokens for instant browser and mobile voice sessions."},
        {"name": "10. Outbound Campaigns", "description": "Create and manage automated outbound calling campaigns and dial execution via Inngest."},
        {"name": "11. Call Logs & CDR", "description": "Call detail records (CDR), billed minute deduction, call recordings, and AI conversation summaries."},
        {"name": "12. Webhooks & Events", "description": "Configure webhook endpoints for call.completed notifications and event payloads."}
    ]

    tags = tags_ar if is_ar else tags_en
    tag_map = {
        "tag_account": tags[0]["name"],
        "tag_profiles": tags[1]["name"],
        "tag_crm": tags[2]["name"],
        "tag_rag": tags[3]["name"],
        "tag_mcp": tags[4]["name"],
        "tag_telephony": tags[5]["name"],
        "tag_employees": tags[6]["name"],
        "tag_queues": tags[7]["name"],
        "tag_token": tags[8]["name"],
        "tag_campaigns": tags[9]["name"],
        "tag_cdr": tags[10]["name"],
        "tag_webhooks": tags[11]["name"],
    }

    paths = {
        "/account/": {
            "get": {
                "tags": [tag_map["tag_account"]],
                "summary": "عرض بيانات الحساب والمحفظة (Get Account)" if is_ar else "Get Account & Wallet Info",
                "description": "يعيد بيانات الحساب ورصيد المحفظة المتاح واسم البروفايل الصوتي النشط." if is_ar else "Returns account details, wallet balance, active voice persona, and usage counters.",
                "responses": {
                    "200": {
                        "description": "بيانات الحساب" if is_ar else "Account info",
                        "content": {
                            "application/json": {
                                "example": {
                                    "status": "success",
                                    "user_id": 1,
                                    "username": "admin",
                                    "email": "admin@example.com",
                                    "wallet_balance": 50.0,
                                    "active_profile": {"id": 1, "name": "مساعد المبيعات السعودي", "dialect": "saudi"},
                                    "total_calls": 12,
                                    "total_documents": 3,
                                    "total_employees": 4,
                                    "total_mcp_servers": 1
                                }
                            }
                        }
                    },
                    "401": {"$ref": "#/components/responses/401Error"}
                }
            }
        },
        "/profiles/studio/": {
            "get": {
                "tags": [tag_map["tag_profiles"]],
                "summary": "استوديو تخصيص الشخصية والأصوات (Persona Studio Metadata)" if is_ar else "Voice & Persona Studio Metadata",
                "description": "استرجاع قائمة كافة أصوات Google الرسمية الـ 30، اللغات الـ 11، اللهجات الـ 29، ونماذج الأدوار والأساليب الحرة." if is_ar else "Get full studio catalog: 30 Google HD voices, 11 languages, 29 dialects, and inspiration roles/styles.",
                "responses": {"200": {"description": "بيانات استوديو الشخصيات" if is_ar else "Persona studio metadata"}}
            }
        },
        "/profiles/": {
            "get": {
                "tags": [tag_map["tag_profiles"]],
                "summary": "استعراض بروفايلات الصوت والشخصيات (List Profiles)" if is_ar else "List Voice Agent Profiles",
                "parameters": [
                    {"name": "is_active", "in": "query", "required": False, "schema": {"type": "boolean"}, "description": "تصفية البروفايلات النشطة فقط" if is_ar else "Filter active only"}
                ],
                "responses": {"200": {"description": "قائمة البروفايلات" if is_ar else "Profiles list"}}
            },
            "post": {
                "tags": [tag_map["tag_profiles"]],
                "summary": "إنشاء بروفايل صوتي وشخصية جديدة (Create Profile)" if is_ar else "Create Voice Agent Profile",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ProfileCreateRequest"}
                        }
                    }
                },
                "responses": {"201": {"description": "تم الإنشاء بنجاح" if is_ar else "Profile created successfully"}}
            }
        },
        "/profiles/{profile_id}/": {
            "get": {
                "tags": [tag_map["tag_profiles"]],
                "summary": "جلب تفاصيل بروفايل محدد (Get Profile)" if is_ar else "Get Voice Profile Details",
                "parameters": [{"$ref": "#/components/parameters/ProfileId"}],
                "responses": {"200": {"description": "تفاصيل البروفايل" if is_ar else "Profile details"}}
            },
            "patch": {
                "tags": [tag_map["tag_profiles"]],
                "summary": "تعديل بروفايل صوتي (Update Profile)" if is_ar else "Update Voice Profile",
                "parameters": [{"$ref": "#/components/parameters/ProfileId"}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ProfileUpdateRequest"}
                        }
                    }
                },
                "responses": {"200": {"description": "تم التحديث بنجاح" if is_ar else "Profile updated successfully"}}
            },
            "delete": {
                "tags": [tag_map["tag_profiles"]],
                "summary": "حذف بروفايل صوتي (Delete Profile)" if is_ar else "Delete Voice Profile",
                "parameters": [{"$ref": "#/components/parameters/ProfileId"}],
                "responses": {"200": {"description": "تم الحذف بنجاح" if is_ar else "Profile deleted successfully"}}
            }
        },
        "/profiles/{profile_id}/activate/": {
            "post": {
                "tags": [tag_map["tag_profiles"]],
                "summary": "تفعيل البروفايل الصوتي كافتراضي (Activate Profile)" if is_ar else "Set Profile as Active",
                "parameters": [{"$ref": "#/components/parameters/ProfileId"}],
                "responses": {"200": {"description": "تم التفعيل بنجاح" if is_ar else "Profile activated successfully"}}
            }
        },
        "/memory/": {
            "get": {
                "tags": [tag_map["tag_crm"]],
                "summary": "استعراض وبحث ذاكرة العملاء (List & Search CRM)" if is_ar else "List & Search CRM Memories",
                "parameters": [
                    {"name": "q", "in": "query", "schema": {"type": "string"}, "description": "بحث بالاسم أو الهاتف" if is_ar else "Search query"},
                    {"name": "phone", "in": "query", "schema": {"type": "string"}, "description": "جلب مباشر برقم هاتف محدد" if is_ar else "Direct phone lookup"},
                    {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 20}}
                ],
                "responses": {"200": {"description": "سجلات الذاكرة" if is_ar else "Customer memories list"}}
            },
            "post": {
                "tags": [tag_map["tag_crm"]],
                "summary": "إنشاء أو تحديث ذاكرة عميل (Upsert Memory)" if is_ar else "Create or Upsert Customer Memory",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/MemoryUpsertRequest"}
                        }
                    }
                },
                "responses": {"200": {"description": "تم الحفظ بنجاح" if is_ar else "Memory saved successfully"}}
            }
        },
        "/memory/{memory_id}/": {
            "get": {
                "tags": [tag_map["tag_crm"]],
                "summary": "جلب تفاصيل ذاكرة عميل (Get Memory)" if is_ar else "Get Customer Memory Details",
                "parameters": [{"$ref": "#/components/parameters/MemoryId"}],
                "responses": {"200": {"description": "تفاصيل الذاكرة" if is_ar else "Memory details"}}
            },
            "put": {
                "tags": [tag_map["tag_crm"]],
                "summary": "تحديث ذاكرة عميل (Update Memory)" if is_ar else "Update Customer Memory",
                "parameters": [{"$ref": "#/components/parameters/MemoryId"}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/MemoryUpsertRequest"}
                        }
                    }
                },
                "responses": {"200": {"description": "تم التحديث بنجاح" if is_ar else "Memory updated successfully"}}
            },
            "delete": {
                "tags": [tag_map["tag_crm"]],
                "summary": "حذف ذاكرة عميل (Delete Memory)" if is_ar else "Delete Customer Memory",
                "parameters": [{"$ref": "#/components/parameters/MemoryId"}],
                "responses": {"200": {"description": "تم الحذف بنجاح" if is_ar else "Memory deleted successfully"}}
            }
        },
        "/documents/": {
            "get": {
                "tags": [tag_map["tag_rag"]],
                "summary": "استعراض مستندات قاعدة المعرفة (List Documents)" if is_ar else "List Knowledge Documents",
                "responses": {"200": {"description": "المستندات المفهرسة" if is_ar else "Indexed documents"}}
            },
            "post": {
                "tags": [tag_map["tag_rag"]],
                "summary": "رفع مستند أو رابط وفهرسته بالمتجهات (Upload Document)" if is_ar else "Upload & Index Knowledge Document",
                "description": "فهرسة مستند حقيقي (PDF, DOCX, CSV, TXT, MD, JSON) عبر رفع ملف مباشر، رابط خارجي (file_url)، أو نص مباشر ليتم استخراج النصوص وفهرستها دلالياً بالمتجهات عبر Gemini." if is_ar else "Upload a document file (PDF, DOCX, CSV, TXT, MD, JSON), pass a direct file_url, or raw text for semantic vector chunking & indexing.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "multipart/form-data": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "file": {
                                        "type": "string",
                                        "format": "binary",
                                        "description": "ملف المستند المراد رفعه وفهرسته (PDF, DOCX, CSV, TXT, MD, JSON)" if is_ar else "Document file (PDF, DOCX, CSV, TXT, MD, JSON)"
                                    },
                                    "file_url": {
                                        "type": "string",
                                        "description": "رابط خارجي مباشر للمستند (PDF, DOCX, CSV, TXT, MD, JSON)" if is_ar else "Direct public URL to document"
                                    },
                                    "title": {
                                        "type": "string",
                                        "description": "عنوان المستند (اختياري - يتم استخدام اسم الملف تلقائياً)" if is_ar else "Document title (optional - defaults to filename)"
                                    },
                                    "content": {
                                        "type": "string",
                                        "description": "نص مباشر كبديل في حال عدم إرفاق ملف أو رابط" if is_ar else "Raw text content as an alternative"
                                    }
                                }
                            }
                        },
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string", "example": "سياسة الاسترجاع والشحن" if is_ar else "Return & Shipping Policy"},
                                    "content": {"type": "string", "example": "يمكن استرجاع المنتجات خلال 14 يوماً من الشراء بحالتها الأصلية." if is_ar else "Products can be returned within 14 days of purchase."},
                                    "file_url": {"type": "string", "example": "https://example.com/company_policy.pdf"}
                                }
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "تمت الفهرسة بنجاح" if is_ar else "Document indexed successfully"}}
            }
        },
        "/rag/query/": {
            "post": {
                "tags": [tag_map["tag_rag"]],
                "summary": "استعلام دلالي ذكي بالمتجهات (Semantic RAG Query)" if is_ar else "Semantic RAG Search Query",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["query"],
                                "properties": {
                                    "query": {"type": "string", "example": "كم مدة استرجاع البضاعة؟" if is_ar else "How long is the return window?"},
                                    "top_k": {"type": "integer", "default": 3}
                                }
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "نتائج البحث الدلالي" if is_ar else "Semantic search matches"}}
            }
        },
        "/mcp/": {
            "get": {
                "tags": [tag_map["tag_mcp"]],
                "summary": "استعراض خوادم الـ FastMCP المسجلة (List MCP Servers)" if is_ar else "List FastMCP Servers",
                "description": "يعيد قائمة خوادم FastMCP والأدوات المكتشفة لكل خادم." if is_ar else "Returns list of configured FastMCP servers and cached tools.",
                "responses": {"200": {"description": "خوادم MCP" if is_ar else "MCP servers list"}}
            },
            "post": {
                "tags": [tag_map["tag_mcp"]],
                "summary": "تسجيل خادم FastMCP ومصادقته (Register MCP Server)" if is_ar else "Register FastMCP Server",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["server_url"],
                                "properties": {
                                    "name": {"type": "string", "example": "خادم متجر سلة (FastMCP)" if is_ar else "Main Store FastMCP"},
                                    "server_url": {"type": "string", "example": "http://mock-store:8002/sse"},
                                    "auth_token": {"type": "string", "example": "secret_token_123"},
                                    "is_active": {"type": "boolean", "default": True}
                                }
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "تم تسجيل الخادم بنجاح" if is_ar else "MCP server registered successfully"}}
            }
        },
        "/mcp/{mcp_id}/sync/": {
            "post": {
                "tags": [tag_map["tag_mcp"]],
                "summary": "مزامنة أدوات خادم الـ MCP فورياً (Sync Tools)" if is_ar else "Sync MCP Server Tools",
                "parameters": [{"name": "mcp_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                "responses": {"200": {"description": "تمت المزامنة بنجاح" if is_ar else "Tools synced successfully"}}
            }
        },
        "/mcp/{mcp_id}/": {
            "get": {
                "tags": [tag_map["tag_mcp"]],
                "summary": "تفاصيل خادم الـ MCP والأدوات (Get MCP Server)" if is_ar else "Get MCP Server Details",
                "parameters": [{"name": "mcp_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                "responses": {"200": {"description": "تفاصيل خادم MCP" if is_ar else "MCP server details"}}
            },
            "patch": {
                "tags": [tag_map["tag_mcp"]],
                "summary": "تعديل إعدادات خادم MCP (Update MCP Server)" if is_ar else "Update MCP Server",
                "parameters": [{"name": "mcp_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                "responses": {"200": {"description": "تم التعديل بنجاح" if is_ar else "Updated successfully"}}
            },
            "delete": {
                "tags": [tag_map["tag_mcp"]],
                "summary": "حذف خادم الـ MCP (Delete MCP Server)" if is_ar else "Delete MCP Server",
                "parameters": [{"name": "mcp_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                "responses": {"200": {"description": "تم الحذف بنجاح" if is_ar else "Deleted successfully"}}
            }
        },
        "/telephony/": {
            "get": {
                "tags": [tag_map["tag_telephony"]],
                "summary": "عرض السنترالات وخطوط SIP (List Trunks)" if is_ar else "List Telephony & PBX Trunks",
                "responses": {"200": {"description": "السنترالات والخطوط" if is_ar else "Trunks list"}}
            },
            "post": {
                "tags": [tag_map["tag_telephony"]],
                "summary": "ربط سنترال أو خط خارجي (Register Trunk)" if is_ar else "Register PBX or SIP Trunk",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["name", "host"],
                                "properties": {
                                    "trunk_type": {"type": "string", "enum": ["pbx", "sip"], "default": "pbx"},
                                    "name": {"type": "string", "example": "Issabel PBX"},
                                    "host": {"type": "string", "example": "192.168.1.100"},
                                    "port": {"type": "integer", "default": 5060},
                                    "username": {"type": "string", "example": "1001"},
                                    "secret": {"type": "string", "example": "secret123"}
                                }
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "تم الربط بنجاح" if is_ar else "Trunk registered successfully"}}
            }
        },
        "/telephony/numbers/": {
            "get": {
                "tags": [tag_map["tag_telephony"]],
                "summary": "استعراض أرقام الـ DID المرتبطة (List DIDs)" if is_ar else "List Assigned DID Numbers",
                "responses": {"200": {"description": "قائمة الأرقام" if is_ar else "DID numbers list"}}
            },
            "post": {
                "tags": [tag_map["tag_telephony"]],
                "summary": "ربط رقم هاتف بالسنترال (Assign DID)" if is_ar else "Assign Phone Number to PBX",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["phone_number"],
                                "properties": {
                                    "phone_number": {"type": "string", "example": "+966112233445"},
                                    "pbx_trunk_id": {"type": "integer", "example": 1},
                                    "description": {"type": "string", "example": "الرقم الموحد" if is_ar else "Main hotline"}
                                }
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "تم التعيين بنجاح" if is_ar else "Number assigned successfully"}}
            }
        },
        "/employees/": {
            "get": {
                "tags": [tag_map["tag_employees"]],
                "summary": "عرض دليل الموظفين والتحويلات (List Employees)" if is_ar else "List Employees & Extensions",
                "responses": {"200": {"description": "دليل الموظفين" if is_ar else "Employee directory"}}
            },
            "post": {
                "tags": [tag_map["tag_employees"]],
                "summary": "إضافة موظف جديد (Create Employee)" if is_ar else "Create Employee",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["name", "extension"],
                                "properties": {
                                    "name": {"type": "string", "example": "سارة أحمد" if is_ar else "Sara Ahmed"},
                                    "extension": {"type": "string", "example": "105"},
                                    "department": {"type": "string", "example": "خدمة العملاء" if is_ar else "Customer Support"},
                                    "status": {"type": "string", "enum": ["ready", "busy", "offline"], "default": "ready"}
                                }
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "تم إنشاء الموظف بنجاح" if is_ar else "Employee created successfully"}}
            }
        },
        "/employees/{employee_id}/": {
            "get": {
                "tags": [tag_map["tag_employees"]],
                "summary": "بيانات موظف محدد (Get Employee)" if is_ar else "Get Employee Details",
                "parameters": [{"$ref": "#/components/parameters/EmployeeId"}],
                "responses": {"200": {"description": "بيانات الموظف" if is_ar else "Employee details"}}
            },
            "delete": {
                "tags": [tag_map["tag_employees"]],
                "summary": "حذف موظف (Delete Employee)" if is_ar else "Delete Employee",
                "parameters": [{"$ref": "#/components/parameters/EmployeeId"}],
                "responses": {"200": {"description": "تم الحذف بنجاح" if is_ar else "Deleted successfully"}}
            }
        },
        "/queues/": {
            "get": {
                "tags": [tag_map["tag_queues"]],
                "summary": "عرض طوابير الانتظار (List Queues)" if is_ar else "List Call Queues",
                "responses": {"200": {"description": "قائمة الطوابير" if is_ar else "Queues list"}}
            },
            "post": {
                "tags": [tag_map["tag_queues"]],
                "summary": "إنشاء طابور انتظار (Create Queue)" if is_ar else "Create Call Queue",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["name"],
                                "properties": {
                                    "name": {"type": "string", "example": "طابور الدعم الفني" if is_ar else "Technical Support Queue"},
                                    "code": {"type": "string", "example": "200", "description": "كود الطابور للتحويل"},
                                    "description": {"type": "string", "example": "طابور استفسارات المنتجات والشحن والمبيعات"},
                                    "strategy": {"type": "string", "enum": ["round_robin", "ring_all"], "default": "round_robin"},
                                    "ring_timeout_seconds": {"type": "integer", "default": 15},
                                    "total_timeout_seconds": {"type": "integer", "default": 60},
                                    "fallback_action": {"type": "string", "enum": ["ai_assistant", "hangup"], "default": "ai_assistant"},
                                    "members": {"type": "array", "items": {"type": "integer"}, "description": "قائمة معرفات الموظفين"}
                                }
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "تم إنشاء الطابور بنجاح" if is_ar else "Queue created successfully"}}
            }
        },
        "/queues/{queue_id}/members/": {
            "get": {
                "tags": [tag_map["tag_queues"]],
                "summary": "استعراض أعضاء الطابور (List Queue Members)" if is_ar else "List Queue Members",
                "parameters": [{"name": "queue_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                "responses": {"200": {"description": "أعضاء الطابور" if is_ar else "Queue members list"}}
            },
            "post": {
                "tags": [tag_map["tag_queues"]],
                "summary": "إضافة موظف إلى الطابور (Add Queue Member)" if is_ar else "Add Employee to Queue",
                "parameters": [{"name": "queue_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["employee_id"],
                                "properties": {
                                    "employee_id": {"type": "integer", "example": 1},
                                    "order": {"type": "integer", "default": 0}
                                }
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "تمت إضافة الموظف للطابور" if is_ar else "Employee added to queue"}}
            },
            "delete": {
                "tags": [tag_map["tag_queues"]],
                "summary": "إزالة موظف من الطابور (Remove Queue Member)" if is_ar else "Remove Employee from Queue",
                "parameters": [
                    {"name": "queue_id", "in": "path", "required": True, "schema": {"type": "integer"}},
                    {"name": "employee_id", "in": "query", "required": True, "schema": {"type": "integer"}}
                ],
                "responses": {"200": {"description": "تمت الإزالة بنجاح" if is_ar else "Member removed successfully"}}
            }
        },
        "/token/": {
            "post": {
                "tags": [tag_map["tag_token"]],
                "summary": "إصدار توكن اتصال WebRTC فوري (Generate Voice Token)" if is_ar else "Generate WebRTC Voice Session Token",
                "description": (
                    "ينشئ غرفة LiveKit وتوكن JWT مشفر مع روابط خادم LiveKit ورابط Centrifugo WebSocket لبدء الاتصال الصوتي المباشر واستقبال نصوص المحادثة الحية في المتصفح أو التطبيق.\n\n"
                    "**طريقة الاتصال المباشر (LiveKit SDK Quickstart):**\n"
                    "```javascript\n"
                    "import { Room } from 'livekit-client';\n\n"
                    "const room = new Room();\n"
                    "await room.connect(response.livekit_url, response.token);\n"
                    "await room.localParticipant.setMicrophoneEnabled(true);\n"
                    "```"
                    if is_ar else
                    "Issues an ephemeral LiveKit JWT token and WebSocket connection URLs for embedding direct real-time voice calls into web/mobile apps."
                ),
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "participant_name": {"type": "string", "example": "زائر الموقع" if is_ar else "Web Visitor"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "تم إصدار التوكن والروابط بنجاح" if is_ar else "LiveKit token & URLs generated successfully",
                        "content": {
                            "application/json": {
                                "example": {
                                    "status": "success",
                                    "room_name": "user_1_8f9e",
                                    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                    "livekit_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                    "livekit_url": "wss://livekit.169.58.32.179.nip.io",
                                    "centrifugo_ws_url": "wss://centrifugo.169.58.32.179.nip.io/connection/websocket",
                                    "centrifugo_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                    "channel": "user_1_8f9e",
                                    "user_id": 1
                                }
                            }
                        }
                    },
                    "402": {"description": "رصيد المحفظة غير كافٍ" if is_ar else "Insufficient wallet balance"}
                }
            }
        },
        "/calls/": {
            "get": {
                "tags": [tag_map["tag_cdr"]],
                "summary": "استعراض سجلات المكالمات والـ CDR (List Call Logs)" if is_ar else "List Call Detail Records (CDR)",
                "description": "يعيد قائمة المكالمات الأخيرة وتكلفتها والدقائق المفوترة وملخص المحادثة الذكي." if is_ar else "Returns recent call history, duration, billed minutes, cost, and AI summaries.",
                "responses": {"200": {"description": "سجلات المكالمات" if is_ar else "Call records list"}}
            }
        },
        "/calls/dial/": {
            "post": {
                "tags": [tag_map["tag_cdr"]],
                "summary": "بدء مكالمة هاتفية صادرة بالذكاء الاصطناعي (Autonomous Outbound Dialing)" if is_ar else "Initiate Autonomous Outbound AI Phone Call",
                "description": (
                    "توجيه روبوت الصوت الذكي للاتصال تلقائياً برقم هاتف خارجي أو تحويلة سنترال PBX داخلية، والتحدث مع العميل فور فتح الخط لتحقيق هدف محدد (مثل تأكيد الطلبات، التذكير بالمواعيد، أو خدمة العملاء)."
                    if is_ar else
                    "Trigger an autonomous outbound AI phone call to an external customer phone number or internal PBX extension. The AI assistant immediately initiates dialogue to achieve the specified goal once answered."
                ),
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["phone_number"],
                                "properties": {
                                    "phone_number": {
                                        "type": "string",
                                        "example": "+201012345678",
                                        "description": "رقم هاتف العميل بالصيغة الدولية أو رقم تحويلة PBX (مثال: 101)" if is_ar else "Destination E.164 phone number or PBX extension (e.g. 101)"
                                    },
                                    "call_goal": {
                                        "type": "string",
                                        "example": "تأكيد تفاصيل الطلب رقم 1042 ومعالجة استفسارات التوصيل" if is_ar else "Confirm details of order #1042 and delivery schedule",
                                        "description": "الهدف أو التعليمات الفورية للمكالمة الصادرة" if is_ar else "Goal or instructions given to the AI voice agent for this outbound call"
                                    },
                                    "profile_id": {
                                        "type": "integer",
                                        "example": 1,
                                        "description": "معرف البروفايل الصوتي (اختياري - يستخدم الافتراضي إن تُرك فارغاً)" if is_ar else "Voice persona profile ID (optional - defaults to active profile)"
                                    },
                                    "gateway_type": {
                                        "type": "string",
                                        "enum": ["auto", "pbx", "cloud"],
                                        "default": "auto",
                                        "description": "مسار الاتصال: auto (تلقائي)، pbx (سنترال محلي)، cloud (جذع سحابي)" if is_ar else "Dialing gateway: auto, pbx, or cloud"
                                    },
                                    "gateway_id": {
                                        "type": "integer",
                                        "example": 2,
                                        "description": "معرف السنترال أو الجذع المحدد عند اختيار pbx" if is_ar else "Specific PBX trunk ID when gateway_type is pbx"
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "تم بدء الاتصال بنجاح" if is_ar else "Outbound call initiated successfully",
                        "content": {
                            "application/json": {
                                "example": {
                                    "status": "success",
                                    "message": "تم بدء الاتصال الصادر بالرقم +201012345678 بنجاح عبر سنترال Issabel (افتراضي)" if is_ar else "AI outbound call initiated successfully",
                                    "call_id": "room_user_1_ai_out_ab12cd34",
                                    "room_name": "room_user_1_ai_out_ab12cd34",
                                    "session_id": 482,
                                    "destination_phone": "+201012345678",
                                    "call_goal": "تأكيد تفاصيل الطلب رقم 1042 ومعالجة استفسارات التوصيل",
                                    "trunk_name": "سنترال Issabel (افتراضي)",
                                    "gateway_used": "سنترال Issabel (افتراضي)",
                                    "caller_id": "+201234567890"
                                }
                            }
                        }
                    },
                    "400": {"description": "بيانات الاتصال غير صالحة أو رقم الهاتف مفقود" if is_ar else "Missing or invalid phone number"},
                    "402": {"description": "رصيد المحفظة غير كافٍ لبدء المكالمة الصادرة" if is_ar else "Insufficient balance for outbound call"},
                    "422": {"description": "لا يوجد مسار اتصال صادر مفعل (سحابي أو سنترال)" if is_ar else "No active outbound route configured"}
                }
            }
        },
        "/calls/hangup/": {
            "post": {
                "tags": [tag_map["tag_cdr"]],
                "summary": "إنهاء مكالمة جارية فورياً (Hangup Active Call)" if is_ar else "Hang Up Active Call Session",
                "description": (
                    "إنهاء مكالمة هاتفية أو صوتية جارية فورياً وفصل المتصل والذكاء الاصطناعي وحذف غرفة LiveKit وتسجيل مدة المكالمة."
                    if is_ar else
                    "Immediately terminates an active voice/phone call session, closes the LiveKit room, notifies presence channels, and finalizes call logs."
                ),
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["call_id"],
                                "properties": {
                                    "call_id": {"type": "string", "example": "user_1_8f9e", "description": "معرف المكالمة أو اسم الغرفة"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "تم إنهاء المكالمة بنجاح" if is_ar else "Call terminated successfully"},
                    "400": {"description": "معرف المكالمة غير محدد" if is_ar else "call_id is required"}
                }
            }
        },
        "/webhooks/": {
            "get": {
                "tags": [tag_map["tag_webhooks"]],
                "summary": "عرض إعدادات الويبهوك الحالية (Get Webhook)" if is_ar else "Get Webhook Settings",
                "responses": {"200": {"description": "إعدادات الويبهوك" if is_ar else "Webhook settings"}}
            },
            "post": {
                "tags": [tag_map["tag_webhooks"]],
                "summary": "حفظ أو تحديث رابط الويبهوك (Save Webhook)" if is_ar else "Save Webhook Settings",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["webhook_url"],
                                "properties": {
                                    "webhook_url": {"type": "string", "example": "https://api.mywebsite.com/voice-events/"},
                                    "webhook_secret": {"type": "string", "example": "my_hmac_secret_key"}
                                }
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "تم الحفظ بنجاح" if is_ar else "Webhook saved successfully"}}
            }
        }
    }

    components = {
        "securitySchemes": {
            "UserApiKey": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": (
                    "مفتاح الـ API الشخصي للمستخدم (يبدأ بـ sk_live_usr_...). يجب تمريره في هيدر كل طلب."
                    if is_ar else
                    "Personal User API key (starts with sk_live_usr_...). Required on all requests."
                )
            }
        },
        "parameters": {
            "ProfileId": {
                "name": "profile_id",
                "in": "path",
                "required": True,
                "schema": {"type": "integer"},
                "description": "المعرف الرقمي للبروفايل" if is_ar else "Numerical ID of the profile"
            },
            "MemoryId": {
                "name": "memory_id",
                "in": "path",
                "required": True,
                "schema": {"type": "integer"},
                "description": "المعرف الرقمي لسجل الذاكرة" if is_ar else "Numerical ID of the memory record"
            },
            "EmployeeId": {
                "name": "employee_id",
                "in": "path",
                "required": True,
                "schema": {"type": "integer"},
                "description": "المعرف الرقمي للموظف" if is_ar else "Numerical ID of the employee"
            }
        },
        "responses": {
            "401Error": {
                "description": "غير مصرح (مفتاح الـ API مفقود)" if is_ar else "Unauthorized (Missing API key)",
                "content": {"application/json": {"example": {"status": "error", "message": "Missing user API key"}}}
            },
            "403Error": {
                "description": "ممنوع (مفتاح الـ API غير صالح)" if is_ar else "Forbidden (Invalid API key)",
                "content": {"application/json": {"example": {"status": "error", "message": "Invalid or inactive API key"}}}
            },
            "404Error": {
                "description": "العنصر غير موجود (Not Found)" if is_ar else "Not Found",
                "content": {"application/json": {"example": {"status": "error", "message": "Resource not found"}}}
            }
        },
        "schemas": {
            "ProfileCreateRequest": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string", "example": "مساعد المبيعات السعودي" if is_ar else "Saudi Sales Advisor"},
                    "voice_name": {"type": "string", "default": "Aoede", "example": "Aoede"},
                    "gender": {"type": "string", "enum": ["female", "male"], "default": "female"},
                    "language": {"type": "string", "default": "arabic", "example": "arabic"},
                    "dialect": {"type": "string", "default": "egyptian", "example": "egyptian"},
                    "persona_role": {"type": "string", "description": "الدور والشخصية المحددة بكتابة حرة مفتوحة", "example": "ممثل خدمة عملاء ومبيعات متجر الكتروني"},
                    "speaking_style": {"type": "string", "description": "أسلوب الإلقاء والنبرة المطلوب الالتزام بها بكتابة حرة", "example": "ودود ولطيف ومرح"},
                    "verbosity": {"type": "string", "enum": ["concise", "balanced", "detailed"], "default": "balanced", "description": "مستوى الإيجاز وسرعة الرد: concise (مختصر 1-2 جملة), balanced (متوازن 2-3 جمل), detailed (مفصل)", "example": "concise"},
                    "custom_instructions": {"type": "string", "example": "أنت مستشار مبيعات ودود وذكي." if is_ar else "You are a friendly and smart sales advisor."},
                    "is_active": {"type": "boolean", "default": True}
                }
            },
            "ProfileUpdateRequest": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "voice_name": {"type": "string"},
                    "gender": {"type": "string", "enum": ["female", "male"]},
                    "language": {"type": "string"},
                    "dialect": {"type": "string"},
                    "persona_role": {"type": "string", "description": "الدور والشخصية بكتابة حرة"},
                    "speaking_style": {"type": "string", "description": "أسلوب الإلقاء والنبرة بكتابة حرة"},
                    "verbosity": {"type": "string", "enum": ["concise", "balanced", "detailed"], "description": "مستوى الإيجاز وسرعة الرد"},
                    "custom_instructions": {"type": "string"},
                    "is_active": {"type": "boolean"}
                }
            },
            "MemoryUpsertRequest": {
                "type": "object",
                "required": ["phone_number"],
                "properties": {
                    "phone_number": {"type": "string", "example": "+966501234567"},
                    "customer_name": {"type": "string", "example": "عبدالله الشمري" if is_ar else "Abdullah Al-Shammari"},
                    "permanent_profile": {
                        "type": "object",
                        "example": {"city": "الرياض" if is_ar else "Riyadh", "vip_tier": "Gold"}
                    },
                    "immediate_notes": {"type": "string", "example": "يفضل الشحن الصباحي" if is_ar else "Prefers morning dispatch"},
                    "total_calls_count": {"type": "integer", "example": 2}
                }
            }
        }
    }

    return {
        "openapi": "3.1.0",
        "info": info,
        "servers": [
            {
                "url": server_url,
                "description": "خادم الواجهة البرمجية المباشر للمطورين" if is_ar else "Direct Developer API Server"
            }
        ],
        "security": [
            {"UserApiKey": []}
        ],
        "tags": tags,
        "paths": paths,
        "components": components
    }
