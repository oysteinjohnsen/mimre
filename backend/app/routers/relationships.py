"""Relationships between people.

Each relationship is stored once. The label each side sees is derived when reading:
if A is parent of B, then A's page lists B as "child" and B's page lists A as "parent".

Family relationships that follow from parent, sibling and spouse links are
also inferred (siblings, grandparents, in-laws, aunts/uncles, nieces/nephews, cousins),
each with the person it goes through ("via").
"""

import uuid
from collections import defaultdict
from collections.abc import Iterable

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from app.deps import SessionDep, get_or_404, get_person_or_404
from app.models import Person, Relationship, RelationshipType
from app.schemas import PersonSummary, RelationshipCreate, RelationshipRead

router = APIRouter(tags=["relationships"])

T = RelationshipType

# Directed types: person_a is the "senior" side. Maps type -> (relation of a seen from b, relation of b seen from a).
DIRECTED: dict[RelationshipType, tuple[str, str]] = {
    T.PARENT: ("parent", "child"),
    T.GRANDPARENT: ("grandparent", "grandchild"),
    T.AUNT_UNCLE: ("aunt_uncle", "niece_nephew"),
    T.PARENT_IN_LAW: ("parent_in_law", "child_in_law"),
}
# Relation name (as seen by the person adding it) -> (type, True if the *other* person is the senior side).
DIRECTED_BY_RELATION = {senior: (t, True) for t, (senior, _) in DIRECTED.items()} | {
    junior: (t, False) for t, (_, junior) in DIRECTED.items()
}

FAMILY = {
    "parent", "child", "sibling", "spouse", "cohabitant", "partner",
    "grandparent", "grandchild", "aunt_uncle", "niece_nephew", "cousin",
    "parent_in_law", "child_in_law", "sibling_in_law",
}  # fmt: skip

# Only marriage creates in-laws (not cohabitants or boyfriends/girlfriends).
IN_LAW_PARTNER_TYPES = [T.SPOUSE]


class FamilyGraph:
    """Parent, sibling, spouse and aunt/uncle links, loaded once per request (a personal contact list is small)."""

    def __init__(self, session: Session):
        self.parents: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
        self.children: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
        self.explicit_siblings: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
        self.explicit_aunts_uncles: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
        self.spouses: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
        rows = session.execute(
            select(Relationship.type, Relationship.person_a_id, Relationship.person_b_id).where(
                Relationship.type.in_([T.PARENT, T.SIBLING, T.AUNT_UNCLE, *IN_LAW_PARTNER_TYPES])
            )
        )
        for type_, a, b in rows:
            if type_ == T.PARENT:
                self.parents[b].add(a)
                self.children[a].add(b)
            elif type_ == T.SIBLING:
                self.explicit_siblings[a].add(b)
                self.explicit_siblings[b].add(a)
            elif type_ == T.AUNT_UNCLE:
                self.explicit_aunts_uncles[b].add(a)
            else:
                self.spouses[a].add(b)
                self.spouses[b].add(a)

    def siblings(self, x: uuid.UUID) -> set[uuid.UUID]:
        shared_parent = {c for p in self.parents[x] for c in self.children[p]}
        return (self.explicit_siblings[x] | shared_parent) - {x}

    def inferred(self, x: uuid.UUID) -> Iterable[tuple[str, uuid.UUID, uuid.UUID]]:
        """(relation, other, via) candidates, closest relations first."""
        parents = sorted(self.parents[x])
        for p in parents:
            for c in sorted(self.children[p] - {x}):
                yield "sibling", c, p
        for p in parents:
            for g in sorted(self.parents[p]):
                yield "grandparent", g, p
        for c in sorted(self.children[x]):
            for g in sorted(self.children[c]):
                yield "grandchild", g, c
        # In-laws, through a spouse (mine, my child's or my sibling's).
        for s in sorted(self.spouses[x]):
            for p in sorted(self.parents[s]):
                yield "parent_in_law", p, s
        for c in sorted(self.children[x]):
            for s in sorted(self.spouses[c]):
                yield "child_in_law", s, c
        for s in sorted(self.spouses[x]):
            for sib in sorted(self.siblings(s)):
                yield "sibling_in_law", sib, s
        for sib in sorted(self.siblings(x)):
            for s in sorted(self.spouses[sib]):
                yield "sibling_in_law", s, sib
        aunts_uncles: list[tuple[uuid.UUID, uuid.UUID | None]] = [
            (s, p) for p in parents for s in sorted(self.siblings(p) - set(parents))
        ]
        yield from (("aunt_uncle", s, p) for s, p in aunts_uncles)
        for s in sorted(self.siblings(x)):
            for c in sorted(self.children[s]):
                yield "niece_nephew", c, s
        # Cousins: children of aunts/uncles, whether those were inferred or entered directly.
        for a in [s for s, _ in aunts_uncles] + sorted(self.explicit_aunts_uncles[x]):
            for c in sorted(self.children[a]):
                yield "cousin", c, a


@router.get("/persons/{person_id}/relationships", response_model=list[RelationshipRead])
def list_relationships(person_id: uuid.UUID, session: SessionDep) -> list[RelationshipRead]:
    get_person_or_404(session, person_id)
    rels = session.scalars(
        select(Relationship).where(or_(Relationship.person_a_id == person_id, Relationship.person_b_id == person_id))
    ).all()

    # (relationship id or None, relation as seen from person_id, other person id, via person id if inferred)
    items: list[tuple[uuid.UUID | None, str, uuid.UUID, uuid.UUID | None]] = []
    seen: set[tuple[str, uuid.UUID]] = set()
    family_of: set[uuid.UUID] = set()  # people already listed with a family relation

    for r in rels:
        if r.type in DIRECTED:
            senior, junior = DIRECTED[r.type]
            other, relation = (r.person_b_id, junior) if r.person_a_id == person_id else (r.person_a_id, senior)
        else:
            other = r.person_b_id if r.person_a_id == person_id else r.person_a_id
            relation = r.type.value
        items.append((r.id, relation, other, None))
        seen.add((relation, other))
        if relation in FAMILY:
            family_of.add(other)

    # Inferred relations, closest first; skip anyone already listed as family (closer relation wins).
    for relation, other, via in FamilyGraph(session).inferred(person_id):
        if other != person_id and other not in family_of and (relation, other) not in seen:
            items.append((None, relation, other, via))
            seen.add((relation, other))
            family_of.add(other)

    ids = {o for _, _, o, _ in items} | {v for *_, v in items if v}
    persons = {p.id: PersonSummary.model_validate(p) for p in session.scalars(select(Person).where(Person.id.in_(ids)))} if ids else {}
    return [
        RelationshipRead(
            id=id_, relation=relation, inferred=via is not None, other=persons[other], via=persons[via] if via else None
        )
        for id_, relation, other, via in items
    ]


@router.post("/relationships", response_model=RelationshipRead, status_code=status.HTTP_201_CREATED)
def create_relationship(data: RelationshipCreate, session: SessionDep) -> RelationshipRead:
    get_person_or_404(session, data.person_id)
    other = get_person_or_404(session, data.other_id)

    if data.relation in DIRECTED_BY_RELATION:
        type_, other_is_senior = DIRECTED_BY_RELATION[data.relation]
        a, b = (data.other_id, data.person_id) if other_is_senior else (data.person_id, data.other_id)
        reverse = exists().where(Relationship.type == type_, Relationship.person_a_id == b, Relationship.person_b_id == a)
        if session.scalar(select(reverse)):
            raise HTTPException(status.HTTP_409_CONFLICT, "The opposite relationship already exists")
    else:
        type_ = RelationshipType(data.relation)
        a, b = sorted((data.person_id, data.other_id))

    duplicate = exists().where(Relationship.type == type_, Relationship.person_a_id == a, Relationship.person_b_id == b)
    if session.scalar(select(duplicate)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Relationship already exists")

    rel = Relationship(person_a_id=a, person_b_id=b, type=type_)
    session.add(rel)
    session.commit()
    return RelationshipRead(id=rel.id, relation=data.relation, other=PersonSummary.model_validate(other))


@router.delete("/relationships/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_relationship(relationship_id: uuid.UUID, session: SessionDep) -> None:
    session.delete(get_or_404(session, Relationship, relationship_id))
    session.commit()
