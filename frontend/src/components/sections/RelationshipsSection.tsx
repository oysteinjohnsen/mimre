import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { ApiError, api, type CreatableRelation, type Gender, type Person, type PersonSummary, type Relationship } from "../../api";
import { fullName } from "../../lib/format";
import { CREATABLE, INVERSE, RELATION_ORDER, useRelationLabel } from "../../lib/relations";
import { Avatar } from "../Avatar";
import { XIcon } from "../icons";
import { PersonPicker } from "../PersonPicker";
import { EditorActions, EmptyText, IconButton, Section } from "../Section";

export function RelationshipsSection({ person }: { person: Person }) {
  const { t } = useTranslation();
  const [adding, setAdding] = useState(false);
  const { data: rels = [], isPending } = useQuery({
    queryKey: ["relationships", person.id],
    queryFn: () => api.listRelationships(person.id),
  });

  // You first, then by relation priority, then by name.
  const rank = (r: Relationship) => (r.other.is_me ? -1 : RELATION_ORDER.indexOf(r.relation));
  const sorted = [...rels].sort((a, b) => rank(a) - rank(b) || fullName(a.other).localeCompare(fullName(b.other)));

  return (
    <Section title={t("relationships.title")} onAdd={adding ? undefined : () => setAdding(true)}>
      {adding && <AddRelationship person={person} onDone={() => setAdding(false)} />}
      {!isPending && rels.length === 0 && !adding && <EmptyText>{t("relationships.empty")}</EmptyText>}
      {sorted.length > 0 && (
        <ul className="-mx-2">
          {sorted.map((r) => (
            <RelationshipRow key={`${r.relation}-${r.other.id}`} rel={r} />
          ))}
        </ul>
      )}
    </Section>
  );
}

function RelationshipRow({ rel }: { rel: Relationship }) {
  const { t } = useTranslation();
  const label = useRelationLabel();
  const queryClient = useQueryClient();
  const remove = useMutation({
    mutationFn: () => api.deleteRelationship(rel.id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["relationships"] }),
  });
  // The user sees themselves as "Deg"/"You" rather than their own full name.
  const name = rel.other.is_me ? t("person.you") : fullName(rel.other);
  const nameInSentence = rel.other.is_me ? t("person.youInSentence") : name;

  return (
    <li className="flex items-center gap-1">
      <Link
        to={rel.other.is_me ? "/me" : `/people/${rel.other.id}`}
        className="flex min-w-0 flex-1 items-center gap-3 rounded-xl px-2 py-1.5 hover:bg-stone-100 dark:hover:bg-stone-800/60"
      >
        <Avatar person={rel.other} />
        <span className="min-w-0">
          <span className="block truncate font-medium">{name}</span>
          <span className="block truncate text-sm text-stone-500">
            {label(rel.relation, rel.other.gender)}
            {rel.via && <span className="text-stone-400"> · {t("relationships.via", { name: fullName(rel.via) })}</span>}
          </span>
        </span>
      </Link>
      {!rel.inferred && (
        <IconButton
          label={t("relationships.remove")}
          onClick={() => window.confirm(t("relationships.confirmDelete", { name: nameInSentence })) && remove.mutate()}
        >
          <XIcon />
        </IconButton>
      )}
    </li>
  );
}

/**
 * Split a typed name: "Hugo Holvik Johnsen" -> first "Hugo", middle "Holvik", last "Johnsen".
 * (A double first name like "Anne Marie" can be fixed afterwards in the person's form.)
 */
function splitName(name: string): Pick<Person, "first_name" | "middle_name" | "last_name"> {
  const [first, ...rest] = name.trim().split(/\s+/);
  const last = rest.length > 0 ? rest.pop()! : null;
  return { first_name: first, middle_name: rest.join(" ") || null, last_name: last };
}

function AddRelationship({ person, onDone }: { person: Person; onDone: () => void }) {
  const { t } = useTranslation();
  const label = useRelationLabel();
  const queryClient = useQueryClient();
  const [other, setOther] = useState<PersonSummary | null>(null);
  const [newName, setNewName] = useState<string | null>(null);
  const [newGender, setNewGender] = useState<Gender | null>(null);
  const [relation, setRelation] = useState<CreatableRelation | "">("");

  const otherGender = other ? other.gender : newGender;
  const otherName = other ? fullName(other) : newName;

  const save = useMutation({
    mutationFn: async () => {
      let otherId = other?.id;
      if (!otherId) {
        const created = await api.createPerson({
          ...splitName(newName!),
          nickname: null,
          gender: newGender,
          birth_year: null,
          birth_month: null,
          birth_day: null,
          summary: null,
        });
        otherId = created.id;
      }
      return api.createRelationship(person.id, otherId, relation as CreatableRelation);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["relationships"] });
      void queryClient.invalidateQueries({ queryKey: ["persons"] });
      onDone();
    },
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if ((other || newName) && relation) save.mutate();
  };

  return (
    <form onSubmit={onSubmit} className="mb-4 space-y-3 rounded-xl bg-stone-50 p-3 dark:bg-stone-900/60">
      <div>
        <span className="mb-1 block text-sm font-medium text-stone-600 dark:text-stone-400">{t("relationships.who")}</span>
        {otherName ? (
          <div className="flex items-center gap-2 rounded-lg border border-stone-300 bg-white px-3 py-1.5 dark:border-stone-700 dark:bg-stone-950">
            <span className="flex-1 truncate">
              {otherName}
              {newName && <span className="ml-2 text-xs text-accent-700 dark:text-accent-500">{t("relationships.newPerson")}</span>}
            </span>
            <IconButton
              label={t("common.cancel")}
              onClick={() => {
                setOther(null);
                setNewName(null);
              }}
            >
              <XIcon />
            </IconButton>
          </div>
        ) : (
          <PersonPicker excludeId={person.id} onSelect={setOther} onCreate={setNewName} />
        )}
      </div>

      {newName && (
        <fieldset className="flex gap-1 rounded-lg bg-stone-200/70 p-1 dark:bg-stone-800">
          <legend className="sr-only">{t("form.gender")}</legend>
          {(["male", "female", null] as const).map((g) => (
            <label
              key={g ?? "unknown"}
              className={`flex-1 cursor-pointer rounded-md px-2 py-1 text-center text-sm ${
                newGender === g ? "bg-white font-medium shadow-sm dark:bg-stone-950" : "text-stone-600 dark:text-stone-400"
              }`}
            >
              <input type="radio" name="new-gender" className="sr-only" checked={newGender === g} onChange={() => setNewGender(g)} />
              {g ? t(`person.${g}`) : t("form.genderUnknown")}
            </label>
          ))}
        </fieldset>
      )}

      <label className="block">
        <span className="mb-1 block text-sm font-medium text-stone-600 dark:text-stone-400">{t("relationships.relation")}</span>
        <select className="input" required aria-label={t("relationships.relation")} value={relation} onChange={(e) => setRelation(e.target.value as CreatableRelation)}>
          <option value="">{t("relationships.choose")}</option>
          {CREATABLE.map((r) => (
            <option key={r} value={r}>
              {label(r, otherGender)}
            </option>
          ))}
        </select>
      </label>

      {otherName && relation && (
        <p className="text-sm text-stone-500">
          {t("relationships.preview", {
            other: otherName,
            person: person.first_name,
            a: label(relation, otherGender),
            b: label(INVERSE[relation], person.gender),
          })}
        </p>
      )}

      {save.isError && (
        <p className="text-sm text-red-700 dark:text-red-400">
          {save.error instanceof ApiError && save.error.status === 409
            ? t("relationships.exists")
            : t("error.generic", { message: save.error.message })}
        </p>
      )}

      <EditorActions onCancel={onDone} saving={save.isPending || !(otherName && relation)} />
    </form>
  );
}
