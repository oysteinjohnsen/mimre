import type { Person } from "../../api";
import { FactsSection } from "./FactsSection";
import { NotesSection } from "./NotesSection";
import { RelationshipsSection } from "./RelationshipsSection";

/** Relationships, facts and notes below a person's card (also used on the profile page). */
export function PersonSections({ person }: { person: Person }) {
  return (
    <div className="mt-4 grid items-start gap-4 lg:grid-cols-2">
      <RelationshipsSection person={person} />
      <FactsSection person={person} />
      <div className="lg:col-span-2">
        <NotesSection person={person} />
      </div>
    </div>
  );
}
