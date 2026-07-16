export interface TextSelectionOffset {
  start: number
  end: number
  text: string
}

export function resolveTextSelection(root: HTMLElement, range: Range, maximum = 5000): TextSelectionOffset | null {
  if (!root.contains(range.startContainer) || !root.contains(range.endContainer) || range.collapsed) return null
  const text = range.toString()
  if (!text.trim() || text.length > maximum) return null
  const prefix = document.createRange()
  prefix.selectNodeContents(root)
  try {
    prefix.setEnd(range.startContainer, range.startOffset)
  } catch {
    return null
  }
  const start = prefix.toString().length
  const end = start + text.length
  const fullText = root.textContent || ''
  if (start < 0 || end <= start || end > fullText.length || fullText.slice(start, end) !== text) return null
  return { start, end, text }
}
