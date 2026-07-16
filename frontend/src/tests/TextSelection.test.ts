import { describe, expect, it } from 'vitest'
import { resolveTextSelection } from '../utils/textSelection'


describe('resolveTextSelection', () => {
  it('computes normalized DOM text offsets across text nodes and Unicode', () => {
    const root = document.createElement('div')
    root.append('前言\n')
    const span = document.createElement('span')
    span.textContent = '论文学习'
    root.append(span, '结束')
    const range = document.createRange()
    range.setStart(root.firstChild!, 2)
    range.setEnd(span.firstChild!, 2)
    expect(resolveTextSelection(root, range)).toEqual({ start: 2, end: 5, text: '\n论文' })
  })

  it('rejects cross-container, blank, collapsed, and oversized selections', () => {
    const root = document.createElement('div')
    root.textContent = 'valid text'
    const outside = document.createElement('div')
    outside.textContent = 'outside'
    const cross = document.createRange()
    cross.setStart(root.firstChild!, 0)
    cross.setEnd(outside.firstChild!, 2)
    expect(resolveTextSelection(root, cross)).toBeNull()

    const collapsed = document.createRange()
    collapsed.setStart(root.firstChild!, 1)
    collapsed.collapse(true)
    expect(resolveTextSelection(root, collapsed)).toBeNull()

    const oversized = document.createRange()
    oversized.selectNodeContents(root)
    expect(resolveTextSelection(root, oversized, 3)).toBeNull()

    root.textContent = '   '
    const blank = document.createRange()
    blank.selectNodeContents(root)
    expect(resolveTextSelection(root, blank)).toBeNull()
  })
})
