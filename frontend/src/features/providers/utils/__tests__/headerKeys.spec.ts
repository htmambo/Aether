import { describe, it, expect } from 'vitest'
import { mergeHeaderKeysUniqueSorted, splitHeaderKeysLines } from '../headerKeys'

describe('headerKeys utils', () => {
  it('splits keys by line and trims whitespace', () => {
    const input = '  User-Agent  \nX-Api-Key\r\n  X-Trace-Id '
    expect(splitHeaderKeysLines(input)).toEqual(['User-Agent', 'X-Api-Key', 'X-Trace-Id'])
  })

  it('filters empty lines', () => {
    const input = '\n  \r\nX-Test\n\n'
    expect(splitHeaderKeysLines(input)).toEqual(['X-Test'])
  })

  it('merges unique keys and sorts ascending (case-insensitive)', () => {
    const existing = ['x-b', 'X-A', '  ']
    const incoming = ['X-C', 'x-a', 'x-b', 'X-0']
    expect(mergeHeaderKeysUniqueSorted(existing, incoming)).toEqual(['X-0', 'X-A', 'x-b', 'X-C'])
  })
})
