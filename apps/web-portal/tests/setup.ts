process.env.DATABASE_URL =
  process.env.DATABASE_URL || 'postgresql://test:test@127.0.0.1:5432/dreamhelper'
process.env.JWT_SECRET = process.env.JWT_SECRET || 'test-secret'
process.env.BRAIN_CORE_URL = process.env.BRAIN_CORE_URL || 'http://127.0.0.1:8000'
