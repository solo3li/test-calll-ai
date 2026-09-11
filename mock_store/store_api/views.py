import json
import random
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Product, Order

def list_products(request):
    """List or search products in the mock store."""
    query = request.GET.get('q', '').strip()
    if query:
        products = Product.objects.filter(name__icontains=query)
    else:
        products = Product.objects.all()

    return JsonResponse({
        "status": "success",
        "count": products.count(),
        "products": [p.to_dict() for p in products]
    })

def get_order(request, order_id):
    """Retrieve details and status for a specific order."""
    order_id_clean = str(order_id).strip()
    try:
        order = Order.objects.get(order_id=order_id_clean)
        return JsonResponse({
            "status": "success",
            "order": order.to_dict()
        })
    except Order.DoesNotExist:
        return JsonResponse({
            "status": "not_found",
            "message": f"عذراً، لم يتم العثور على طلبية بالرقم '{order_id_clean}'."
        }, status=404)

@csrf_exempt
def create_order(request):
    """Create a new order in the mock store."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        customer_name = data.get('customer_name', 'عميل المتجر')
        customer_phone = data.get('customer_phone', '')
        address = data.get('address', 'القاهرة')
        product_name = data.get('product_name', 'منتج إلكتروني')
        quantity = int(data.get('quantity', 1))

        # Check product price if exists
        prod = Product.objects.filter(name__icontains=product_name).first()
        if prod:
            unit_price = prod.price
            actual_product_name = prod.name
        else:
            unit_price = Decimal("250.00")
            actual_product_name = product_name

        total_price = unit_price * quantity
        new_order_id = str(random.randint(2000, 9999))

        order = Order.objects.create(
            order_id=new_order_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            address=address,
            product_name=actual_product_name,
            quantity=quantity,
            total_price=total_price,
            status="جاري التجهيز والتأكيد"
        )

        return JsonResponse({
            "status": "success",
            "message": f"تم تسجيل الطلب بنجاح برقم {new_order_id}",
            "order": order.to_dict()
        }, status=201)

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)

from django.http import HttpResponse

def store_home(request):
    """Render a visual dashboard for the Mock Store."""
    products = Product.objects.all()
    orders = Order.objects.all().order_by('-id')

    products_html = ""
    for p in products:
        products_html += f"""
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between shadow-lg hover:border-indigo-500/50 transition">
          <div>
            <div class="flex justify-between items-start mb-2">
              <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-950/80 text-indigo-400 border border-indigo-800/60">{p.category or 'عام'}</span>
              <span class="text-xs text-slate-400">متبقي {p.stock} قطع</span>
            </div>
            <h3 class="text-base font-bold text-slate-100 mb-1">{p.name}</h3>
            <p class="text-xs text-slate-400 leading-relaxed">{p.description}</p>
          </div>
          <div class="mt-4 pt-3 border-t border-slate-800 flex justify-between items-center">
            <span class="text-lg font-extrabold text-emerald-400">{p.price} ج.م</span>
            <span class="text-[11px] text-slate-500 font-mono">ID: {p.id}</span>
          </div>
        </div>
        """

    orders_html = ""
    for o in orders:
        badge_color = "bg-amber-950/80 text-amber-300 border-amber-800" if "تجهيز" in o.status else "bg-emerald-950/80 text-emerald-300 border-emerald-800"
        orders_html += f"""
        <tr class="hover:bg-slate-850/50 transition border-b border-slate-800/50">
          <td class="py-3 px-4 font-mono font-bold text-indigo-400">#{o.order_id}</td>
          <td class="py-3 px-4 font-semibold text-slate-200">{o.customer_name}</td>
          <td class="py-3 px-4 text-slate-300">{o.product_name} (x{o.quantity})</td>
          <td class="py-3 px-4 text-emerald-400 font-bold">{o.total_price} ج.م</td>
          <td class="py-3 px-4 text-slate-400 text-xs">{o.address}</td>
          <td class="py-3 px-4"><span class="px-2.5 py-1 rounded-full text-xs font-medium border {badge_color}">{o.status}</span></td>
          <td class="py-3 px-4 text-slate-500 text-xs">{o.created_at.strftime('%Y-%m-%d %H:%M')}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>المتجر الإلكتروني التجريبي | Mock Store</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans">
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur px-8 py-5 flex flex-wrap justify-between items-center gap-4">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-indigo-600 flex items-center justify-center text-xl shadow-lg shadow-emerald-500/20">
        🛍️
      </div>
      <div>
        <h1 class="text-xl font-bold bg-gradient-to-r from-emerald-400 via-teal-300 to-indigo-400 bg-clip-text text-transparent">
          المتجر الإلكتروني التجريبي (Mock Store)
        </h1>
        <p class="text-xs text-slate-400">نظام الـ API المستقل لخدمة مساعد الصوت الذكي (Port 8001)</p>
      </div>
    </div>
    <div class="flex items-center gap-3 text-xs">
      <span class="px-3 py-1.5 rounded-xl bg-emerald-950/80 border border-emerald-800 text-emerald-300 flex items-center gap-1.5 font-semibold">
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        حاوية مستقلة متصلة بـ voice_net
      </span>
      <a href="/admin/" target="_blank" class="px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold shadow-md transition flex items-center gap-1">
        🔑 لوحة الأدمن (Admin)
      </a>
      <a href="/api/products/" target="_blank" class="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition">
        📄 JSON المنتجات
      </a>
      <a href="/api/orders/1001/" target="_blank" class="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition">
        📦 JSON أوردر #1001
      </a>
    </div>
  </header>

  <main class="max-w-6xl mx-auto p-6 space-y-8">
    <!-- Notice Banner -->
    <div class="p-4 rounded-2xl bg-slate-900/70 border border-slate-800 text-xs text-slate-300 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <span class="text-xl">🤖</span>
        <span>
          <strong>الربط الصوتي الفوري:</strong> هذا المتجر مربوط مباشرة بالمساعد الصوتي عبر <strong>محرك الإجراءات (Actions Engine)</strong> للمستخدم <strong>hamo</strong>. تستطيع المساعدة الاستعلام عن المنتجات والطلبات وإنشاء أوردر جديد عبر الصوت في أي وقت.
        </span>
      </div>
    </div>

    <!-- Products Catalog Section -->
    <section>
      <div class="flex justify-between items-center mb-4">
        <div>
          <h2 class="text-lg font-bold text-slate-100 flex items-center gap-2">
            <span>📦</span> كتالوج المنتجات المتوفرة ({products.count()})
          </h2>
          <p class="text-xs text-slate-400">المنتجات المعروضة في المتجر والتي يمكن للمساعد الصوتي البحث فيها وإبلاغ العملاء بأسعارها ومواصفاتها</p>
        </div>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {products_html}
      </div>
    </section>

    <!-- Orders Management Section -->
    <section>
      <div class="flex justify-between items-center mb-4">
        <div>
          <h2 class="text-lg font-bold text-slate-100 flex items-center gap-2">
            <span>🚚</span> الطلبيات وحالات الشحن والتوصيل ({orders.count()})
          </h2>
          <p class="text-xs text-slate-400">سجل الطلبيات الحالي، يشمل الطلبية التجريبية #1001 للعميل "حمو" وأي طلبيات يتم إنشاؤها عبر الصوت</p>
        </div>
      </div>
      <div class="bg-slate-900/90 border border-slate-800 rounded-2xl overflow-x-auto shadow-xl">
        <table class="w-full text-right text-xs">
          <thead>
            <tr class="text-slate-400 border-b border-slate-800 bg-slate-950/40">
              <th class="py-3 px-4">رقم الطلب</th>
              <th class="py-3 px-4">اسم العميل</th>
              <th class="py-3 px-4">المنتج والكمية</th>
              <th class="py-3 px-4">الإجمالي</th>
              <th class="py-3 px-4">العنوان</th>
              <th class="py-3 px-4">حالة الشحن والتسليم</th>
              <th class="py-3 px-4">تاريخ الطلب</th>
            </tr>
          </thead>
          <tbody>
            {orders_html}
          </tbody>
        </table>
      </div>
    </section>
  </main>
</body>
</html>"""
    return HttpResponse(html)
