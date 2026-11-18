def relations(client, person_id: str) -> dict[str, tuple[str, bool]]:
    """{other first name: (relation, inferred)} as seen from person_id."""
    res = client.get(f"/api/persons/{person_id}/relationships")
    assert res.status_code == 200, res.text
    return {r["other"]["first_name"]: (r["relation"], r["inferred"]) for r in res.json()}


def link(client, person, other, relation):
    return client.post("/api/relationships", json={"person_id": person["id"], "other_id": other["id"], "relation": relation})


def test_parent_child_seen_from_both_sides(client, make_person):
    kari = make_person("Kari", gender="female")
    lars = make_person("Lars", gender="male")
    res = link(client, lars, kari, "parent")  # Kari is Lars's parent
    assert res.status_code == 201
    assert res.json()["relation"] == "parent"

    assert relations(client, lars["id"]) == {"Kari": ("parent", False)}
    assert relations(client, kari["id"]) == {"Lars": ("child", False)}


def test_symmetric_relationship_stored_once(client, make_person):
    a, b = make_person("A"), make_person("B")
    assert link(client, a, b, "friend").status_code == 201
    assert link(client, b, a, "friend").status_code == 409  # same pair, other direction
    assert relations(client, b["id"]) == {"A": ("friend", False)}
    # A different type between the same pair is fine.
    assert link(client, a, b, "colleague").status_code == 201


def test_invalid_relationships_rejected(client, make_person):
    a, b = make_person("A"), make_person("B")
    assert link(client, a, a, "friend").status_code == 422
    assert link(client, a, b, "boss").status_code == 422  # unknown relation
    assert link(client, a, b, "parent").status_code == 201
    assert link(client, a, b, "child").status_code == 409  # opposite of existing parent link


def test_inferred_family(client, make_person):
    granny = make_person("Granny")
    kari = make_person("Kari")
    emma, jonas = make_person("Emma"), make_person("Jonas")
    link(client, kari, granny, "parent")
    link(client, emma, kari, "parent")
    link(client, jonas, kari, "parent")

    assert relations(client, emma["id"]) == {
        "Kari": ("parent", False),
        "Jonas": ("sibling", True),
        "Granny": ("grandparent", True),
    }
    assert relations(client, granny["id"]) == {
        "Kari": ("child", False),
        "Emma": ("grandchild", True),
        "Jonas": ("grandchild", True),
    }

    # Inferred relationships say who they go through.
    vias = {r["other"]["first_name"]: (r["via"] or {}).get("first_name") for r in client.get(f"/api/persons/{emma['id']}/relationships").json()}
    assert vias == {"Kari": None, "Jonas": "Kari", "Granny": "Kari"}

    # An explicit sibling link replaces the inferred one rather than duplicating it.
    link(client, emma, jonas, "sibling")
    assert relations(client, emma["id"])["Jonas"] == ("sibling", False)


def test_delete_relationship_and_cascade(client, make_person):
    a, b, c = make_person("A"), make_person("B"), make_person("C")
    rel = link(client, a, b, "friend").json()
    link(client, a, c, "friend")

    assert client.delete(f"/api/relationships/{rel['id']}").status_code == 204
    assert relations(client, a["id"]) == {"C": ("friend", False)}

    assert client.delete(f"/api/persons/{c['id']}").status_code == 204
    assert relations(client, a["id"]) == {}


def test_aunts_uncles_nieces_nephews_cousins_inferred(client, make_person):
    granny = make_person("Granny")
    mum, uncle = make_person("Mum"), make_person("Uncle")
    me, sis = make_person("Me"), make_person("Sis")
    cousin, niece = make_person("Cousin"), make_person("Niece")
    for child in (mum, uncle):
        link(client, child, granny, "parent")
    for child in (me, sis):
        link(client, child, mum, "parent")
    link(client, cousin, uncle, "parent")
    link(client, niece, sis, "parent")

    rels = client.get(f"/api/persons/{me['id']}/relationships").json()
    got = {r["other"]["first_name"]: (r["relation"], (r["via"] or {}).get("first_name")) for r in rels}
    assert got == {
        "Mum": ("parent", None),
        "Sis": ("sibling", "Mum"),
        "Granny": ("grandparent", "Mum"),
        "Uncle": ("aunt_uncle", "Mum"),
        "Niece": ("niece_nephew", "Sis"),
        "Cousin": ("cousin", "Uncle"),
    }
    # And the other way round.
    assert relations(client, uncle["id"])["Me"] == ("niece_nephew", True)
    assert relations(client, cousin["id"])["Me"] == ("cousin", True)


def test_extended_family_can_be_entered_directly(client, make_person):
    me, uncle, cousin, granny = make_person("Me"), make_person("Uncle"), make_person("Cousin"), make_person("Granny")
    assert link(client, me, uncle, "aunt_uncle").status_code == 201
    assert link(client, me, granny, "grandparent").status_code == 201
    assert link(client, uncle, me, "aunt_uncle").status_code == 409  # opposite direction already exists
    link(client, cousin, uncle, "parent")

    assert relations(client, uncle["id"])["Me"] == ("niece_nephew", False)
    assert relations(client, granny["id"])["Me"] == ("grandchild", False)
    # Children of a directly entered uncle are inferred as cousins.
    assert relations(client, me["id"])["Cousin"] == ("cousin", True)


def test_closer_relation_wins_over_inferred(client, make_person):
    mum, me, sis = make_person("Mum"), make_person("Me"), make_person("Sis")
    link(client, me, mum, "parent")
    link(client, sis, mum, "parent")
    link(client, me, sis, "friend")  # a sister who is also a friend: both shown
    assert {(r["relation"]) for r in client.get(f"/api/persons/{me['id']}/relationships").json() if r["other"]["first_name"] == "Sis"} == {
        "friend",
        "sibling",
    }


def test_in_laws_inferred_through_spouse(client, make_person):
    me, wife = make_person("Me"), make_person("Wife")
    father_in_law, wifes_brother = make_person("FatherInLaw"), make_person("WifesBrother")
    my_sister, her_husband = make_person("MySister"), make_person("HerHusband")
    mum = make_person("Mum")
    link(client, me, wife, "spouse")
    for child in (wife, wifes_brother):
        link(client, child, father_in_law, "parent")
    for child in (me, my_sister):
        link(client, child, mum, "parent")
    link(client, my_sister, her_husband, "spouse")

    rels = client.get(f"/api/persons/{me['id']}/relationships").json()
    got = {r["other"]["first_name"]: (r["relation"], (r["via"] or {}).get("first_name")) for r in rels}
    assert got["FatherInLaw"] == ("parent_in_law", "Wife")
    assert got["WifesBrother"] == ("sibling_in_law", "Wife")
    assert got["HerHusband"] == ("sibling_in_law", "MySister")
    # Reverse: I'm my father-in-law's child-in-law, and Mum sees her daughter's husband as child-in-law.
    assert relations(client, father_in_law["id"])["Me"] == ("child_in_law", True)
    assert relations(client, mum["id"])["HerHusband"] == ("child_in_law", True)


def test_only_marriage_creates_in_laws(client, make_person):
    me, gf, her_dad = make_person("Me"), make_person("Girlfriend"), make_person("HerDad")
    link(client, gf, her_dad, "parent")
    for relation in ("partner", "cohabitant"):  # kjæreste, samboer
        rel = link(client, me, gf, relation).json()
        assert "HerDad" not in relations(client, me["id"])
        client.delete(f"/api/relationships/{rel['id']}")
    link(client, me, gf, "spouse")
    assert relations(client, me["id"])["HerDad"] == ("parent_in_law", True)


def test_in_laws_can_be_entered_directly(client, make_person):
    me, mil, bil = make_person("Me"), make_person("MotherInLaw"), make_person("BrotherInLaw")
    assert link(client, me, mil, "parent_in_law").status_code == 201
    assert link(client, me, bil, "sibling_in_law").status_code == 201
    assert relations(client, mil["id"])["Me"] == ("child_in_law", False)
    assert relations(client, bil["id"])["Me"] == ("sibling_in_law", False)
