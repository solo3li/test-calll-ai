import os
import sys
import random
from decimal import Decimal
from typing import Optional
import uvicorn

# Initialize Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'store_project.settings')
import django
django.setup()

from store_api.models import Product, Order

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

# Create FastMCP instance
mcp = FastMCP("MockStoreMCP")

@mcp.tool()
def search_store_products(query: str = "") -> list[dict]:
    """البحث في كتالوج منتجات المتجر الإلكتروني واسترجاع تفاصيل المنتجات والأسعار والمخزون المتوفر.

    Args:
        query: كلمة البحث أو اسم المنتج المراد الاستعلام عنه (مثل: سماعة، شاحن، ساعة).
    """
    q = (query or "").strip()
    if q:
        products = Product.objects.filter(name__icontains=q)
    else:
        products = Product.objects.all()

    return [p.to_dict() for p in products]

@mcp.tool()
def get_order_status(order_id: str) -> dict:
    """الاستعلام عن حالة شحن وتوصيل طلبية محددة وموعد التسليم المتوقع عبر رقم الطلب.

    Args:
        order_id: رقم الطلبية (مثل 1001).
    """
    oid = str(order_id).strip()
    try:
        order = Order.objects.get(order_id=oid)
        return {
            "status": "success",
            "order": order.to_dict()
        }
    except Order.DoesNotExist:
        return {
            "status": "not_found",
            "message": f"عذراً، لم يتم العثور على أي طلبية مسجلة برقم '{oid}'."
        }

@mcp.tool()
def create_store_order(
    product_name: str,
    quantity: int = 1,
    customer_name: str = "عميل المتجر",
    customer_phone: str = "",
    customer_address: str = "القاهرة"
) -> dict:
    """إنشاء وتسجيل طلبية شراء جديدة لمنتج في المتجر الإلكتروني.

    Args:
        product_name: اسم المنتج المطلوب شراؤه (مثال: سماعة بلوتوث لاسلكية برو).
        quantity: الكمية المطلوبة من المنتج.
        customer_name: اسم العميل صاحب الطلب.
        customer_phone: رقم هاتف العميل للتواصل والتوصيل.
        customer_address: عنوان التوصيل بالتفصيل.
    """
    p_name = (product_name or "").strip()
    qty = max(1, int(quantity or 1))

    prod = Product.objects.filter(name__icontains=p_name).first()
    if prod:
        unit_price = prod.price
        actual_product_name = prod.name
    else:
        unit_price = Decimal("250.00")
        actual_product_name = p_name or "منتج إلكتروني"

    total_price = unit_price * qty
    new_order_id = str(random.randint(2000, 9999))

    order = Order.objects.create(
        order_id=new_order_id,
        customer_name=customer_name or "عميل المتجر",
        customer_phone=customer_phone or "",
        address=customer_address or "القاهرة",
        product_name=actual_product_name,
        quantity=qty,
        total_price=total_price,
        status="جاري التجهيز والتأكيد"
    )

    return {
        "status": "success",
        "message": f"تم تسجيل الطلب بنجاح برقم {new_order_id}",
        "order": order.to_dict()
    }

try:
    from mcp.server.transport_security import TransportSecuritySettings
    security_settings = TransportSecuritySettings(enable_dns_rebinding_protection=False)
except Exception:
    security_settings = None

if __name__ == "__main__":
    print("[FastMCP] Starting Mock Store MCP Server on http://0.0.0.0:8002/sse ...")
    if security_settings:
        app = mcp.sse_app(transport_security=security_settings)
    else:
        app = mcp.sse_app()
    uvicorn.run(app, host="0.0.0.0", port=8002)
