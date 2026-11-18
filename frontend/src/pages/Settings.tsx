import { useTranslation } from "react-i18next";

import { BackLink } from "../components/BackLink";
import { LANGUAGES, type Language, setLanguage } from "../i18n";

export function Settings() {
  const { t, i18n } = useTranslation();
  const current = i18n.resolvedLanguage as Language;

  return (
    <div className="p-4 md:p-0">
      <BackLink />
      <div className="card space-y-8 p-5 md:p-8">
        <h1 className="text-2xl font-semibold tracking-tight">{t("settings.title")}</h1>

        <fieldset>
          <legend className="font-medium">{t("settings.language")}</legend>
          <p className="mb-3 text-sm text-stone-500">{t("settings.languageHint")}</p>
          <div className="grid max-w-sm gap-2">
            {(Object.keys(LANGUAGES) as Language[]).map((lang) => (
              <label
                key={lang}
                className={`flex cursor-pointer items-center gap-3 rounded-lg border px-4 py-3 ${
                  current === lang
                    ? "border-accent-600 bg-accent-50 dark:bg-accent-900/30"
                    : "border-stone-200 hover:bg-stone-50 dark:border-stone-800 dark:hover:bg-stone-900"
                }`}
              >
                <input
                  type="radio"
                  name="language"
                  className="accent-accent-700"
                  checked={current === lang}
                  onChange={() => setLanguage(lang)}
                />
                {LANGUAGES[lang]}
              </label>
            ))}
          </div>
        </fieldset>
      </div>
    </div>
  );
}
