import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { api } from "../api";
import { BackLink } from "../components/BackLink";
import { PersonCard } from "../components/PersonCard";
import { PersonSections } from "../components/sections/PersonSections";

export function Profile() {
  const { t } = useTranslation();
  const { data: me, isPending } = useQuery({ queryKey: ["me"], queryFn: api.getMe });

  if (isPending) return null;

  return (
    <div className="p-4 md:p-0">
      <BackLink />
      <p className="mb-3 text-sm font-medium tracking-wide text-stone-500 uppercase">{t("profile.title")}</p>
      {me ? (
        <>
          <PersonCard
            person={me}
            actions={
              <Link to="/me/edit" className="btn-secondary">
                {t("form.edit")}
              </Link>
            }
          />
          <PersonSections person={me} />
        </>
      ) : (
        <div className="card p-8 text-center">
          <h1 className="text-lg font-semibold">{t("profile.emptyTitle")}</h1>
          <p className="mx-auto mt-1 max-w-sm text-sm text-stone-500">{t("profile.emptyBody")}</p>
          <Link to="/me/edit" className="btn-primary mt-5">
            {t("profile.create")}
          </Link>
        </div>
      )}
    </div>
  );
}
