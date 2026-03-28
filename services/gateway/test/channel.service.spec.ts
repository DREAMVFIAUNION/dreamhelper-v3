/**
 * ChannelService 单元测试 — 适配器注册、消息路由、指标统计
 */

import { Test, TestingModule } from '@nestjs/testing'
import { ChannelService } from '../src/modules/channels/channel.service'
import { UserMappingService } from '../src/modules/channels/user-mapping.service'

// Mock UserMappingService to avoid DB calls
const mockUserMapping = {
  getOrCreateMapping: jest.fn().mockResolvedValue({
    channelType: 'telegram',
    channelUserId: '12345',
    systemUserId: 'sys-uuid',
    createdAt: new Date(),
    lastActiveAt: new Date(),
  }),
  getSessionId: jest.fn().mockReturnValue('telegram_12345'),
  getStats: jest.fn().mockResolvedValue({ total: 1, byChannel: { telegram: 1 } }),
  bindToUser: jest.fn().mockResolvedValue(true),
  listMappings: jest.fn().mockResolvedValue([]),
}

describe('ChannelService', () => {
  let service: ChannelService
  let consoleErrorSpy: jest.SpyInstance

  beforeEach(async () => {
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => undefined)

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        ChannelService,
        { provide: UserMappingService, useValue: mockUserMapping },
      ],
    }).compile()

    service = module.get<ChannelService>(ChannelService)
  })

  afterEach(() => {
    consoleErrorSpy.mockRestore()
  })

  it('should be defined', () => {
    expect(service).toBeDefined()
  })

  it('should have 3 adapters registered', () => {
    expect(service.getAdapter('telegram')).toBeDefined()
    expect(service.getAdapter('wechat')).toBeDefined()
    expect(service.getAdapter('wecom')).toBeDefined()
  })

  it('should return undefined for unknown channel', () => {
    expect(service.getAdapter('discord' as any)).toBeUndefined()
  })

  it('should return channel stats', async () => {
    const stats = await service.getChannelStats()
    expect(stats).toHaveProperty('telegram')
    expect(stats).toHaveProperty('wechat')
    expect(stats).toHaveProperty('wecom')
    expect(stats.telegram.metrics).toBeDefined()
    expect(stats.telegram.metrics.received).toBe(0)
  })

  it('should handle null inbound for unknown channel', async () => {
    const result = await service.handleInbound('discord' as any, {})
    expect(result).toBeNull()
  })
})
