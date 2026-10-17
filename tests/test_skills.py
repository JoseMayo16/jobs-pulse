import pytest

from jobs_pulse.skills import SKILLS, clean_text, extract


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("We use Python and Django", {"Python", "Django"}),
        ("JavaScript and TypeScript", {"JavaScript", "TypeScript"}),
        ("Java 21, Spring Boot", {"Java", "Spring"}),
        ("C# / .NET and C++", {"C#", "C++"}),
        ("React Native for mobile", {"React Native"}),
        ("React and React Native", {"React", "React Native"}),
        ("Vue.js 3 with Nuxt", {"Vue"}),
        ("Postgres, Redis, k8s", {"PostgreSQL", "Redis", "Kubernetes"}),
        ("Experience with LLMs and generative AI", {"LLMs"}),
    ],
)
def test_extract_finds_canonical_names(text, expected):
    assert set(extract(text)) == expected


@pytest.mark.parametrize(
    ("text", "has_go"),
    [
        ("Stack: Go, Postgres", True),
        ("Python / Go / Rust", True),
        ("We love golang", True),
        ("Go to our careers page", False),
        ("Ready to go live?", False),
        ("Let's Go!", False),
    ],
)
def test_go_only_counts_in_a_technology_list(text, has_go):
    assert ("Go" in extract(text)) is has_go


def test_java_is_not_javascript():
    assert extract("JavaScript only") == ["JavaScript"]


def test_html_is_stripped_and_unescaped():
    assert clean_text("<p>Rust &#x2F; Python</p>").strip() == "Rust / Python"
    assert set(extract("<li>Rust&#x2F;Python</li>")) == {"Rust", "Python"}


def test_result_follows_dictionary_order_without_duplicates():
    found = extract("python Python PYTHON and docker")
    assert found == ["Python", "Docker"]


def test_skill_names_are_unique():
    names = [s.name for s in SKILLS]
    assert len(names) == len(set(names))
