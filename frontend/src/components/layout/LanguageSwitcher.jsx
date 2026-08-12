import { useLanguage } from "../../i18n";

export default function LanguageSwitcher() {
  const { language, setLanguage, translations } = useLanguage();

  return (
    <select
      value={language}
      onChange={(e) => setLanguage(e.target.value)}
      style={{
        border: "1px solid #e5e7eb",
        borderRadius: "8px",
        padding: "6px 10px",
        background: "white",
        cursor: "pointer",
        fontSize: "14px",
      }}
      aria-label="Language"
    >
      {Object.values(translations).map((lang) => (
        <option key={lang.code} value={lang.code}>
          {lang.flag} {lang.name}
        </option>
      ))}
    </select>
  );
}