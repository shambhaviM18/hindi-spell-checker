import sys
sys.path.insert(0, '/backend')

import math
import regex as re
import json
from collections import defaultdict, Counter
from typing import List, Tuple, Dict, Iterable, Set

DEVANAGARI_START = 0x0900
DEVANAGARI_END = 0x097F
VIRAMA = '\u094D'
ANUSVARA = '\u0902'
ANUSVARA_ALT = '\u0950'
VISARGA = '\u0903'
NUKTA = '\u093C'

VOWEL_SIGNS = {
    '\u093E', '\u093F', '\u0940', '\u0941', '\u0942', '\u0943', '\u0944', '\u0947', '\u0948', '\u094B', '\u094C'
}

VOWELS = {
    '\u0904','\u0905','\u0906','\u0907','\u0908','\u0909','\u090A','\u090B','\u090C','\u090F','\u0910','\u0913','\u0914'
}

CONSONANTS = [chr(x) for x in range(0x0915, 0x093A)]
PUNCTUATION_RE = re.compile(r"[\p{P}\p{S}]+")

TRANSLIT_MAP = {
    'क':'k','ख':'kh','ग':'g','घ':'gh','ङ':'ng',
    'च':'ch','छ':'chh','ज':'j','झ':'jh','ञ':'ny',
    'ट':'t','ठ':'th','ड':'d','ढ':'dh','ण':'n',
    'त':'t','थ':'th','द':'d','ध':'dh','न':'n',
    'प':'p','फ':'ph','ब':'b','भ':'bh','म':'m',
    'य':'y','र':'r','ल':'l','व':'v','श':'sh',
    'ष':'sh','स':'s','ह':'h',
}

NORMALIZATION_MAP = {
    '\u0958':'क', '\u0959':'ख', '\u095A':'ज', '\u095B':'ड', '\u095C':'ढ', '\u095D':'फ़',
}

WORD_FREQ = Counter({
    'मैं': 5000, 'तुम': 3000, 'यह': 8000, 'वह': 6000, 'है': 15000, 'हैं': 9000, 'नहीं': 7000,
    'एक': 12000, 'दो': 4000, 'तीन': 2000, 'किताब': 3000, 'किताबें': 2500, 'लड़का': 2700, 'लड़की': 2600,
    'घर': 8000, 'रास्ता': 1800, 'स्कूल': 3500, 'कॉलेज': 1800, 'खाना': 4200, 'पीना': 2000, 'खुश': 3000,
    'दुःख': 500, 'सुंदर': 1800, 'बड़ा': 4000, 'छोटा': 3500, 'काम': 9000, 'पानी': 7000, 'संपर्क': 600,
    'भारत': 9000, 'हिन्दी': 5000, 'भाषा': 4800, 'लोक': 300, 'जन': 200, 'समाचार': 1200, 'रक्त': 50,
    'रात': 3600, 'दिन': 8900, 'सुबह': 1200, 'शाम': 1100, 'खिड़की': 800, 'दरवाज़ा': 900, 'बाहर': 3400,
    'अंदर': 2000, 'सड़क': 2100, 'वाहन': 1300, 'ट्रेन': 1700, 'हवाईजहाज': 400, 'बस': 2900, 'गाड़ी': 2600,
    'खर्च': 800, 'कम': 4400, 'ज्यादा': 4300, 'खेल': 2400, 'गीत': 900, 'संगीत': 1200, 'चित्र': 700,
    'कला': 1500, 'स्वास्थ्य': 800, 'रोग': 600, 'दवा': 400, 'डॉक्टर': 1200, 'अध्यापक': 700,
    'छात्र': 2100, 'कक्षा': 1600, 'गुरु': 500, 'प्रेम': 2600, 'प्यार': 7000, 'दोस्त': 3500, 'परिवार': 3800,
    'माता': 1200, 'पिता': 1400, 'भाई': 1700, 'बहन': 1600, 'बाज़ार': 1100, 'दुकान': 2000, 'मोबाइल': 1200,
    'कम्प्युटर': 800, 'इंटरनेट': 1800, 'समस्या': 1500, 'समाधान': 700, 'आराम': 900, 'यात्रा': 1300,
    'शिक्षा': 2200, 'परीक्षा': 2400, 'नक्शा': 200, 'सुविधा': 450, 'शहर': 4200, 'गाँव': 900,
    'खरीद': 600, 'बेचना': 200, 'उत्पाद': 500, 'सेना': 800, 'नौकरी': 2200, 'कर्मचारी': 800, 'वेतन': 400,
    'नियम': 700, 'कानून': 1200, 'नीति': 600, 'विधि': 300, 'अधिकार': 900, 'कर्तव्य': 350, 'धर्म': 1200,
    'समाज': 1800, 'राज्य': 900, 'सरकार': 1600, 'चुनाव': 700, 'वोट': 500, 'मौसम': 1000, 'तापमान': 200,
    'बारिश': 1500, 'तूफान': 100, 'बर्फ': 80, 'बहार': 250, 'फल': 600, 'सब्ज़ी': 500, 'दाल': 400,
    'से': 14000, 'को': 13000, 'पर': 8000, 'में': 15000, 'का': 16000, 'की': 14000, 'के': 12000,
})

BIGRAM_FREQ = Counter({
    ('मैं','हूँ'): 3000, ('वह','है'): 2500, ('यह','है'): 4000, ('एक','लडका'): 800, ('एक','लड़की'): 750,
    ('किताब','है'): 900, ('खाना','खाया'): 400, ('पानी','पीया'): 300, ('स्कूल','जाता'): 600, ('स्कूल','गया'): 150,
    ('दोस्त','है'): 500, ('भारत','है'): 1000, ('धन्यवाद','बहुत'): 200, ('धन्यवाद','आपका'): 150,
    ('आनंद','मिलता'): 80, ('मैं','खुश'): 300, ('वह','आया'): 400, ('वह','गया'): 350,
})

KNOWN_WORDS = set(WORD_FREQ.keys())

def is_devanagari(text: str) -> bool:
    for ch in text:
        code = ord(ch)
        if DEVANAGARI_START <= code <= DEVANAGARI_END:
            return True
    return False

def remove_diacritics(word: str) -> str:
    normalized = ''.join(ch for ch in word if ch != NUKTA)
    normalized = re.sub(r'[' + VIRAMA + r']+', VIRAMA, normalized)
    normalized = re.sub(r'[' + ANUSVARA + r']+', ANUSVARA, normalized)
    return normalized

def normalize_word(word: str) -> str:
    w = word.strip()
    w = ''.join(NORMALIZATION_MAP.get(ch, ch) for ch in w)
    w = remove_diacritics(w)
    w = re.sub(r'\s+', ' ', w)
    return w

def edits1(word: str) -> Set[str]:
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [L + R[1:] for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
    replaces = []
    for L, R in splits:
        if R:
            ch = R[0]
            pool = list(CONSONANTS) + list(VOWEL_SIGNS)
            for c in pool:
                if c != ch:
                    replaces.append(L + c + R[1:])
    inserts = [L + c + R for L, R in splits for c in (list(CONSONANTS) + list(VOWEL_SIGNS))]
    return set(deletes + transposes + replaces + inserts)

def edits2(word: str) -> Set[str]:
    return set(e2 for e1 in edits1(word) for e2 in edits1(e1))

def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev_row = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur_row = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            insert_cost = cur_row[j-1] + 1
            delete_cost = prev_row[j] + 1
            replace_cost = prev_row[j-1] + (0 if ca == cb else 1)
            cur_row[j] = min(insert_cost, delete_cost, replace_cost)
        prev_row = cur_row
    return prev_row[-1]

def known(words: Iterable[str]) -> Set[str]:
    return set(w for w in words if w in KNOWN_WORDS)

def transliterate_for_compare(word: str) -> str:
    out = []
    skip_next = False
    for i, ch in enumerate(word):
        if skip_next:
            skip_next = False
            continue
        if ch in TRANSLIT_MAP and i+1 < len(word) and word[i+1] == VIRAMA:
            if i+2 < len(word) and word[i+2] in TRANSLIT_MAP:
                out.append(TRANSLIT_MAP[ch] + TRANSLIT_MAP[word[i+2]])
                skip_next = True
                continue
        out.append(TRANSLIT_MAP.get(ch, ch))
    return ''.join(out)

def common_prefix_length(a: str, b: str) -> int:
    i = 0
    for ca, cb in zip(a, b):
        if ca == cb:
            i += 1
        else:
            break
    return i

def score_for(source: str, candidate: str, edit_distance: int) -> float:
    freq = WORD_FREQ.get(candidate, 1)
    frequency_score = math.log(freq + 1)
    distance_penalty = math.exp(-0.8 * edit_distance)
    src_trans = transliterate_for_compare(source)
    cand_trans = transliterate_for_compare(candidate)
    phonetic_bonus = 1.0
    common_pref_len = common_prefix_length(src_trans, cand_trans)
    if common_pref_len > 0:
        phonetic_bonus += 0.2 * common_pref_len
    score = frequency_score * distance_penalty * phonetic_bonus
    return score

def candidates(word: str, max_candidates: int = 20) -> List[Tuple[str, float]]:
    word = normalize_word(word)
    cand_set: Set[str] = set()
    if word in KNOWN_WORDS:
        return [(word, score_for(word, word, 0))]
    e1 = edits1(word)
    cand_set.update(known(e1))
    if not cand_set:
        e2 = edits2(word)
        cand_set.update(known(e2))
    if not cand_set:
        distances = []
        for w in KNOWN_WORDS:
            d = levenshtein(word, w)
            distances.append((d, w))
        distances.sort()
        for d, w in distances[:max_candidates * 3]:
            cand_set.add(w)
    scored = []
    for cand in cand_set:
        d = levenshtein(word, cand)
        s = score_for(word, cand, d)
        scored.append((cand, s))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored[:max_candidates]

def score_with_context(prev_word: str, cand: str, next_word: str = None) -> float:
    score = 0.0
    if prev_word:
        score += math.log(BIGRAM_FREQ.get((prev_word, cand), 0) + 1)
    if next_word:
        score += math.log(BIGRAM_FREQ.get((cand, next_word), 0) + 1)
    return score

def tokenize(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []
    text_spaced = PUNCTUATION_RE.sub(lambda m: ' ' + m.group(0) + ' ', text)
    tokens = [t for t in text_spaced.split() if t]
    return tokens

class SpellChecker:
    def __init__(self, word_freq: Counter = None, bigram_freq: Counter = None):
        self.word_freq = word_freq or WORD_FREQ
        self.bigram_freq = bigram_freq or BIGRAM_FREQ
        self.known_words = set(self.word_freq.keys())

    def normalize(self, token: str) -> str:
        return normalize_word(token)

    def correct_word(self, word: str, context_prev: str = None, context_next: str = None) -> Tuple[str, List[Tuple[str, float]]]:
        w = self.normalize(word)
        if w in self.known_words:
            return w, [(w, float('inf'))]
        cand_scores = candidates(w, max_candidates=15)
        scored_context = []
        for cand, score in cand_scores:
            ctx_bonus = score_with_context(context_prev, cand, context_next)
            scored_context.append((cand, score + ctx_bonus))
        if not scored_context:
            return word, []
        scored_context.sort(key=lambda x: (-x[1], x[0]))
        best = scored_context[0][0]
        return best, scored_context

    def correct_sentence(self, sentence: str) -> Tuple[str, List[Tuple[int, str, List[Tuple[str, float]]]]]:
        tokens = tokenize(sentence)
        corrected_tokens = tokens[:]
        corrections = []
        for i, token in enumerate(tokens):
            if not is_devanagari(token):
                continue
            prev_tok = tokens[i-1] if i-1 >= 0 else None
            next_tok = tokens[i+1] if i+1 < len(tokens) else None
            best, ranked = self.correct_word(token, context_prev=prev_tok, context_next=next_tok)
            if ranked and ranked[0][0] != token:
                corrected_tokens[i] = best
                corrections.append((i, token, ranked))
        corrected_sentence = ' '.join(corrected_tokens)
        return corrected_sentence, corrections
