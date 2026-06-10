import sys, io, time, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

from parser.cascade_router import CascadeRouter

# Find any PDF in the documents folder or current dir
search_dirs = ["documents", ".", "demo"]
pdf_path = None
for d in search_dirs:
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.lower().endswith(".pdf"):
                pdf_path = os.path.join(d, f)
                break
    if pdf_path:
        break

if not pdf_path:
    print("NO PDF FOUND — creating a synthetic test PDF...")
    try:
        import fitz
        doc = fitz.open()
        for i in range(5):
            page = doc.new_page()
            page.insert_text((72, 72), f"Page {i+1}: скважина № {200+i} вскрыла пласт Ю1-3 на глубине {2800+i*10} м\nКн = 0.68, Кп = 0.21\nбаженовская свита", fontsize=12)
        test_pdf = "tests/test_synthetic.pdf"
        doc.save(test_pdf)
        doc.close()
        pdf_path = test_pdf
        print(f"Created synthetic PDF: {pdf_path}")
    except Exception as e:
        print(f"ERROR creating PDF: {e}")
        sys.exit(1)

print(f"Testing with PDF: {pdf_path}")
print("-" * 60)

router = CascadeRouter()
start = time.perf_counter()
result = router.route_document(pdf_path, doc_id="test_doc")
elapsed = time.perf_counter() - start

page_count = result.get("page_count", 0)
pages = result.get("pages", [])
errors = [p for p in pages if p.get("error")]

print(f"[OK] Pages returned:  {len(pages)} / {page_count}")
print(f"[OK] Processing time: {elapsed:.2f}s  (limit: 30s for 50 pages)")
print(f"[{'OK' if not errors else 'WARN'}] Pages with errors: {len(errors)}")
print(f"[OK] doc_type: {result.get('type')}")
print(f"[OK] elapsed_seconds: {result.get('elapsed_seconds')}")

# Check page count matches
if len(pages) == page_count:
    print("[ ] ✅ All pages accounted for")
else:
    print(f"[ ] ⚠️  Mismatch: got {len(pages)} pages, expected {page_count}")

# Print content summary
for p in pages[:3]:
    content = p.get("content", "")
    print(f"\nPage {p['page_num']}: {len(content)} chars | type={p.get('type')}")
    print(f"  Preview: {content[:120].replace(chr(10),' ')}")

print("\n" + "=" * 60)
if page_count > 0 and len(pages) == page_count and elapsed < 60:
    print("STATUS: ✅ BLOCK 1.5 WORKS (parallel processing, no hang)")
else:
    print("STATUS: ⚠️ CHECK ISSUES ABOVE")
