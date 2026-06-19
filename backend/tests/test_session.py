from backend.session import GameSession, ParagraphRecord, SessionStore


def test_create_session():
    store = SessionStore()
    session = store.create(initial_prompt="test prompt")
    assert session.id is not None
    assert session.initial_prompt == "test prompt"
    assert session.history == []
    assert session.current_outcome_tier == 0


def test_create_session_default_initial_prompt():
    store = SessionStore()
    session = store.create()
    assert session.initial_prompt == ""


def test_get_existing_session():
    store = SessionStore()
    created = store.create()
    retrieved = store.get(created.id)
    assert retrieved is created


def test_get_nonexistent_session():
    store = SessionStore()
    assert store.get("nonexistent-id") is None


def test_append_paragraph():
    store = SessionStore()
    session = store.create()

    record = store.append_paragraph(
        session_id=session.id,
        text="test paragraph",
        speed_cpm=300.0,
        time_taken_ms=5000,
        accuracy=0.95,
        outcome_tier=2,
    )

    assert record is not None
    assert record.text == "test paragraph"
    assert record.speed_cpm == 300.0
    assert record.time_taken_ms == 5000
    assert record.accuracy == 0.95
    assert record.outcome_tier == 2
    assert len(session.history) == 1
    assert session.history[0] is record


def test_append_paragraph_multiple():
    store = SessionStore()
    session = store.create()

    r1 = store.append_paragraph(session.id, "first", 100.0, 2000, 0.9, 0)
    r2 = store.append_paragraph(session.id, "second", 400.0, 3000, 0.95, 3)

    assert r1 is not None
    assert r2 is not None
    assert len(session.history) == 2
    assert session.history[0] is r1
    assert session.history[1] is r2


def test_append_paragraph_nonexistent_session():
    store = SessionStore()
    record = store.append_paragraph(
        session_id="bad-id",
        text="test",
        speed_cpm=100.0,
        time_taken_ms=1000,
        accuracy=1.0,
        outcome_tier=0,
    )
    assert record is None


def test_sessions_are_independent():
    store = SessionStore()
    s1 = store.create("prompt 1")
    s2 = store.create("prompt 2")

    store.append_paragraph(s1.id, "s1 paragraph", 200.0, 4000, 0.9, 1)

    assert len(s1.history) == 1
    assert len(s2.history) == 0


def test_paragraph_record_immutable_fields():
    r = ParagraphRecord(text="hello", speed_cpm=150.0, time_taken_ms=3000, accuracy=0.88, outcome_tier=1)
    assert r.text == "hello"
    assert r.speed_cpm == 150.0
    assert r.time_taken_ms == 3000
    assert r.accuracy == 0.88
    assert r.outcome_tier == 1
