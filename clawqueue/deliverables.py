from __future__ import annotations

ARTIFACT_LABELS = {"cq:artifact", "cq:deliverable:artifact", "deliverable:artifact"}
CHANGE_LABELS = {"cq:change", "cq:deliverable:change", "deliverable:change"}
ARTIFACT_KEYWORDS = (
    "audit",
    "analysis",
    "brief",
    "decision",
    "design",
    "doc",
    "document",
    "markdown",
    "md artifact",
    "plan",
    "proposal",
    "recommendation",
    "report",
    "research",
    "review",
    "spec",
    "strategy",
)
CHANGE_KEYWORDS = (
    "add",
    "build",
    "change",
    "code",
    "content",
    "fix",
    "implement",
    "modify",
    "patch",
    "refactor",
    "remove",
    "rename",
    "source",
    "test",
    "update",
)


def resolve_deliverable_type(labels: list[str], title: str = "", body: str = "") -> str:
    label_set = {label.strip().lower() for label in labels if label.strip()}
    if label_set & ARTIFACT_LABELS:
        return "artifact"
    if label_set & CHANGE_LABELS:
        return "change"

    text = f"{title}\n{body}".lower()
    artifact_hit = any(keyword in text for keyword in ARTIFACT_KEYWORDS)
    change_hit = any(keyword in text for keyword in CHANGE_KEYWORDS)
    if artifact_hit and not change_hit:
        return "artifact"
    return "change"


def deliverable_label(deliverable_type: str) -> str:
    return "cq:artifact" if deliverable_type == "artifact" else "cq:change"
