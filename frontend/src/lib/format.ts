import type { Person } from "../api";

export function fullName(p: Pick<Person, "first_name" | "last_name">): string {
  return [p.first_name, p.last_name].filter(Boolean).join(" ");
}

export function initials(p: Pick<Person, "first_name" | "last_name">): string {
  return [p.first_name, p.last_name]
    .filter(Boolean)
    .map((s) => s!.trim()[0]?.toUpperCase())
    .join("");
}

/** Formats a possibly partial birthdate, e.g. "14. mars 2019", "14. mars", "mars 2019" or "2019". */
export function formatBirthdate(p: Pick<Person, "birth_year" | "birth_month" | "birth_day">, locale: string): string | null {
  const { birth_year: y, birth_month: m, birth_day: d } = p;
  if (y == null && m == null) return null;
  if (m == null) return String(y);
  const date = new Date(Date.UTC(y ?? 2000, m - 1, d ?? 1));
  const opts: Intl.DateTimeFormatOptions = { month: "long", timeZone: "UTC" };
  if (d != null) opts.day = "numeric";
  if (y != null) opts.year = "numeric";
  return new Intl.DateTimeFormat(locale, opts).format(date);
}

/**
 * Number of selectable days for a (possibly unknown) month and year.
 * Unknown month: 31. February with unknown year: 29 (it exists in leap years).
 */
export function daysInMonth(month: number | null, year: number | null): number {
  if (month == null) return 31;
  return new Date(Date.UTC(year ?? 2000, month, 0)).getUTCDate();
}

/** Age in whole years. `exact` is false when only the year (or year+month) is known. */
export function age(
  p: Pick<Person, "birth_year" | "birth_month" | "birth_day">,
  today = new Date(),
): { years: number; exact: boolean } | null {
  const { birth_year: y, birth_month: m, birth_day: d } = p;
  if (y == null) return null;
  let years = today.getFullYear() - y;
  if (m == null || d == null) return { years: Math.max(years, 0), exact: false };
  const hadBirthday = today.getMonth() + 1 > m || (today.getMonth() + 1 === m && today.getDate() >= d);
  if (!hadBirthday) years -= 1;
  return { years: Math.max(years, 0), exact: true };
}

const AVATAR_COLORS = [
  "bg-teal-100 text-teal-800 dark:bg-teal-900/60 dark:text-teal-200",
  "bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-200",
  "bg-sky-100 text-sky-800 dark:bg-sky-900/60 dark:text-sky-200",
  "bg-rose-100 text-rose-800 dark:bg-rose-900/60 dark:text-rose-200",
  "bg-violet-100 text-violet-800 dark:bg-violet-900/60 dark:text-violet-200",
  "bg-lime-100 text-lime-800 dark:bg-lime-900/60 dark:text-lime-200",
];

export function avatarColor(id: string): string {
  let hash = 0;
  for (const ch of id) hash = (hash * 31 + ch.charCodeAt(0)) | 0;
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}
