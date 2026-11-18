import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import type { Person } from "../api";
import { LOCALES, type Language } from "../i18n";
import { age, formatBirthdate, fullName } from "../lib/format";
import { Avatar } from "./Avatar";

/** Read-only view of a person, shared by the person page and the profile page. */
export function PersonCard({ person, actions, children }: { person: Person; actions?: ReactNode; children?: ReactNode }) {
  const { t, i18n } = useTranslation();
  const locale = LOCALES[i18n.resolvedLanguage as Language];

  const birthdate = formatBirthdate(person, locale);
  const personAge = age(person);
  const meta = [
    person.gender && t(`person.${person.gender}`),
    personAge && t(personAge.exact ? "person.age" : "person.approxAge", { count: personAge.years }),
  ].filter(Boolean);

  return (
    <article className="card p-5 md:p-8">
      <header className="flex flex-wrap items-start gap-4">
        <Avatar person={person} size="lg" />
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-semibold tracking-tight">{fullName(person)}</h1>
          {person.nickname && <p className="text-stone-500">«{person.nickname}»</p>}
          {meta.length > 0 && <p className="mt-1 text-sm text-stone-500">{meta.join(" · ")}</p>}
        </div>
        {actions && <div className="flex basis-full gap-2 sm:basis-auto">{actions}</div>}
      </header>

      {children}

      <dl className="mt-8 grid gap-6 sm:grid-cols-[10rem_1fr]">
        {birthdate && (
          <>
            <dt className="text-sm font-medium text-stone-500">{t("person.birthday")}</dt>
            <dd className="-mt-5 sm:mt-0">{birthdate}</dd>
          </>
        )}
        {person.summary && (
          <>
            <dt className="text-sm font-medium text-stone-500">{t("person.summary")}</dt>
            <dd className="-mt-5 whitespace-pre-wrap sm:mt-0">{person.summary}</dd>
          </>
        )}
      </dl>

      <p className="mt-10 border-t border-dashed border-stone-200 pt-4 text-sm text-stone-400 dark:border-stone-800">
        {t("person.comingSoon")}
      </p>
    </article>
  );
}
