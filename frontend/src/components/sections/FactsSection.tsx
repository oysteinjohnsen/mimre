import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type Fact, type FactInput, type FactKind, type Person } from "../../api";
import { LOCALES, type Language } from "../../i18n";
import { EditorActions, EmptyText, IconButton, Section } from "../Section";

const KINDS: FactKind[] = ["text", "phone", "email", "address", "url", "date"];

/** Common labels offered as suggestions alongside the ones already in use. */
const DEFAULT_LABELS: Record<Language, { label: string; kind: FactKind }[]> = {
  nb: [
    { label: "Telefon", kind: "phone" },
    { label: "E-post", kind: "email" },
    { label: "Adresse", kind: "address" },
    { label: "Bor i", kind: "text" },
    { label: "Jobber i", kind: "text" },
    { label: "Stilling", kind: "text" },
    { label: "Hund", kind: "text" },
    { label: "Katt", kind: "text" },
    { label: "Hobby", kind: "text" },
    { label: "Allergi", kind: "text" },
    { label: "Gaveidé", kind: "text" },
    { label: "Bryllupsdag", kind: "date" },
    { label: "Nettside", kind: "url" },
  ],
  en: [
    { label: "Phone", kind: "phone" },
    { label: "Email", kind: "email" },
    { label: "Address", kind: "address" },
    { label: "Lives in", kind: "text" },
    { label: "Works at", kind: "text" },
    { label: "Job title", kind: "text" },
    { label: "Dog", kind: "text" },
    { label: "Cat", kind: "text" },
    { label: "Hobby", kind: "text" },
    { label: "Allergy", kind: "text" },
    { label: "Gift idea", kind: "text" },
    { label: "Wedding anniversary", kind: "date" },
    { label: "Website", kind: "url" },
  ],
};

export function FactsSection({ person }: { person: Person }) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState<string | null>(null); // fact id, "new" or null
  const { data: facts = [], isPending } = useQuery({
    queryKey: ["facts", person.id],
    queryFn: () => api.listFacts(person.id),
  });

  return (
    <Section title={t("facts.title")} onAdd={editing === "new" ? undefined : () => setEditing("new")}>
      {!isPending && facts.length === 0 && editing !== "new" && <EmptyText>{t("facts.empty")}</EmptyText>}
      <dl className="divide-y divide-stone-100 dark:divide-stone-800/80">
        {facts.map((f) =>
          editing === f.id ? (
            <FactEditor key={f.id} personId={person.id} fact={f} onDone={() => setEditing(null)} />
          ) : (
            <div key={f.id} className="flex items-start gap-2 py-2">
              <div className="min-w-0 flex-1">
                <dt className="text-sm text-stone-500">{f.label}</dt>
                <dd className="break-words">
                  <FactValue fact={f} />
                </dd>
              </div>
              <IconButton label={t("common.edit")} onClick={() => setEditing(f.id)} />
            </div>
          ),
        )}
      </dl>
      {editing === "new" && <FactEditor personId={person.id} onDone={() => setEditing(null)} />}
    </Section>
  );
}

function FactValue({ fact }: { fact: Fact }) {
  const { i18n } = useTranslation();
  const link = "text-accent-700 underline-offset-2 hover:underline dark:text-accent-500";
  const v = fact.value;
  switch (fact.kind) {
    case "phone":
      return (
        <a className={link} href={`tel:${v.replace(/[^\d+]/g, "")}`}>
          {v}
        </a>
      );
    case "email":
      return (
        <a className={link} href={`mailto:${v}`}>
          {v}
        </a>
      );
    case "url":
      return (
        <a className={link} href={/^https?:\/\//i.test(v) ? v : `https://${v}`} target="_blank" rel="noopener noreferrer">
          {v.replace(/^https?:\/\//i, "")}
        </a>
      );
    case "address":
      return (
        <a className={`${link} whitespace-pre-line`} href={`https://maps.apple.com/?q=${encodeURIComponent(v)}`} target="_blank" rel="noopener noreferrer">
          {v}
        </a>
      );
    case "date": {
      const [y, m, d] = v.split("-").map(Number);
      const locale = LOCALES[i18n.resolvedLanguage as Language];
      return <>{new Intl.DateTimeFormat(locale, { dateStyle: "long", timeZone: "UTC" }).format(new Date(Date.UTC(y, m - 1, d)))}</>;
    }
    default:
      return <span className="whitespace-pre-wrap">{v}</span>;
  }
}

function FactEditor({ personId, fact, onDone }: { personId: string; fact?: Fact; onDone: () => void }) {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const listId = useId();
  const [form, setForm] = useState<FactInput>({ kind: fact?.kind ?? "text", label: fact?.label ?? "", value: fact?.value ?? "" });

  const { data: used = [] } = useQuery({ queryKey: ["factLabels"], queryFn: api.factLabels, staleTime: 60_000 });
  const suggestions = [...used, ...DEFAULT_LABELS[i18n.resolvedLanguage as Language].filter((d) => !used.some((u) => u.label === d.label))];

  const done = () => {
    void queryClient.invalidateQueries({ queryKey: ["facts", personId] });
    void queryClient.invalidateQueries({ queryKey: ["factLabels"] });
    onDone();
  };
  const save = useMutation({
    mutationFn: (data: FactInput) => (fact ? api.updateFact(fact.id, data) : api.createFact(personId, data)),
    onSuccess: done,
  });
  const remove = useMutation({ mutationFn: () => api.deleteFact(fact!.id), onSuccess: done });

  const onLabelChange = (label: string) => {
    // Picking a known label (e.g. "Telefon") also picks its type.
    const match = suggestions.find((s) => s.label.toLowerCase() === label.trim().toLowerCase());
    setForm((f) => ({ ...f, label, kind: match && !fact ? match.kind : f.kind }));
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate({ ...form, label: form.label.trim(), value: form.value.trim() });
  };

  const valueProps = {
    className: "input",
    required: true,
    "aria-label": t("facts.value"),
    value: form.value,
    onChange: (e: { target: { value: string } }) => setForm((f) => ({ ...f, value: e.target.value })),
  };

  return (
    <form onSubmit={onSubmit} className="my-2 space-y-2 rounded-xl bg-stone-50 p-3 dark:bg-stone-900/60">
      <div className="grid grid-cols-[1fr_8rem] gap-2">
        <input
          className="input"
          required
          autoFocus
          list={listId}
          aria-label={t("facts.label")}
          placeholder={t("facts.labelPlaceholder")}
          value={form.label}
          onChange={(e) => onLabelChange(e.target.value)}
        />
        <datalist id={listId}>
          {suggestions.map((s) => (
            <option key={s.label} value={s.label} />
          ))}
        </datalist>
        <select
          className="input"
          aria-label={t("facts.kind")}
          value={form.kind}
          onChange={(e) => setForm((f) => ({ ...f, kind: e.target.value as FactKind }))}
        >
          {KINDS.map((k) => (
            <option key={k} value={k}>
              {t(`facts.kinds.${k}`)}
            </option>
          ))}
        </select>
      </div>
      {form.kind === "address" ? (
        <textarea rows={2} {...valueProps} />
      ) : form.kind === "text" ? (
        <textarea rows={1} {...valueProps} className="input field-sizing-content min-h-10" />
      ) : (
        <input
          {...valueProps}
          type={{ phone: "tel", email: "email", date: "date", url: "text" }[form.kind]}
          inputMode={form.kind === "url" ? "url" : undefined}
        />
      )}
      {(save.isError || remove.isError) && (
        <p className="text-sm text-red-700 dark:text-red-400">{t("error.generic", { message: (save.error ?? remove.error)?.message })}</p>
      )}
      <EditorActions
        onCancel={onDone}
        saving={save.isPending}
        onDelete={fact ? () => window.confirm(t("facts.confirmDelete", { label: fact.label })) && remove.mutate() : undefined}
      />
    </form>
  );
}
