import { useTranslation } from "react-i18next";

export function EmptyState() {
  const { t } = useTranslation();
  return (
    <div className="card flex h-full flex-col items-center justify-center p-8 text-center">
      <img src="/favicon.svg" alt="" className="mb-4 size-12 opacity-80" />
      <h2 className="text-lg font-semibold">{t("empty.title")}</h2>
      <p className="mt-1 max-w-xs text-sm text-stone-500">{t("empty.body")}</p>
    </div>
  );
}
