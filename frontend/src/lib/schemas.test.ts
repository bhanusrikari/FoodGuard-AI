import { describe, expect, it } from 'vitest'
import { complaintSchema, loginSchema, registerSchema, reportSchema } from './schemas'

describe('loginSchema', () => {
  it('accepts a valid email/password', () => {
    const result = loginSchema.safeParse({ email: 'a@b.com', password: 'x' })
    expect(result.success).toBe(true)
  })

  it('rejects a missing email', () => {
    const result = loginSchema.safeParse({ email: '', password: 'x' })
    expect(result.success).toBe(false)
  })

  it('rejects an invalid email format', () => {
    const result = loginSchema.safeParse({ email: 'not-an-email', password: 'x' })
    expect(result.success).toBe(false)
  })

  it('rejects a missing password', () => {
    const result = loginSchema.safeParse({ email: 'a@b.com', password: '' })
    expect(result.success).toBe(false)
  })
})

describe('registerSchema', () => {
  const base = {
    first_name: 'Jane',
    last_name: 'Doe',
    email: 'jane@example.com',
    password: 'StrongPass99',
    preferred_language: 'en' as const,
  }

  it('accepts a fully valid payload', () => {
    expect(registerSchema.safeParse(base).success).toBe(true)
  })

  it('rejects a password shorter than 8 characters', () => {
    const result = registerSchema.safeParse({ ...base, password: 'short' })
    expect(result.success).toBe(false)
  })

  it('rejects an unsupported preferred_language value', () => {
    const result = registerSchema.safeParse({ ...base, preferred_language: 'fr' })
    expect(result.success).toBe(false)
  })

  it('accepts every language the backend User model actually supports', () => {
    for (const lang of ['en', 'te', 'hi', 'ta', 'kn', 'mr']) {
      expect(registerSchema.safeParse({ ...base, preferred_language: lang }).success).toBe(true)
    }
  })

  it('rejects a missing first name', () => {
    const result = registerSchema.safeParse({ ...base, first_name: '' })
    expect(result.success).toBe(false)
  })
})

describe('reportSchema', () => {
  it('accepts a valid report', () => {
    const result = reportSchema.safeParse({ title: 'Cold food', description: 'It was cold.', restaurant: '1' })
    expect(result.success).toBe(true)
  })

  it('rejects an empty title', () => {
    const result = reportSchema.safeParse({ title: '', description: 'x', restaurant: '1' })
    expect(result.success).toBe(false)
  })

  it('rejects a title over 255 characters', () => {
    const result = reportSchema.safeParse({ title: 'a'.repeat(256), description: 'x', restaurant: '1' })
    expect(result.success).toBe(false)
  })

  it('rejects a missing restaurant selection', () => {
    const result = reportSchema.safeParse({ title: 'x', description: 'x', restaurant: '' })
    expect(result.success).toBe(false)
  })

  it('rejects an empty description', () => {
    const result = reportSchema.safeParse({ title: 'x', description: '', restaurant: '1' })
    expect(result.success).toBe(false)
  })
})

describe('complaintSchema', () => {
  const base = {
    food_report: '1',
    title: 'Found plastic',
    description: 'There was plastic in the food.',
    category: 'FOREIGN_OBJECT' as const,
  }

  it('accepts a valid complaint', () => {
    expect(complaintSchema.safeParse(base).success).toBe(true)
  })

  it('rejects an invalid category', () => {
    const result = complaintSchema.safeParse({ ...base, category: 'NOT_A_REAL_CATEGORY' })
    expect(result.success).toBe(false)
  })

  it('rejects a missing food_report selection', () => {
    const result = complaintSchema.safeParse({ ...base, food_report: '' })
    expect(result.success).toBe(false)
  })

  it('accepts every category the backend actually defines', () => {
    for (const category of ['FOOD_QUALITY', 'SPOILAGE', 'FOREIGN_OBJECT', 'HYGIENE', 'TASTE_OR_ODOR', 'OTHER']) {
      expect(complaintSchema.safeParse({ ...base, category }).success).toBe(true)
    }
  })
})
