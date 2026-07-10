import hashlib
from difflib import SequenceMatcher


def fingerprint_finding(data: dict) -> str:
    normalized = "|".join([
        str(data.get("file_path", "")).lower().strip(),
        str(data.get("start_line", 0)),
        str(data.get("category", "")).lower().strip(),
        str(data.get("rule_identifier", data.get("title", ""))).lower().strip(),
    ])
    return hashlib.sha256(normalized.encode()).hexdigest()


def deduplicate(findings: list[dict]) -> list[dict]:
    merged: list[dict] = []
    for finding in findings:
        finding = dict(finding)
        finding["fingerprint"] = finding.get("fingerprint") or fingerprint_finding(finding)
        match = next((x for x in merged if x["fingerprint"] == finding["fingerprint"]), None)
        if not match:
            # conservative near-duplicate merge: same file/category and highly similar title
            match = next((x for x in merged if x.get("file_path") == finding.get("file_path") and x.get("category") == finding.get("category") and SequenceMatcher(None, x.get("title", ""), finding.get("title", "")).ratio() > 0.88), None)
        if match:
            sources = set(match.get("sources", [match.get("source", "unknown")]))
            sources.update(finding.get("sources", [finding.get("source", "unknown")]))
            match["sources"] = sorted(s for s in sources if s)
            match["confidence"] = min(0.99, max(match.get("confidence", 0.7), finding.get("confidence", 0.7)) + 0.05)
            if len(finding.get("evidence", "")) > len(match.get("evidence", "")):
                match["evidence"] = finding["evidence"]
        else:
            finding["sources"] = finding.get("sources") or [finding.get("source", "unknown")]
            merged.append(finding)
    return merged
