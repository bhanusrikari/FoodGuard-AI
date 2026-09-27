import type { TranslationKey } from './en'

/**
 * Hindi translations. Deliberately `Partial` — see te.ts for why partial
 * coverage is safe here (falls back to English, never a raw key).
 *
 * Written directly for this project; not yet reviewed by a native
 * Hindi-speaking linguist — treat as an MVP first pass.
 */
export const hi: Partial<Record<TranslationKey, string>> = {
  'nav.dashboard': 'डैशबोर्ड',
  'nav.reports': 'रिपोर्ट्स',
  'nav.complaints': 'शिकायतें',
  'nav.profile': 'प्रोफ़ाइल',
  'nav.myRestaurants': 'मेरे रेस्टोरेंट',
  'nav.restaurants': 'रेस्टोरेंट',

  'common.cancel': 'रद्द करें',
  'common.confirm': 'पुष्टि करें',
  'common.delete': 'हटाएं',
  'common.save': 'सहेजें',
  'common.tryAgain': 'पुनः प्रयास करें',
  'common.logOut': 'लॉग आउट',
  'common.language': 'भाषा',

  'topbar.openMenu': 'मेनू खोलें',
  'topbar.closeMenu': 'मेनू बंद करें',

  'auth.login.title': 'वापसी पर स्वागत है',
  'auth.login.subtitle': 'अपने FoodGuard AI खाते में साइन इन करें',
  'auth.login.email': 'ईमेल',
  'auth.login.password': 'पासवर्ड',
  'auth.login.submit': 'साइन इन करें',
  'auth.login.noAccount': 'खाता नहीं है?',
  'auth.login.createOne': 'एक बनाएं',
  'auth.login.accountCreated': 'खाता बना दिया गया है। कृपया साइन इन करें।',

  'auth.register.title': 'अपना खाता बनाएं',
  'auth.register.subtitle': 'अपने समुदाय में खाद्य सुरक्षा संबंधी चिंताओं की रिपोर्ट करें',
  'auth.register.firstName': 'पहला नाम',
  'auth.register.lastName': 'अंतिम नाम',
  'auth.register.email': 'ईमेल',
  'auth.register.password': 'पासवर्ड',
  'auth.register.passwordHint': 'कम से कम 8 अक्षर होने चाहिए।',
  'auth.register.phone': 'फोन (वैकल्पिक)',
  'auth.register.preferredLanguage': 'पसंदीदा भाषा',
  'auth.register.submit': 'खाता बनाएं',
  'auth.register.haveAccount': 'क्या आपके पास पहले से खाता है?',
  'auth.register.signIn': 'साइन इन करें',

  'reports.list.heading': 'आपकी खाद्य सुरक्षा रिपोर्ट्स',
  'reports.list.subtitle': 'ड्राफ्ट से समाधान तक, आपके द्वारा दर्ज की गई हर रिपोर्ट को ट्रैक करें।',
  'reports.list.new': 'नई रिपोर्ट',
  'reports.list.createAction': 'रिपोर्ट बनाएं',
  'reports.list.emptyTitle': 'अभी तक कोई खाद्य सुरक्षा रिपोर्ट नहीं',
  'reports.list.emptyDescription': 'यदि आपने किसी खाद्य सुरक्षा समस्या का अनुभव किया है, तो आप यहां इसकी रिपोर्ट कर सकते हैं।',
  'reports.list.emptyFilterTitle': 'इस फ़िल्टर से कोई रिपोर्ट मेल नहीं खाती',
  'reports.list.emptyFilterDescription': 'एक अलग स्थिति फ़िल्टर आज़माएं।',
  'reports.list.loadError': 'हम आपकी रिपोर्ट्स लोड नहीं कर सके।',
  'reports.detail.edit': 'संपादित करें',
  'reports.detail.delete': 'हटाएं',
  'reports.detail.submitForReview': 'समीक्षा के लिए सबमिट करें',
  'reports.detail.deleteConfirmTitle': 'इस ड्राफ्ट रिपोर्ट को हटाएं?',
  'reports.detail.deleteConfirmDescription': 'यह कार्रवाई पूर्ववत नहीं की जा सकती।',
  'reports.detail.draftNotice': 'यह रिपोर्ट एक ड्राफ्ट है। समीक्षा के लिए सबमिट करने से पहले एक प्रमाण फ़ोटो आवश्यक है।',
  'reports.detail.loadError': 'हम इस रिपोर्ट को लोड नहीं कर सके।',

  'dashboard.reviewer.heading': 'संचालन अवलोकन',
  'dashboard.reviewer.subtitle': 'आपके ध्यान की प्रतीक्षा कर रही रिपोर्ट्स, शिकायतें और रेस्टोरेंट।',
  'dashboard.admin.heading': 'प्लेटफ़ॉर्म अवलोकन',
  'dashboard.admin.subtitle': 'डेटाबेस से सीधे एकत्र की गई लाइव संख्याएं — कोई अनुमान या रुझान नहीं।',
  'dashboard.admin.noData': 'अभी तक कोई डेटा नहीं।',
  'dashboard.admin.loadError': 'हम प्लेटफ़ॉर्म अवलोकन लोड नहीं कर सके।',

  'state.errorTitle': 'हम यह डेटा लोड नहीं कर सके।',
  'state.errorMessage': 'सर्वर से बात करते समय कुछ गड़बड़ हो गई। कृपया पुनः प्रयास करें।',
}
