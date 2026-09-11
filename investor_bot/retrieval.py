"""Дуже простий пошук релевантних фрагментів під питання інвестора — без
векторної бази: рахуємо перетин слів питання й фрагмента. Достатньо для
десятків документів на проект; для сотень варто буде замінити на embeddings.
"""
import re

WORD_RE = re.compile(r"[а-щьюяїієґ0-9a-z]+", re.IGNORECASE)

STOPWORDS = {
    "яка", "який", "яке", "які", "що", "де", "чи", "коли", "як", "для",
    "по", "на", "в", "у", "з", "із", "та", "і", "й", "цей", "ця", "це",
    "буде", "є", "цьому", "цього", "мені", "нам", "мого", "моєї",
}


def _tokens(text):
    return {w for w in WORD_RE.findall(text.lower()) if w not in STOPWORDS and len(w) > 2}


def top_chunks(question, chunks, k=25, max_chars=45000):
    """chunks: list of dicts з ключами 'text', 'material_title', 'location', ...
    Повертає до k найрелевантніших, у межах max_chars сумарно."""
    q_tokens = _tokens(question)
    if not q_tokens:
        scored = [(0, c) for c in chunks]
    else:
        scored = []
        for c in chunks:
            overlap = len(q_tokens & _tokens(c["text"]))
            if overlap:
                scored.append((overlap, c))
        scored.sort(key=lambda x: x[0], reverse=True)

    if not scored:
        # Нічого не перетнулось за ключовими словами — краще віддати
        # найсвіжіші фрагменти, ніж нічого, і чесно сказати межі відповіді.
        scored = [(0, c) for c in chunks[-k:]]

    picked = []
    total = 0
    for _, c in scored[:k]:
        if total + len(c["text"]) > max_chars and picked:
            break
        picked.append(c)
        total += len(c["text"])
    return picked
