export type SafeState = 'locked' | 'listening' | 'processing' | 'granted' | 'denied' | 'unlocked'

export interface VoicePassword {
  id: number
  name: string
  phrase: string
  threshold: number | null
  speaker_threshold: number | null
  is_active: boolean
  failed_attempts: number
  locked_until: string | null
  created_at: string
  template_count: number
  command_template_count: number
  requires_reenrollment: boolean
}

export interface VerifyResult {
  granted: boolean
  score: number | null
  threshold: number | null
  processing_ms: number
  reason: string
  message?: string | null
  auto_lock_seconds: number
  lockout_until: string | null
  transcript: string | null
  command_matched: boolean | null
  speaker_matched: boolean | null
  dtw_score: number | null
  dtw_threshold: number | null
  dtw_matched: boolean | null
  speaker_score: number | null
  speaker_threshold: number | null
}

export interface CalibrationResult {
  accepted: boolean
  score: number
  previous_threshold: number
  threshold: number
  transcript: string
  command_matched: boolean
  reason: string
  command_samples: number
  command_ready: boolean
  dtw_threshold: number | null
}

export interface Attempt {
  id: number
  voice_password_id: number
  voice_password_name: string
  granted: boolean
  score: number | null
  speaker_score: number | null
  threshold: number | null
  dtw_score: number | null
  dtw_threshold: number | null
  processing_ms: number
  reason: string
  created_at: string
}

export interface Stats {
  total_attempts: number
  granted: number
  denied: number
  success_rate: number
  average_processing_ms: number
  p95_processing_ms: number
  far: number | null
  frr: number | null
}

export interface AlgorithmSettings {
  sample_rate: number
  n_mfcc: number
  frame_ms: number
  hop_ms: number
  default_threshold: number
  auto_lock_seconds: number
  max_failed_attempts: number
  lockout_seconds: number
  min_duration_seconds: number
  max_duration_seconds: number
  min_rms: number
}
