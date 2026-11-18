export type Gender = "male" | "female";

export interface PersonInput {
  first_name: string;
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
  listPersons: (q?: string) => request<Person[]>(`/persons${q ? `?q=${encodeURIComponent(q)}` : ""}`),
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
};
