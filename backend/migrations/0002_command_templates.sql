CREATE TABLE voice_command_templates (
  id INTEGER PRIMARY KEY,
  voice_password_id INTEGER NOT NULL REFERENCES voice_passwords(id) ON DELETE CASCADE,
  feature_path VARCHAR(500) NOT NULL UNIQUE,
  speaker_score FLOAT NOT NULL,
  dtw_threshold FLOAT,
  created_at DATETIME NOT NULL
);
ALTER TABLE authentication_attempts ADD COLUMN dtw_score FLOAT;
ALTER TABLE authentication_attempts ADD COLUMN dtw_threshold FLOAT;
