import { Check, Globe } from 'lucide-react'
import { Dropdown } from '@/components/ui/Dropdown'
import { SUPPORTED_UI_LANGUAGES, useLanguage } from '@/i18n/LanguageContext'
import { LANGUAGE_LABELS } from '@/types/user'

/** Global language switcher — lives in the Topbar so it's reachable from
 * every authenticated page. Only lists languages this app actually has a
 * translation dictionary for (see SUPPORTED_UI_LANGUAGES); switching
 * updates the page immediately and persists the choice (localStorage +
 * best-effort backend sync via useLanguage()'s setLanguage). */
export function LanguageSelector() {
  const { language, setLanguage, t } = useLanguage()

  return (
    <Dropdown
      align="right"
      trigger={
        <span
          className="flex items-center gap-1.5 rounded-full px-2.5 py-1.5 text-sm font-medium text-neutral-600 hover:bg-neutral-50"
          aria-label={t('common.language')}
        >
          <Globe className="size-4" aria-hidden="true" />
          <span className="hidden sm:inline">{LANGUAGE_LABELS[language]}</span>
        </span>
      }
      items={SUPPORTED_UI_LANGUAGES.map((code) => ({
        label: LANGUAGE_LABELS[code],
        onSelect: () => setLanguage(code),
        icon: code === language ? <Check className="size-4" aria-hidden="true" /> : <span className="size-4" />,
      }))}
    />
  )
}
