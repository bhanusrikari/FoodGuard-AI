/**
 * English translation dictionary — the canonical source of truth for
 * every translation key in the app. `te.ts` and `hi.ts` are typed as
 * `Partial<Record<TranslationKey, string>>` against this file's keys, so
 * a missing key there always falls back to this English text rather than
 * ever leaking a raw key name into the UI.
 *
 * Keys are namespaced by feature area (nav.*, common.*, auth.*, ...) —
 * add new keys here first, then translate into te.ts/hi.ts when ready.
 */
export const en = {
  // Navigation
  'nav.dashboard': 'Dashboard',
  'nav.reports': 'Reports',
  'nav.complaints': 'Complaints',
  'nav.profile': 'Profile',
  'nav.myRestaurants': 'My Restaurants',
  'nav.restaurants': 'Restaurants',

  // Common actions/labels used across many components
  'common.cancel': 'Cancel',
  'common.confirm': 'Confirm',
  'common.delete': 'Delete',
  'common.save': 'Save',
  'common.tryAgain': 'Try Again',
  'common.logOut': 'Log out',
  'common.language': 'Language',

  // Topbar
  'topbar.openMenu': 'Open menu',
  'topbar.closeMenu': 'Close menu',

  // Auth — Login
  'auth.login.title': 'Welcome back',
  'auth.login.subtitle': 'Sign in to your FoodGuard AI account',
  'auth.login.email': 'Email',
  'auth.login.password': 'Password',
  'auth.login.submit': 'Sign in',
  'auth.login.noAccount': "Don't have an account?",
  'auth.login.createOne': 'Create one',
  'auth.login.accountCreated': 'Account created. Please sign in.',

  // Auth — Register
  'auth.register.title': 'Create your account',
  'auth.register.subtitle': 'Report food safety concerns in your community',
  'auth.register.firstName': 'First name',
  'auth.register.lastName': 'Last name',
  'auth.register.email': 'Email',
  'auth.register.password': 'Password',
  'auth.register.passwordHint': 'At least 8 characters.',
  'auth.register.phone': 'Phone (optional)',
  'auth.register.preferredLanguage': 'Preferred language',
  'auth.register.submit': 'Create account',
  'auth.register.haveAccount': 'Already have an account?',
  'auth.register.signIn': 'Sign in',

  // Reports
  'reports.list.heading': 'Your food safety reports',
  'reports.list.subtitle': "Track every report you've filed, from draft to resolution.",
  'reports.list.new': 'New Report',
  'reports.list.createAction': 'Create Report',
  'reports.list.emptyTitle': 'No food safety reports yet',
  'reports.list.emptyDescription': "If you've experienced a food safety concern, you can report it here.",
  'reports.list.emptyFilterTitle': 'No reports match this filter',
  'reports.list.emptyFilterDescription': 'Try a different status filter.',
  'reports.list.loadError': "We couldn't load your reports.",
  'reports.detail.edit': 'Edit',
  'reports.detail.delete': 'Delete',
  'reports.detail.submitForReview': 'Submit for Review',
  'reports.detail.deleteConfirmTitle': 'Delete this draft report?',
  'reports.detail.deleteConfirmDescription': 'This action cannot be undone.',
  'reports.detail.draftNotice': 'This report is a draft. An evidence photo is required before it can be submitted for review.',
  'reports.detail.loadError': "We couldn't load this report.",

  // Dashboards
  'dashboard.reviewer.heading': 'Operations overview',
  'dashboard.reviewer.subtitle': 'Reports, complaints, and restaurants awaiting your attention.',
  'dashboard.admin.heading': 'Platform overview',
  'dashboard.admin.subtitle': 'Live counts aggregated directly from the database — no estimates or trends.',
  'dashboard.admin.noData': 'No data yet.',
  'dashboard.admin.loadError': "We couldn't load the platform overview.",

  // Generic state components
  'state.errorTitle': "We couldn't load this data.",
  'state.errorMessage': 'Something went wrong while talking to the server. Please try again.',
} as const

export type TranslationKey = keyof typeof en
