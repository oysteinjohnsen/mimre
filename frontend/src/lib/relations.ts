import { useTranslation } from "react-i18next";

import type { CreatableRelation, Gender, Relation } from "../api";

/**
 * Display priority: partner, closest family, second-degree family, friends, then more distant relations.
 * (The user's own profile is always shown first, regardless of relation.)
 */
export const RELATION_ORDER: Relation[] = [
  "spouse",
  "cohabitant",
  "partner",
  "parent",
  "child",
  "sibling",
  "grandparent",
  "grandchild",
  "parent_in_law",
  "child_in_law",
  "sibling_in_law",
  "aunt_uncle",
  "niece_nephew",
  "cousin",
  "friend",
  "colleague",
  "neighbor",
  "ex",
  "acquaintance",
];

/** Relations offered when adding. Family ones can also be inferred, but entering them directly is handy. */
export const CREATABLE: CreatableRelation[] = [
  "parent",
  "child",
  "sibling",
  "grandparent",
  "grandchild",
  "parent_in_law",
  "child_in_law",
  "sibling_in_law",
  "aunt_uncle",
  "niece_nephew",
  "cousin",
  "spouse",
  "cohabitant",
  "partner",
  "ex",
  "friend",
  "colleague",
  "neighbor",
  "acquaintance",
];

/** If B is A's `relation`, then A is B's `INVERSE[relation]`. */
export const INVERSE: Record<Relation, Relation> = {
  parent: "child",
  child: "parent",
  grandparent: "grandchild",
  grandchild: "grandparent",
  aunt_uncle: "niece_nephew",
  niece_nephew: "aunt_uncle",
  cousin: "cousin",
  parent_in_law: "child_in_law",
  child_in_law: "parent_in_law",
  sibling_in_law: "sibling_in_law",
  sibling: "sibling",
  spouse: "spouse",
  cohabitant: "cohabitant",
  partner: "partner",
  ex: "ex",
  friend: "friend",
  colleague: "colleague",
  neighbor: "neighbor",
  acquaintance: "acquaintance",
};

/** Label for a relation, gendered by the person it describes: ("parent", "female") -> "Mor". */
export function useRelationLabel() {
  const { t } = useTranslation();
  return (relation: Relation, gender: Gender | null | undefined) => t(`relation.${relation}`, { context: gender ?? undefined });
}
