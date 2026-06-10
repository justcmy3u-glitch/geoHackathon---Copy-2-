from ner.local_normalizer import LocalNormalizer

normalizer = LocalNormalizer()
test_cases = [
    "В скважине № 247 вскрыт горизонт Ю₁³ на глубине 2847 м",
    "пласт Ю1-3 имеет Кн = 0.68 и Кп = 0.21",
    "баженовская свита в скважинах №312, №445 месторождения X",
    "Ju1-3 коррелируется с БС¹⁰",
]
for text in test_cases:
    result = normalizer.normalize(text)
    print("IN: ", text)
    print("OUT entities:", result["entities"])
    print("    needs_llm:", result["needs_llm"])
    print()
