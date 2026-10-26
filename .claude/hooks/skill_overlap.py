"""Overlap between skills in different subjects, for the app's All skills map.

Inferred, not recorded: two skills overlap when the records name one from the
other ("`oop` n6"), when they share one concept from CONCEPTS, or when they
share two other meaningful words. Until plan.md stores each node's concepts,
this guesses from words, and the map says the links are inferred.
Moved here from the Mac prototype (.scratch/vault-mac-design/prototype-holo).
"""
import re
from collections import Counter

STOP = set("""a an the and or of to in on for with from by as at is are be it its into that this than then what which
when where who how why your you can now say tell write writing written read name named names find give pick fresh
answer answers questions question mixed check final quiz review shape slot people class classes method methods new
each one two three four five use used using without within between after before more most less over under about
across their them they his her while also just only both first last other same different show shows explain explains
case cases example examples scenario simple every output does count counted rule order exam style practice problem
solve predict built call runs tracing trace classification classify compute work works part parts thing things kind
kinds give given type types value values make makes made know known state purpose condition""".split())

# One concept, many words. A shared concept is enough on its own.
CONCEPTS = {
    "inheritance": "inheritance inherit inherits inherited extends subclass subclasses superclass is-a",
    "polymorphism": "polymorphism dispatch override overrides overriding overridden",
    "equality": "equality equals ==",
    "encapsulation": "encapsulation private protected",
    "constructor": "constructor constructors super(...) super()",
    "static": "static",
    "pointer": "pointer pointers reference references",
    "tree": "tree trees subtree",
}
WORD_TO_CONCEPT = {w: c for c, words in CONCEPTS.items() for w in words.split()}
# These are programming ideas: "tree" in a Genji chapter title or "parent" in a
# folder path is not one, so a concept links only subjects in these themes.
CONCEPT_THEMES = {"code", "circuits"}
REF = re.compile(r"`([a-z0-9-]+)` (n\d+)")


def words(text):
    text = re.sub(r"`([^`]*)`", r" \1 ", text.lower())
    text = re.sub(r"\(s\d+(?:[-, ]+s\d+)*\)", "", text)
    text = re.sub(r"\b(child|parent) class", "subclass", text)
    found, concepts = set(), set()
    for raw in re.findall(r"[a-z][a-z+#()=.\-]{1,}", text):
        w = raw.strip(".-")
        if w in WORD_TO_CONCEPT:
            concepts.add(WORD_TO_CONCEPT[w])
            continue
        if len(w) < 4 or not w.isalpha() or w in STOP:
            continue
        w = re.sub(r"ies$", "y", w)
        w = re.sub(r"(?<=[a-z]{4})s$", "", w)
        if w in WORD_TO_CONCEPT:
            concepts.add(WORD_TO_CONCEPT[w])
        elif w not in STOP:
            found.add(w)
    return found, concepts


def overlaps(subjects, record_texts):
    """[(slug, node, slug, node, [shared words or concepts], explicit)] across subjects."""
    nodes = []
    for s in subjects:
        for n in s["nodes"]:
            w, c = words(n["name"] + " " + n.get("can_do", ""))
            nodes.append((s["slug"], n["id"], w, c if s.get("theme") in CONCEPT_THEMES else set()))
    spread = Counter(t for t in set().union(*[x[2] for x in nodes]) for slug in {x[0] for x in nodes if t in x[2]})
    out = {}
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            if a[0] == b[0]:
                continue
            shared_words = {t for t in a[2] & b[2] if spread[t] <= 5}
            shared = sorted(a[3] & b[3]) + (sorted(shared_words) if len(shared_words) >= 2 else [])
            if shared:
                out[(a[0], a[1], b[0], b[1])] = (shared, False)
    slugs = {s["slug"] for s in subjects}
    for slug, text in record_texts.items():  # the record names another subject's node
        for other, node in set(REF.findall(text)):
            if other in slugs and other != slug:
                for key in [k for k in out if {k[0], k[2]} == {slug, other} and node in (k[1], k[3])]:
                    out[key] = (out[key][0], True)
                if not any({k[0], k[2]} == {slug, other} and node in (k[1], k[3]) for k in out):
                    out[(slug, "", other, node)] = (["named in the record"], True)
    return [dict(a=k[0], an=k[1], b=k[2], bn=k[3], shared=v[0], explicit=v[1]) for k, v in out.items()]
