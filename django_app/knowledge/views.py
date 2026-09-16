import os
import json
import logging
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from google import genai
from google.genai import types
from pgvector.django import CosineDistance

from .models import Document, DocumentChunk
from .rag_utils import extract_text_from_file, chunk_text, get_embeddings_batch

logger = logging.getLogger(__name__)

def verify_internal_api_key(request) -> bool:
    """Validate internal request from AI agent service."""
    expected_key = getattr(settings, 'INTERNAL_API_KEY', 'default-internal-secret-key-12345')
    auth_header = request.headers.get('X-Internal-API-Key') or request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ', 1)[1].strip()
    else:
        token = auth_header.strip()
    return token == expected_key or request.user.is_authenticated

@login_required(login_url='/login/')
def list_documents(request):
    """List all documents uploaded by the current user."""
    docs = Document.objects.filter(user=request.user).order_by('-created_at')
    data = []
    for d in docs:
        data.append({
            "id": d.id,
            "title": d.title,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "chunks_count": d.chunks.count(),
            "created_at": d.created_at.strftime("%Y-%m-%d %H:%M"),
        })
    return JsonResponse({"status": "success", "documents": data})

@login_required(login_url='/login/')
def upload_document(request):
    """Handle document upload, text extraction, chunking, and Gemini embedding generation."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    file_obj = request.FILES.get('file')
    if not file_obj:
        return JsonResponse({"status": "error", "message": "لم يتم تحديد أي ملف للرفع"}, status=400)

    filename = file_obj.name
    ext = os.path.splitext(filename)[1].lower()
    allowed_exts = ['.pdf', '.docx', '.doc', '.txt', '.md']
    if ext not in allowed_exts:
        return JsonResponse({
            "status": "error",
            "message": f"صيغة الملف غير مدعومة ({ext}). الصيغ المدعومة هي: PDF, DOCX, TXT, MD"
        }, status=400)

    try:
        # 1. Extract text from uploaded file
        text = extract_text_from_file(file_obj, filename)
        if not text:
            return JsonResponse({"status": "error", "message": "الملف فارغ أو يتعذر استخراج نص منه."}, status=400)

        # 2. Chunk text
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        if not chunks:
            return JsonResponse({"status": "error", "message": "لم يتم العثور على محتوى صالح للتقطيع."}, status=400)

        # 3. Create Document DB record
        doc = Document.objects.create(
            user=request.user,
            title=filename,
            file=file_obj,
            file_type=ext.lstrip('.'),
            file_size=file_obj.size
        )

        # 4. Generate embeddings with Gemini
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        embeddings = get_embeddings_batch(client, chunks, batch_size=50)

        # 5. Bulk create DocumentChunks in pgvector
        chunk_objects = []
        for i, (chunk_text_content, emb) in enumerate(zip(chunks, embeddings)):
            chunk_objects.append(DocumentChunk(
                document=doc,
                user=request.user,
                chunk_index=i,
                content=chunk_text_content,
                embedding=emb,
            ))
        DocumentChunk.objects.bulk_create(chunk_objects)

        logger.info(f"Successfully processed document '{filename}' for user {request.user.username}: {len(chunks)} chunks embedded.")

        return JsonResponse({
            "status": "success",
            "message": f"تمت معالجة المستند '{filename}' بنجاح وفهرسة {len(chunks)} مقطعاً دلالياً.",
            "document": {
                "id": doc.id,
                "title": doc.title,
                "chunks_count": len(chunks),
                "created_at": doc.created_at.strftime("%Y-%m-%d %H:%M"),
            }
        })

    except Exception as e:
        logger.error(f"Error processing document upload: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": f"حدث خطأ أثناء معالجة المستند: {str(e)}"}, status=500)

@login_required(login_url='/login/')
def delete_document(request, doc_id):
    """Delete a document and all its chunks for the authenticated user."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    doc = get_object_or_404(Document, id=doc_id, user=request.user)
    title = doc.title
    doc.delete()
    logger.info(f"Deleted document '{title}' (id={doc_id}) for user {request.user.username}")
    return JsonResponse({"status": "success", "message": f"تم حذف المستند '{title}' بنجاح."})

@csrf_exempt
def api_internal_rag_search(request):
    """
    Internal RAG semantic similarity search API for the AI Agent.
    Accepts: { user_id: int, query: str, top_k: int }
    Returns: { status: 'success', text: str, matches: list }
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    if not verify_internal_api_key(request):
        return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
        user_id = data.get('user_id')
        query = str(data.get('query', '')).strip()
        top_k = int(data.get('top_k', 3))

        if not user_id or not query:
            return JsonResponse({"status": "error", "message": "user_id and query are required"}, status=400)

        # 1. Generate query embedding with Gemini
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        embed_res = client.models.embed_content(
            model="gemini-embedding-001",
            contents=query,
            config=types.EmbedContentConfig(output_dimensionality=768)
        )
        if not embed_res or not embed_res.embeddings:
            return JsonResponse({"status": "error", "message": "Failed to generate query embedding"}, status=500)

        query_vec = embed_res.embeddings[0].values

        # 2. Similarity search using pgvector CosineDistance
        chunks = DocumentChunk.objects.filter(user_id=user_id) \
            .annotate(distance=CosineDistance('embedding', query_vec)) \
            .filter(distance__lte=0.50) \
            .order_by('distance')[:top_k]

        if not chunks:
            has_any = DocumentChunk.objects.filter(user_id=user_id).exists()
            msg = "لا توجد أي مستندات مرفوعة في قاعدة المعرفة الخاصة بك." if not has_any else "لم يتم العثور على أي معلومات متعلقة بهذا السؤال في المستندات المرفوعة الخاصة بك."
            return JsonResponse({
                "status": "success",
                "text": msg,
                "matches": []
            })

        matches = [c.content for c in chunks]
        formatted_text = "المعلومات الموثقة المستخرجة من مستنداتك:\n" + "\n---\n".join(matches)

        return JsonResponse({
            "status": "success",
            "text": formatted_text,
            "matches": matches
        })

    except Exception as e:
        logger.error(f"Internal RAG search error: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
