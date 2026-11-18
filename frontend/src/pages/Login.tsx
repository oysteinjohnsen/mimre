import { useQueryClient } from "@tanstack/react-query";
import { type FormEvent, type ReactNode, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api, resetSession } from "../api";
import { LANGUAGES, type Language, setLanguage } from "../i18n";

const RESEND_SECONDS = 30;
const KNOWN_ERRORS = [
  "invalid_credentials",
  "locked",
  "invalid_code",
  "challenge_expired",
  "resend_too_soon",
  "too_many_codes",
  "email_failed",
];

/** Two-step login: email + password, then the one-time code sent by email. */
export function Login() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const language = i18n.resolvedLanguage as Language;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [resendIn, setResendIn] = useState(0);

  useEffect(() => {
    if (resendIn <= 0) return;
    const id = setTimeout(() => setResendIn((s) => s - 1), 1000);
    return () => clearTimeout(id);
  }, [resendIn]);

  const fail = (e: unknown) => {
    const key = e instanceof ApiError && KNOWN_ERRORS.includes(e.message) ? e.message : "generic";
    setError(t(`login.errors.${key}`));
    // These mean the code step can't continue: go back to email + password.
    if (key === "challenge_expired" || key === "too_many_codes") {
      setChallengeId(null);
      setCode("");
    }
  };

  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      await action();
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  };

  const submitPassword = (e: FormEvent) => {
    e.preventDefault();
    void run(async () => {
      const res = await api.login(email.trim(), password, language);
      setPassword("");
      setChallengeId(res.challenge_id);
      setResendIn(RESEND_SECONDS);
    });
  };

  const submitCode = (e: FormEvent) => {
    e.preventDefault();
    void run(async () => {
      const user = await api.verifyCode(challengeId!, code.trim());
      resetSession(queryClient, user);
    });
  };

  const resend = () =>
    void run(async () => {
      await api.resendCode(challengeId!, language);
      setInfo(t("login.resent"));
      setResendIn(RESEND_SECONDS);
    });

  return (
    <div className="flex min-h-dvh items-center justify-center p-4 pt-[max(1rem,env(safe-area-inset-top))]">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center justify-center gap-2">
          <img src="/favicon.svg" alt="" className="size-10" />
          <span className="text-2xl font-semibold tracking-tight">Mimre</span>
        </div>

        <div className="card p-6">
          {challengeId === null ? (
            <form onSubmit={submitPassword} className="space-y-4">
              <h1 className="text-xl font-semibold">{t("login.title")}</h1>
              <Field label={t("login.email")}>
                <input
                  className="input"
                  type="email"
                  autoComplete="username"
                  autoCapitalize="none"
                  required
                  autoFocus
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </Field>
              <Field label={t("login.password")}>
                <input
                  className="input"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </Field>
              <Messages error={error} info={info} />
              <button type="submit" className="btn-primary w-full" disabled={busy}>
                {busy ? t("login.working") : t("login.submit")}
              </button>
            </form>
          ) : (
            <form onSubmit={submitCode} className="space-y-4">
              <h1 className="text-xl font-semibold">{t("login.codeTitle")}</h1>
              <p className="text-sm text-stone-500">{t("login.codeSent", { email: email.trim() })}</p>
              <Field label={t("login.code")}>
                <input
                  className="input text-center text-2xl tracking-[0.5em]"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  required
                  autoFocus
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                />
              </Field>
              <Messages error={error} info={info} />
              <button type="submit" className="btn-primary w-full" disabled={busy || code.length !== 6}>
                {busy ? t("login.working") : t("login.verify")}
              </button>
              <div className="flex items-center justify-between text-sm">
                <button
                  type="button"
                  className="text-stone-500 hover:text-stone-800 dark:hover:text-stone-200"
                  onClick={() => {
                    setChallengeId(null);
                    setCode("");
                    setError(null);
                    setInfo(null);
                  }}
                >
                  ‹ {t("login.back")}
                </button>
                <button
                  type="button"
                  className="font-medium text-accent-700 disabled:text-stone-400 dark:text-accent-500"
                  disabled={busy || resendIn > 0}
                  onClick={resend}
                >
                  {resendIn > 0 ? t("login.resendIn", { seconds: resendIn }) : t("login.resend")}
                </button>
              </div>
            </form>
          )}
        </div>

        <div className="mt-4 flex justify-center gap-3 text-sm">
          {(Object.keys(LANGUAGES) as Language[]).map((lang) => (
            <button
              key={lang}
              type="button"
              onClick={() => setLanguage(lang)}
              className={lang === language ? "font-medium text-stone-800 dark:text-stone-200" : "text-stone-500 hover:text-stone-800"}
            >
              {LANGUAGES[lang]}
            </button>
          ))}
        </div>
      </div>
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

function Messages({ error, info }: { error: string | null; info: string | null }) {
  if (error) return <p role="alert" className="text-sm text-red-700 dark:text-red-400">{error}</p>;
  if (info) return <p className="text-sm text-accent-700 dark:text-accent-500">{info}</p>;
  return null;
}
