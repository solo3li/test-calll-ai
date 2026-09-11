from decimal import Decimal
from django.core.management.base import BaseCommand
from store_api.models import Product, Order

class Command(BaseCommand):
    help = 'Seed initial products and orders for testing'

    def handle(self, *args, **options):
        # 1. Seed Products
        products_data = [
            {
                "name": "سماعة بلوتوث لاسلكية برو",
                "price": Decimal("550.00"),
                "description": "سماعة لاسلكية عازلة للضوضاء ببطارية تدوم 24 ساعة وشحن سريع.",
                "stock": 15,
                "category": "سماعات"
            },
            {
                "name": "شاحن سريع 65 واط جان",
                "price": Decimal("320.00"),
                "description": "شاحن ذكي فائق السرعة يدعم Type-C و USB بتقنية GaN لجميع الهواتف واللابتوب.",
                "stock": 25,
                "category": "شواحن"
            },
            {
                "name": "ساعة ذكية ألترا مقاومة للماء",
                "price": Decimal("1200.00"),
                "description": "ساعة رياضية ذكية مع قياس نبضات القلب وشاشة أموليد وبطارية أسبوع.",
                "stock": 8,
                "category": "ساعات ذكية"
            },
            {
                "name": "باور بانك 20000 مللي أمبير",
                "price": Decimal("480.00"),
                "description": "بنك طاقة بسعة ضخمة وشحن سريع يدعم شحن 3 أجهزة في وقت واحد.",
                "stock": 12,
                "category": "شواحن وبطاريات"
            }
        ]

        for p in products_data:
            Product.objects.get_or_create(name=p["name"], defaults=p)

        # 2. Seed Test Order #1001 for user hamo
        Order.objects.get_or_create(
            order_id="1001",
            defaults={
                "customer_name": "حمو",
                "customer_phone": "01012345678",
                "address": "القاهرة - مدينة نصر - شارع عباس العقاد",
                "product_name": "سماعة بلوتوث لاسلكية برو",
                "quantity": 1,
                "total_price": Decimal("550.00"),
                "status": "في الطريق للتوصيل (موعد التسليم المتوقع: غداً الساعة 3 عصراً)"
            }
        )

        self.stdout.write(self.style.SUCCESS("Successfully seeded mock store products and Order #1001!"))
