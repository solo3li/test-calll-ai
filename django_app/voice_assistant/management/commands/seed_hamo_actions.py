from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from voice_assistant.models import UserAction

class Command(BaseCommand):
    help = 'Pre-seed custom HTTP actions for user hamo to connect with mock_store'

    def handle(self, *args, **options):
        # 1. Get or create user hamo
        hamo, created = User.objects.get_or_create(username='hamo')
        if created:
            hamo.set_password('hamo1234')
            hamo.save()
            self.stdout.write(self.style.SUCCESS("Created user 'hamo' with password 'hamo1234'."))
        else:
            self.stdout.write(f"User 'hamo' exists (ID: {hamo.id}).")

        # 2. Define pre-seeded actions
        actions = [
            {
                "name": "search_store_products",
                "description": "البحث عن المنتجات في المتجر الإلكتروني ومعرفة أسعارها ومواصفاتها وتوافرها في المخزون.",
                "url": "http://mock-store:8000/api/products/",
                "method": "GET",
                "parameters_schema": {
                    "type": "OBJECT",
                    "properties": {
                        "q": {
                            "type": "STRING",
                            "description": "اسم أو نوع المنتج المراد البحث عنه (مثل: سماعة، شاحن، ساعة)"
                        }
                    }
                }
            },
            {
                "name": "get_order_status",
                "description": "الاستعلام عن تفاصيل وموعد تسليم وحالة شحن طلبية العميل بواسطة رقم الطلب (Order ID).",
                "url": "http://mock-store:8000/api/orders/{order_id}/",
                "method": "GET",
                "parameters_schema": {
                    "type": "OBJECT",
                    "properties": {
                        "order_id": {
                            "type": "STRING",
                            "description": "رقم الطلبية المراد الاستعلام عنها (مثل: 1001)"
                        }
                    },
                    "required": ["order_id"]
                }
            },
            {
                "name": "create_store_order",
                "description": "تسجيل وإنشاء طلبية شراء جديدة لمنتج في المتجر وتحديد الكمية وعنوان التوصيل واسم العميل.",
                "url": "http://mock-store:8000/api/orders/",
                "method": "POST",
                "parameters_schema": {
                    "type": "OBJECT",
                    "properties": {
                        "product_name": {
                            "type": "STRING",
                            "description": "اسم المنتج المطلوب شراؤه"
                        },
                        "quantity": {
                            "type": "INTEGER",
                            "description": "الكمية المطلوبة من المنتج"
                        },
                        "customer_name": {
                            "type": "STRING",
                            "description": "اسم العميل صاحب الطلب"
                        },
                        "address": {
                            "type": "STRING",
                            "description": "عنوان التوصيل الخاص بالعميل"
                        }
                    },
                    "required": ["product_name"]
                }
            }
        ]

        for act in actions:
            action_obj, act_created = UserAction.objects.update_or_create(
                user=hamo,
                name=act["name"],
                defaults={
                    "description": act["description"],
                    "url": act["url"],
                    "method": act["method"],
                    "parameters_schema": act["parameters_schema"],
                    "is_active": True
                }
            )
            state = "Created" if act_created else "Updated"
            self.stdout.write(f"  {state} action: {act['name']}")

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(actions)} actions for user 'hamo'!"))
