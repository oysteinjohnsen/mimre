import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, type ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";

import { api, type Gender, type Person, type PersonInput } from "../api";
import { BackLink } from "../components/BackLink";
import { LOCALES, type Language } from "../i18n";
import { daysInMonth, fullName } from "../lib/format";

/** Create (/people/new) or edit (/people/:id/edit) a person. */
export function PersonForm() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: person, isPending } = useQuery({
    queryKey: ["person", id],
    queryFn: () => api.getPerson(id!),
    enabled: !!id,
  });
  if (id && isPending) return null;

  return (
    <PersonEditor
      key={id ?? "new"} // resets form state when switching between people
      person={person}
      title={person ? t("form.editTitle", { name: fullName(person) }) : t("form.newTitle")}
      cancelTo={person ? `/people/${person.id}` : "/"}
      save={(data) => (person ? api.updatePerson(person.id, data) : api.createPerson(data))}
      onSaved={(saved) => {
        void queryClient.invalidateQueries({ queryKey: ["persons"] });
        return `/people/${saved.id}`;
      }}
    />
  );
}

/** Create or edit the user's own profile (/me/edit). */
export function ProfileForm() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: me, isPending } = useQuery({ queryKey: ["me"], queryFn: api.getMe });
  if (isPending) return null;

  return (
    <PersonEditor
      person={me ?? undefined}
      title={me ? t("profile.editTitle") : t("profile.create")}
      cancelTo="/me"
      save={api.saveMe}
      onSaved={(saved) => {
        queryClient.setQueryData(["me"], saved);
        return "/me";
      }}
    />
  );
}

interface FormState {
  first_name: string;
  middle_name: string;
  last_name: string;
  nickname: string;
  gender: Gender | "";
  birth_day: string;
  birth_month: string;
  birth_year: string;
  summary: string;
}

function toFormState(p?: Person): FormState {
  return {
    first_name: p?.first_name ?? "",
    middle_name: p?.middle_name ?? "",
    last_name: p?.last_name ?? "",
    nickname: p?.nickname ?? "",
    gender: p?.gender ?? "",
    birth_day: p?.birth_day?.toString() ?? "",
    birth_month: p?.birth_month?.toString() ?? "",
    birth_year: p?.birth_year?.toString() ?? "",
    summary: p?.summary ?? "",
  };
}

const textOrNull = (s: string) => s.trim() || null;
const numberOrNull = (s: string) => (s.trim() ? Number(s) : null);

function toInput(f: FormState): PersonInput {
  return {
    first_name: f.first_name.trim(),
    middle_name: textOrNull(f.middle_name),
    last_name: textOrNull(f.last_name),
    nickname: textOrNull(f.nickname),
    gender: f.gender || null,
    birth_day: numberOrNull(f.birth_day),
    birth_month: numberOrNull(f.birth_month),
    birth_year: numberOrNull(f.birth_year),
    summary: textOrNull(f.summary),
  };
}

interface EditorProps {
  person?: Person;
  title: string;
  cancelTo: string;
  save: (data: PersonInput) => Promise<Person>;
  /** Called after a successful save; returns the path to navigate to. */
  onSaved: (saved: Person) => string;
}

function PersonEditor({ person, title, cancelTo, save: saveFn, onSaved }: EditorProps) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form, setForm] = useState(() => toFormState(person));
  const locale = LOCALES[i18n.resolvedLanguage as Language];

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm((f) => ({ ...f, [key]: value }));

  // A year only limits the days once it's complete, so typing "201…" on the way to "2019" doesn't clear 29 Feb.
  const maxDay = (f: FormState) => daysInMonth(numberOrNull(f.birth_month), f.birth_year.length === 4 ? Number(f.birth_year) : null);

  /** Set month or year; clears the day if it no longer exists (rather than silently changing it). */
  const setBirthPart = (key: "birth_month" | "birth_year", value: string) =>
    setForm((f) => {
      const next = { ...f, [key]: value };
      if (next.birth_day && Number(next.birth_day) > maxDay(next)) next.birth_day = "";
      return next;
    });

  const save = useMutation({
    mutationFn: saveFn,
    onSuccess: (saved) => {
      queryClient.setQueryData(["person", saved.id], saved);
      void navigate(onSaved(saved), { replace: true });
    },
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate(toInput(form));
  };

  const monthNames = Array.from({ length: 12 }, (_, i) =>
    new Intl.DateTimeFormat(locale, { month: "long", timeZone: "UTC" }).format(new Date(Date.UTC(2000, i, 1))),
  );

  return (
    <div className="p-4 md:p-0">
      <BackLink to={cancelTo} />
      <form onSubmit={onSubmit} className="card space-y-6 p-5 md:p-8">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>

        <div className="grid gap-4 sm:grid-cols-3">
          <Field label={t("form.firstName")}>
            <input className="input" required autoFocus={!person} value={form.first_name} onChange={(e) => set("first_name", e.target.value)} />
          </Field>
          <Field label={t("form.middleName")}>
            <input className="input" value={form.middle_name} onChange={(e) => set("middle_name", e.target.value)} />
          </Field>
          <Field label={t("form.lastName")}>
            <input className="input" value={form.last_name} onChange={(e) => set("last_name", e.target.value)} />
          </Field>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("form.nickname")}>
            <input className="input" value={form.nickname} onChange={(e) => set("nickname", e.target.value)} />
          </Field>
          <fieldset>
            <legend className="mb-1 block text-sm font-medium text-stone-600 dark:text-stone-400">{t("form.gender")}</legend>
            <div className="grid grid-cols-3 gap-1 rounded-lg bg-stone-200/70 p-1 dark:bg-stone-800">
              {(["male", "female", ""] as const).map((g) => (
                <label
                  key={g || "unknown"}
                  className={`cursor-pointer rounded-md px-2 py-1.5 text-center text-sm ${
                    form.gender === g ? "bg-white font-medium shadow-sm dark:bg-stone-950" : "text-stone-600 dark:text-stone-400"
                  }`}
                >
                  <input type="radio" name="gender" className="sr-only" checked={form.gender === g} onChange={() => set("gender", g)} />
                  {g ? t(`person.${g}`) : t("form.genderUnknown")}
                </label>
              ))}
            </div>
          </fieldset>
        </div>

        <fieldset>
          <legend className="block text-sm font-medium text-stone-600 dark:text-stone-400">{t("form.birthdate")}</legend>
          <p className="mb-2 text-xs text-stone-500">{t("form.birthdateHint")}</p>
          <div className="grid grid-cols-[5rem_1fr_6rem] gap-2 sm:max-w-md">
            <select className="input" aria-label={t("form.day")} value={form.birth_day} onChange={(e) => set("birth_day", e.target.value)}>
              <option value="">{t("form.day")}</option>
              {Array.from({ length: maxDay(form) }, (_, i) => (
                <option key={i} value={i + 1}>
                  {i + 1}
                </option>
              ))}
            </select>
            <select className="input" aria-label={t("form.month")} value={form.birth_month} onChange={(e) => setBirthPart("birth_month", e.target.value)}>
              <option value="">{t("form.month")}</option>
              {monthNames.map((name, i) => (
                <option key={i} value={i + 1}>
                  {name}
                </option>
              ))}
            </select>
            <input
              className="input"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={4}
              placeholder={t("form.year")}
              aria-label={t("form.year")}
              value={form.birth_year}
              onChange={(e) => setBirthPart("birth_year", e.target.value.replace(/\D/g, ""))}
            />
          </div>
        </fieldset>

        <Field label={t("form.summary")}>
          <textarea
            className="input min-h-28"
            placeholder={t("form.summaryPlaceholder")}
            value={form.summary}
            onChange={(e) => set("summary", e.target.value)}
          />
        </Field>

        {save.isError && <p className="text-sm text-red-700 dark:text-red-400">{t("error.generic", { message: save.error.message })}</p>}

        <div className="flex justify-end gap-2 border-t border-stone-200 pt-5 dark:border-stone-800">
          <Link to={cancelTo} className="btn-secondary">
            {t("form.cancel")}
          </Link>
          <button type="submit" className="btn-primary" disabled={save.isPending}>
            {save.isPending ? t("form.saving") : t("form.save")}
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-stone-600 dark:text-stone-400">{label}</span>
      {children}
    </label>
  );
}
