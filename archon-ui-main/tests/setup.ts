import { expect, afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'

// Set required environment variables for tests
process.env.ARCHON_SERVER_PORT = '8181'

// Mock import.meta.env for tests
Object.defineProperty(import.meta, 'env', {
  value: {
    DEV: true,
    PROD: false,
    VITE_HOST: 'localhost',
    VITE_PORT: '8181',
    VITE_ALLOWED_HOSTS: '',
  },
  configurable: true,
})

// Clean up after each test
afterEach(() => {
  cleanup()
})

// Simple mocks only - fetch
global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(''),
    status: 200,
    headers: new Headers(),
  } as Response)
) as any

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(() => null),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})

// Mock DOM methods that might not exist in test environment
Element.prototype.scrollIntoView = vi.fn()
window.HTMLElement.prototype.scrollIntoView = vi.fn()

// Mock lucide-react icons - use actual module with passthrough
// This approach ensures all icons are available while still allowing simple test assertions
vi.mock('lucide-react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('lucide-react')>()
  return {
    ...actual,
  }
})

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))