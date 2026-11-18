import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink } from "react-router";

import { api } from "../api";
import { fullName } from "../lib/format";
import { Avatar } from "./Avatar";
import { SidebarFooter } from "./SidebarFooter";

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return debounced;
}

export function PersonList() {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const q = useDebounced(search.trim(), 200);

  const { data: persons, isPending, isError } = useQuery({
    queryKey: ["persons", q],
    queryFn: () => api.listPersons(q),
    placeholderData: keepPreviousData,
  });

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="flex items-center gap-2 px-4 pt-4 pb-3 md:px-1 md:pt-0">
        <Link to="/" className="flex items-center gap-2">
          <img src="/favicon.svg" alt="" className="size-8" />
          <span className="text-xl font-semibold tracking-tight">Mimre</span>
        </Link>
        <Link to="/people/new" className="btn-primary ml-auto w-20 px-0" title={t("nav.newPerson")} aria-label={t("nav.newPerson")}>
          <span aria-hidden className="text-lg leading-none">+</span>
          {t("nav.new")}
        </Link>
      </header>

      <div className="px-4 pb-3 md:px-0">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t("search.placeholder")}
          aria-label={t("search.placeholder")}
          className="input"
        />
      </div>

      <nav className="min-h-0 flex-1 overflow-y-auto px-2 md:card md:px-1.5 md:py-1.5">
        {isError && <p className="p-4 text-sm text-red-700 dark:text-red-400">{t("error.loading")}</p>}
        {!isPending && persons?.length === 0 && (
          <p className="p-4 text-sm text-stone-500">{q ? t("search.noResults") : t("search.empty")}</p>
        )}
        <ul>
          {persons?.map((p) => (
            <li key={p.id}>
              <NavLink
                to={`/people/${p.id}`}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-2.5 ${
                    isActive
                      ? "bg-accent-50 text-accent-900 dark:bg-accent-900/40 dark:text-accent-100"
                      : "hover:bg-stone-200/60 dark:hover:bg-stone-800/60"
                  }`
                }
              >
                <Avatar person={p} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium">{fullName(p)}</span>
                  {p.nickname && <span className="block truncate text-sm text-stone-500">«{p.nickname}»</span>}
                </span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <SidebarFooter />
    </div>
  );
}
