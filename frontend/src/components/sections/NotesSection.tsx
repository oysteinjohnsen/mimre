import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type Note, type NoteInput, type Person } from "../../api";
import { LOCALES, type Language } from "../../i18n";
import { EditorActions, EmptyText, IconButton, Section } from "../Section";

/** Today's date in local time as YYYY-MM-DD. */
function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function NotesSection({ person }: { person: Person }) {
  const { t, i18n } = useTranslation();
  const [editing, setEditing] = useState<string | null>(null);
  const { data: notes = [], isPending } = useQuery({
    queryKey: ["notes", person.id],
    queryFn: () => api.listNotes(person.id),
  });
  const dateFormat = new Intl.DateTimeFormat(LOCALES[i18n.resolvedLanguage as Language], { dateStyle: "long", timeZone: "UTC" });
  const formatDate = (iso: string) => dateFormat.format(new Date(`${iso}T00:00:00Z`));

  return (
    <Section title={t("notes.title")}>
      <NoteEditor personId={person.id} />
      {!isPending && notes.length === 0 && (
        <div className="mt-3">
          <EmptyText>{t("notes.empty")}</EmptyText>
        </div>
      )}
      <ol className="mt-2 divide-y divide-stone-100 dark:divide-stone-800/80">
        {notes.map((n) =>
          editing === n.id ? (
            <li key={n.id}>
              <NoteEditor personId={person.id} note={n} onDone={() => setEditing(null)} />
            </li>
          ) : (
            <li key={n.id} className="flex items-start gap-2 py-3">
              <div className="min-w-0 flex-1">
                <time dateTime={n.happened_on} className="text-sm text-stone-500">
                  {formatDate(n.happened_on)}
                </time>
                <p className="mt-0.5 break-words whitespace-pre-wrap">{n.body}</p>
              </div>
              <IconButton label={t("common.edit")} onClick={() => setEditing(n.id)} />
            </li>
          ),
        )}
      </ol>
    </Section>
  );
}

/** New-note composer (no `note`) or inline editor for an existing note. */
function NoteEditor({ personId, note, onDone }: { personId: string; note?: Note; onDone?: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const empty = { body: "", happened_on: todayIso() };
  const [form, setForm] = useState<NoteInput>(note ? { body: note.body, happened_on: note.happened_on } : empty);

  const done = () => {
    void queryClient.invalidateQueries({ queryKey: ["notes", personId] });
    if (note) onDone?.();
    else setForm(empty);
  };
  const save = useMutation({
    mutationFn: (data: NoteInput) => (note ? api.updateNote(note.id, data) : api.createNote(personId, data)),
    onSuccess: done,
  });
  const remove = useMutation({ mutationFn: () => api.deleteNote(note!.id), onSuccess: done });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (form.body.trim()) save.mutate({ ...form, body: form.body.trim() });
  };

  const showActions = note || form.body.trim().length > 0;

  return (
    <form onSubmit={onSubmit} className={note ? "my-2 space-y-2 rounded-xl bg-stone-50 p-3 dark:bg-stone-900/60" : "space-y-2"}>
      <textarea
        className="input field-sizing-content min-h-20"
        autoFocus={!!note}
        placeholder={t("notes.placeholder")}
        aria-label={t("notes.title")}
        value={form.body}
        onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
      />
      {showActions && (
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="date"
            className="input w-auto"
            aria-label={t("notes.date")}
            required
            value={form.happened_on}
            onChange={(e) => setForm((f) => ({ ...f, happened_on: e.target.value }))}
          />
          <div className="min-w-60 flex-1">
            <EditorActions
              onCancel={note ? onDone! : () => setForm(empty)}
              saving={save.isPending}
              onDelete={note ? () => window.confirm(t("notes.confirmDelete")) && remove.mutate() : undefined}
            />
          </div>
        </div>
      )}
      {(save.isError || remove.isError) && (
        <p className="text-sm text-red-700 dark:text-red-400">{t("error.generic", { message: (save.error ?? remove.error)?.message })}</p>
      )}
    </form>
  );
}
