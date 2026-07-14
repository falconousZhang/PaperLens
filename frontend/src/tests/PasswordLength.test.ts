import { describe, expect, it } from 'vitest'
import { passwordCodePointLength } from '../utils/password'


describe('passwordCodePointLength', () => {
  it('counts Unicode code points instead of UTF-16 code units', () => {
    expect('😀'.length).toBe(2)
    expect(passwordCodePointLength('😀'.repeat(15))).toBe(15)
    expect(passwordCodePointLength('文'.repeat(128))).toBe(128)
  })
})
