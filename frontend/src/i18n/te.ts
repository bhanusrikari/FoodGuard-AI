import type { TranslationKey } from './en'

/**
 * Telugu translations. Deliberately `Partial` — any key not yet
 * translated here falls back to English automatically (see
 * useTranslation() in LanguageContext.tsx), so partial coverage never
 * breaks the UI or leaks a raw key name.
 *
 * Written directly for this project; not yet reviewed by a native
 * Telugu-speaking linguist — treat as an MVP first pass.
 */
export const te: Partial<Record<TranslationKey, string>> = {
  'nav.dashboard': 'డాష్‌బోర్డ్',
  'nav.reports': 'నివేదికలు',
  'nav.complaints': 'ఫిర్యాదులు',
  'nav.profile': 'ప్రొఫైల్',
  'nav.myRestaurants': 'నా రెస్టారెంట్లు',
  'nav.restaurants': 'రెస్టారెంట్లు',

  'common.cancel': 'రద్దు చేయండి',
  'common.confirm': 'నిర్ధారించండి',
  'common.delete': 'తొలగించండి',
  'common.save': 'సేవ్ చేయండి',
  'common.tryAgain': 'మళ్లీ ప్రయత్నించండి',
  'common.logOut': 'లాగ్ అవుట్',
  'common.language': 'భాష',

  'topbar.openMenu': 'మెనూ తెరవండి',
  'topbar.closeMenu': 'మెనూ మూసివేయండి',

  'auth.login.title': 'తిరిగి స్వాగతం',
  'auth.login.subtitle': 'మీ FoodGuard AI ఖాతాలోకి సైన్ ఇన్ చేయండి',
  'auth.login.email': 'ఇమెయిల్',
  'auth.login.password': 'పాస్‌వర్డ్',
  'auth.login.submit': 'సైన్ ఇన్',
  'auth.login.noAccount': 'ఖాతా లేదా?',
  'auth.login.createOne': 'ఒకటి సృష్టించండి',
  'auth.login.accountCreated': 'ఖాతా సృష్టించబడింది. దయచేసి సైన్ ఇన్ చేయండి.',

  'auth.register.title': 'మీ ఖాతాను సృష్టించండి',
  'auth.register.subtitle': 'మీ సమాజంలో ఆహార భద్రతా సమస్యలను నివేదించండి',
  'auth.register.firstName': 'మొదటి పేరు',
  'auth.register.lastName': 'చివరి పేరు',
  'auth.register.email': 'ఇమెయిల్',
  'auth.register.password': 'పాస్‌వర్డ్',
  'auth.register.passwordHint': 'కనీసం 8 అక్షరాలు ఉండాలి.',
  'auth.register.phone': 'ఫోన్ (ఐచ్ఛికం)',
  'auth.register.preferredLanguage': 'ఇష్టపడే భాష',
  'auth.register.submit': 'ఖాతా సృష్టించండి',
  'auth.register.haveAccount': 'ఇప్పటికే ఖాతా ఉందా?',
  'auth.register.signIn': 'సైన్ ఇన్ చేయండి',

  'reports.list.heading': 'మీ ఆహార భద్రతా నివేదికలు',
  'reports.list.subtitle': 'డ్రాఫ్ట్ నుండి పరిష్కారం వరకు మీరు దాఖలు చేసిన ప్రతి నివేదికను ట్రాక్ చేయండి.',
  'reports.list.new': 'కొత్త నివేదిక',
  'reports.list.createAction': 'నివేదిక సృష్టించండి',
  'reports.list.emptyTitle': 'ఇంకా ఆహార భద్రతా నివేదికలు లేవు',
  'reports.list.emptyDescription': 'మీరు ఆహార భద్రతా సమస్యను ఎదుర్కొంటే, మీరు ఇక్కడ దానిని నివేదించవచ్చు.',
  'reports.list.emptyFilterTitle': 'ఈ ఫిల్టర్‌కు సరిపోలే నివేదికలు లేవు',
  'reports.list.emptyFilterDescription': 'వేరే స్థితి ఫిల్టర్‌ను ప్రయత్నించండి.',
  'reports.list.loadError': 'మీ నివేదికలను లోడ్ చేయలేకపోయాము.',
  'reports.detail.edit': 'సవరించండి',
  'reports.detail.delete': 'తొలగించండి',
  'reports.detail.submitForReview': 'సమీక్ష కోసం సమర్పించండి',
  'reports.detail.deleteConfirmTitle': 'ఈ డ్రాఫ్ట్ నివేదికను తొలగించాలా?',
  'reports.detail.deleteConfirmDescription': 'ఈ చర్యను తిరిగి మార్చలేరు.',
  'reports.detail.draftNotice': 'ఈ నివేదిక డ్రాఫ్ట్‌లో ఉంది. సమీక్ష కోసం సమర్పించే ముందు సాక్ష్యం ఫోటో అవసరం.',
  'reports.detail.loadError': 'ఈ నివేదికను లోడ్ చేయలేకపోయాము.',

  'dashboard.reviewer.heading': 'కార్యకలాపాల అవలోకనం',
  'dashboard.reviewer.subtitle': 'మీ దృష్టి కోసం వేచి ఉన్న నివేదికలు, ఫిర్యాదులు మరియు రెస్టారెంట్లు.',
  'dashboard.admin.heading': 'ప్లాట్‌ఫారమ్ అవలోకనం',
  'dashboard.admin.subtitle': 'డేటాబేస్ నుండి నేరుగా సేకరించిన ప్రత్యక్ష గణాంకాలు — అంచనాలు లేదా ధోరణులు లేవు.',
  'dashboard.admin.noData': 'ఇంకా డేటా లేదు.',
  'dashboard.admin.loadError': 'ప్లాట్‌ఫారమ్ అవలోకనాన్ని లోడ్ చేయలేకపోయాము.',

  'state.errorTitle': 'ఈ డేటాను లోడ్ చేయలేకపోయాము.',
  'state.errorMessage': 'సర్వర్‌తో సంభాషిస్తున్నప్పుడు ఏదో తప్పు జరిగింది. దయచేసి మళ్లీ ప్రయత్నించండి.',
}
