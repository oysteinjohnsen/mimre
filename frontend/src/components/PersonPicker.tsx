import { useQuery } from "@tanstack/react-query";
import { type KeyboardEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type PersonSummary } from "../api";
import { fullName } from "../lib/format";
import { useDebounced } from "../lib/hooks";
import { Avatar } from "./Avatar";

type Option = { type: "person"; person: PersonSummary } | { type: "create"; name: string };

/** Search for an existing person, or offer to create a new one with the typed name. */
export function PersonPicker({
  excludeId,
  onSelect,
  onCreate,
}: {
  excludeId: string;
  onSelect: (person: PersonSummary) => void;
  onCreate: (name: string) => void;
}) {
  const { t } = useTranslation();
  const [text, setText] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const q = useDebounced(text.trim(), 150);

  const { data = [] } = useQuery({
    queryKey: ["persons", q, "withMe"],
    queryFn: () => api.listPersons(q, { includeMe: true }),
    enabled: q.length > 0,
  });

  const name = text.trim();
  const options: Option[] = name
    ? [
        ...data.filter((p) => p.id !== excludeId).slice(0, 6).map((person) => ({ type: "person" as const, person })),
        { type: "create", name },
      ]
    : [];

  const choose = (o: Option) => (o.type === "person" ? onSelect(o.person) : onCreate(o.name));

  const onKeyDown = (e: KeyboardEvent) => {
    if (!options.length) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      setOpen(true);
      setActive((i) => (i + (e.key === "ArrowDown" ? 1 : -1) + options.length) % options.length);
    } else if (e.key === "Enter") {
      e.preventDefault(); // don't submit the surrounding form
      choose(options[Math.min(active, options.length - 1)]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div className="relative">
      <input
        className="input"
        autoFocus
        role="combobox"
        aria-expanded={open && options.length > 0}
        aria-label={t("relationships.who")}
        placeholder={t("relationships.searchPerson")}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          setActive(0);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={onKeyDown}
      />
      {open && options.length > 0 && (
        <ul role="listbox" className="absolute inset-x-0 top-full z-10 mt-1 overflow-hidden rounded-lg border border-stone-200 bg-white shadow-lg dark:border-stone-700 dark:bg-stone-900">
          {options.map((o, i) => (
            <li key={o.type === "person" ? o.person.id : "create"} role="option" aria-selected={i === active}>
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()} // keep focus so onBlur doesn't close first
                onClick={() => choose(o)}
                onMouseEnter={() => setActive(i)}
                className={`flex w-full items-center gap-3 px-3 py-2 text-left ${i === active ? "bg-stone-100 dark:bg-stone-800" : ""}`}
              >
                {o.type === "person" ? (
                  <>
                    <Avatar person={o.person} />
                    <span className="truncate">{fullName(o.person)}</span>
                  </>
                ) : (
                  <span className="py-1.5 font-medium text-accent-700 dark:text-accent-500">+ {t("relationships.createNew", { name: o.name })}</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
