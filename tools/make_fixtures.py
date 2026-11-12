"""Generate schema fixtures (valid + targeted invalid). Run once; output is committed."""
import copy, json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "schemas"
NOW = "2026-10-28T10:00:00+01:00"

def phase(status="not_started", **kw):
    d = {"status": status}; d.update(kw); return d

state = {
  "protocol": "sancho/1.0",
  "project": {"name": "Demo", "level": "L2", "platforms": ["web", "android"]},
  "created_at": NOW, "updated_at": NOW, "current_phase": "specify",
  "phases": {
    "discover": phase("approved", lead="analyst-pm", gate={"checklist": [{"id": "DIS-1", "result": "pass"}], "coherence": "n/a", "approved_at": NOW}),
    "specify": phase("in_progress", lead="analyst-pm", started_at=NOW),
    "plan": phase(), "tasks": phase(), "implement": phase(), "verify": phase(),
    "release": phase(), "evolve": phase("skipped", skip_reason="user asked to stop after first release", adr="docs/adr/0003-skip-evolve.md"),
  },
  "settings": {"language": "it", "complexity_threshold": 7, "tdd": True},
}
s_bad1 = copy.deepcopy(state); s_bad1["phases"]["evolve"].pop("adr")          # skip without ADR
s_bad2 = copy.deepcopy(state); s_bad2["phases"]["discover"]["gate"].pop("approved_at")  # approved without approval time
s_bad3 = copy.deepcopy(state); s_bad3["project"]["platforms"] = ["web", "smartwatch"]

ev_cmd = {"type": "test", "command": "npm test -- auth", "exit_code": 0}
backlog = {
  "protocol": "sancho/1.0",
  "requirements": [{"id": "R-001", "kind": "functional", "statement": "Users sign in with email and password", "priority": "must", "source": "user"}],
  "stories": [{
    "id": "S-001", "title": "Sign in", "as_a": "registered user", "i_want": "to sign in", "so_that": "I see my data",
    "requirements": ["R-001"], "priority": "must",
    "context": "Auth uses the session cookie decided in ADR-0002; follow standards/api.md.",
    "acceptance_criteria": [
      {"id": "AC-001.1", "description": "Valid credentials open the dashboard", "verification": {"method": "automated_test", "ref": "tests/auth.test.ts"}, "status": "met", "evidence": [ev_cmd]},
      {"id": "AC-001.2", "description": "Wrong password shows a generic error", "verification": {"method": "uat", "ref": "UAT-001"}, "status": "not_verified"}]}],
  "tasks": [
    {"id": "T-001", "story": "S-001", "title": "Login endpoint", "owner": "developer", "status": "completed", "depends_on": [], "complexity": {"score": 4}, "evidence": [ev_cmd]},
    {"id": "T-002", "story": "S-001", "title": "Login screen", "owner": "developer", "status": "pending", "depends_on": ["T-001"], "complexity": {"score": 3}}],
}
b_bad1 = copy.deepcopy(backlog); b_bad1["stories"][0]["acceptance_criteria"][0].pop("evidence")  # met without evidence
b_bad2 = copy.deepcopy(backlog); b_bad2["tasks"][0].pop("evidence")                               # completed without evidence
b_bad3 = copy.deepcopy(backlog); b_bad3["tasks"][1]["complexity"]["score"] = 11

uat = {
  "protocol": "sancho/1.0",
  "cases": [
    {"id": "UAT-001", "story": "S-001", "criteria": ["AC-001.2"], "title": "Wrong password", "platform": "web (Chrome)",
     "preconditions": ["A user exists: mario@example.com"], "test_data": ["password: wrong-pass"],
     "steps": [{"n": 1, "action": "Open the login page"}, {"n": 2, "action": "Type the email and a wrong password, press Sign in", "expected": "An error message appears"}],
     "expected_result": "The message says the credentials are wrong without revealing which field", "result": "fail",
     "executed_by": "Danilo", "executed_at": NOW, "defects": ["DEF-001"]}],
  "defects": [{"id": "DEF-001", "uat": "UAT-001", "severity": "major", "description": "Message reveals the email exists", "status": "open"}],
}
u_bad1 = copy.deepcopy(uat); u_bad1["cases"][0].pop("defects")        # fail without defect
u_bad2 = copy.deepcopy(uat); u_bad2["cases"][0].pop("executed_at")    # result without execution time
u_bad3 = copy.deepcopy(uat); u_bad3["cases"][0]["steps"] = []

handoff = {
  "protocol": "sancho/1.0", "phase": "implement", "task": "T-001", "source": "developer", "target": "qa",
  "objective": "Login endpoint ready for verification", "status": "ready_for_review",
  "completed_work": ["POST /api/login with rate limit"],
  "verified_findings": [{"statement": "Auth tests pass", "evidence": [ev_cmd]}],
  "unverified_hypotheses": [{"statement": "Rate limit holds under load", "how_to_verify": "k6 run load/login.js"}],
  "modified_artifacts": [{"path": "src/auth/login.ts", "change": "added"}],
  "test_results": [{"name": "auth unit", "command": "npm test -- auth", "status": "passed", "executed": True},
                   {"name": "load", "status": "not_run", "executed": False, "summary": "k6 not installed"}],
  "open_issues": [], "next_actions": [{"action": "Run UAT-001", "owner": "user"}],
}
h_bad1 = copy.deepcopy(handoff); h_bad1["test_results"][0]["executed"] = False   # passed but not executed
h_bad2 = copy.deepcopy(handoff); h_bad2["verified_findings"][0]["evidence"] = [] # verified without evidence
h_bad3 = copy.deepcopy(handoff); h_bad3["status"] = "blocked"                     # blocked without issues

sec = {
  "protocol": "sancho/1.0", "generated_at": NOW,
  "scope": {"targets": ["http://localhost:8080"], "environment": "local", "active_testing": True,
            "approval": {"granted_by": "user", "granted_at": NOW, "scope": "ZAP baseline on localhost:8080"}},
  "tools": [{"name": "osv-scanner", "status": "run", "command": "osv-scanner -L package-lock.json"},
            {"name": "zap-baseline", "status": "run", "command": "zap-baseline.py -t http://localhost:8080"},
            {"name": "mobsf", "status": "not_run", "note": "no Android build yet"}],
  "enrichment": {"osv": "run", "nvd": "not_run", "kev": "run", "epss": "run"},
  "findings": [{"id": "F-001", "title": "Prototype pollution in lodash", "category": "sca",
                "component": {"name": "lodash", "version": "4.17.15", "ecosystem": "npm"},
                "cve": ["CVE-2020-8203"], "cwe": ["CWE-1321"],
                "cvss": {"version": "3.1", "vector": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:H/A:H", "base_score": 7.4, "source": "osv"},
                "epss": {"score": 0.02}, "kev": False, "severity": "major",
                "severity_rationale": "CVSS 7.4 >= 7.0, not in KEV, EPSS < 0.1", "remediation": "Upgrade lodash to 4.17.21", "status": "open"}],
  "summary": {"blocker": 0, "major": 1, "minor": 0, "nit": 0, "not_run": ["NVD: no API key and rate limit reached"]},
}
x_bad1 = copy.deepcopy(sec); x_bad1["scope"].pop("approval")                       # active testing without approval
x_bad2 = copy.deepcopy(sec); x_bad2["findings"][0]["cve"] = ["CVE-20-1"]
x_bad3 = copy.deepcopy(sec); x_bad3["tools"][0].pop("command")                     # tool run without command

sets = {
  "state": (state, {"skip-without-adr": s_bad1, "approved-without-time": s_bad2, "unknown-platform": s_bad3}),
  "backlog": (backlog, {"met-without-evidence": b_bad1, "completed-without-evidence": b_bad2, "complexity-out-of-range": b_bad3}),
  "uat": (uat, {"fail-without-defect": u_bad1, "result-without-execution": u_bad2, "no-steps": u_bad3}),
  "handoff": (handoff, {"passed-not-executed": h_bad1, "verified-without-evidence": h_bad2, "blocked-without-issues": h_bad3}),
  "security-report": (sec, {"active-without-approval": x_bad1, "bad-cve-id": x_bad2, "run-without-command": x_bad3}),
}
for name, (valid, invalids) in sets.items():
    d = OUT / name; d.mkdir(parents=True, exist_ok=True)
    (d / "valid.json").write_text(json.dumps(valid, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for reason, doc in invalids.items():
        (d / f"invalid-{reason}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("ok")
