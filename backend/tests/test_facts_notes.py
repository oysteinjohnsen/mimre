def test_fact_crud_and_validation(client, make_person):
    kari = make_person("Kari")
    url = f"/api/persons/{kari['id']}/facts"

    res = client.post(url, json={"label": "Hund", "value": "Bamse"})
    assert res.status_code == 201
    fact = res.json()
    assert fact["kind"] == "text"

    assert client.post(url, json={"kind": "date", "label": "Bryllupsdag", "value": "14.03.2015"}).status_code == 422
    assert client.post(url, json={"kind": "date", "label": "Bryllupsdag", "value": "2015-03-14"}).status_code == 201
    assert client.post(url, json={"kind": "email", "label": "E-post", "value": "nope"}).status_code == 422
    assert client.post(url, json={"label": "  ", "value": "x"}).status_code == 422

    res = client.patch(f"/api/facts/{fact['id']}", json={"value": "Bamse (golden retriever)"})
    assert res.json()["value"] == "Bamse (golden retriever)"
    # Changing kind validates the existing value.
    assert client.patch(f"/api/facts/{fact['id']}", json={"kind": "date"}).status_code == 422

    assert [f["label"] for f in client.get(url).json()] == ["Hund", "Bryllupsdag"]
    assert client.delete(f"/api/facts/{fact['id']}").status_code == 204
    assert [f["label"] for f in client.get(url).json()] == ["Bryllupsdag"]


def test_fact_labels_most_used_first(client, make_person):
    a, b = make_person("A"), make_person("B")
    for p in (a, b):
        client.post(f"/api/persons/{p['id']}/facts", json={"kind": "phone", "label": "Telefon", "value": "123"})
    client.post(f"/api/persons/{a['id']}/facts", json={"label": "Hund", "value": "Bamse"})
    labels = client.get("/api/facts/labels").json()
    assert labels == [{"label": "Telefon", "kind": "phone"}, {"label": "Hund", "kind": "text"}]


def test_notes_ordered_newest_first(client, make_person):
    kari = make_person("Kari")
    url = f"/api/persons/{kari['id']}/notes"
    client.post(url, json={"body": "Old", "happened_on": "2024-05-01"})
    today = client.post(url, json={"body": "Today"}).json()
    client.post(url, json={"body": "Middle", "happened_on": "2025-01-01"})

    assert [n["body"] for n in client.get(url).json()] == ["Today", "Middle", "Old"]
    assert client.post(url, json={"body": "   "}).status_code == 422

    res = client.patch(f"/api/notes/{today['id']}", json={"body": "Today, edited"})
    assert res.json()["body"] == "Today, edited"
    assert client.delete(f"/api/notes/{today['id']}").status_code == 204
    assert len(client.get(url).json()) == 2


def test_person_delete_removes_facts_and_notes(client, make_person):
    kari = make_person("Kari")
    client.post(f"/api/persons/{kari['id']}/facts", json={"label": "Hund", "value": "Bamse"})
    client.post(f"/api/persons/{kari['id']}/notes", json={"body": "Hei"})
    assert client.delete(f"/api/persons/{kari['id']}").status_code == 204
    assert client.get("/api/facts/labels").json() == []
