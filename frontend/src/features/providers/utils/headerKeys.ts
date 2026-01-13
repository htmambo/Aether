export function splitHeaderKeysLines(input: string): string[] {
  return input
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
}

function compareHeaderKeyAsc(a: string, b: string): number {
  const aLower = a.toLowerCase()
  const bLower = b.toLowerCase()
  if (aLower < bLower) return -1
  if (aLower > bLower) return 1
  if (a < b) return -1
  if (a > b) return 1
  return 0
}

export function mergeHeaderKeysUniqueSorted(existing: string[], incoming: string[]): string[] {
  const seen = new Map<string, string>()

  for (const key of existing) {
    const trimmed = key.trim()
    if (!trimmed) continue
    const lower = trimmed.toLowerCase()
    if (!seen.has(lower)) seen.set(lower, trimmed)
  }

  for (const key of incoming) {
    const trimmed = key.trim()
    if (!trimmed) continue
    const lower = trimmed.toLowerCase()
    if (!seen.has(lower)) seen.set(lower, trimmed)
  }

  return Array.from(seen.values()).sort(compareHeaderKeyAsc)
}
