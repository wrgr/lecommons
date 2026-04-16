"""Second supplement pass: expert conversations with embeds + summaries,
current papers we missed, and adjacent-but-not-on-ICICLE-resources material.

This adds a new content pattern: every expert-conversation item carries
`summary` (2-4 sentence abstract in our voice), `embed` (YouTube /embed/ URL),
and `tags: ["expert-conversation"]`. The Events page surfaces them as a
"Conversations with experts" sub-group, and the Card component lazy-loads
the embed behind a click so mobile data is preserved.

    source venv/bin/activate
    python3 site/scripts/import_icicle_web_supplement_v2.py
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "site" / "src" / "content"

DATASET = "IEEE ICICLE resources page (web harvest) + curated extensions"

ITEMS: list[tuple[str, dict]] = [
    # ══════════════════════════════════════════════════════════════════════
    # Expert conversations — videos + podcasts with summaries and embeds.
    # ══════════════════════════════════════════════════════════════════════
    ("events", {
        "title": "Learning Engineering: What We Know, What We Can Do — Bror Saxberg keynote",
        "format": "keynote",
        "venue": "MIT Festival of Learning",
        "authors": "Bror Saxberg",
        "year": 2023,
        "url": "https://www.youtube.com/watch?v=VSrsOzzjV8I",
        "embed": "https://www.youtube.com/embed/VSrsOzzjV8I",
        "cluster": "Expert conversations",
        "topics": ["T00", "T01"],
        "tags": ["expert-conversation", "saxberg", "icicle"],
        "featured": True,
        "summary": (
            "Saxberg's clearest public statement of the learning-engineer role: why "
            "instructional design's compliance model falls short at scale, what evidence-"
            "based iteration actually looks like in industry, and where the next generation "
            "of LEs needs to come from. The canonical 'what is LE' talk for newcomers."
        ),
    }),
    ("events", {
        "title": "Leveraging AI and Learning Engineering in Large-Scale Learning Sciences — Danielle McNamara",
        "format": "keynote",
        "venue": "Empowering Learners for the Age of AI Conference",
        "authors": "Danielle McNamara",
        "year": 2022,
        "url": "https://www.youtube.com/watch?v=Yn3AIuKJ1RY",
        "embed": "https://www.youtube.com/embed/Yn3AIuKJ1RY",
        "cluster": "Expert conversations",
        "topics": ["T07", "T04"],
        "tags": ["expert-conversation", "ai", "icicle"],
        "summary": (
            "McNamara's case for AI-enabled learning engineering at scale — grounded in her "
            "two decades of NLP-and-learning-sciences work. Argues that the most promising "
            "AI applications in LE aren't content generation but formative measurement and "
            "adaptive scaffolding. Technical but accessible."
        ),
    }),
    ("events", {
        "title": "Learning Engineering in the Age of AI — Kumar Garg",
        "format": "keynote",
        "venue": "Empowering Learners for the Age of AI Conference",
        "authors": "Kumar Garg",
        "year": 2022,
        "url": "https://www.youtube.com/watch?v=HCDis6ELscA",
        "embed": "https://www.youtube.com/embed/HCDis6ELscA",
        "cluster": "Expert conversations",
        "topics": ["T07", "T15"],
        "tags": ["expert-conversation", "ai", "icicle"],
        "summary": (
            "Garg (Walton-funded LE efforts; formerly OSTP) frames AI-and-LE as an evidence "
            "and infrastructure problem, not a pedagogical one. The pitch: the field needs "
            "many more studies, faster, to match AI's pace — and LE is the discipline set up "
            "to do that."
        ),
    }),
    ("events", {
        "title": "Learning Engineering: A path to empowering learners in and for the Age of AI — Panel",
        "format": "video",
        "venue": "Empowering Learners for the Age of AI Conference",
        "year": 2022,
        "url": "https://www.youtube.com/watch?v=H-MbNTt2NRc",
        "embed": "https://www.youtube.com/embed/H-MbNTt2NRc",
        "cluster": "Expert conversations",
        "topics": ["T07", "T00"],
        "tags": ["expert-conversation", "ai", "icicle"],
        "summary": (
            "Panel response to the McNamara and Garg keynotes above. Worth watching as a "
            "trio — the panel is where the rough edges of AI-in-LE show up (evaluation, "
            "equity, disciplinary identity)."
        ),
    }),
    ("events", {
        "title": "Advancing Workforce Learning through Learning Engineering",
        "format": "webinar",
        "venue": "IEEE ICICLE — Invitation to LE Webinar Series",
        "year": 2023,
        "url": "https://www.youtube.com/watch?v=CIMkm7YqJnE",
        "embed": "https://www.youtube.com/embed/CIMkm7YqJnE",
        "cluster": "Invitation to LE",
        "topics": ["T10", "T16"],
        "tags": ["expert-conversation", "icicle"],
        "summary": (
            "Episode from ICICLE's Invitation to LE series, focused on workforce/corporate "
            "L&D. Useful if you're explaining the LE value proposition to a CLO or head of "
            "talent development."
        ),
    }),
    ("events", {
        "title": "Applying Learning Engineering in Mission-Critical Environments",
        "format": "webinar",
        "venue": "IEEE ICICLE — Invitation to LE Webinar Series",
        "year": 2023,
        "url": "https://www.youtube.com/watch?v=k-miyqOhHsg",
        "embed": "https://www.youtube.com/embed/k-miyqOhHsg",
        "cluster": "Invitation to LE",
        "topics": ["T13", "T10"],
        "tags": ["expert-conversation", "icicle"],
        "summary": (
            "High-consequence domains — aviation, defense, medicine — have different "
            "error tolerances than classroom LE. This episode walks through what changes "
            "when 'not learning' has real-world safety consequences."
        ),
    }),
    ("events", {
        "title": "Discover the World of Learning Engineering in Post-Secondary Contexts",
        "format": "webinar",
        "venue": "IEEE ICICLE — Invitation to LE Webinar Series",
        "year": 2023,
        "url": "https://youtu.be/GlHn8SoyXwM",
        "embed": "https://www.youtube.com/embed/GlHn8SoyXwM",
        "cluster": "Invitation to LE",
        "topics": ["T11", "T06"],
        "tags": ["expert-conversation", "icicle"],
        "summary": (
            "How LE actually lives inside universities — through units like CMU's OLI, ASU's "
            "LEI, and the UPenn Center for Learning Analytics. Good companion piece to the "
            "programs on our Community page."
        ),
    }),
    ("events", {
        "title": "Unlock the Learning Engineer in You — pK-12 Context",
        "format": "webinar",
        "venue": "IEEE ICICLE — Invitation to LE Webinar Series",
        "year": 2024,
        "url": "https://www.youtube.com/watch?v=jXbvdqtARw0",
        "embed": "https://www.youtube.com/embed/jXbvdqtARw0",
        "cluster": "Invitation to LE",
        "topics": ["T12", "T01"],
        "tags": ["expert-conversation", "icicle"],
        "summary": (
            "ICICLE's pK-12 MIG hosts this episode, aimed at K-12 teachers and "
            "instructional designers considering LE practices. Lightweight entry point "
            "to the field for school-based practitioners."
        ),
    }),
    ("events", {
        "title": "Bringing Learning Engineering Into Online Education",
        "format": "webinar",
        "venue": "Maryland Online",
        "authors": "Karen Rege, Jodi Lis",
        "year": 2023,
        "url": "https://www.youtube.com/watch?v=zlEo9mEHKuw",
        "embed": "https://www.youtube.com/embed/zlEo9mEHKuw",
        "cluster": "Expert conversations",
        "topics": ["T11", "T03"],
        "tags": ["expert-conversation"],
        "summary": (
            "A two-practitioner conversation — Rege and Lis — walking concretely through what "
            "it takes to bring LE into an existing online-education operation. Practical, "
            "institutional, grounded."
        ),
    }),
    ("events", {
        "title": "Crazy Idea: What If We Use Engineering to Develop and Deliver Engineering Education?",
        "format": "webinar",
        "venue": "IFEES / GEDC / IUCEE",
        "authors": "Abul Azad, Jim Goodell",
        "year": 2025,
        "url": "https://sagroups.ieee.org/icicle/invitation-to-learning-engineering-webinar-series/",
        "cluster": "Expert conversations",
        "topics": ["T10", "T16"],
        "tags": ["expert-conversation", "icicle"],
        "summary": (
            "Goodell in conversation with Azad (IFEES) on the provocative inverse of our "
            "normal framing: if LE is how we rigorously teach people to engineer, why don't "
            "we use LE to teach engineering itself? A 2025 entry worth watching for the "
            "international-engineering-education perspective."
        ),
    }),
    ("events", {
        "title": "IEEE Learning Engineering Podcast",
        "format": "series",
        "venue": "IEEE ICICLE",
        "url": "https://open.spotify.com/show/6I0YYNGO7SqrqDz1pLAAbj",
        "cluster": "Expert conversations",
        "topics": ["T00"],
        "tags": ["expert-conversation", "icicle"],
        "summary": (
            "ICICLE's official podcast series — interviews with working learning engineers "
            "across sectors. The first episode (\"What is Learning Engineering?\") is the most "
            "linked-to; subsequent episodes get into specific practitioner stories."
        ),
    }),
    ("events", {
        "title": "Silver Lining for Learning — The Art and Science of Learning Engineering",
        "format": "podcast",
        "venue": "Silver Lining for Learning",
        "authors": "Danielle McNamara, Scotty Craig, Rod Roscoe",
        "year": 2023,
        "url": "https://silverliningforlearning.org/episode-162-the-art-science-of-learning-engineering/",
        "cluster": "Expert conversations",
        "topics": ["T00", "T01"],
        "tags": ["expert-conversation"],
        "summary": (
            "Roscoe, Craig, and McNamara on what makes LE distinct from adjacent fields — "
            "and where art/intuition still lives inside what's meant to be an engineering "
            "discipline. A more philosophical companion to the ICICLE 2024 materials."
        ),
    }),
    ("events", {
        "title": "Silver Lining for Learning — Applying Human-Centered Engineering Methods to Learning",
        "format": "podcast",
        "venue": "Silver Lining for Learning",
        "authors": "Janet Kolodner, Jim Goodell, Sae Schatz",
        "year": 2023,
        "url": "https://silverliningforlearning.org/episode-149-applying-human-centered-engineering-methods-to-learning/",
        "cluster": "Expert conversations",
        "topics": ["T03", "T02"],
        "tags": ["expert-conversation", "icicle"],
        "summary": (
            "Kolodner, Goodell, and Schatz on where human-centered design methods actually "
            "fit inside the LE process — which ones matter, which get applied lazily, and "
            "where the practitioner discipline still has gaps."
        ),
    }),
    ("events", {
        "title": "AECT Learner Engagement Activated — Jim Goodell episode",
        "format": "podcast",
        "venue": "AECT Learner Engagement Division",
        "authors": "Jim Goodell (guest), Anne Fensie (host)",
        "year": 2022,
        "url": "https://learnerengagement.podbean.com/e/episode-8-jim-goodell/",
        "cluster": "Expert conversations",
        "topics": ["T00"],
        "tags": ["expert-conversation"],
        "summary": (
            "Fensie interviews Goodell in a long-form format — origin story, ICICLE's founding, "
            "and the case for LE as an engineering discipline. If you want biographical "
            "context on one of the field's anchors, start here."
        ),
    }),
    ("events", {
        "title": "All Rise the Learning Engineers",
        "format": "podcast",
        "venue": "The EdTech Podcast",
        "authors": "Aaron Barr, Robby Robson",
        "year": 2018,
        "url": "https://theedtechpodcast.com/120-all-rise-the-learning-engineer/",
        "cluster": "Expert conversations",
        "topics": ["T00"],
        "tags": ["expert-conversation"],
        "summary": (
            "An early (2018) public conversation about the LE role. Useful as a time-capsule: "
            "what the field thought it was before ICICLE consolidated. Barr and Robson are "
            "both early movers; the episode holds up."
        ),
    }),

    # ══════════════════════════════════════════════════════════════════════
    # Current papers we missed in the last pass (2020+)
    # ══════════════════════════════════════════════════════════════════════
    ("reading-list", {
        "title": "Why Did We Do That? A Systematic Approach to Tracking Decisions in the Design and Iteration of Learning Experiences",
        "format": "article",
        "venue": "Journal of Applied Instructional Design",
        "authors": "Lauren Totino, Aaron Kessler",
        "year": 2023,
        "url": "https://edtechbooks.org/jaid_13_2/why_did_we_do_that_a_systematic_approach_to_tracking_decisions_in_the_design_and_iteration_of_learning_experiences",
        "cluster": "ICICLE resources",
        "topics": ["T03", "T15"],
        "tags": ["icicle"],
        "summary": (
            "Totino and Kessler's practical protocol for decision tracking across LE projects. "
            "Pairs well with our Field Note on Five Whys — this paper operationalizes the "
            "evidence-decision-tracker discipline ICICLE publishes."
        ),
    }),
    ("reading-list", {
        "title": "Designing a Student Progress Panel for Formative Practice: A Learning Engineering Process",
        "format": "paper",
        "venue": "ICLS 2023",
        "authors": "Rachel Van Campenhout, Michelle Selinger, Bill Jerome",
        "year": 2023,
        "url": "https://repository.isls.org/bitstream/1/10225/1/ICLS2023_2193-2196.pdf",
        "cluster": "ICICLE resources",
        "topics": ["T03", "T04", "T06"],
        "tags": ["icicle"],
        "summary": (
            "A compact case study of the LE process applied to a real adaptive-learning "
            "product (Acrobatiq). Worth reading back-to-back with Fensie's ICLS piece on "
            "Data-Informed Course Improvement."
        ),
    }),
    ("reading-list", {
        "title": "Data-Informed Course Improvement: The Application of Learning Engineering in the Classroom",
        "format": "paper",
        "venue": "ICLS 2023",
        "authors": "Anne Fensie",
        "year": 2023,
        "url": "https://repository.isls.org/bitstream/1/10244/1/ICLS2023_2267-2270.pdf",
        "cluster": "ICICLE resources",
        "topics": ["T04", "T03"],
        "tags": ["icicle"],
        "summary": (
            "Higher-ed classroom case study. Fensie walks through a specific course "
            "intervention, what data moved, and what didn't — an honest practitioner paper "
            "at a major learning sciences venue."
        ),
    }),
    ("reading-list", {
        "title": "Designing for Transfer: Developing a Skill-Based Simulation Using Learning Engineering Design Frameworks",
        "format": "paper",
        "venue": "MODSIM 2025",
        "authors": "Jessica M. Johnson, Austin Connolly, John Shull, Hector Garcia",
        "year": 2025,
        "url": "https://www.modsimworld.org/papers/2025/MODSIM_2025_paper_25.pdf",
        "cluster": "ICICLE resources",
        "topics": ["T08", "T10"],
        "tags": ["icicle"],
        "summary": (
            "MODSIM paper on building a skills simulator with transfer as the explicit "
            "design target. Good example of LE-in-defense-adjacent training contexts where "
            "simulators are the primary medium."
        ),
    }),
    ("reading-list", {
        "title": "Learning Engineering Enlightenment: Think Like an Engineer",
        "format": "article",
        "venue": "New Learning Frontier",
        "authors": "Ellen Wagner",
        "year": 2024,
        "url": "https://newlearningfrontier.com/learning-engineering-enlightenment-think-like-an-engineer/",
        "cluster": "ICICLE resources",
        "topics": ["T00"],
        "tags": ["icicle"],
        "summary": (
            "Wagner's 2024 follow-on to her long thread of LE-vs-ID articles. The sharpest "
            "version of her argument that the shift isn't tools, it's disposition: LEs "
            "reason like engineers about uncertainty and evidence."
        ),
    }),
    ("reading-list", {
        "title": "Teaming up to Improve Medical/Healthcare Education: Instructional Design & Learning Engineering",
        "format": "article",
        "venue": "Journal of Applied Instructional Design",
        "authors": "Dina Kurzweil, Karen E. Marcellas",
        "year": 2020,
        "url": "https://253f0a53-bb62-46af-b495-b4548f4d5d90.filesusr.com/ugd/c9b0ce_5251ffb6173c4c9a968a76832aa36778.pdf",
        "cluster": "ICICLE resources",
        "topics": ["T13", "T03"],
        "tags": ["icicle"],
        "summary": (
            "Kurzweil and Marcellas on how ID and LE team up inside a clinical-training "
            "context. A canonical healthcare-LE reference, cited widely in the high-"
            "consequence-domain thread of the field."
        ),
    }),
    ("reading-list", {
        "title": "Why We Need Learning Engineers",
        "format": "article",
        "venue": "Chronicle of Higher Education",
        "authors": "Bror Saxberg",
        "year": 2015,
        "url": "https://www.chronicle.com/article/Why-We-Need-Learning-Engineers/229391",
        "cluster": "ICICLE resources",
        "topics": ["T00"],
        "tags": ["icicle"],
        "featured": True,
        "summary": (
            "Saxberg's original 2015 Chronicle piece — the first mainstream op-ed "
            "asking for learning engineers as a distinct profession. Still the "
            "most-cited newcomer reference; worth reading before watching his later keynotes."
        ),
    }),

    # ══════════════════════════════════════════════════════════════════════
    # Adjacent-but-relevant material NOT on the ICICLE resources page.
    # ══════════════════════════════════════════════════════════════════════
    ("tools", {
        "title": "xAPI — Experience API specification",
        "format": "platform",
        "venue": "IEEE LTSC / ADL",
        "url": "https://xapi.com/",
        "cluster": "Standards",
        "topics": ["T11", "T16"],
        "tags": ["adjacent", "standards"],
        "summary": (
            "The de facto standard for learning-event instrumentation. Not explicitly on "
            "ICICLE's resource page, but every LE platform conversation eventually comes "
            "back to xAPI. Runs through the IEEE LTSC where much of ICICLE's standards "
            "work also happens."
        ),
    }),
    ("tools", {
        "title": "Caliper Analytics",
        "format": "platform",
        "venue": "1EdTech (formerly IMS Global)",
        "url": "https://www.1edtech.org/standards/caliper",
        "cluster": "Standards",
        "topics": ["T04", "T11", "T16"],
        "tags": ["adjacent", "standards"],
        "summary": (
            "Caliper is xAPI's closest sibling — a learning-analytics interop standard "
            "from 1EdTech. If you're picking an LMS analytics stack, you'll encounter "
            "both. Worth having in this registry even though ICICLE doesn't list it."
        ),
    }),
    ("community", {
        "title": "Advanced Distributed Learning Initiative (ADL)",
        "format": "org",
        "venue": "U.S. Department of Defense",
        "url": "https://adlnet.gov/",
        "cluster": "U.S. Air Force",
        "topics": ["T10", "T16"],
        "tags": ["adjacent"],
        "summary": (
            "DoD-funded learning-technology R&D center. Birthplace of SCORM and xAPI. "
            "Not officially on ICICLE's pages, but the overlap between ADL and the "
            "Government/Military MIG is substantial and they co-sponsor iFEST each year."
        ),
    }),
    ("community", {
        "title": "The Learning Agency",
        "format": "org",
        "venue": "Learning Agency / Learning Agency Lab",
        "url": "https://www.the-learning-agency.com/",
        "cluster": "IEEE ICICLE",
        "topics": ["T15", "T16"],
        "tags": ["icicle"],
        "summary": (
            "Non-profit research and policy shop led by Ulrich Boser, the co-author of "
            "'High-Leverage Opportunities for LE.' Runs several open-data competitions and "
            "the Learning Engineering Google Group that ICICLE references."
        ),
    }),
    ("tools", {
        "title": "Teaching Online Preparation Toolkit (TOPkit)",
        "format": "toolkit",
        "venue": "University of Central Florida",
        "url": "https://topkit.org/",
        "cluster": "ICICLE resources",
        "topics": ["T12", "T11"],
        "tags": ["icicle"],
        "summary": (
            "UCF's open toolkit for preparing faculty to teach online — widely referenced "
            "as a pragmatic, institutionally-scaled resource. ICICLE points to it from their "
            "resources page; it's one of the few real-world implementations of LE-style "
            "staff development at scale."
        ),
    }),
]


def slugify(text: str) -> str:
    """Convert a title to a filesystem-safe slug, clipped to 70 chars."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:70] or "untitled"


def yaml_escape(s: str) -> str:
    """Quote a string value for YAML frontmatter output."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_mdx(collection: str, data: dict) -> bool:
    """Write a single MDX file unless a file with the same slug already exists."""
    out_dir = CONTENT / collection
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(data["title"])
    path = out_dir / f"{slug}.mdx"
    if path.exists():
        return False

    lines: list[str] = ["---"]

    def put(key: str, value):
        if value is None or value == "" or value == []:
            return
        if isinstance(value, bool):
            if value:
                lines.append(f"{key}: true")
            return
        if isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
            return
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {yaml_escape(str(item))}")
            return
        lines.append(f"{key}: {yaml_escape(str(value))}")

    put("title", data["title"])
    put("format", data["format"])
    put("venue", data.get("venue"))
    put("authors", data.get("authors"))
    if data.get("year"):
        put("year", int(data["year"]))
    put("url", data.get("url"))
    put("embed", data.get("embed"))
    put("cluster", data.get("cluster"))
    put("topics", data.get("topics", []))
    put("tags", data.get("tags", []))
    put("featured", data.get("featured", False))
    put("summary", data.get("summary"))

    lines.append("provenance:")
    lines.append(f"  dataset: {yaml_escape(DATASET)}")

    lines.append("---")
    lines.append("")
    lines.append("")  # empty body; summary does the work

    path.write_text("\n".join(lines), encoding="utf-8")
    return True


def main() -> None:
    """Emit every item in ITEMS into its collection, skipping duplicates."""
    counts: dict[str, int] = {}
    for collection, data in ITEMS:
        if write_mdx(collection, data):
            counts[collection] = counts.get(collection, 0) + 1

    print("Wrote MDX from ICICLE web supplement v2:")
    for k in ("practice", "tools", "reading-list", "events", "community"):
        print(f"  {k:13s} +{counts.get(k, 0)}")
    print(f"  total         {sum(counts.values())}")


if __name__ == "__main__":
    main()
