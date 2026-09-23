"""
OpenAPI 3.1 Specification for Headless B2B Voice SaaS Partner API.
Covers all 11 documentation sections with complete schemas, realistic examples, and security definitions.
"""

def get_partner_openapi_spec(server_url: str = "/api/partner/v1") -> dict:
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "منظومة المساعد الصوتي للشركاء (Voice SaaS Partner API)",
            "version": "1.0.0",
            "description": (
                "دليل تكامل واجهات الشركاء وخدمات الـ SaaS (Headless Architecture). "
                "يتيح لك هذا الـ API بناء وتضمين خدمة المساعد الصوتي الذكي داخل تطبيقك أو متجرك "
                "أو نظامك السحابي دون أن يرى عميلك واجهتنا مطلقاً (White-Label). "
                "تتم محاسبتك بسعر الجملة المخفض المخصص لك بخصم مباشر من محفظتك المركزية مع التقريب الصارم لأعلى دقيقة."
            ),
            "contact": {
                "name": "فريق الدعم الفني للمنظومة",
                "url": "https://localhost/api/partner/v1/docs/"
            }
        },
        "servers": [
            {
                "url": server_url,
                "description": "خادم الواجهة البرمجية للشريك"
            }
        ],
        "security": [
            {"PartnerKey": []}
        ],
        "tags": [
            {
                "name": "1. نظرة عامة والمصادقة",
                "description": "طريقة المصادقة عبر هيدر X-Partner-Key وسياسة الفوترة والأسعار المخفضة."
            },
            {
                "name": "2. تسجيل وإدارة العملاء",
                "description": "تسجيل المتاجر والعملاء الفرعيين وضبط سقوف الاستهلاك والدقائق."
            },
            {
                "name": "3. الصوت واللهجات والشخصيات",
                "description": "إدارة بروفايلات الذكاء الاصطناعي، اللهجات (سعودي، مصري، شامي، فصحى)، وتفعيل الشخصيات."
            },
            {
                "name": "4. ذاكرة وسياق العملاء CRM",
                "description": "سجلات الذاكرة التراكمية، ملاحظات المكالمات، والاستعلام برقم هاتف المتصل مع الترقيم والبحث."
            },
            {
                "name": "5. قواعد المعرفة والاستعلام الدلالي RAG",
                "description": "رفع المستندات وفهرستها دلالياً بالمتجهات (pgvector) والبحث الذكي عبر Gemini."
            },
            {
                "name": "6. السنترالات والخطوط والأرقام",
                "description": "ربط سنترالات PBX (Issabel)، خطوط SIP الصادرة، وربط أرقام الـ DIDs."
            },
            {
                "name": "7. دليل الموظفين والتحويلات",
                "description": "إدارة الموظفين والتحويلات الداخلية للعميل وحالات التوفر (Ready, Busy, Offline)."
            },
            {
                "name": "8. طوابير الانتظار والأعضاء",
                "description": "طوابير الكول سنتر واستراتيجيات التوزيع (Round Robin) وإدارة الأعضاء."
            },
            {
                "name": "9. بدء مكالمة WebRTC",
                "description": "إصدار توكنات LiveKit المشفرة لبدء المكالمة الصوتية الفورية في المتصفح أو التطبيق."
            },
            {
                "name": "10. سجلات المكالمات والفوترة",
                "description": "استعراض سجلات المكالمات CDR، الدقائق المفوترة، تكلفة المكالمة، وملخصات المحادثة."
            },
            {
                "name": "11. الويبهوك والتوقيع المشفر",
                "description": "استقبال إشعارات انتهاء المكالمات والتحقق البرمجي من توقيع HMAC-SHA256."
            }
        ],
        "paths": {
            "/clients/register/": {
                "post": {
                    "tags": ["2. تسجيل وإدارة العملاء"],
                    "summary": "تسجيل عميل فرعي جديد (Register Sub-Client)",
                    "description": "يسجل متجراً أو عميلاً فرعياً تابعاً لشركتك خلفياً ويعيد client_id لتقوم بتخزينه في قاعدة بياناتك.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ClientRegisterRequest"},
                                "example": {
                                    "external_reference": "sub_store_9942",
                                    "name": "متجر النور التجريبي",
                                    "email": "store9942@saas-demo.com",
                                    "spending_cap": 25.0,
                                    "minute_cap": 200
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "تم تسجيل العميل بنجاح",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ClientRegisterResponse"},
                                    "example": {
                                        "status": "success",
                                        "client_id": 19,
                                        "name": "متجر النور التجريبي",
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
                    "tags": ["2. تسجيل وإدارة العملاء"],
                    "summary": "عرض جميع العملاء الفرعيين (List Clients)",
                    "description": "استعراض قائمة كافة عملاء الساس التابعين للشريك وإحصائيات استهلاك وسقوف كل عميل.",
                    "responses": {
                        "200": {
                            "description": "قائمة العملاء بنجاح",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ClientListResponse"},
                                    "example": {
                                        "status": "success",
                                        "total_clients": 1,
                                        "clients": [
                                            {
                                                "client_id": 19,
                                                "name": "متجر النور التجريبي",
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
                    "tags": ["2. تسجيل وإدارة العملاء"],
                    "summary": "تحديث سقف استهلاك العميل (Update Usage Cap)",
                    "description": "تعديل سقف الرصيد المالي وسقف الدقائق لعميل فرعي معين لمنع تجاوز الميزانية.",
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
                        "200": {"description": "تم تحديث السقف بنجاح"},
                        "403": {"$ref": "#/components/responses/403Error"},
                        "404": {"$ref": "#/components/responses/404Error"}
                    }
                }
            },
            "/clients/{client_id}/profiles/": {
                "get": {
                    "tags": ["3. الصوت واللهجات والشخصيات"],
                    "summary": "استعراض بروفايلات الصوت والشخصيات (List Profiles)",
                    "description": "استعراض جميع شخصيات الذكاء الاصطناعي مع إمكانية التصفية عبر ?is_active=true.",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"},
                        {
                            "name": "is_active",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "boolean"},
                            "description": "تصفية البروفايلات النشطة فقط (true أو false)"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "قائمة البروفايلات",
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
                    "tags": ["3. الصوت واللهجات والشخصيات"],
                    "summary": "إنشاء بروفايل صوتي وشخصية جديدة (Create Profile)",
                    "description": "إنشاء بروفايل صوتي جديد بلهجة محددة (سعودي، مصري، شامي، فصحى) وتعليمات مخصصة.",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ProfileCreateRequest"},
                                "example": {
                                    "name": "مساعد المبيعات السعودي",
                                    "voice_name": "Aoede",
                                    "gender": "female",
                                    "dialect": "saudi",
                                    "persona_role": "sales_advisor",
                                    "speaking_style": "friendly",
                                    "custom_instructions": "أنت مستشار مبيعات ودود تتحدث باللهجة السعودية البيضاء وتقدم عروض المتجر.",
                                    "is_active": True
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "تم إنشاء البروفايل بنجاح",
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
                    "tags": ["3. الصوت واللهجات والشخصيات"],
                    "summary": "جلب تفاصيل بروفايل صوتي (Retrieve Profile)",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"},
                        {"$ref": "#/components/parameters/ProfileId"}
                    ],
                    "responses": {
                        "200": {"description": "تفاصيل البروفايل"},
                        "404": {"$ref": "#/components/responses/404Error"}
                    }
                },
                "patch": {
                    "tags": ["3. الصوت واللهجات والشخصيات"],
                    "summary": "تعديل بروفايل صوتي (Update Profile)",
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
                                    "name": "مستشار الدعم الفني المصري",
                                    "dialect": "egyptian",
                                    "voice_name": "Fenrir",
                                    "speaking_style": "formal"
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "تم تحديث البروفايل بنجاح"},
                        "404": {"$ref": "#/components/responses/404Error"}
                    }
                },
                "delete": {
                    "tags": ["3. الصوت واللهجات والشخصيات"],
                    "summary": "حذف بروفايل صوتي (Delete Profile)",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"},
                        {"$ref": "#/components/parameters/ProfileId"}
                    ],
                    "responses": {
                        "200": {"description": "تم حذف البروفايل بنجاح"},
                        "404": {"$ref": "#/components/responses/404Error"}
                    }
                }
            },
            "/clients/{client_id}/profiles/{profile_id}/activate/": {
                "post": {
                    "tags": ["3. الصوت واللهجات والشخصيات"],
                    "summary": "تفعيل الشخصية الافتراضية (Activate Profile)",
                    "description": "تعيين هذا البروفايل كبروفايل نشط للمكالمات القادمة وتعطيل باقي البروفايلات تلقائياً.",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"},
                        {"$ref": "#/components/parameters/ProfileId"}
                    ],
                    "responses": {
                        "200": {"description": "تم تفعيل البروفايل بنجاح"},
                        "404": {"$ref": "#/components/responses/404Error"}
                    }
                }
            },
            "/clients/{client_id}/memory/": {
                "get": {
                    "tags": ["4. ذاكرة وسياق العملاء CRM"],
                    "summary": "استعراض سجلات الذاكرة التراكمية (List or Query Memory)",
                    "description": (
                        "عند تمرير `phone` يتم إرجاع سياق العميل المحدد فقط (توافقية عكسية). "
                        "عند عدم تمرير هاتف، يتم إرجاع قائمة السجلات مع إمكانية الترقيم والبحث عبر `q`."
                    ),
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"},
                        {
                            "name": "phone",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "رقم الهاتف للاستعلام المباشر عن عميل محدد (مثال: +966501234567)"
                        },
                        {
                            "name": "q",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "كلمة البحث في أسماء العملاء أو أرقام الهواتف"
                        },
                        {
                            "name": "page",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 1},
                            "description": "رقم الصفحة المطلوبة"
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 20},
                            "description": "عدد السجلات في كل صفحة (الحد الأقصى 100)"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "سجلات الذاكرة التراكمية",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/MemoryListResponse"}
                                }
                            }
                        }
                    }
                },
                "post": {
                    "tags": ["4. ذاكرة وسياق العملاء CRM"],
                    "summary": "إضافة أو تحديث ذاكرة عميل (Upsert Memory)",
                    "description": "حفظ أو تحديث ملف العميل التراكمي وتفضيلاته وملاحظات المكالمة وعدد اتصالاته.",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/MemoryUpsertRequest"},
                                "example": {
                                    "phone_number": "+966501234567",
                                    "customer_name": "عبدالله الشمري",
                                    "permanent_profile": {
                                        "city": "الرياض",
                                        "vip_tier": "Gold",
                                        "notes": "يفضل الشحن السريع بالصباح ومهتم بمنتجات العطور"
                                    },
                                    "immediate_notes": "استفسر عن كود الخصم وتم إرساله له بنجاح",
                                    "total_calls_count": 3
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "تم التحديث بنجاح"},
                        "201": {"description": "تم إنشاء السجل بنجاح"}
                    }
                }
            },
            "/clients/{client_id}/memory/{memory_id}/": {
                "get": {
                    "tags": ["4. ذاكرة وسياق العملاء CRM"],
                    "summary": "جلب سجل ذاكرة بالمعرف (Retrieve Memory by ID)",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"},
                        {"$ref": "#/components/parameters/MemoryId"}
                    ],
                    "responses": {
                        "200": {"description": "سجل العميل"},
                        "404": {"$ref": "#/components/responses/404Error"}
                    }
                },
                "patch": {
                    "tags": ["4. ذاكرة وسياق العملاء CRM"],
                    "summary": "تعديل سجل ذاكرة بالمعرف (Update Memory by ID)",
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
                        "200": {"description": "تم التعديل بنجاح"},
                        "404": {"$ref": "#/components/responses/404Error"}
                    }
                },
                "delete": {
                    "tags": ["4. ذاكرة وسياق العملاء CRM"],
                    "summary": "حذف سجل الذاكرة بالمعرف (Delete Memory by ID)",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"},
                        {"$ref": "#/components/parameters/MemoryId"}
                    ],
                    "responses": {
                        "200": {"description": "تم حذف السجل بنجاح"},
                        "404": {"$ref": "#/components/responses/404Error"}
                    }
                }
            },
            "/clients/{client_id}/documents/": {
                "get": {
                    "tags": ["5. قواعد المعرفة والاستعلام الدلالي RAG"],
                    "summary": "عرض جميع مستندات قاعدة المعرفة (List Documents)",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"}
                    ],
                    "responses": {
                        "200": {"description": "قائمة المستندات"}
                    }
                },
                "post": {
                    "tags": ["5. قواعد المعرفة والاستعلام الدلالي RAG"],
                    "summary": "رفع وفهرسة مستند جديد (Ingest Document)",
                    "description": "رفع ملف PDF أو نص خام ليتم تقطيعه وتوليد التضمينات الدلالية وحفظها في pgvector.",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "multipart/form-data": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string", "example": "كتالوج وسياسة متجر النور"},
                                        "text": {"type": "string", "example": "سياسة التوصيل: التوصيل مجاني للطلبات فوق 200 ريال."},
                                        "file": {"type": "string", "format": "binary"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {"description": "تمت فهرسة المستند بنجاح"}
                    }
                }
            },
            "/clients/{client_id}/rag/query/": {
                "post": {
                    "tags": ["5. قواعد المعرفة والاستعلام الدلالي RAG"],
                    "summary": "استعلام دلالي ذكي (Semantic Vector Search)",
                    "description": "البحث في مستندات العميل بناءً على المعنى والسياق الدلالي وإرجاع أعلى النتائج تطابقاً.",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["query"],
                                    "properties": {
                                        "query": {"type": "string", "example": "ما هي شروط وسياسة التوصيل المجاني لديكم؟"},
                                        "top_k": {"type": "integer", "default": 3, "example": 2}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "نتائج البحث الدلالي",
                            "content": {
                                "application/json": {
                                    "example": {
                                        "status": "success",
                                        "client_id": 19,
                                        "total_matches": 1,
                                        "results": [
                                            {
                                                "content": "التوصيل مجاني لكافة مدن المملكة للطلبات فوق 200 ريال...",
                                                "similarity": 0.7949
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/clients/{client_id}/telephony/": {
                "get": {
                    "tags": ["6. السنترالات والخطوط والأرقام"],
                    "summary": "عرض خطوط السنترال و SIP (List Trunks)",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"}
                    ],
                    "responses": {
                        "200": {"description": "قائمة الخطوط"}
                    }
                },
                "post": {
                    "tags": ["6. السنترالات والخطوط والأرقام"],
                    "summary": "إنشاء سنترال أو خط اتصال جديد (Create Trunk)",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["trunk_type", "name"],
                                    "properties": {
                                        "trunk_type": {"type": "string", "enum": ["inbound", "outbound"], "example": "inbound"},
                                        "name": {"type": "string", "example": "سنترال متجر النور (Issabel PBX)"},
                                        "auth_mode": {"type": "string", "enum": ["ip", "credentials"], "example": "ip"},
                                        "pbx_ip": {"type": "string", "example": "192.168.10.50"},
                                        "inbound_numbers": {"type": "string", "example": "920005544"},
                                        "sip_host": {"type": "string", "example": "sip.telnyx.com"},
                                        "caller_id": {"type": "string", "example": "+966920005544"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {"description": "تم إنشاء الجذع بنجاح"}
                    }
                }
            },
            "/clients/{client_id}/telephony/numbers/": {
                "get": {
                    "tags": ["6. السنترالات والخطوط والأرقام"],
                    "summary": "عرض أرقام الـ DIDs المرتبطة (List Phone Numbers)",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"}
                    ],
                    "responses": {
                        "200": {"description": "قائمة الأرقام"}
                    }
                },
                "post": {
                    "tags": ["6. السنترالات والخطوط والأرقام"],
                    "summary": "ربط رقم هاتف وتوليد إعدادات Issabel (Link Phone Number)",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["phone_number", "trunk_type"],
                                    "properties": {
                                        "phone_number": {"type": "string", "example": "+966114455667"},
                                        "trunk_type": {"type": "string", "example": "inbound"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "تم ربط الرقم وتوليد الإعدادات بنجاح",
                            "content": {
                                "application/json": {
                                    "example": {
                                        "status": "success",
                                        "trunk": {
                                            "phone_number": "+966114455667",
                                            "issabel_config": {
                                                "peer_details": "type=peer\nhost=voice.domain\n..."
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/clients/{client_id}/employees/": {
                "get": {
                    "tags": ["7. دليل الموظفين والتحويلات"],
                    "summary": "عرض دليل موظفي العميل (List Employees)",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"}
                    ],
                    "responses": {
                        "200": {"description": "قائمة الموظفين"}
                    }
                },
                "post": {
                    "tags": ["7. دليل الموظفين والتحويلات"],
                    "summary": "إضافة موظف وتحويلة جديدة (Create Employee)",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["display_name", "extension"],
                                    "properties": {
                                        "display_name": {"type": "string", "example": "سارة الخالد"},
                                        "extension": {"type": "string", "example": "102"},
                                        "department": {"type": "string", "example": "خدمة العملاء والدعم الفني"},
                                        "password": {"type": "string", "example": "SecureEmpPassword123"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {"description": "تم إنشاء الموظف بنجاح"},
                        "409": {"description": "التحويلة مكررة بالفعل لدى هذا العميل"}
                    }
                }
            },
            "/clients/{client_id}/employees/{employee_id}/": {
                "get": {
                    "tags": ["7. دليل الموظفين والتحويلات"],
                    "summary": "تفاصيل موظف محدد (Retrieve Employee)",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"},
                        {"$ref": "#/components/parameters/EmployeeId"}
                    ],
                    "responses": {
                        "200": {"description": "تفاصيل الموظف"},
                        "404": {"$ref": "#/components/responses/404Error"}
                    }
                },
                "post": {
                    "tags": ["7. دليل الموظفين والتحويلات"],
                    "summary": "تعديل بيانات أو حالة الموظف (Update Employee)",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"},
                        {"$ref": "#/components/parameters/EmployeeId"}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "display_name": {"type": "string", "example": "سارة الخالد (مشرفة)"},
                                        "status": {"type": "string", "enum": ["ready", "busy", "offline"], "example": "busy"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "تم التحديث بنجاح"}
                    }
                },
                "delete": {
                    "tags": ["7. دليل الموظفين والتحويلات"],
                    "summary": "حذف موظف (Delete Employee)",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"},
                        {"$ref": "#/components/parameters/EmployeeId"}
                    ],
                    "responses": {
                        "200": {"description": "تم الحذف بنجاح"}
                    }
                }
            },
            "/clients/{client_id}/queues/": {
                "get": {
                    "tags": ["8. طوابير الانتظار والأعضاء"],
                    "summary": "عرض طوابير الانتظار (List Queues)",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"}
                    ],
                    "responses": {
                        "200": {"description": "قائمة الطوابير"}
                    }
                },
                "post": {
                    "tags": ["8. طوابير الانتظار والأعضاء"],
                    "summary": "إنشاء طابور انتظار جديد (Create Queue)",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["name", "code"],
                                    "properties": {
                                        "name": {"type": "string", "example": "طابور خدمة عملاء المتجر VIP"},
                                        "code": {"type": "string", "example": "401"},
                                        "strategy": {"type": "string", "enum": ["round_robin", "least_recent"], "example": "round_robin"},
                                        "ring_timeout_seconds": {"type": "integer", "example": 20},
                                        "total_timeout_seconds": {"type": "integer", "example": 60},
                                        "fallback_action": {"type": "string", "example": "ai_assistant"},
                                        "members": {"type": "array", "items": {"type": "integer"}, "example": [14]}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {"description": "تم إنشاء الطابور بنجاح"}
                    }
                }
            },
            "/clients/{client_id}/queues/{queue_id}/members/": {
                "get": {
                    "tags": ["8. طوابير الانتظار والأعضاء"],
                    "summary": "عرض أعضاء الطابور (List Queue Members)",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"},
                        {"$ref": "#/components/parameters/QueueId"}
                    ],
                    "responses": {
                        "200": {"description": "أعضاء الطابور"}
                    }
                },
                "post": {
                    "tags": ["8. طوابير الانتظار والأعضاء"],
                    "summary": "إدارة أعضاء الطابور (Manage Queue Members)",
                    "description": "إضافة أو حذف موظف من الطابور عبر action: 'add' | 'remove' | 'set'.",
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
                                    "required": ["action", "employee_id"],
                                    "properties": {
                                        "action": {"type": "string", "enum": ["add", "remove", "set"], "example": "add"},
                                        "employee_id": {"type": "integer", "example": 15},
                                        "order": {"type": "integer", "example": 2}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "تم تعديل أعضاء الطابور بنجاح"}
                    }
                }
            },
            "/clients/{client_id}/token/": {
                "post": {
                    "tags": ["9. بدء مكالمة WebRTC"],
                    "summary": "إصدار توكن مكالمة صوتية مباشرة (LiveKit WebRTC Token)",
                    "description": "يتحقق من رصيد الشريك وسقف العميل، ويصدر توكن اتصال صوتي مشفر لمحادثة الذكاء الاصطناعي.",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"}
                    ],
                    "responses": {
                        "200": {
                            "description": "تم إصدار التوكن بنجاح",
                            "content": {
                                "application/json": {
                                    "example": {
                                        "status": "success",
                                        "token": "eyJhbGciOi...",
                                        "room_name": "partner_1_19_ca4f1c3a",
                                        "ws_url": "wss://localhost:7881"
                                    }
                                }
                            }
                        },
                        "403": {"description": "تجاوز سقف الاستهلاك أو نفاد رصيد الشريك"}
                    }
                }
            },
            "/clients/{client_id}/calls/": {
                "get": {
                    "tags": ["10. سجلات المكالمات والفوترة"],
                    "summary": "استعراض سجلات المكالمات والفوترة (Call Logs & CDR)",
                    "description": "استعراض تفاصيل المكالمات الخاصة بهذا العميل مع مدة المكالمة، الدقائق المفوترة، التكلفة، والملخص.",
                    "parameters": [
                        {"$ref": "#/components/parameters/ClientId"}
                    ],
                    "responses": {
                        "200": {
                            "description": "سجلات المكالمات بنجاح",
                            "content": {
                                "application/json": {
                                    "example": {
                                        "status": "success",
                                        "client_id": 19,
                                        "total_calls": 1,
                                        "total_billed_minutes": 2,
                                        "calls": [
                                            {
                                                "room_name": "partner_1_19_call_101",
                                                "caller_phone": "+966501234567",
                                                "duration_seconds": 65,
                                                "billed_minutes": 2,
                                                "cost": 0.06,
                                                "summary": "استفسار عن الشحن وتمت الإفادة بأن الشحن مجاني فوق 200 ريال.",
                                                "created_at": "2026-09-23 11:30"
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "PartnerKey": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-Partner-Key",
                    "description": "مفتاح الشريك السري (يبدأ بـ sk_live_prt_...). يجب تمريره في كل طلب."
                }
            },
            "parameters": {
                "ClientId": {
                    "name": "client_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                    "description": "المعرف الرقمي للعميل الفرعي (client_id)"
                },
                "ProfileId": {
                    "name": "profile_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                    "description": "المعرف الرقمي لبروفايل الصوت"
                },
                "MemoryId": {
                    "name": "memory_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                    "description": "المعرف الرقمي لسجل ذاكرة العميل"
                },
                "EmployeeId": {
                    "name": "employee_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                    "description": "المعرف الرقمي للموظف"
                },
                "QueueId": {
                    "name": "queue_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                    "description": "المعرف الرقمي لطابور الانتظار"
                }
            },
            "responses": {
                "400Error": {
                    "description": "طلب غير صالح (Bad Request)",
                    "content": {
                        "application/json": {
                            "example": {"status": "error", "message": "Invalid JSON body"}
                        }
                    }
                },
                "403Error": {
                    "description": "غير مصرح (مفتاح الشريك غير صالح أو غير مصرح له بهذا العميل)",
                    "content": {
                        "application/json": {
                            "example": {"status": "error", "message": "Invalid partner API key"}
                        }
                    }
                },
                "404Error": {
                    "description": "العنصر غير موجود (Not Found)",
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
                        "name": {"type": "string", "example": "متجر النور التجريبي"},
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
                        "name": {"type": "string", "example": "متجر النور التجريبي"},
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
                        "name": {"type": "string", "example": "مساعد المبيعات السعودي"},
                        "voice_name": {"type": "string", "default": "Aoede", "example": "Aoede"},
                        "gender": {"type": "string", "enum": ["female", "male"], "default": "female"},
                        "dialect": {"type": "string", "enum": ["saudi", "egyptian", "levantine", "fusha", "english"], "default": "saudi"},
                        "persona_role": {"type": "string", "enum": ["customer_support", "sales_advisor", "personal_assistant", "technical_consultant"], "default": "sales_advisor"},
                        "speaking_style": {"type": "string", "enum": ["friendly", "formal", "concise", "enthusiastic"], "default": "friendly"},
                        "custom_instructions": {"type": "string", "example": "أنت مستشار مبيعات ودود تتحدث باللهجة السعودية البيضاء."},
                        "is_active": {"type": "boolean", "default": True}
                    }
                },
                "ProfileUpdateRequest": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "voice_name": {"type": "string"},
                        "gender": {"type": "string", "enum": ["female", "male"]},
                        "dialect": {"type": "string", "enum": ["saudi", "egyptian", "levantine", "fusha", "english"]},
                        "persona_role": {"type": "string"},
                        "speaking_style": {"type": "string"},
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
                        "customer_name": {"type": "string", "example": "عبدالله الشمري"},
                        "permanent_profile": {
                            "type": "object",
                            "example": {
                                "city": "الرياض",
                                "vip_tier": "Gold",
                                "notes": "يفضل الشحن السريع بالصباح"
                            }
                        },
                        "immediate_notes": {"type": "string", "example": "استفسر عن كود الخصم وتم إرساله له بنجاح"},
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
    }
