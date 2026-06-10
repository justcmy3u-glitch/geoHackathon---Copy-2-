import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

from ner.local_normalizer import LocalNormalizer

normalizer = LocalNormalizer()

print("=" * 60)
print("BLOCK 3.1 — ASSERTIONS")
print("=" * 60)

def check(label, condition):
    status = "OK" if condition else "FAIL"
    print(f"  [{status}] {label}")
    return condition

results = []

# 1. горизонт Ю₁³ → contains Ю1-3 in entities
r1 = normalizer.normalize("горизонт Ю₁³")
results.append(check("горизонт Ю₁³ → ПЛАСТ_Ю1-3 (or Ю13)",
    any("Ю1-3" in e or "Ю13" in e for e in r1["entities"])))

# 2. баженовская свита → ПЛАСТ_БЖ
r2 = normalizer.normalize("баженовская свита")
results.append(check("баженовская свита → ПЛАСТ_БЖ",
    any("БЖ" in e for e in r2["entities"])))

# 3. БС¹⁰ and bc10 → БС10
r3a = normalizer.normalize("БС¹⁰")
r3b = normalizer.normalize("bc10")
results.append(check("БС¹⁰ → ПЛАСТ_БС10",
    any("БС10" in e for e in r3a["entities"])))
results.append(check("bc10 → ПЛАСТ_БС10",
    any("БС10" in e for e in r3b["entities"])))

# 4. Ju1-3 → text contains Ю1-3
r4 = normalizer.normalize("Ju1-3")
results.append(check("Ju1-3 → text Ю1-3",
    "Ю1-3" in r4["text"]))
results.append(check("Ju1-3 → entity ПЛАСТ_Ю1-3",
    any("Ю1-3" in e for e in r4["entities"])))

# 5. скважина № 247 → СКВАЖИНА_247
r5 = normalizer.normalize("скважина № 247")
results.append(check("скважина № 247 → СКВАЖИНА_247",
    "СКВАЖИНА_247" in r5["entities"]))

# 6. Кн = 0.68 → НЕФТЕНАСЫЩЕННОСТЬ_0.68
r6 = normalizer.normalize("Кн = 0.68")
results.append(check("Кн = 0.68 → НЕФТЕНАСЫЩЕННОСТЬ_0.68",
    "НЕФТЕНАСЫЩЕННОСТЬ_0.68" in r6["entities"]))

# 7. needs_llm() returns False when coverage > threshold
r7 = normalizer.normalize("пласт Ю1-3 имеет Кн = 0.68 и Кп = 0.21")
results.append(check("needs_llm=False when entities found",
    r7["needs_llm"] == False))

# 8. needs_llm() returns True for text with no geological terms
long_text = "это очень длинный текст который содержит много обычных слов без геологических терминов вообще никаких"
r8 = normalizer.normalize(long_text)
results.append(check("needs_llm=True for non-geological text",
    r8["needs_llm"] == True))

# 9. Case-insensitivity
r9 = normalizer.normalize("БАЖЕНОВСКАЯ СВИТА")
results.append(check("БАЖЕНОВСКАЯ СВИТА (upper) → БЖ",
    any("БЖ" in e for e in r9["entities"])))

print()
passed = sum(results)
total = len(results)
print(f"RESULT: {passed}/{total} checks passed")
if passed == total:
    print("STATUS: ✅ BLOCK 3.1 WORKS")
else:
    print("STATUS: ⚠️ PARTIAL — see FAILs above")
    # Print details for failed checks
    print("\nDetailed outputs for failed tests:")
    for label, result in [
        ("горизонт Ю₁³", r1),
        ("баженовская свита", r2),
        ("БС¹⁰", r3a),
        ("bc10", r3b),
        ("Ju1-3", r4),
    ]:
        print(f"  {label} -> entities={result['entities']}, text={result['text']}")
