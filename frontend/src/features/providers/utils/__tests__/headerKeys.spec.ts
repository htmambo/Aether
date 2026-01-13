import { describe, it, expect } from 'vitest'
import { splitHeaderKeysLines } from '../headerKeys'

describe('headerKeys utils', () => {
  it('splits keys by line and trims whitespace', () => {
    const input = '  User-Agent  \nX-Api-Key\r\n  X-Trace-Id '
    expect(splitHeaderKeysLines(input)).toEqual(['User-Agent', 'X-Api-Key', 'X-Trace-Id'])
  })

  it('filters empty lines', () => {
    const input = '\n  \r\nX-Test\n\n'
    expect(splitHeaderKeysLines(input)).toEqual(['X-Test'])
  })
})

