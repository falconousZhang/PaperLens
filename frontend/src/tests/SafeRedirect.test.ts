import { describe, expect, it } from 'vitest'
import { safeInternalRedirect } from '../router/safeRedirect'


describe('safeInternalRedirect', () => {
  it('allows only application-relative paths', () => {
    expect(safeInternalRedirect('/papers/abc?tab=review')).toBe('/papers/abc?tab=review')
    expect(safeInternalRedirect('//evil.example')).toBe('/papers')
    expect(safeInternalRedirect('https://evil.example')).toBe('/papers')
    expect(safeInternalRedirect('/\\evil.example')).toBe('/papers')
    expect(safeInternalRedirect(['/papers'])).toBe('/papers')
    expect(safeInternalRedirect(null)).toBe('/papers')
  })
})
