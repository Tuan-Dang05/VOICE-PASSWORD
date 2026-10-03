import { describe, expect, it } from 'vitest'
import { transition } from './safeMachine'

describe('safe state machine', () => {
  it('follows a successful authentication flow', () => {
    expect(transition('locked', 'START')).toBe('listening')
    expect(transition('listening', 'STOP')).toBe('processing')
    expect(transition('processing', 'GRANT')).toBe('granted')
    expect(transition('granted', 'OPEN')).toBe('unlocked')
    expect(transition('unlocked', 'RESET')).toBe('locked')
  })

  it('never opens after a denial or invalid transition', () => {
    expect(transition('processing', 'DENY')).toBe('denied')
    expect(transition('denied', 'OPEN')).toBe('denied')
    expect(transition('locked', 'GRANT')).toBe('locked')
  })
})

