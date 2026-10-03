ALTER TABLE voice_passwords ADD COLUMN speaker_threshold FLOAT;
ALTER TABLE authentication_attempts ADD COLUMN speaker_score FLOAT;
