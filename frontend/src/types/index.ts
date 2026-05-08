export interface User {
  id: string
  email: string
  full_name: string
  role: 'admin' | 'editor' | 'viewer'
  is_active: boolean
  created_at: string
}

export interface VideoJob {
  id: string
  user_id: string
  status: 'pending' | 'processing' | 'done' | 'failed'
  original_filename: string
  s3_input_path?: string
  metadata_json: Record<string, any>
  s3_output_prefix?: string
  error_message?: string
  created_at: string
  updated_at: string
}

export interface Segment {
  id: string
  job_id: string
  start_time: number
  end_time: number
  transcript_text?: string
  scene_confidence: number
  energy_score: number
  llm_completeness: number
  llm_relevance: number
  llm_engagement: number
  llm_clarity: number
  llm_emotion: number
  llm_total_score: number
  llm_reasoning?: string
}

export interface Clip {
  id: string
  job_id: string
  segment_id?: string
  editor_decision: 'pending' | 'approved' | 'rejected' | 'edited'
  start_time?: number
  end_time?: number
  output_paths_json: Record<string, string>
  created_at: string
  updated_at: string
}

export interface Feedback {
  id: string
  clip_id: string
  user_id?: string
  action: string
  comment_text?: string
  created_at: string
}
