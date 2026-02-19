-- Log Analysis 설정 추가
INSERT INTO settings (key, value, description)
VALUES (
  'log_analysis',
  '{"enabled": false, "paths": [], "masking": {"enabled": true, "patterns": [{"name": "API Key", "regex": "(api[_-]?key)[=:].+", "replacement": "$1=***"}, {"name": "Password", "regex": "(password|pwd)[=:].+", "replacement": "$1=***"}]}, "defaults": {"maxLines": 500, "timeRangeMinutes": 60}}'::jsonb,
  '서버 로그 분석 설정'
) ON CONFLICT (key) DO NOTHING;
