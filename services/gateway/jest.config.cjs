/** @type {import('jest').Config} */
module.exports = {
  rootDir: '.',
  testEnvironment: 'node',
  moduleFileExtensions: ['ts', 'js', 'json'],
  testMatch: ['<rootDir>/test/**/*.spec.ts'],
  transform: {
    '^.+\\.ts$': [
      'ts-jest',
      {
        tsconfig: '<rootDir>/tsconfig.json',
      },
    ],
  },
  moduleNameMapper: {
    '^@dreamhelp/auth$': '<rootDir>/../../packages/auth/src',
    '^@dreamhelp/config$': '<rootDir>/../../packages/config/src',
    '^@dreamhelp/database$': '<rootDir>/../../packages/database/src',
    '^@dreamhelp/logger$': '<rootDir>/../../packages/logger/src',
    '^@dreamhelp/ts-sdk$': '<rootDir>/../../packages/ts-sdk/src',
  },
  transformIgnorePatterns: ['/node_modules/(?!@dreamhelp/)'],
  collectCoverageFrom: ['src/**/*.ts'],
}
