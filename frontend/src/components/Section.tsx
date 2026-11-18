import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { PencilIcon, PlusIcon } from "./icons";

export function Section({ title, onAdd, children }: { title: string; onAdd?: () => void; children: ReactNode }) {
  const { t } = useTranslation();
  return (
    <section className="card p-5 md:p-6">
      <header className="mb-3 flex items-center justify-between gap-2">
        <h2 className="font-semibold">{title}</h2>
        {onAdd && (
          <button type="button" onClick={onAdd} className="btn -mr-2 px-2 py-1 text-accent-700 hover:bg-accent-50 dark:text-accent-500 dark:hover:bg-accent-900/30">
            <PlusIcon /> {t("common.add")}
          </button>
        )}
      </header>
      {children}
    </section>
  );
}

export function EmptyText({ children }: { children: ReactNode }) {
  return <p className="text-sm text-stone-500">{children}</p>;
}

/** Small, low-contrast icon button (edit/remove) that stays visible on touch screens. */
export function IconButton({ label, onClick, children }: { label: string; onClick: () => void; children?: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      aria-label={label}
      className="shrink-0 rounded-md p-1.5 text-stone-400 hover:bg-stone-100 hover:text-stone-700 dark:hover:bg-stone-800 dark:hover:text-stone-200"
    >
      {children ?? <PencilIcon />}
    </button>
  );
}

/** Save / cancel / (delete) row used by inline editors. */
export function EditorActions({ onCancel, onDelete, saving }: { onCancel: () => void; onDelete?: () => void; saving?: boolean }) {
  const { t } = useTranslation();
  return (
    <div className="flex items-center gap-2">
      {onDelete && (
        <button type="button" className="btn-danger -ml-2 px-2" onClick={onDelete}>
          {t("common.delete")}
        </button>
      )}
      <div className="ml-auto flex gap-2">
        <button type="button" className="btn-secondary px-3 py-1.5" onClick={onCancel}>
          {t("common.cancel")}
        </button>
        <button type="submit" className="btn-primary px-3 py-1.5" disabled={saving}>
          {t("common.save")}
        </button>
      </div>
    </div>
  );
}
