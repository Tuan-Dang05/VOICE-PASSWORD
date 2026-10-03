-- Reference schema for the SQLite demo. The application creates the same tables
-- from SQLAlchemy metadata on first start.
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  username VARCHAR(80) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'admin',
  created_at DATETIME NOT NULL
);
CREATE TABLE voice_passwords (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  phrase VARCHAR(255) NOT NULL,
  threshold FLOAT,
  is_active BOOLEAN NOT NULL DEFAULT 0,
  config_version VARCHAR(30) NOT NULL,
  failed_attempts INTEGER NOT NULL DEFAULT 0,
  locked_until DATETIME,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
CREATE TABLE voice_templates (
  id INTEGER PRIMARY KEY,
  voice_password_id INTEGER NOT NULL REFERENCES voice_passwords(id) ON DELETE CASCADE,
  feature_path VARCHAR(500) NOT NULL UNIQUE,
  duration_seconds FLOAT NOT NULL,
  quality JSON NOT NULL,
  created_at DATETIME NOT NULL
);
CREATE TABLE authentication_attempts (
  id INTEGER PRIMARY KEY,
  voice_password_id INTEGER NOT NULL REFERENCES voice_passwords(id) ON DELETE CASCADE,
  granted BOOLEAN NOT NULL,
  score FLOAT,
  threshold FLOAT,
  processing_ms FLOAT NOT NULL,
  reason VARCHAR(80) NOT NULL,
  ground_truth VARCHAR(20),
  created_at DATETIME NOT NULL
);
CREATE TABLE algorithm_configs (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  sample_rate INTEGER NOT NULL,
  n_mfcc INTEGER NOT NULL,
  frame_ms FLOAT NOT NULL,
  hop_ms FLOAT NOT NULL,
  default_threshold FLOAT NOT NULL,
  auto_lock_seconds INTEGER NOT NULL,
  max_failed_attempts INTEGER NOT NULL,
  lockout_seconds INTEGER NOT NULL,
  min_duration_seconds FLOAT NOT NULL,
  max_duration_seconds FLOAT NOT NULL,
  min_rms FLOAT NOT NULL,
  updated_at DATETIME NOT NULL
);

