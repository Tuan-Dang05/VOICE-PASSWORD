import type { SafeState } from '../types'

export type SafeEvent = 'START' | 'STOP' | 'GRANT' | 'DENY' | 'OPEN' | 'RESET' | 'ERROR'

export function transition(state: SafeState, event: SafeEvent): SafeState {
  const transitions: Partial<Record<SafeState, Partial<Record<SafeEvent, SafeState>>>> = {
    locked: { START: 'listening' },
    listening: { STOP: 'processing', ERROR: 'denied' },
    processing: { GRANT: 'granted', DENY: 'denied', ERROR: 'denied' },
    granted: { OPEN: 'unlocked', RESET: 'locked' },
    denied: { RESET: 'locked' },
    unlocked: { RESET: 'locked' },
  }
  return transitions[state]?.[event] ?? state
}

