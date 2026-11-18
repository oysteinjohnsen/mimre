import { useTranslation } from "react-i18next";
import { Link } from "react-router";

/** Back to the list; only shown on narrow screens where the list is hidden. */
export function BackLink({ to = "/" }: { to?: string }) {
  const { t } = useTranslation();
  return (
    <Link to={to} className="mb-2 inline-flex items-center gap-1 py-2 text-sm font-medium text-accent-700 md:hidden dark:text-accent-500">
      <span aria-hidden>‹</span> {t("nav.people")}
    </Link>
  );
}
