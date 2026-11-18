"""Stand-ins for the teammates' code. Delete once the real functions arrive."""


def research(name, entity_type, meeting_time_iso, days=30):
    # Matches CONTRACT 1 (list of dicts).
    return [
        {"title": f"{name} announces a new product update",
         "url": "https://example.com/news/1", "domain": "example.com",
         "published_date": "2026-11-10",
         "content": "Mock snippet about a product update.",
         "category": "product", "score": 0.91, "query": f"{name} product launch"},
        {"title": f"{name} confirms the same update",
         "url": "https://example.org/story/2", "domain": "example.org",
         "published_date": "2026-11-11",
         "content": "Mock snippet from a second site.",
         "category": "product", "score": 0.84, "query": f"{name} news"},
        {"title": f"Rumor: {name} may hire a new executive",
         "url": "https://example.net/post/3", "domain": "example.net",
         "published_date": None,
         "content": "Mock undated snippet.",
         "category": "leadership", "score": 0.55, "query": f"{name} hires"},
    ]


def synthesize(name, entity_type, meeting_type, results):
    # Returns the "writing" parts. The API adds meeting, sources and timing.
    return {
        "entity": {"name": name, "type": entity_type,
                   "description": f"Mock description of {name}.",
                   "disambiguation_note": None},
        "snapshot": f"{name} shipped a product update recently. (mock data)",
        "snapshot_source_ids": [1],
        "key_developments": [
            {"date": "2026-11-10", "category": "product",
             "text": "Product update announced (mock).",
             "confidence": "verified", "source_ids": [1, 2], "note": None},
            {"date": None, "category": "leadership",
             "text": "Possible executive hire (mock).",
             "confidence": "uncertain", "source_ids": [3],
             "note": "Undated, single weak source."},
        ],
        "talking_points": [{"text": "Ask about the new update.", "source_ids": [1]}],
        "risks": [{"text": "Hiring rumor is unconfirmed.", "source_ids": [3]}],
        "questions": ["How is the update changing your roadmap?"],
        "models_used": ["mock/none"],
        "provider_used": "mock",
        "fallback_used": False,
        "notes": "MOCK DATA: not real research.",
    }