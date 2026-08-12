import { createContext, useContext, useEffect, useState } from "react";

import en from "./en";
import nl from "./nl";
import de from "./de";

const translations = {
  en,
  nl,
  de,
};

const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(() => {
    return localStorage.getItem("ned_language") || "en";
  });

  useEffect(() => {
    localStorage.setItem("ned_language", language);

    document.documentElement.lang = language;
    document.documentElement.dir = "ltr";
  }, [language]);

  const setLanguage = (lang) => {
    if (!translations[lang]) return;
    setLanguageState(lang);
  };

  const t = (key) => {
    return translations[language]?.[key] ?? translations.en[key] ?? key;
  };

  return (
    <LanguageContext.Provider
      value={{
        language,
        setLanguage,
        t,
        translations,
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);

  if (!context) {
    throw new Error("useLanguage must be used inside LanguageProvider");
  }

  return context;
}

export { translations };