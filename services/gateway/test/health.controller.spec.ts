import { HealthController } from '../src/health.controller'

describe('HealthController', () => {
  it('should expose a stable health payload', () => {
    const controller = new HealthController()
    const result = controller.check()

    expect(result.status).toBe('ok')
    expect(result.service).toBe('gateway')
    expect(result.version).toBe('3.7.0')
    expect(result.timestamp).toBeDefined()
  })
})
