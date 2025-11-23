// Hindi Spell Checker - Core Logic
interface WordFreqCounter {
  [key: string]: number
}

const DEVANAGARI_START = 0x0900
const DEVANAGARI_END = 0x097f
const VIRAMA = "\u094D"
const NUKTA = "\u093C"

const VOWEL_SIGNS = new Set([
  "\u093E",
  "\u093F",
  "\u0940",
  "\u0941",
  "\u0942",
  "\u0943",
  "\u0944",
  "\u0947",
  "\u0948",
  "\u094B",
  "\u094C",
])

const CONSONANTS = Array.from({ length: 0x093a - 0x0915 }, (_, i) => String.fromCharCode(0x0915 + i))

const WORD_FREQ: WordFreqCounter = {
  मैं: 5000,
  तुम: 3000,
  यह: 8000,
  वह: 6000,
  है: 15000,
  हैं: 9000,
  नहीं: 7000,
  एक: 12000,
  दो: 4000,
  तीन: 2000,
  किताब: 3000,
  किताबें: 2500,
  लड़का: 2700,
  लड़की: 2600,
  घर: 8000,
  रास्ता: 1800,
  स्कूल: 3500,
  कॉलेज: 1800,
  खाना: 4200,
  पीना: 2000,
  खुश: 3000,
  जाता: 3000,
  गया: 2500,
  आया: 2200,
  पढ़ता: 2800,
  करता: 3200,
  देता: 1800,
  लेता: 1600,
}

const BIGRAM_FREQ: { [key: string]: number } = {
  "मैं,हूँ": 3000,
  "वह,है": 2500,
  "यह,है": 4000,
  "स्कूल,जाता": 600,
}

function isDevanagari(text: string): boolean {
  for (const ch of text) {
    const code = ch.charCodeAt(0)
    if (code >= DEVANAGARI_START && code <= DEVANAGARI_END) return true
  }
  return false
}

function removeDiacritics(word: string): string {
  let normalized = word
    .split("")
    .filter((ch) => ch !== NUKTA)
    .join("")
  normalized = normalized.replace(new RegExp(`[${VIRAMA}]+`, "g"), VIRAMA)
  return normalized
}

function normalizeWord(word: string): string {
  let w = word.trim()
  w = removeDiacritics(w)
  w = w.replace(/\s+/g, " ")
  return w
}

function levenshtein(a: string, b: string): number {
  if (a === b) return 0
  if (!a) return b.length
  if (!b) return a.length

  const prevRow = Array.from({ length: b.length + 1 }, (_, i) => i)

  for (let i = 1; i <= a.length; i++) {
    const curRow = [i]
    for (let j = 1; j <= b.length; j++) {
      const insertCost = curRow[j - 1] + 1
      const deleteCost = prevRow[j] + 1
      const replaceCost = prevRow[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1)
      curRow[j] = Math.min(insertCost, deleteCost, replaceCost)
    }
    prevRow.length = 0
    prevRow.push(...curRow)
  }

  return prevRow[b.length]
}

function edits1(word: string): Set<string> {
  const result = new Set<string>()
  const splits = []

  for (let i = 0; i <= word.length; i++) {
    splits.push([word.slice(0, i), word.slice(i)])
  }

  // Deletions
  for (const [L, R] of splits) {
    if (R) result.add(L + R.slice(1))
  }

  // Transpositions
  for (const [L, R] of splits) {
    if (R.length > 1) result.add(L + R[1] + R[0] + R.slice(2))
  }

  // Replacements
  for (const [L, R] of splits) {
    if (R) {
      for (const c of [...CONSONANTS, ...Array.from(VOWEL_SIGNS)]) {
        if (c !== R[0]) result.add(L + c + R.slice(1))
      }
    }
  }

  // Insertions
  for (const [L, R] of splits) {
    for (const c of [...CONSONANTS, ...Array.from(VOWEL_SIGNS)]) {
      result.add(L + c + R)
    }
  }

  return result
}

function scoreFor(source: string, candidate: string, editDistance: number): number {
  const freq = WORD_FREQ[candidate] || 1
  const frequencyScore = Math.log(freq + 1)
  const distancePenalty = Math.exp(-0.8 * editDistance)
  const phoneticsBonus = 1.0

  return frequencyScore * distancePenalty * phoneticsBonus
}

function findCandidates(word: string, maxCandidates = 15): Array<[string, number]> {
  const w = normalizeWord(word)

  if (WORD_FREQ[w]) {
    return [[w, scoreFor(w, w, 0)]]
  }

  const candidates = new Set<string>()
  const e1 = edits1(w)

  for (const candidate of e1) {
    if (WORD_FREQ[candidate]) candidates.add(candidate)
  }

  if (candidates.size === 0) {
    for (const known of Object.keys(WORD_FREQ)) {
      const dist = levenshtein(w, known)
      if (dist <= 2) candidates.add(known)
    }
  }

  if (candidates.size === 0) {
    const distances: Array<[number, string]> = []
    for (const known of Object.keys(WORD_FREQ)) {
      distances.push([levenshtein(w, known), known])
    }
    distances.sort((a, b) => a[0] - b[0])
    for (let i = 0; i < Math.min(maxCandidates * 2, distances.length); i++) {
      candidates.add(distances[i][1])
    }
  }

  const scored: Array<[string, number]> = []
  for (const cand of candidates) {
    const d = levenshtein(w, cand)
    const s = scoreFor(w, cand, d)
    scored.push([cand, s])
  }

  scored.sort((a, b) => b[1] - a[1])
  return scored.slice(0, maxCandidates)
}

function tokenize(text: string): string[] {
  const punctuationRegex = /[\p{P}\p{S}]+/gu
  const textSpaced = text.replace(punctuationRegex, (m) => ` ${m} `)
  return textSpaced.split(/\s+/).filter((t) => t.length > 0)
}

export interface CorrectionResult {
  index: number
  original: string
  suggestions: Array<[string, number]>
}

export function correctSentence(sentence: string): { corrected: string; corrections: CorrectionResult[] } {
  const tokens = tokenize(sentence)
  const correctedTokens = [...tokens]
  const corrections: CorrectionResult[] = []

  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i]

    if (!isDevanagari(token)) continue

    const candidates = findCandidates(token, 5)
    if (candidates.length > 0 && candidates[0][0] !== token) {
      correctedTokens[i] = candidates[0][0]
      corrections.push({
        index: i,
        original: token,
        suggestions: candidates.map((c) => [c[0], Math.round(c[1] * 100)]),
      })
    }
  }

  return {
    corrected: correctedTokens.join(" "),
    corrections,
  }
}
