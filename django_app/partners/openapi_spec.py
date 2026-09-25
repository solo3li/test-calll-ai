"""
OpenAPI 3.1 Specification for Headless B2B Voice SaaS Partner API.
Supports both Arabic ('ar') and English ('en') with complete schemas,
endpoint summaries, realistic examples, and security definitions.
"""

def get_partner_openapi_spec(server_url: str = "/api/partner/v1", lang: str = "ar") -> dict:
    lang = "en" if lang.lower() == "en" else "ar"
    is_ar = (lang == "ar")

    # 1. Info Definition
    info = {
        "title": "منظومة المساعد الصوتي للشركاء (Voice SaaS Partner API)" if is_ar else "Voice AI Partner Platform API (Headless Voice SaaS)",
        "version": "1.0.0",
        "description": (
            "دليل تكامل واجهات الشركاء وخدمات الـ SaaS (Headless Architecture). "
            "يتيح لك هذا الـ API بناء وتضمين خدمة المساعد الصوتي الذكي داخل تطبيقك أو متجرك "
            "أو نظامك السحابي دون أن يرى عميلك واجهتنا مطلقاً (White-Label). "
            "تتم محاسبتك بسعر الجملة المخفض المخصص لك بخصم مباشر من محفظتك المركزية مع التقريب الصارم لأعلى دقيقة."
            if is_ar else
            "Developer Integration Guide for SaaS Partners & Resellers (Headless Architecture). "
            "This API enables you to embed intelligent, dialect-aware conversational voice AI directly into your applications, "
            "e-commerce stores, or SaaS platforms with zero third-party branding (White-Label). "
            "Usage is billed at your negotiated wholesale per-minute rate directly from your central pooled wallet with strict ceiling minute rounding."
        ),
        "contact": {
            "name": "فريق الدعم الفني للمنظومة" if is_ar else "Voice AI Platform Partner Support",
            "url": "https://localhost/api/partner/v1/docs/"
        }
    }

    # 2. Tags Definition
    tags_ar = [
        {"name": "1. نظرة عامة والمصادقة", "description": "طريقة المصادقة عبر هيدر X-Partner-Key وسياسة الفوترة والأسعار المخفضة."},
        {"name": "2. تسجيل وإدارة العملاء", "description": "تسجيل المتاجر والعملاء الفرعيين وضبط سقوف الاستهلاك والدقائق."},
        {"name": "3. الصوت واللهجات والشخصيات", "description": "إدارة بروفايلات الذكاء الاصطناعي، اللهجات (سعودي، مصري، شامي، فصحى)، وتفعيل الشخصيات."},
        {"name": "4. ذاكرة وسياق العملاء CRM", "description": "سجلات الذاكرة التراكمية، ملاحظات المكالمات، والاستعلام برقم هاتف المتصل مع الترقيم والبحث."},
        {"name": "5. قواعد المعرفة والاستعلام الدلالي RAG", "description": "رفع المستندات وفهرستها دلالياً بالمتجهات (pgvector) والبحث الذكي عبر Gemini."},
        {"name": "6. السنترالات والخطوط والأرقام", "description": "ربط سنترالات PBX (Issabel)، خطوط SIP الصادرة، وربط أرقام الـ DIDs."},
        {"name": "7. دليل الموظفين والتحويلات", "description": "إدارة الموظفين والتحويلات الداخلية للعميل وحالات التوفر (Ready, Busy, Offline)."},
        {"name": "8. طوابير الانتظار والأعضاء", "description": "طوابير الكول سنتر واستراتيجيات التوزيع (Round Robin) وإدارة الأعضاء."},
        {"name": "9. بدء مكالمة WebRTC", "description": "إصدار توكنات LiveKit المشفرة لبدء المكالمة الصوتية الفورية في المتصفح أو التطبيق."},
        {"name": "10. سجلات المكالمات والفوترة", "description": "استعراض سجلات المكالمات CDR، الدقائق المفوترة، تكلفة المكالمة، وملخصات المحادثة."},
        {"name": "11. الويبهوك والتوقيع المشفر", "description": "استقبال إشعارات انتهاء المكالمات والتحقق البرمجي من توقيع HMAC-SHA256."},
        {"name": "12. إدارة خوادم FastMCP للعملاء", "description": "ربط خوادم FastMCP الخارجية لعميل محدد عبر بروتوكول SSE ومزامنة أدوات الذكاء الاصطناعي الحية."},
        {"name": "13. حملات اتصال العملاء (Client Campaigns)", "description": "إنشاء وإدارة حملات الاتصال الآلي وجدولة الاتصال المتوازي لعملاء الشريك عبر Inngest."}
    ]

    tags_en = [
        {"name": "1. Overview & Authentication", "description": "Authentication via X-Partner-Key header, wholesale billing model, and discounted rates."},
        {"name": "2. Client Management", "description": "Sub-client store provisioning, account status, and spending/minute caps."},
        {"name": "3. Voice Profiles & Personas", "description": "AI voice agent profiles, regional dialects (Saudi, Egyptian, Levantine, Fusha, English), and activation."},
        {"name": "4. Customer CRM & Context Memory", "description": "Cumulative caller context, CRM customer memory, phone lookups, and notes."},
        {"name": "5. Knowledge Base & Semantic RAG", "description": "Document ingestion, pgvector semantic indexing, and RAG knowledge search."},
        {"name": "6. Telephony, PBX & DIDs", "description": "PBX trunks (Issabel), outbound SIP endpoints, and DID phone number mapping."},
        {"name": "7. Employee Directory & Extensions", "description": "Staff directory, internal SIP extensions, call transfers, and agent availability status."},
        {"name": "8. Call Queues & Routing", "description": "Call center queues, routing strategies (Round Robin), and queue membership."},
        {"name": "9. WebRTC Voice Sessions", "description": "Issuing encrypted LiveKit access tokens for instant browser and mobile voice sessions."},
        {"name": "10. Call Logs & CDR", "description": "Call detail records (CDR), billed minute deduction, call recordings, and AI conversation summaries."},
        {"name": "11. Webhooks & HMAC Signatures", "description": "Real-time call completion webhook notifications and HMAC-SHA256 signature verification."},
        {"name": "12. Client FastMCP Management", "description": "Manage external FastMCP SSE tool servers per sub-client and synchronize live tool schemas."},
        {"name": "13. Client Outbound Campaigns", "description": "Create and execute outbound calling campaigns for sub-clients via Inngest."}
    ]

    tags = tags_ar if is_ar else tags_en
    tag_map = {
        "tag_auth": tags[0]["name"],
        "tag_clients": tags[1]["name"],
        "tag_profiles": tags[2]["name"],
        "tag_crm": tags[3]["name"],
        "tag_rag": tags[4]["name"],
        "tag_telephony": tags[5]["name"],
        "tag_employees": tags[6]["name"],
        "tag_queues": tags[7]["name"],
        "tag_token": tags[8]["name"],
        "tag_cdr": tags[9]["name"],
        "tag_webhooks": tags[10]["name"],
        "tag_mcp": tags[11]["name"],
        "tag_campaigns": tags[12]["name"],
    }

    # 3. Path Operations
    paths = {
        "/clients/register/": {
            "post": {
                "tags": [tag_map["tag_clients"]],
                "summary": "تسجيل عميل فرعي جديد (Register Sub-Client)" if is_ar else "Register New Sub-Client",
                "description": (
                    "يسجل متجراً أو عميلاً فرعياً تابعاً لشركتك خلفياً ويعيد client_id لتقوم بتخزينه في قاعدة بياناتك."
                    if is_ar else
                    "Provisions a new tenant/client under your partner account and returns a unique client_id."
                ),
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ClientRegisterRequest"},
                            "example": {
                                "external_reference": "sub_store_9942",
                                "name": "متجر النور التجريبي" if is_ar else "Al-Noor Store Demo",
                                "email": "store9942@saas-demo.com",
                                "spending_cap": 25.0,
                                "minute_cap": 200
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "تم تسجيل العميل بنجاح" if is_ar else "Sub-client registered successfully",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ClientRegisterResponse"},
                                "example": {
                                    "status": "success",
                                    "client_id": 19,
                                    "name": "متجر النور التجريبي" if is_ar else "Al-Noor Store Demo",
                                    "external_reference": "sub_store_9942",
                                    "spending_cap": 25.0,
                                    "minute_cap": 200
                                }
                            }
                        }
                    },
                    "400": {"$ref": "#/components/responses/400Error"},
                    "403": {"$ref": "#/components/responses/403Error"}
                }
            }
        },
        "/clients/": {
            "get": {
                "tags": [tag_map["tag_clients"]],
                "summary": "عرض جميع العملاء الفرعيين (List Clients)" if is_ar else "List All Sub-Clients",
                "description": (
                    "استعراض قائمة كافة عملاء الساس التابعين للشريك وإحصائيات استهلاك وسقوف كل عميل."
                    if is_ar else
                    "Retrieves a list of all sub-clients registered under the partner with usage and cap statistics."
                ),
                "responses": {
                    "200": {
                        "description": "قائمة العملاء بنجاح" if is_ar else "Clients list retrieved successfully",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ClientListResponse"},
                                "example": {
                                    "status": "success",
                                    "total_clients": 1,
                                    "clients": [
                                        {
                                            "client_id": 19,
                                            "name": "متجر النور التجريبي" if is_ar else "Al-Noor Store Demo",
                                            "external_reference": "sub_store_9942",
                                            "spending_cap": 25.0,
                                            "minute_cap": 200,
                                            "total_spent": 0.06,
                                            "total_minutes": 2,
                                            "is_active": True
                                        }
                                    ]
                                }
                            }
                        }
                    },
                    "403": {"$ref": "#/components/responses/403Error"}
                }
            }
        },
        "/clients/cap/": {
            "post": {
                "tags": [tag_map["tag_clients"]],
                "summary": "تحديث سقف استهلاك العميل (Update Usage Cap)" if is_ar else "Update Client Usage Cap",
                "description": (
                    "تعديل سقف الرصيد المالي وسقف الدقائق لعميل فرعي معين لمنع تجاوز الميزانية."
                    if is_ar else
                    "Updates the dollar and minute consumption ceiling for a designated client."
                ),
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["client_id"],
                                "properties": {
                                    "client_id": {"type": "integer", "example": 19},
                                    "spending_cap": {"type": "number", "example": 50.0},
                                    "minute_cap": {"type": "integer", "example": 500}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "تم تحديث السقف بنجاح" if is_ar else "Cap updated successfully"},
                    "403": {"$ref": "#/components/responses/403Error"},
                    "404": {"$ref": "#/components/responses/404Error"}
                }
            }
        },
        "/studio/": {
            "get": {
                "tags": [tag_map["tag_profiles"]],
                "summary": "استوديو تخصيص الشخصية والأصوات للشريك (Partner Persona Studio)" if is_ar else "Voice & Persona Studio Metadata",
                "description": "استرجاع قائمة كافة أصوات Google الـ 30 واللغات الـ 11 واللهجات الـ 29 ونماذج الأدوار والأساليب." if is_ar else "Get full studio catalog: 30 Google HD voices, 11 languages, 29 dialects, and sample roles/styles.",
                "responses": {"200": {"description": "بيانات استوديو الشخصيات" if is_ar else "Persona studio metadata"}}
            }
        },
        "/clients/{client_id}/profiles/studio/": {
            "get": {
                "tags": [tag_map["tag_profiles"]],
                "summary": "استوديو تخصيص الشخصية لصالح عميل فرعي (Client Persona Studio)" if is_ar else "Client Voice & Persona Studio Metadata",
                "parameters": [{"$ref": "#/components/parameters/ClientId"}],
                "responses": {"200": {"description": "بيانات استوديو الشخصيات" if is_ar else "Persona studio metadata"}}
            }
        },
        "/clients/{client_id}/profiles/": {
            "get": {
                "tags": [tag_map["tag_profiles"]],
                "summary": "استعراض بروفايلات الصوت والشخصيات (List Profiles)" if is_ar else "List Voice Agent Profiles",
                "description": (
                    "استعراض جميع شخصيات الذكاء الاصطناعي مع إمكانية التصفية عبر ?is_active=true."
                    if is_ar else
                    "Lists all AI voice profiles for the client with optional active filter (?is_active=true)."
                ),
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {
                        "name": "is_active",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "boolean"},
                        "description": "تصفية البروفايلات النشطة فقط (true أو false)" if is_ar else "Filter active profiles only"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "قائمة البروفايلات" if is_ar else "Profiles list",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ProfileListResponse"}
                            }
                        }
                    },
                    "403": {"$ref": "#/components/responses/403Error"},
                    "404": {"$ref": "#/components/responses/404Error"}
                }
            },
            "post": {
                "tags": [tag_map["tag_profiles"]],
                "summary": "إنشاء بروفايل صوتي وشخصية جديدة (Create Profile)" if is_ar else "Create Voice Agent Profile",
                "description": (
                    "إنشاء بروفايل صوتي جديد بلهجة محددة (سعودي، مصري، شامي، فصحى، إنجليزي) وتعليمات مخصصة."
                    if is_ar else
                    "Provisions a customized AI voice persona with regional dialect and system prompt instructions."
                ),
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"}
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ProfileCreateRequest"},
                            "example": {
                                "name": "مساعد المبيعات السعودي" if is_ar else "Saudi Sales Advisor",
                                "voice_name": "Aoede",
                                "gender": "female",
                                "dialect": "saudi",
                                "persona_role": "sales_advisor",
                                "speaking_style": "friendly",
                                "custom_instructions": "أنت مستشار مبيعات ودود تتحدث باللهجة السعودية البيضاء وتقدم عروض المتجر." if is_ar else "You are a friendly sales advisor speaking Saudi dialect.",
                                "is_active": True
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "تم إنشاء البروفايل بنجاح" if is_ar else "Profile created successfully",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ProfileSingleResponse"}
                            }
                        }
                    },
                    "400": {"$ref": "#/components/responses/400Error"},
                    "403": {"$ref": "#/components/responses/403Error"}
                }
            }
        },
        "/clients/{client_id}/profiles/{profile_id}/": {
            "get": {
                "tags": [tag_map["tag_profiles"]],
                "summary": "جلب تفاصيل بروفايل صوتي (Retrieve Profile)" if is_ar else "Retrieve Voice Profile Details",
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"$ref": "#/components/parameters/ProfileId"}
                ],
                "responses": {
                    "200": {"description": "تفاصيل البروفايل" if is_ar else "Profile details"},
                    "404": {"$ref": "#/components/responses/404Error"}
                }
            },
            "patch": {
                "tags": [tag_map["tag_profiles"]],
                "summary": "تعديل بروفايل صوتي (Update Profile)" if is_ar else "Update Voice Profile",
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"$ref": "#/components/parameters/ProfileId"}
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ProfileUpdateRequest"},
                            "example": {
                                "name": "مستشار الدعم الفني المصري" if is_ar else "Egyptian Tech Consultant",
                                "dialect": "egyptian",
                                "voice_name": "Fenrir",
                                "speaking_style": "formal"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "تم تحديث البروفايل بنجاح" if is_ar else "Profile updated successfully"},
                    "404": {"$ref": "#/components/responses/404Error"}
                }
            },
            "delete": {
                "tags": [tag_map["tag_profiles"]],
                "summary": "حذف بروفايل صوتي (Delete Profile)" if is_ar else "Delete Voice Profile",
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"$ref": "#/components/parameters/ProfileId"}
                ],
                "responses": {
                    "200": {"description": "تم حذف البروفايل بنجاح" if is_ar else "Profile deleted successfully"},
                    "404": {"$ref": "#/components/responses/404Error"}
                }
            }
        },
        "/clients/{client_id}/profiles/{profile_id}/activate/": {
            "post": {
                "tags": [tag_map["tag_profiles"]],
                "summary": "تفعيل البروفايل الصوتي كافتراضي للمكالمات (Activate Profile)" if is_ar else "Set Profile as Active",
                "description": (
                    "يجعل هذا البروفايل هو الشخصية الافتراضية النشطة لجميع مكالمات العميل القادمة مع إلغاء تنشيط البقية."
                    if is_ar else
                    "Designates this profile as the sole active voice agent for all incoming and outbound calls."
                ),
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"$ref": "#/components/parameters/ProfileId"}
                ],
                "responses": {
                    "200": {"description": "تم تفعيل البروفايل بنجاح" if is_ar else "Profile activated successfully"},
                    "404": {"$ref": "#/components/responses/404Error"}
                }
            }
        },
        "/clients/{client_id}/memory/": {
            "get": {
                "tags": [tag_map["tag_crm"]],
                "summary": "استعراض ذاكرة وسياق العملاء مع البحث والترقيم (List/Search CRM Memories)" if is_ar else "List & Search CRM Memories",
                "description": (
                    "استرجاع بطاقات ذاكرة المتصلين مع دعم البحث بالاسم أو رقم الهاتف ?q= وبترقيم الصفحات ?page=1&limit=20."
                    if is_ar else
                    "Searches and paginates through CRM caller memories by name or phone (?q=, ?page=, ?limit=)."
                ),
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"name": "q", "in": "query", "schema": {"type": "string"}, "description": "بحث بالاسم أو الهاتف" if is_ar else "Search query by name or phone"},
                    {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 20}}
                ],
                "responses": {
                    "200": {
                        "description": "قائمة سجلات الذاكرة" if is_ar else "CRM memories list",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/MemoryListResponse"}
                            }
                        }
                    },
                    "404": {"$ref": "#/components/responses/404Error"}
                }
            },
            "post": {
                "tags": [tag_map["tag_crm"]],
                "summary": "إنشاء أو تحديث ذاكرة عميل بالهاتف (Upsert Memory)" if is_ar else "Create or Upsert Customer Memory",
                "description": (
                    "إنشاء بطاقة ذاكرة متصل جديدة أو تحديثها إذا كان رقم الهاتف مسجلاً مسبقاً (Upsert)."
                    if is_ar else
                    "Inserts or updates context data, notes, and profile attributes keyed by the customer phone number."
                ),
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"}
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/MemoryUpsertRequest"}
                        }
                    }
                },
                "responses": {
                    "200": {"description": "تم حفظ الذاكرة بنجاح" if is_ar else "Memory saved successfully"},
                    "201": {"description": "تم إنشاء الذاكرة بنجاح" if is_ar else "Memory created successfully"},
                    "400": {"$ref": "#/components/responses/400Error"}
                }
            }
        },
        "/clients/{client_id}/memory/{memory_id}/": {
            "get": {
                "tags": [tag_map["tag_crm"]],
                "summary": "جلب تفاصيل ذاكرة عميل محددة (Retrieve Memory)" if is_ar else "Retrieve Single Customer Memory",
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"$ref": "#/components/parameters/MemoryId"}
                ],
                "responses": {
                    "200": {"description": "تفاصيل الذاكرة" if is_ar else "Memory details"},
                    "404": {"$ref": "#/components/responses/404Error"}
                }
            },
            "put": {
                "tags": [tag_map["tag_crm"]],
                "summary": "تحديث بطاقة ذاكرة المتصل (Update Memory)" if is_ar else "Update Customer Memory",
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"$ref": "#/components/parameters/MemoryId"}
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/MemoryUpsertRequest"}
                        }
                    }
                },
                "responses": {
                    "200": {"description": "تم التحديث بنجاح" if is_ar else "Memory updated successfully"},
                    "404": {"$ref": "#/components/responses/404Error"}
                }
            },
            "delete": {
                "tags": [tag_map["tag_crm"]],
                "summary": "حذف بطاقة ذاكرة عميل (Delete Memory)" if is_ar else "Delete Customer Memory",
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"$ref": "#/components/parameters/MemoryId"}
                ],
                "responses": {
                    "200": {"description": "تم حذف سجل الذاكرة بنجاح" if is_ar else "Memory deleted successfully"},
                    "404": {"$ref": "#/components/responses/404Error"}
                }
            }
        },
        "/clients/{client_id}/documents/": {
            "get": {
                "tags": [tag_map["tag_rag"]],
                "summary": "استعراض مستندات قاعدة المعرفة (List Documents)" if is_ar else "List Knowledge Documents",
                "parameters": [{"$ref": "#/components/parameters/ClientId"}],
                "responses": {"200": {"description": "قائمة المستندات المفهرسة" if is_ar else "Indexed documents list"}}
            },
            "post": {
                "tags": [tag_map["tag_rag"]],
                "summary": "رفع مستند أو رابط وفهرسته بالمتجهات (Upload Document)" if is_ar else "Upload & Index Knowledge Document",
                "description": "فهرسة مستند حقيقي (PDF, DOCX, CSV, TXT, MD, JSON) عبر ملف مباشر، رابط خارجي (file_url)، أو نص مباشر ليتم استخراج النصوص وفهرستها دلالياً بالمتجهات عبر Gemini." if is_ar else "Upload a document file (PDF, DOCX, CSV, TXT, MD, JSON), pass a direct file_url, or raw text for semantic vector chunking & indexing.",
                "parameters": [{"$ref": "#/components/parameters/ClientId"}],
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
                                        "description": "ملف المستند المراد رفعه وفهرسته للعميل (PDF, DOCX, CSV, TXT, MD, JSON)" if is_ar else "Document file for sub-client (PDF, DOCX, CSV, TXT, MD, JSON)"
                                    },
                                    "file_url": {
                                        "type": "string",
                                        "description": "رابط مباشر لمستند خارجي (PDF, DOCX, CSV, TXT, MD, JSON)" if is_ar else "Direct public URL to document"
                                    },
                                    "title": {
                                        "type": "string",
                                        "description": "عنوان المستند (اختياري - يتم استخدام اسم الملف تلقائياً)" if is_ar else "Document title (optional - defaults to filename)"
                                    },
                                    "content": {
                                        "type": "string",
                                        "description": "نص مباشر كبديل في حال عدم إرفاق ملف أو رابط" if is_ar else "Raw text content as an alternative to file upload"
                                    }
                                }
                            }
                        },
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string", "example": "سياسة الاسترجاع والشحن" if is_ar else "Return & Shipping Policy"},
                                    "content": {"type": "string", "example": "يمكن استرجاع المنتجات خلال 14 يوماً من الاستلام بشرط حالتها الأصلية." if is_ar else "Products can be returned within 14 days of receipt."},
                                    "file_url": {"type": "string", "example": "https://example.com/company_policy.pdf"}
                                }
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "تمت الفهرسة بنجاح" if is_ar else "Document indexed successfully"}}
            }
        },
        "/clients/{client_id}/rag/query/": {
            "post": {
                "tags": [tag_map["tag_rag"]],
                "summary": "استعلام دلالي ذكي في قاعدة المعرفة (Semantic RAG Query)" if is_ar else "Semantic RAG Search Query",
                "description": "يبحث دلالياً عن أقرب المقاطع صلة بالسؤال باستخدام تشابه الجيب تماماً (Cosine Similarity) في pgvector." if is_ar else "Performs semantic vector cosine-similarity search against indexed client documents.",
                "parameters": [{"$ref": "#/components/parameters/ClientId"}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["query"],
                                "properties": {
                                    "query": {"type": "string", "example": "ما هي مهلة إرجاع المنتجات؟" if is_ar else "What is the return policy window?"},
                                    "top_k": {"type": "integer", "default": 3, "example": 3}
                                }
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "نتائج البحث الدلالي مع درجات التشابه" if is_ar else "Semantic search matches with similarity scores"}}
            }
        },
        "/clients/{client_id}/telephony/": {
            "get": {
                "tags": [tag_map["tag_telephony"]],
                "summary": "عرض السنترالات والخطوط المربوطة (List Trunks)" if is_ar else "List Telephony & PBX Trunks",
                "parameters": [{"$ref": "#/components/parameters/ClientId"}],
                "responses": {"200": {"description": "قائمة السنترالات والخطوط" if is_ar else "Trunks and PBX configurations"}}
            },
            "post": {
                "tags": [tag_map["tag_telephony"]],
                "summary": "ربط سنترال PBX أو خط خارجي (Register Trunk)" if is_ar else "Register PBX or SIP Trunk",
                "parameters": [{"$ref": "#/components/parameters/ClientId"}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["trunk_type", "name", "host"],
                                "properties": {
                                    "trunk_type": {"type": "string", "enum": ["pbx", "sip"], "example": "pbx"},
                                    "name": {"type": "string", "example": "Issabel Main PBX"},
                                    "host": {"type": "string", "example": "192.168.1.100"},
                                    "port": {"type": "integer", "default": 5060},
                                    "username": {"type": "string", "example": "1001"},
                                    "secret": {"type": "string", "example": "TrunkSecret123"},
                                    "is_active": {"type": "boolean", "default": True}
                                }
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "تم الربط بنجاح" if is_ar else "Trunk registered successfully"}}
            }
        },
        "/clients/{client_id}/telephony/numbers/": {
            "get": {
                "tags": [tag_map["tag_telephony"]],
                "summary": "عرض أرقام الـ DID المرتبطة (List DIDs)" if is_ar else "List DID Phone Numbers",
                "parameters": [{"$ref": "#/components/parameters/ClientId"}],
                "responses": {"200": {"description": "قائمة الأرقام" if is_ar else "DID phone numbers list"}}
            },
            "post": {
                "tags": [tag_map["tag_telephony"]],
                "summary": "ربط رقم هاتف بالسنترال (Assign DID)" if is_ar else "Assign Phone Number to PBX",
                "parameters": [{"$ref": "#/components/parameters/ClientId"}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["phone_number", "pbx_trunk_id"],
                                "properties": {
                                    "phone_number": {"type": "string", "example": "+966112233445"},
                                    "pbx_trunk_id": {"type": "integer", "example": 1},
                                    "description": {"type": "string", "example": "الرقم الموحد الرئيسي للفرع" if is_ar else "Main office incoming hotline"}
                                }
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "تم ربط الرقم بنجاح" if is_ar else "Number assigned successfully"}}
            }
        },
        "/clients/{client_id}/telephony/{trunk_type}/{trunk_id}/": {
            "delete": {
                "tags": [tag_map["tag_telephony"]],
                "summary": "حذف خط أو سنترال مربوط (Delete Trunk)" if is_ar else "Delete Telephony Trunk",
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"name": "trunk_type", "in": "path", "required": True, "schema": {"type": "string", "enum": ["pbx", "sip"]}},
                    {"name": "trunk_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                ],
                "responses": {"200": {"description": "تم حذف الخط بنجاح" if is_ar else "Trunk deleted successfully"}}
            }
        },
        "/clients/{client_id}/employees/": {
            "get": {
                "tags": [tag_map["tag_employees"]],
                "summary": "عرض دليل موظفي العميل (List Employees)" if is_ar else "List Client Employees",
                "parameters": [{"$ref": "#/components/parameters/ClientId"}],
                "responses": {"200": {"description": "قائمة الموظفين والتحويلات" if is_ar else "Employee directory and extensions"}}
            },
            "post": {
                "tags": [tag_map["tag_employees"]],
                "summary": "إضافة موظف جديد للعميل (Create Employee)" if is_ar else "Create Employee",
                "parameters": [{"$ref": "#/components/parameters/ClientId"}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["name", "extension"],
                                "properties": {
                                    "name": {"type": "string", "example": "محمد السعيد" if is_ar else "Mohammed Saeed"},
                                    "extension": {"type": "string", "example": "104"},
                                    "department": {"type": "string", "example": "المبيعات" if is_ar else "Sales"},
                                    "email": {"type": "string", "example": "m.saeed@sub-client.com"},
                                    "status": {"type": "string", "enum": ["ready", "busy", "offline"], "default": "ready"}
                                }
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "تم إنشاء الموظف بنجاح" if is_ar else "Employee created successfully"}}
            }
        },
        "/clients/{client_id}/employees/{employee_id}/": {
            "get": {
                "tags": [tag_map["tag_employees"]],
                "summary": "جلب بيانات موظف (Retrieve Employee)" if is_ar else "Retrieve Employee Details",
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"$ref": "#/components/parameters/EmployeeId"}
                ],
                "responses": {"200": {"description": "بيانات الموظف" if is_ar else "Employee details"}}
            },
            "patch": {
                "tags": [tag_map["tag_employees"]],
                "summary": "تعديل بيانات موظف أو حالته (Update Employee)" if is_ar else "Update Employee Details/Status",
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"$ref": "#/components/parameters/EmployeeId"}
                ],
                "responses": {"200": {"description": "تم التحديث بنجاح" if is_ar else "Employee updated successfully"}}
            },
            "delete": {
                "tags": [tag_map["tag_employees"]],
                "summary": "حذف موظف (Delete Employee)" if is_ar else "Delete Employee",
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"$ref": "#/components/parameters/EmployeeId"}
                ],
                "responses": {"200": {"description": "تم حذف الموظف بنجاح" if is_ar else "Employee deleted successfully"}}
            }
        },
        "/clients/{client_id}/queues/": {
            "get": {
                "tags": [tag_map["tag_queues"]],
                "summary": "عرض طوابير الانتظار للعميل (List Queues)" if is_ar else "List Call Center Queues",
                "parameters": [{"$ref": "#/components/parameters/ClientId"}],
                "responses": {"200": {"description": "قائمة الطوابير وأعضائها" if is_ar else "Queues list and active members"}}
            },
            "post": {
                "tags": [tag_map["tag_queues"]],
                "summary": "إنشاء طابور انتظار جديد (Create Queue)" if is_ar else "Create Call Queue",
                "parameters": [{"$ref": "#/components/parameters/ClientId"}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["name"],
                                "properties": {
                                    "name": {"type": "string", "example": "طابور خدمة العملاء الرئيسي" if is_ar else "Main Support Queue"},
                                    "strategy": {"type": "string", "enum": ["round_robin", "least_recent", "random"], "default": "round_robin"},
                                    "timeout_seconds": {"type": "integer", "default": 30}
                                }
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "تم إنشاء الطابور بنجاح" if is_ar else "Queue created successfully"}}
            }
        },
        "/clients/{client_id}/queues/{queue_id}/": {
            "get": {
                "tags": [tag_map["tag_queues"]],
                "summary": "جلب تفاصيل طابور انتظار (Retrieve Queue)" if is_ar else "Retrieve Queue Details",
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"$ref": "#/components/parameters/QueueId"}
                ],
                "responses": {"200": {"description": "تفاصيل الطابور" if is_ar else "Queue details"}}
            },
            "delete": {
                "tags": [tag_map["tag_queues"]],
                "summary": "حذف طابور انتظار (Delete Queue)" if is_ar else "Delete Queue",
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"$ref": "#/components/parameters/QueueId"}
                ],
                "responses": {"200": {"description": "تم حذف الطابور بنجاح" if is_ar else "Queue deleted successfully"}}
            }
        },
        "/clients/{client_id}/queues/{queue_id}/members/": {
            "get": {
                "tags": [tag_map["tag_queues"]],
                "summary": "عرض أعضاء طابور الانتظار (List Members)" if is_ar else "List Queue Members",
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"$ref": "#/components/parameters/QueueId"}
                ],
                "responses": {"200": {"description": "قائمة الموظفين في الطابور" if is_ar else "Assigned employee members"}}
            },
            "post": {
                "tags": [tag_map["tag_queues"]],
                "summary": "إضافة موظف إلى طابور الانتظار (Add Member)" if is_ar else "Add Member to Queue",
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"$ref": "#/components/parameters/QueueId"}
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["employee_id"],
                                "properties": {
                                    "employee_id": {"type": "integer", "example": 1},
                                    "penalty": {"type": "integer", "default": 0}
                                }
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "تمت إضافة الموظف للطابور" if is_ar else "Member added to queue"}}
            }
        },
        "/clients/{client_id}/token/": {
            "post": {
                "tags": [tag_map["tag_token"]],
                "summary": "إصدار توكن اتصال WebRTC فوري (Generate Voice Token)" if is_ar else "Generate WebRTC Voice Session Token",
                "description": (
                    "ينشئ غرفة LiveKit وتوكن وصول JWT مشفر ليتصل المتصفح أو التطبيق مباشرة بالمساعد الذكي للعميل مع روابط خادم LiveKit ورابط Centrifugo WebSocket.\n\n"
                    "**طريقة الاتصال المباشر (LiveKit SDK Quickstart):**\n"
                    "```javascript\n"
                    "import { Room } from 'livekit-client';\n\n"
                    "const room = new Room();\n"
                    "await room.connect(response.livekit_url, response.token);\n"
                    "await room.localParticipant.setMicrophoneEnabled(true);\n"
                    "```"
                    if is_ar else
                    "Generates an ephemeral JWT token and WebSocket connection URLs for connecting browser or mobile client to a LiveKit voice room."
                ),
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"}
                ],
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "participant_name": {"type": "string", "example": "متسوق المتجر" if is_ar else "Online Shopper"},
                                    "caller_phone": {"type": "string", "example": "+966551122334"}
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
                                    "room_name": "partner_1_19_a8b7c6",
                                    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                    "livekit_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                    "livekit_url": "wss://livekit.169.58.32.179.nip.io",
                                    "centrifugo_ws_url": "wss://centrifugo.169.58.32.179.nip.io/connection/websocket",
                                    "centrifugo_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                    "channel": "partner_1_19_a8b7c6",
                                    "client_id": 19
                                }
                            }
                        }
                    }
                }
            }
        },
        "/clients/{client_id}/calls/": {
            "get": {
                "tags": [tag_map["tag_cdr"]],
                "summary": "استعراض سجلات مكالمات العميل CDR (List Call Logs)" if is_ar else "List Client Call Logs (CDR)",
                "description": (
                    "يعيد قائمة مكالمات العميل الفرعي مع مدة كل مكالمة، الدقائق المفوترة، تكلفة المكالمة، والملخص الذكي."
                    if is_ar else
                    "Returns call records including duration, billed wholesale minutes, cost, and AI summaries."
                ),
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"}
                ],
                "responses": {
                    "200": {
                        "description": "قائمة السجلات بنجاح" if is_ar else "CDR records list",
                        "content": {
                            "application/json": {
                                "example": {
                                    "status": "success",
                                    "client_id": 19,
                                    "calls_count": 1,
                                    "calls": [
                                        {
                                            "call_id": "partner_1_19_a8b7c6",
                                            "direction": "inbound",
                                            "caller_phone": "+966551122334",
                                            "started_at": "2026-09-23 11:45:00",
                                            "duration_seconds": 65,
                                            "billed_minutes": 2,
                                            "cost": 0.06,
                                            "summary": "استفسر العميل عن المنتجات المتوفرة وتم الرد عليه بالكامل." if is_ar else "Customer inquired about available stock."
                                        }
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        },
        "/clients/{client_id}/calls/dial/": {
            "post": {
                "tags": [tag_map["tag_cdr"]],
                "summary": "إجراء مكالمة صادرة بالذكاء الاصطناعي لعميل فرعي (Autonomous Outbound Dialing for Sub-Client)" if is_ar else "Initiate Autonomous Outbound AI Phone Call for Sub-Client",
                "description": (
                    "توجيه روبوت الصوت الذكي لإجراء اتصال هاتفي صادر لصالح هذا العميل الفرعي مع مراقبة سقف الاستهلاك (Spending/Minute Cap) وخصم الدقائق بسعر الجملة من محفظة الشريك المركزية. يدعم السنترالات السحابية والمحلية والتحويلات الداخلية."
                    if is_ar else
                    "Trigger an autonomous outbound phone call on behalf of a sub-client with strict spending/minute cap enforcement and wholesale rate deduction from the partner's central wallet. Supports external E.164 numbers and PBX extensions."
                ),
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"}
                ],
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
                                        "example": "+966551122334",
                                        "description": "رقم هاتف العميل بالصيغة الدولية أو تحويلة PBX (مثال: 101)" if is_ar else "Destination E.164 phone number or PBX extension (e.g. 101)"
                                    },
                                    "call_goal": {
                                        "type": "string",
                                        "example": "الاتصال بالعميل لتأكيد تفاصيل الشحنة واستلام الطلب #5502" if is_ar else "Call customer to verify shipment details for order #5502",
                                        "description": "الهدف أو التعليمات الفورية الموجهة للمساعد الصوتي للمكالمة الصادرة" if is_ar else "Goal or directive given to the AI voice agent for this outbound call"
                                    },
                                    "profile_id": {
                                        "type": "integer",
                                        "example": 3,
                                        "description": "معرف البروفايل الصوتي للعميل (اختياري - يستخدم الافتراضي)" if is_ar else "Client voice profile ID (optional - defaults to active profile)"
                                    },
                                    "gateway_type": {
                                        "type": "string",
                                        "enum": ["auto", "pbx", "cloud"],
                                        "default": "auto",
                                        "description": "مسار الاتصال: auto (تلقائي)، pbx (سنترال محلي)، cloud (جذع سحابي)" if is_ar else "Dialing gateway: auto, pbx, or cloud"
                                    },
                                    "gateway_id": {
                                        "type": "integer",
                                        "example": 1,
                                        "description": "معرف السنترال المحدد عند اختيار pbx" if is_ar else "Specific PBX trunk ID when gateway_type is pbx"
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "تم بدء المكالمة الصادرة بنجاح" if is_ar else "Outbound call initiated successfully",
                        "content": {
                            "application/json": {
                                "example": {
                                    "status": "success",
                                    "message": "تم بدء الاتصال الصادر بالرقم +966551122334 بنجاح عبر سنترال الشريك (افتراضي)" if is_ar else "Sub-client AI outbound call initiated successfully",
                                    "client_id": 19,
                                    "call_id": "partner_1_19_ai_out_fa7b2c",
                                    "room_name": "partner_1_19_ai_out_fa7b2c",
                                    "session_id": 490,
                                    "destination_phone": "+966551122334",
                                    "call_goal": "الاتصال بالعميل لتأكيد تفاصيل الشحنة واستلام الطلب #5502",
                                    "trunk_name": "جذع الشريك Telnyx Primary",
                                    "gateway_used": "جذع الشريك Telnyx Primary",
                                    "caller_id": "+966112233445"
                                }
                            }
                        }
                    },
                    "400": {"description": "بيانات الاتصال غير صالحة أو رقم الهاتف مفقود" if is_ar else "Missing or invalid phone number"},
                    "402": {"description": "رصيد محفظة الشريك غير كافٍ" if is_ar else "Partner balance insufficient"},
                    "403": {"description": "تم تجاوز سقف الاستهلاك المحدد للعميل الفرعي" if is_ar else "Client spending or minute cap exceeded"},
                    "422": {"description": "لا يوجد مسار اتصال صادر مفعل" if is_ar else "No active outbound route configured"}
                }
            }
        },
        "/clients/{client_id}/calls/hangup/": {
            "post": {
                "tags": [tag_map["tag_cdr"]],
                "summary": "إنهاء مكالمة جارية لعميل فرعي (Hangup Client Call)" if is_ar else "Hang Up Client Call Session",
                "parameters": [{"$ref": "#/components/parameters/ClientId"}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["call_id"],
                                "properties": {
                                    "call_id": {"type": "string", "example": "partner_1_19_ai_out_fa7b2c", "description": "معرف المكالمة أو اسم الغرفة"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "تم إنهاء المكالمة بنجاح" if is_ar else "Call terminated successfully"}
                }
            }
        },
        "/settings/test-webhook/": {
            "post": {
                "tags": [tag_map["tag_webhooks"]],
                "summary": "اختبار إرسال حدث ويبهوك تجريبي (Test Webhook & HMAC)" if is_ar else "Test Webhook & HMAC Dispatch",
                "description": (
                    "يرسل حدث call.completed تجريبي مشفر بتوقيع HMAC-SHA256 إلى رابط الويبهوك المسجل في إعدادات الشريك."
                    if is_ar else
                    "Triggers a mock call.completed event with HMAC-SHA256 signature to the registered partner webhook."
                ),
                "responses": {
                    "200": {
                        "description": "نتيجة إرسال الويبهوك" if is_ar else "Webhook delivery response",
                        "content": {
                            "application/json": {
                                "example": {
                                    "status": "success",
                                    "message": "Webhook test sent successfully (HTTP 200 OK)"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/clients/{client_id}/mcp/": {
            "get": {
                "tags": [tag_map["tag_mcp"]],
                "summary": "استعراض خوادم FastMCP للعميل الفرعي (List Client MCP Servers)" if is_ar else "List Client FastMCP Servers",
                "description": (
                    "يعيد قائمة خوادم FastMCP المخصصة لهذا العميل مع الأدوات المتزامنة، بالإضافة إلى خادم الشريك المشترك إن وُجد."
                    if is_ar else
                    "Returns all FastMCP servers attached to this sub-client plus the partner shared fallback server."
                ),
                "parameters": [{"$ref": "#/components/parameters/ClientId"}],
                "responses": {
                    "200": {
                        "description": "قائمة خوادم MCP للعميل" if is_ar else "Client MCP servers list",
                        "content": {
                            "application/json": {
                                "example": {
                                    "status": "success",
                                    "client_id": 19,
                                    "total_servers": 1,
                                    "partner_shared_server": None,
                                    "servers": [
                                        {
                                            "id": 1,
                                            "name": "خادم المتجر والطلبات (FastMCP)",
                                            "server_url": "http://mock-store:8002/sse",
                                            "is_active": True,
                                            "tools_count": 2,
                                            "cached_tools": [
                                                {"name": "check_order_status", "description": "تحقق من حالة الطلب"},
                                                {"name": "check_product_inventory", "description": "التحقق من المخزون"}
                                            ],
                                            "last_synced_at": "2026-09-23 12:00:00"
                                        }
                                    ]
                                }
                            }
                        }
                    }
                }
            },
            "post": {
                "tags": [tag_map["tag_mcp"]],
                "summary": "إضافة خادم FastMCP جديد للعميل الفرعي (Create Client MCP Server)" if is_ar else "Create Client FastMCP Server",
                "description": (
                    "يربط خادم أدوات FastMCP خارجي (عبر بروتوكول SSE) بهذا العميل ليستخدمه المساعد الصوتي أثناء المكالمات."
                    if is_ar else
                    "Connects an external FastMCP SSE tool server to this client for live AI function calling during calls."
                ),
                "parameters": [{"$ref": "#/components/parameters/ClientId"}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["server_url"],
                                "properties": {
                                    "name": {"type": "string", "example": "متجر سلة - أدوات المنتجات"},
                                    "server_url": {"type": "string", "example": "http://mock-store:8002/sse"},
                                    "auth_token": {"type": "string", "example": "Bearer salla_sec_xxx"},
                                    "is_active": {"type": "boolean", "default": True},
                                    "sync_now": {"type": "boolean", "default": True}
                                }
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "تم إنشاء خادم MCP ومزامنة الأدوات" if is_ar else "MCP server created and tools synced"}}
            }
        },
        "/clients/{client_id}/mcp/{mcp_id}/": {
            "get": {
                "tags": [tag_map["tag_mcp"]],
                "summary": "جلب تفاصيل خادم FastMCP محدد (Get Client MCP Server)" if is_ar else "Get Client FastMCP Server",
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"$ref": "#/components/parameters/McpId"}
                ],
                "responses": {"200": {"description": "تفاصيل خادم FastMCP والأدوات" if is_ar else "MCP server details"}}
            },
            "patch": {
                "tags": [tag_map["tag_mcp"]],
                "summary": "تعديل بيانات خادم FastMCP للعميل (Update Client MCP Server)" if is_ar else "Update Client FastMCP Server",
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"$ref": "#/components/parameters/McpId"}
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "server_url": {"type": "string"},
                                    "auth_token": {"type": "string"},
                                    "is_active": {"type": "boolean"}
                                }
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "تم التحديث بنجاح" if is_ar else "Updated successfully"}}
            },
            "delete": {
                "tags": [tag_map["tag_mcp"]],
                "summary": "حذف خادم FastMCP للعميل (Delete Client MCP Server)" if is_ar else "Delete Client FastMCP Server",
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"$ref": "#/components/parameters/McpId"}
                ],
                "responses": {"200": {"description": "تم حذف الخادم بنجاح" if is_ar else "Deleted successfully"}}
            }
        },
        "/clients/{client_id}/mcp/{mcp_id}/sync/": {
            "post": {
                "tags": [tag_map["tag_mcp"]],
                "summary": "مزامنة الأدوات الحية فورياً عبر SSE (Sync Client MCP Tools)" if is_ar else "Sync Client FastMCP Tools via SSE",
                "description": (
                    "يتصل مباشرة برابط SSE لخادم FastMCP، ويستكشف الأدوات الحية وقوالب المدخلات، ويحدث قاعدة البيانات."
                    if is_ar else
                    "Performs an immediate SSE handshake to discover tools and schema signatures for this client's agent."
                ),
                "parameters": [
                    {"$ref": "#/components/parameters/ClientId"},
                    {"$ref": "#/components/parameters/McpId"}
                ],
                "responses": {
                    "200": {
                        "description": "تمت المزامنة بنجاح" if is_ar else "Tools synchronized successfully",
                        "content": {
                            "application/json": {
                                "example": {
                                    "status": "success",
                                    "message": "Successfully synchronized 2 tools from FastMCP server via SSE.",
                                    "client_id": 19,
                                    "mcp_id": 1,
                                    "server_name": "خادم المتجر والطلبات (FastMCP)",
                                    "tools_count": 2,
                                    "tools": [
                                        {"name": "check_order_status", "description": "التحقق من حالة الطلب برقم الطلب"},
                                        {"name": "check_product_inventory", "description": "التحقق من كميات المخزون"}
                                    ],
                                    "synced_at": "2026-09-23 12:00:00"
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    # 4. Parameters & Schemas
    components = {
        "securitySchemes": {
            "PartnerKey": {
                "type": "apiKey",
                "in": "header",
                "name": "X-Partner-Key",
                "description": (
                    "مفتاح الشريك السري (يبدأ بـ sk_live_prt_...). يجب تمريره في كل طلب."
                    if is_ar else
                    "Partner secret API key (starts with sk_live_prt_...). Required on all requests."
                )
            }
        },
        "parameters": {
            "ClientId": {
                "name": "client_id",
                "in": "path",
                "required": True,
                "schema": {"type": "integer"},
                "description": "المعرف الرقمي للعميل الفرعي (client_id)" if is_ar else "Numerical ID of the sub-client"
            },
            "McpId": {
                "name": "mcp_id",
                "in": "path",
                "required": True,
                "schema": {"type": "integer"},
                "description": "المعرف الرقمي لخادم FastMCP" if is_ar else "Numerical ID of the FastMCP server"
            },
            "ProfileId": {
                "name": "profile_id",
                "in": "path",
                "required": True,
                "schema": {"type": "integer"},
                "description": "المعرف الرقمي لبروفايل الصوت" if is_ar else "Numerical ID of the voice profile"
            },
            "MemoryId": {
                "name": "memory_id",
                "in": "path",
                "required": True,
                "schema": {"type": "integer"},
                "description": "المعرف الرقمي لسجل ذاكرة العميل" if is_ar else "Numerical ID of the customer memory record"
            },
            "EmployeeId": {
                "name": "employee_id",
                "in": "path",
                "required": True,
                "schema": {"type": "integer"},
                "description": "المعرف الرقمي للموظف" if is_ar else "Numerical ID of the employee"
            },
            "QueueId": {
                "name": "queue_id",
                "in": "path",
                "required": True,
                "schema": {"type": "integer"},
                "description": "المعرف الرقمي لطابور الانتظار" if is_ar else "Numerical ID of the queue"
            }
        },
        "responses": {
            "400Error": {
                "description": "طلب غير صالح (Bad Request)" if is_ar else "Bad Request",
                "content": {
                    "application/json": {
                        "example": {"status": "error", "message": "Invalid JSON body"}
                    }
                }
            },
            "403Error": {
                "description": "غير مصرح (مفتاح الشريك غير صالح أو غير مصرح له بهذا العميل)" if is_ar else "Forbidden / Invalid partner API key",
                "content": {
                    "application/json": {
                        "example": {"status": "error", "message": "Invalid partner API key"}
                    }
                }
            },
            "404Error": {
                "description": "العنصر غير موجود (Not Found)" if is_ar else "Resource Not Found",
                "content": {
                    "application/json": {
                        "example": {"status": "error", "message": "Resource not found"}
                    }
                }
            }
        },
        "schemas": {
            "ClientRegisterRequest": {
                "type": "object",
                "required": ["external_reference", "name"],
                "properties": {
                    "external_reference": {"type": "string", "example": "sub_store_9942"},
                    "name": {"type": "string", "example": "متجر النور التجريبي" if is_ar else "Al-Noor Store Demo"},
                    "email": {"type": "string", "format": "email", "example": "store9942@saas-demo.com"},
                    "spending_cap": {"type": "number", "default": 10.0, "example": 25.0},
                    "minute_cap": {"type": "integer", "default": 60, "example": 200}
                }
            },
            "ClientRegisterResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "success"},
                    "client_id": {"type": "integer", "example": 19},
                    "name": {"type": "string", "example": "متجر النور التجريبي" if is_ar else "Al-Noor Store Demo"},
                    "external_reference": {"type": "string", "example": "sub_store_9942"},
                    "spending_cap": {"type": "number", "example": 25.0},
                    "minute_cap": {"type": "integer", "example": 200}
                }
            },
            "ClientListResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "success"},
                    "total_clients": {"type": "integer", "example": 1},
                    "clients": {
                        "type": "array",
                        "items": {"type": "object"}
                    }
                }
            },
            "ProfileCreateRequest": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string", "example": "مساعد المبيعات السعودي" if is_ar else "Saudi Sales Advisor"},
                    "voice_name": {"type": "string", "default": "Aoede", "example": "Aoede"},
                    "gender": {"type": "string", "enum": ["female", "male"], "default": "female"},
                    "language": {"type": "string", "default": "arabic", "example": "arabic"},
                    "dialect": {"type": "string", "default": "saudi", "example": "saudi"},
                    "persona_role": {"type": "string", "description": "الدور والشخصية بكتابة حرة", "example": "ممثل خدمة عملاء محترف"},
                    "speaking_style": {"type": "string", "description": "أسلوب الإلقاء والنبرة بكتابة حرة", "example": "ودود ولطيف ومرح"},
                    "verbosity": {"type": "string", "enum": ["concise", "balanced", "detailed"], "default": "balanced", "description": "مستوى الإيجاز وسرعة الرد: concise (مختصر), balanced (متوازن), detailed (مفصل)", "example": "concise"},
                    "custom_instructions": {"type": "string", "example": "أنت مستشار مبيعات ودود تتحدث باللهجة السعودية البيضاء." if is_ar else "You are a friendly sales advisor speaking in Saudi dialect."},
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
            "ProfileSingleResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "success"},
                    "message": {"type": "string", "example": "Agent profile created successfully"},
                    "client_id": {"type": "integer", "example": 19},
                    "profile": {"type": "object"}
                }
            },
            "ProfileListResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "success"},
                    "client_id": {"type": "integer", "example": 19},
                    "total": {"type": "integer", "example": 2},
                    "active_profile": {"type": "object"},
                    "profiles": {"type": "array", "items": {"type": "object"}}
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
                        "example": {
                            "city": "الرياض" if is_ar else "Riyadh",
                            "vip_tier": "Gold",
                            "notes": "يفضل الشحن السريع بالصباح" if is_ar else "Prefers morning express delivery"
                        }
                    },
                    "immediate_notes": {"type": "string", "example": "استفسر عن كود الخصم وتم إرساله له بنجاح" if is_ar else "Inquired about coupon code, delivered successfully"},
                    "total_calls_count": {"type": "integer", "example": 3}
                }
            },
            "MemoryListResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "success"},
                    "client_id": {"type": "integer", "example": 19},
                    "total": {"type": "integer", "example": 12},
                    "page": {"type": "integer", "example": 1},
                    "limit": {"type": "integer", "example": 20},
                    "total_pages": {"type": "integer", "example": 1},
                    "memories": {"type": "array", "items": {"type": "object"}}
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
                "description": "خادم الواجهة البرمجية للشريك" if is_ar else "Partner SaaS API Server"
            }
        ],
        "security": [
            {"PartnerKey": []}
        ],
        "tags": tags,
        "paths": paths,
        "components": components
    }
