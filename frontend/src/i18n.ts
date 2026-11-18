import i18n from "i18next";
import { initReactI18next } from "react-i18next";

const nb = {
  app: { tagline: "Husk det som betyr noe" },
  nav: { people: "Personer", new: "Ny", newPerson: "Ny person", profile: "Min profil", settings: "Innstillinger" },
  search: { placeholder: "Søk etter navn…", noResults: "Ingen treff", empty: "Ingen personer ennå" },
  empty: {
    title: "Velg en person",
    body: "Velg noen i listen, eller legg til en ny person.",
  },
  person: {
    male: "Mann",
    female: "Kvinne",
    birthday: "Bursdag",
    age_one: "{{count}} år",
    age_other: "{{count}} år",
    approxAge_one: "ca. {{count}} år",
    approxAge_other: "ca. {{count}} år",
    summary: "Notat",
    notFound: "Fant ikke personen.",
    comingSoon: "Relasjoner, fakta og notater kommer snart.",
  },
  form: {
    newTitle: "Ny person",
    editTitle: "Rediger {{name}}",
    firstName: "Fornavn",
    lastName: "Etternavn",
    nickname: "Kallenavn",
    gender: "Kjønn",
    genderUnknown: "Ikke angitt",
    birthdate: "Fødselsdato",
    birthdateHint: "Fyll inn det du vet – f.eks. bare dag og måned, eller bare år.",
    day: "Dag",
    month: "Måned",
    year: "År",
    summary: "Kort notat",
    summaryPlaceholder: "Hvem er dette? Hvordan kjenner du dem?",
    save: "Lagre",
    cancel: "Avbryt",
    delete: "Slett",
    edit: "Rediger",
    confirmDelete: "Slette {{name}}? Dette kan ikke angres.",
    saving: "Lagrer…",
  },
  profile: {
    title: "Min profil",
    editTitle: "Rediger profil",
    emptyTitle: "Fortell litt om deg selv",
    emptyBody: "Profilen din er utgangspunktet for relasjoner – som «min søster» eller «min kollega».",
    create: "Opprett profil",
  },
  settings: {
    title: "Innstillinger",
    language: "Språk",
    languageHint: "Språket som brukes i appen.",
  },
  error: { generic: "Noe gikk galt: {{message}}", loading: "Kunne ikke laste data." },
};

type Translation = typeof nb;

const en: Translation = {
  app: { tagline: "Remember what matters" },
  nav: { people: "People", new: "New", newPerson: "New person", profile: "My profile", settings: "Settings" },
  search: { placeholder: "Search by name…", noResults: "No matches", empty: "No people yet" },
  empty: {
    title: "Select a person",
    body: "Pick someone from the list, or add a new person.",
  },
  person: {
    male: "Male",
    female: "Female",
    birthday: "Birthday",
    age_one: "{{count}} year old",
    age_other: "{{count}} years old",
    approxAge_one: "about {{count}} year old",
    approxAge_other: "about {{count}} years old",
    summary: "Note",
    notFound: "Person not found.",
    comingSoon: "Relationships, facts and notes are coming soon.",
  },
  form: {
    newTitle: "New person",
    editTitle: "Edit {{name}}",
    firstName: "First name",
    lastName: "Last name",
    nickname: "Nickname",
    gender: "Gender",
    genderUnknown: "Not specified",
    birthdate: "Date of birth",
    birthdateHint: "Fill in what you know – e.g. only day and month, or only the year.",
    day: "Day",
    month: "Month",
    year: "Year",
    summary: "Short note",
    summaryPlaceholder: "Who is this? How do you know them?",
    save: "Save",
    cancel: "Cancel",
    delete: "Delete",
    edit: "Edit",
    confirmDelete: "Delete {{name}}? This cannot be undone.",
    saving: "Saving…",
  },
  profile: {
    title: "My profile",
    editTitle: "Edit profile",
    emptyTitle: "Tell us a little about yourself",
    emptyBody: "Your profile is the starting point for relationships – like “my sister” or “my colleague”.",
    create: "Create profile",
  },
  settings: {
    title: "Settings",
    language: "Language",
    languageHint: "The language used in the app.",
  },
  error: { generic: "Something went wrong: {{message}}", loading: "Could not load data." },
};

export const LANGUAGES = { nb: "Norsk", en: "English" } as const;
export type Language = keyof typeof LANGUAGES;

/** BCP 47 locale used for Intl date formatting. */
export const LOCALES: Record<Language, string> = { nb: "nb-NO", en: "en-GB" };

const STORAGE_KEY = "mimre.language";

function storedLanguage(): Language {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    if (value && value in LANGUAGES) return value as Language;
  } catch {
    /* storage unavailable */
  }
  return "nb";
}

export function setLanguage(lang: Language) {
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    /* storage unavailable */
  }
  void i18n.changeLanguage(lang);
}

i18n.on("languageChanged", (lng) => {
  document.documentElement.lang = lng;
});

void i18n.use(initReactI18next).init({
  resources: { nb: { translation: nb }, en: { translation: en } },
  lng: storedLanguage(),
  fallbackLng: "nb",
  interpolation: { escapeValue: false },
});

export default i18n;
