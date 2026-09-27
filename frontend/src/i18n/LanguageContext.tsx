import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { authApi } from '@/api/auth'
import { useAuth } from '@/context/AuthContext'
import { en, type TranslationKey } from './en'
import { hi } from './hi'
import { te } from './te'

/** Languages with a real translation dictionary in this app. The backend
 * User.Language field supports more codes (ta/kn/mr) for future
 * expansion — see frontend/src/types/user.ts's LANGUAGE_LABELS — but the
 * UI only ever renders one of these three today; anything else falls
 * back to English (see useTranslation()'s `t()` below). */
export const SUPPORTED_UI_LANGUAGES = ['en', 'te', 'hi'] as const
export type UiLanguage = (typeof SUPPORTED_UI_LANGUAGES)[number]

const DICTIONARIES: Record<UiLanguage, Partial<Record<TranslationKey, string>>> = { en, te, hi }

const STORAGE_KEY = 'foodguard.language'

function isSupportedUiLanguage(value: string | null | undefined): value is UiLanguage {
  return !!value && (SUPPORTED_UI_LANGUAGES as readonly string[]).includes(value)
}

function readStoredLanguage(): UiLanguage | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return isSupportedUiLanguage(stored) ? stored : null
  } catch {
    // Private browsing / storage disabled — treat as "no stored preference".
    return null
  }
}

interface LanguageContextValue {
  language: UiLanguage
  setLanguage: (lang: UiLanguage) => void
  t: (key: TranslationKey, vars?: Record<string, string | number>) => string
}

const LanguageContext = createContext<LanguageContextValue | null>(null)

export function LanguageProvider({ children }: { children: ReactNode }) {
  const { user, isAuthenticated } = useAuth()
  const [language, setLanguageState] = useState<UiLanguage>(() => readStoredLanguage() ?? 'en')

  // First time on this device (no explicit local choice saved yet), adopt
  // the signed-in user's server-side preference if we have a translation
  // dictionary for it. Never overrides a choice the person already made
  // on this device/browser.
  useEffect(() => {
    if (!isAuthenticated || !user) return
    if (readStoredLanguage() !== null) return
    if (isSupportedUiLanguage(user.preferred_language)) {
      setLanguageState(user.preferred_language)
    }
  }, [isAuthenticated, user])

  const setLanguage = useCallback(
    (lang: UiLanguage) => {
      setLanguageState(lang)
      try {
        localStorage.setItem(STORAGE_KEY, lang)
      } catch {
        // Best-effort persistence only — the in-memory state above is
        // what actually drives the current page, regardless.
      }
      if (isAuthenticated) {
        // Best-effort sync to the backend so the choice follows the user
        // across devices/sessions. A failed PATCH must never block or
        // revert the language switch that already happened above.
        void authApi.updatePreferredLanguage(lang).catch(() => {})
      }
    },
    [isAuthenticated],
  )

  const t = useCallback(
    (key: TranslationKey, vars?: Record<string, string | number>): string => {
      const text = DICTIONARIES[language][key] ?? en[key]
      if (!vars) return text
      return Object.entries(vars).reduce(
        (result, [name, value]) => result.replaceAll(`{${name}}`, String(value)),
        text,
      )
    },
    [language],
  )

  const value = useMemo<LanguageContextValue>(() => ({ language, setLanguage, t }), [language, setLanguage, t])

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error('useLanguage must be used within a LanguageProvider.')
  return ctx
}

/** Convenience hook for components that only need the translate function. */
export function useTranslation() {
  return useLanguage().t
}
