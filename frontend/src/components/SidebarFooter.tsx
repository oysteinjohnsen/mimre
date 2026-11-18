import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router";

import { api } from "../api";
import { fullName } from "../lib/format";
import { Avatar } from "./Avatar";

const itemClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-3 rounded-xl px-3 py-2 ${
    isActive
      ? "bg-accent-50 text-accent-900 dark:bg-accent-900/40 dark:text-accent-100"
      : "text-stone-600 hover:bg-stone-200/60 dark:text-stone-300 dark:hover:bg-stone-800/60"
  }`;

/** Bottom of the menu pane: the user's own profile and settings. */
export function SidebarFooter() {
  const { t } = useTranslation();
  const { data: me } = useQuery({ queryKey: ["me"], queryFn: api.getMe });

  return (
    <footer className="flex items-center gap-1 border-t border-stone-200 px-2 pt-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] md:mt-3 md:border-0 md:px-0 md:pb-0 dark:border-stone-800">
      <NavLink to="/me" className={(s) => `${itemClass(s)} min-w-0 flex-1`}>
        {me ? (
          <Avatar person={me} />
        ) : (
          <span className="inline-flex size-9 items-center justify-center rounded-full border border-dashed border-stone-400 text-stone-400">?</span>
        )}
        <span className="min-w-0">
          <span className="block truncate text-sm font-medium">{me ? fullName(me) : t("profile.create")}</span>
          <span className="block text-xs text-stone-500">{t("nav.profile")}</span>
        </span>
      </NavLink>
      <NavLink to="/settings" className={(s) => `${itemClass(s)} px-2.5`} title={t("nav.settings")} aria-label={t("nav.settings")}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="size-5" aria-hidden>
          <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      </NavLink>
    </footer>
  );
}
