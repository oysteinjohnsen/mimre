def search(client, q: str, **params) -> list[tuple[str, str | None]]:
    res = client.get("/api/persons", params={"q": q, **params})
    assert res.status_code == 200, res.text
    return [(p["first_name"], p["match"]) for p in res.json()]


def test_name_search_is_fuzzy_and_accent_insensitive(client, make_person):
    make_person("Ingrid", last_name="Haugen")
    make_person("Hugo", middle_name="Holvik", last_name="Johnsen")
    make_person("Bjørn", last_name="Ødegård")
    make_person("Kari", last_name="Nordmann", nickname="Kaja")

    assert search(client, "Ingird") == [("Ingrid", None)]  # typo
    assert search(client, "odegard") == [("Bjørn", None)]  # no accents
    assert search(client, "kaja") == [("Kari", None)]  # nickname
    assert search(client, "holvik") == [("Hugo", None)]  # middle name
    assert search(client, "hugo holvik johnsen") == [("Hugo", None)]  # full name
    assert search(client, "zzzz") == []


def test_search_finds_facts_and_notes_with_excerpt(client, make_person):
    kari = make_person("Kari")
    lars = make_person("Lars")
    client.post(f"/api/persons/{kari['id']}/facts", json={"label": "Hund", "value": "Bamse"})
    client.post(f"/api/persons/{lars['id']}/notes", json={"body": "Snakket om at de skal flytte til Bergen neste år."})

    assert search(client, "bamse") == [("Kari", "Hund: Bamse")]
    assert search(client, "bergen") == [("Lars", "Snakket om at de skal flytte til Bergen neste år.")]


def test_name_match_ranks_above_fact_match(client, make_person):
    bergen = make_person("Bergljot")
    kari = make_person("Kari")
    client.post(f"/api/persons/{kari['id']}/facts", json={"label": "Bor i", "value": "Bergen"})
    assert [name for name, _ in search(client, "berg")] == ["Bergljot", "Kari"]
    assert bergen  # created


def test_search_excludes_me_unless_asked(client):
    client.put("/api/me", json={"first_name": "Øystein"})
    assert search(client, "øystein") == []
    assert search(client, "øystein", include_me="true") == [("Øystein", None)]
