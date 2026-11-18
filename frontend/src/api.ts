export type Gender = "male" | "female";

export interface PersonInput {
  first_name: string;
  middle_name: string | null;
  last_name: string | null;
  nickname: string | null;
  gender: Gender | null;
  birth_year: number | null;
  birth_month: number | null;
  birth_day: number | null;
  summary: string | null;
}

export interface Person extends PersonInput {
  id: string;
  /** True for the user's own profile (managed via /me). */
  is_me: boolean;
  created_at: string;
  updated_at: string;
}

/** Search results may include an excerpt of the fact or note that matched. */
export interface PersonListItem extends Person {
  match?: string | null;
}

export type PersonSummary = Pick<Person, "id" | "first_name" | "middle_name" | "last_name" | "nickname" | "gender" | "is_me">;

/** What the other person is to the person being viewed. */
export type Relation =
  | "parent"
  | "child"
  | "sibling"
  | "spouse"
  | "cohabitant"
  | "partner"
  | "ex"
  | "friend"
  | "colleague"
  | "neighbor"
  | "acquaintance"
  | "grandparent"
  | "grandchild"
  | "aunt_uncle"
  | "niece_nephew"
  | "cousin"
  | "parent_in_law"
  | "child_in_law"
  | "sibling_in_law";
/** All relations can be entered directly; family ones may also be inferred. */
export type CreatableRelation = Relation;

export interface Relationship {
  id: string | null; // null when inferred
  relation: Relation;
  inferred: boolean;
  other: PersonSummary;
  /** For inferred relationships: who it goes through (e.g. the shared parent of two siblings). */
  via: PersonSummary | null;
}

export type FactKind = "text" | "phone" | "email" | "address" | "url" | "date";

export interface FactInput {
  kind: FactKind;
  label: string;
  value: string;
}

export interface Fact extends FactInput {
  id: string;
  person_id: string;
  created_at: string;
  updated_at: string;
}

export interface NoteInput {
  body: string;
  happened_on: string; // YYYY-MM-DD
}

export interface Note extends NoteInput {
  id: string;
  person_id: string;
  created_at: string;
  updated_at: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      // FastAPI returns either a string or a list of validation errors.
      message = typeof body.detail === "string" ? body.detail : body.detail.map((d: { msg: string }) => d.msg).join(", ");
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, message);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export const api = {
  listPersons: (q?: string, opts?: { includeMe?: boolean }) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (opts?.includeMe) params.set("include_me", "true");
    const qs = params.toString();
    return request<PersonListItem[]>(`/persons${qs ? `?${qs}` : ""}`);
  },
  getPerson: (id: string) => request<Person>(`/persons/${id}`),
  createPerson: (data: PersonInput) => request<Person>("/persons", { method: "POST", body: JSON.stringify(data) }),
  updatePerson: (id: string, data: Partial<PersonInput>) =>
    request<Person>(`/persons/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deletePerson: (id: string) => request<void>(`/persons/${id}`, { method: "DELETE" }),

  /** The user's own profile, or null if it hasn't been created yet. */
  getMe: async () => {
    try {
      return await request<Person>("/me");
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }
  },
  saveMe: (data: PersonInput) => request<Person>("/me", { method: "PUT", body: JSON.stringify(data) }),

  listRelationships: (personId: string) => request<Relationship[]>(`/persons/${personId}/relationships`),
  createRelationship: (personId: string, otherId: string, relation: CreatableRelation) =>
    request<Relationship>("/relationships", {
      method: "POST",
      body: JSON.stringify({ person_id: personId, other_id: otherId, relation }),
    }),
  deleteRelationship: (id: string) => request<void>(`/relationships/${id}`, { method: "DELETE" }),

  listFacts: (personId: string) => request<Fact[]>(`/persons/${personId}/facts`),
  factLabels: () => request<Pick<Fact, "label" | "kind">[]>("/facts/labels"),
  createFact: (personId: string, data: FactInput) =>
    request<Fact>(`/persons/${personId}/facts`, { method: "POST", body: JSON.stringify(data) }),
  updateFact: (id: string, data: Partial<FactInput>) =>
    request<Fact>(`/facts/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteFact: (id: string) => request<void>(`/facts/${id}`, { method: "DELETE" }),

  listNotes: (personId: string) => request<Note[]>(`/persons/${personId}/notes`),
  createNote: (personId: string, data: NoteInput) =>
    request<Note>(`/persons/${personId}/notes`, { method: "POST", body: JSON.stringify(data) }),
  updateNote: (id: string, data: Partial<NoteInput>) =>
    request<Note>(`/notes/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteNote: (id: string) => request<void>(`/notes/${id}`, { method: "DELETE" }),
};
