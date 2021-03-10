module.exports = {
  moduleFileExtensions: ['js', 'jsx', 'ts', 'tsx', 'json', 'vue'],
  transform: {
    '^.+\\.vue$': 'vue-jest',
    '^.+\\.jsx?$': 'babel-jest',
    '^.+\\.tsx?$': 'ts-jest',
  },
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    'ace-builds': '<rootDir>/node_modules/ace-builds',
  },
  testMatch: [
    '<rootDir>/**/*.spec.(js|jsx|ts|tsx)',
  ],
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  transformIgnorePatterns: ['<rootDir>/node_modules/'],
  coverageThreshold: {
    global: {
      branches: 90,
      functions: 85,
      lines: 90,
      statements: 90,
    },
  },
}
