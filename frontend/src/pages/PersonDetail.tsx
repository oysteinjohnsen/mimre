import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useNavigate, useParams } from "react-router";

import { api } from "../api";
import { BackLink } from "../components/BackLink";
import { PersonCard } from "../components/PersonCard";
import { fullName } from "../lib/format";

export function PersonDetail() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: person, isPending, isError } = useQuery({
    queryKey: ["person", id],
    queryFn: () => api.getPerson(id!),
  });

  const remove = useMutation({
    mutationFn: () => api.deletePerson(id!),
    onSuccess: async () => {
      // Leave the page first so the detail query isn't refetched for a deleted person.
      await navigate("/");
      queryClient.removeQueries({ queryKey: ["person", id] });
      await queryClient.invalidateQueries({ queryKey: ["persons"] });
    },
  });

  if (isPending) return null;
  if (isError || !person) {
    return (
      <div className="p-4 md:p-0">
        <BackLink />
        <p className="text-stone-500">{t("person.notFound")}</p>
      </div>
    );
  }
  // The user's own details live on the profile page.
  if (person.is_me) return <Navigate to="/me" replace />;

  return (
    <div className="p-4 md:p-0">
      <BackLink />
      <PersonCard
        person={person}
        actions={
          <>
            <Link to={`/people/${person.id}/edit`} className="btn-secondary">
              {t("form.edit")}
            </Link>
            <button
              type="button"
              className="btn-danger"
              disabled={remove.isPending}
              onClick={() => {
                if (window.confirm(t("form.confirmDelete", { name: fullName(person) }))) remove.mutate();
              }}
            >
              {t("form.delete")}
            </button>
          </>
        }
      >
        {remove.isError && (
          <p className="mt-4 text-sm text-red-700 dark:text-red-400">{t("error.generic", { message: remove.error.message })}</p>
        )}
      </PersonCard>
    </div>
  );
}
