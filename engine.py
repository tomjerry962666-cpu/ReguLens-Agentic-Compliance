"""ReguLens Competition Prototype — transparent local compliance pipeline.
Synthetic/demo use only. No production banking changes or legal conclusions.
"""
from __future__ import annotations
from datetime import datetime, timezone, date
from difflib import SequenceMatcher
import hashlib, json, re
from typing import Any

SAMPLE_REGULATION = """Banks must review privileged access at least every 90 days.
Evidence of each review must be retained for 12 months.
High-risk access exceptions must be remediated within 5 business days.
The bank must monitor material access changes and investigate alerts.
"""
SAMPLE_REGULATION_OLD = """Banks must review privileged access at least every 180 days.
Evidence of each review must be retained for 6 months.
High-risk access exceptions must be remediated within 10 business days.
"""
DEFAULT_CONTROLS = [
    {"control_id":"CTRL-IAM-01","control_name":"Privileged access recertification","description":"Review privileged access and record reviewer decisions at least quarterly.","keywords":"privileged access, access review, recertification, reviewer","owner":"IAM Operations","jurisdiction":"India","products":"Digital banking, Core banking","implemented":True,"evidence_present":True,"test_passed":True,"evidence_age_days":20,"review_frequency_days":90,"system":"Identity Governance","criticality":"High"},
    {"control_id":"CTRL-EVD-02","control_name":"Evidence retention and retrieval","description":"Retain access review evidence and make it retrievable for the required period.","keywords":"evidence, retained, retention, record, retrieve","owner":"Compliance Operations","jurisdiction":"India","products":"All banking products","implemented":True,"evidence_present":False,"test_passed":False,"evidence_age_days":0,"review_frequency_days":365,"system":"Evidence Vault","criticality":"High"},
    {"control_id":"CTRL-EXC-03","control_name":"High-risk exception SLA","description":"Assign and remediate high-risk access exceptions within the required deadline.","keywords":"exception, remediated, business days, sla, high-risk","owner":"Access Governance","jurisdiction":"India","products":"Digital banking, Core banking","implemented":True,"evidence_present":True,"test_passed":True,"evidence_age_days":15,"review_frequency_days":5,"system":"ITSM","criticality":"Critical"},
    {"control_id":"CTRL-MON-04","control_name":"Access-change monitoring","description":"Monitor material access changes, alert on drift, and investigate events.","keywords":"monitor, material access changes, investigate, alerts, change","owner":"Security Monitoring","jurisdiction":"India","products":"Digital banking, Core banking","implemented":False,"evidence_present":False,"test_passed":False,"evidence_age_days":0,"review_frequency_days":1,"system":"SIEM","criticality":"High"},
    {"control_id":"CTRL-LOG-05","control_name":"Audit-log integrity","description":"Protect audit logs from unauthorized alteration and periodically test retrieval.","keywords":"audit logs, log integrity, alteration, logs","owner":"Security Engineering","jurisdiction":"India","products":"Core banking","implemented":True,"evidence_present":True,"test_passed":True,"evidence_age_days":10,"review_frequency_days":30,"system":"Log Platform","criticality":"High"},
]
SAMPLE_CONTROL_POLICY = """Control policy sample (synthetic):
- Privileged access is reviewed quarterly by IAM Operations.
- Evidence of access review is stored in the evidence vault.
- High-risk exceptions are assigned to Access Governance.
- Material access changes are monitored by Security Monitoring.
"""

# Mapping synonyms are explicit and visible; scores are not represented as AI confidence.
SYNONYMS = {
    "access_review": ["privileged access","access review","access right","recertification","review privileged"],
    "evidence_retention": ["evidence","retained","retention","record","retrievable","stored"],
    "exception_sla": ["exception","remediated","business days","sla","high-risk","deadline"],
    "monitoring": ["monitor","material access changes","investigate","alerts","drift"],
    "audit_integrity": ["audit logs","log integrity","alteration","logs"],
}
NORMATIVE = re.compile(r"\b(must|shall|required to|is required|are required|should|will be required|no later than|at least|within|retain|maintain|ensure)\b", re.I)

def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def split_sentences(text: str) -> list[str]:
    # Preserve clause-like lines and avoid breaking decimal/article numbers.
    raw = re.split(r"(?<=[.!?])\s+(?=[A-Z])|\n+", text or "")
    return [re.sub(r"\s+", " ", x).strip(" \t-•") for x in raw if x.strip(" \t-•")]

def classify_domain(text: str) -> str:
    low = text.lower()
    # Prefer specific domains over broad terms such as evidence/record.
    if any(k in low for k in ["exception","remediated","business days","sla","deadline"]): return "exception_sla"
    if any(k in low for k in ["privileged access","access review","access right","recertification"]): return "access_review"
    if any(k in low for k in ["monitor","material access changes","investigate","alerts","drift"]): return "monitoring"
    if any(k in low for k in ["audit logs","log integrity","alteration"]): return "audit_integrity"
    if any(k in low for k in ["evidence","retained","retention","record","retrievable","stored"]): return "evidence_retention"
    return "unmapped"

def parse_obligations(text: str, source_name: str = "regulation.txt") -> list[dict[str, Any]]:
    obligations = []
    for i, sentence in enumerate(split_sentences(text), 1):
        if not NORMATIVE.search(sentence): continue
        domain = classify_domain(sentence)
        # Keep only obligation-like text; unknown obligations are retained for escalation.
        obligations.append({
            "obligation_id": f"OBL-{i:03d}",
            "source_name": source_name,
            "source_clause": sentence,
            "source_hash": sha(sentence)[:16],
            "domain": domain,
            "normative_signal": next((m.group(0).lower() for m in NORMATIVE.finditer(sentence)), ""),
            "extraction_method": "transparent normative-language rules",
        })
    return obligations

def compare_versions(old_text: str, new_text: str) -> list[dict[str, Any]]:
    old = split_sentences(old_text); new = split_sentences(new_text)
    pairs = []
    used_old, used_new = set(), set()
    # Exact matches first.
    for i, n in enumerate(new):
        for j, o in enumerate(old):
            if j not in used_old and n.lower() == o.lower():
                pairs.append({"change":"UNCHANGED","old_text":o,"new_text":n,"similarity":1.0})
                used_old.add(j); used_new.add(i); break
    # Pair most similar remaining sentences to surface revisions.
    candidates=[]
    for i,n in enumerate(new):
        if i in used_new: continue
        for j,o in enumerate(old):
            if j in used_old: continue
            ratio=SequenceMatcher(None, o.lower(), n.lower()).ratio()
            candidates.append((ratio,i,j))
    for ratio,i,j in sorted(candidates, reverse=True):
        if i in used_new or j in used_old: continue
        if ratio >= 0.35:
            pairs.append({"change":"MODIFIED","old_text":old[j],"new_text":new[i],"similarity":round(ratio,2)})
            used_old.add(j); used_new.add(i)
    for i,n in enumerate(new):
        if i not in used_new: pairs.append({"change":"ADDED","old_text":"","new_text":n,"similarity":0.0})
    for j,o in enumerate(old):
        if j not in used_old: pairs.append({"change":"REMOVED","old_text":o,"new_text":"","similarity":0.0})
    order={"MODIFIED":0,"ADDED":1,"REMOVED":2,"UNCHANGED":3}
    return sorted(pairs,key=lambda x:(order[x["change"]], x["new_text"] or x["old_text"]))

def _keywords(control: dict) -> list[str]:
    val = control.get("keywords", [])
    if isinstance(val, list): return [str(x).strip().lower() for x in val if str(x).strip()]
    return [x.strip().lower() for x in str(val or "").split(",") if x.strip()]

def map_obligations(obligations: list[dict], controls: list[dict]) -> list[dict]:
    mappings=[]
    for ob in obligations:
        ranked=[]
        txt=ob["source_clause"].lower()
        domain=ob["domain"]
        for c in controls:
            keywords=_keywords(c)
            hits=[kw for kw in keywords if kw in txt]
            # Add a domain alignment signal, still inspectable.
            domain_hits=[k for k in SYNONYMS.get(domain,[]) if k in txt and any(k in (c.get("description","")+" "+c.get("control_name","")).lower() for _ in [0])]
            score=len(set(hits + domain_hits))
            if score:
                ranked.append((score,c,hits))
        ranked.sort(key=lambda x:(-x[0], str(x[1].get("control_id",""))))
        best=ranked[0] if ranked else None
        # Low confidence ties are explicitly review-required.
        tie=bool(best and len([r for r in ranked if r[0]==best[0]])>1)
        mappings.append({
            "obligation_id":ob["obligation_id"],"domain":domain,
            "control_id":best[1].get("control_id") if best else "",
            "control_name":best[1].get("control_name") if best else "Unmapped — human control design required",
            "match_score":best[0] if best else 0,
            "matched_terms":", ".join(best[2]) if best else "",
            "mapping_status":"REVIEW_REQUIRED" if not best or tie or best[0] < 2 else "PROPOSED_MATCH",
            "alternatives":"; ".join(f"{r[1].get('control_id')} (score {r[0]})" for r in ranked[1:3]),
        })
    return mappings

def evaluate_obligations(obligations: list[dict], mappings: list[dict], controls: list[dict], scope: dict | None = None) -> list[dict]:
    scope = scope or {}
    out=[]
    for ob, mp in zip(obligations,mappings):
        c=next((c for c in controls if str(c.get("control_id"))==mp["control_id"]),None)
        reasons=[]
        applicable_jur=str(scope.get("jurisdiction","India")).lower()
        applicable_product=str(scope.get("product","Digital banking")).lower()
        applicable_entity=str(scope.get("entity","Retail Bank")).lower()
        # Demo scope is explicit and not inferred as legal advice.
        applicability="APPLICABLE"
        if c:
            cj=str(c.get("jurisdiction","All")).lower()
            cp=str(c.get("products","All")).lower()
            if cj not in ("all","") and applicable_jur not in cj: applicability="SCOPE_REVIEW"
            if cp not in ("all","") and applicable_product not in cp and "all" not in cp: applicability="SCOPE_REVIEW"
        else:
            applicability="UNASSESSED"
        if c is None: reasons.append("No mapped control")
        else:
            if applicability=="SCOPE_REVIEW": reasons.append("Control scope does not clearly cover selected jurisdiction/product")
            if not bool(c.get("implemented",False)): reasons.append("Control not implemented")
            if not bool(c.get("evidence_present",False)): reasons.append("Evidence missing")
            if not bool(c.get("test_passed",False)): reasons.append("Latest effectiveness test failed/not recorded")
            age=int(c.get("evidence_age_days") or 0)
            freq=int(c.get("review_frequency_days") or 0)
            if freq>0 and age>freq: reasons.append(f"Evidence stale ({age} days; review frequency {freq} days)")
        # A mapping is a proposal; ties/weak matches require review even if a control exists.
        if mp["mapping_status"]=="REVIEW_REQUIRED": reasons.append("Mapping requires human validation")
        urgency= "CRITICAL" if "No mapped control" in reasons or "Control not implemented" in reasons else "HIGH" if any("missing" in x.lower() or "failed" in x.lower() or "stale" in x.lower() for x in reasons) else "MEDIUM" if reasons else "LOW"
        base={"CRITICAL":70,"HIGH":55,"MEDIUM":35,"LOW":5}[urgency]
        score=min(100,base+min(25,10*max(0,len(reasons)-1))+(10 if re.search(r"\b(within|no later than|immediately)\b",ob["source_clause"],re.I) else 0))
        out.append({
            "obligation_id":ob["obligation_id"],"source_clause":ob["source_clause"],"source_hash":ob["source_hash"],
            "domain":ob["domain"],"applicability":applicability,"control_id":mp["control_id"],
            "control_name":mp["control_name"],"mapping_status":mp["mapping_status"],
            "assessment":"GAP" if reasons else "EVIDENCE_SUPPORTED",
            "severity":urgency,"risk_score":score,"gap_reasons":"; ".join(reasons) if reasons else "No configured failure detected",
            "required_evidence":_required_evidence(ob["domain"]),"suggested_remediation":_remedy(ob["domain"],reasons),
            "review_due":"Requires domain-owner confirmation" if applicability!="APPLICABLE" or mp["mapping_status"]=="REVIEW_REQUIRED" else "Within assigned remediation SLA",
            "entity":applicable_entity,"jurisdiction":applicable_jur,"product":applicable_product,
        })
    return sorted(out,key=lambda x:(-x["risk_score"],x["obligation_id"]))

def _required_evidence(domain):
    return {
        "access_review":"Dated access review export, reviewer identity, exceptions and sign-off",
        "evidence_retention":"Retention configuration, sample retained review record, retrieval test",
        "exception_sla":"Exception register with opened/closed timestamps and SLA calculation",
        "monitoring":"Monitoring rule/configuration, alert sample, investigation ticket",
        "audit_integrity":"Log access policy, integrity/tamper test, retrieval sample",
        "unmapped":"Evidence requirement to be defined by compliance owner",
    }.get(domain,"Evidence requirement to be defined by compliance owner")

def _remedy(domain,reasons):
    if "No mapped control" in reasons: return "Compliance owner to design or nominate a control; do not auto-map."
    if "Control not implemented" in reasons: return "Assign implementation task; attach design/implementation proof; then retest."
    if "Evidence missing" in reasons: return "Collect the required evidence artefact and validate source, period and owner."
    if any("failed" in x.lower() for x in reasons): return "Investigate failed test, remediate root cause and rerun independent test."
    if any("stale" in x.lower() for x in reasons): return "Refresh evidence and perform the scheduled control test."
    if any("Mapping requires" in x for x in reasons): return "Ask control owner to confirm or correct the proposed mapping."
    if any("scope" in x.lower() for x in reasons): return "Confirm legal entity/product applicability and map a scope-valid control."
    return "No remediation indicated by current configured checks; retain evidence and monitor."

def detect_contradictions(obligations: list[dict]) -> list[dict]:
    """Flags only obvious numeric/frequency conflicts within same topic; review is required."""
    groups={}
    for o in obligations:
        d=o["domain"]
        nums=re.findall(r"\b(\d+)\s*(day|days|month|months|year|years)\b",o["source_clause"].lower())
        if nums: groups.setdefault(d,[]).append((o,nums))
    out=[]
    for domain, rows in groups.items():
        if len(rows)<2: continue
        for i,(a,na) in enumerate(rows):
            for b,nb in rows[i+1:]:
                if a["source_clause"].lower()!=b["source_clause"].lower() and na!=nb:
                    out.append({"domain":domain,"obligation_a":a["obligation_id"],"clause_a":a["source_clause"],"obligation_b":b["obligation_id"],"clause_b":b["source_clause"],"flag":"POSSIBLE_CONFLICT","reason":"Different numeric periods appear in the same topic domain; source context may explain the difference, so human review is mandatory."})
    return out

def build_remediation_plan(findings: list[dict], controls: list[dict], owner_unavailable=False) -> list[dict]:
    plan=[]
    for f in findings:
        if f["assessment"]!="GAP": continue
        c=next((c for c in controls if str(c.get("control_id"))==f["control_id"]),None)
        owner=(c.get("owner") if c else "Compliance Lead") or "Compliance Lead"
        if owner_unavailable: owner=f"Compliance Lead (fallback from {owner})"
        plan.append({
            "task_id":f"TASK-{len(plan)+1:03d}","obligation_id":f["obligation_id"],"control_id":f["control_id"],
            "priority":f["severity"],"risk_score":f["risk_score"],"task":f["suggested_remediation"],
            "owner":owner,"required_evidence":f["required_evidence"],"status":"OPEN",
            "target":"5 business days (demo default; confirm against governing rule)","closure_gate":"Evidence uploaded + owner attestation + successful retest",
        })
    return plan

def run_pipeline(regulation_text: str, controls: list[dict], scope: dict | None = None, old_text: str = "", scenario: dict | None = None, source_name="uploaded_regulation.txt") -> dict:
    scenario=scenario or {}
    # Normalize controls into independent state so user edits do not mutate shared defaults.
    controls=[dict(c) for c in controls]
    events=[]
    def log(agent,action,status,detail):
        events.append({"sequence":len(events)+1,"timestamp_utc":datetime.now(timezone.utc).isoformat(timespec="seconds"),"agent":agent,"action":action,"status":status,"detail":detail})
    log("Intake Agent","validate_inputs","OK",f"Received {len(regulation_text or '')} characters, {len(controls)} control records, source={source_name}.")
    if not (regulation_text or "").strip():
        log("Safety Gate","stop_empty_source","BLOCKED","No regulatory text supplied; no compliance conclusion generated.")
        return {"status":"BLOCKED","obligations":[],"mappings":[],"findings":[],"plan":[],"events":events,"changes":[],"contradictions":[],"metrics":_metrics([],[],[]),"controls":controls,"scenario":scenario}
    if scenario.get("disable_first_control"):
        if controls: controls[0]["implemented"]=False
        log("Scenario Agent","inject_control_regression","APPLIED","Disabled the first control in the sandbox copy only.")
    if scenario.get("remove_evidence"):
        target=scenario.get("evidence_control_id") or next((c.get("control_id") for c in controls if "evidence" in str(c.get("control_name","")).lower()),None)
        for c in controls:
            if c.get("control_id")==target: c["evidence_present"]=False
        log("Scenario Agent","inject_evidence_failure","APPLIED",f"Evidence removed from {target or 'no matching control'} in sandbox state.")
    obligations=parse_obligations(regulation_text,source_name)
    log("Obligation Agent","extract_obligation_candidates","OK",f"Extracted {len(obligations)} normative candidates; each retains source sentence and hash.")
    mappings=map_obligations(obligations,controls)
    log("Mapping Agent","propose_control_links","OK",f"Proposed {sum(bool(m['control_id']) for m in mappings)} links; low-confidence/tied links are marked for human review.")
    findings=evaluate_obligations(obligations,mappings,controls,scope)
    log("Applicability & Evidence Agent","assess_scope_and_evidence","OK",f"Evaluated applicability, implementation, evidence freshness and latest test for {len(findings)} candidates.")
    changes=compare_versions(old_text,regulation_text) if old_text.strip() else []
    if old_text.strip():
        changed=sum(c["change"]!="UNCHANGED" for c in changes)
        log("Change Intelligence Agent","compare_regulatory_versions","OK",f"Compared source versions; {changed} added/modified/removed lines flagged.")
    contradictions=detect_contradictions(obligations)
    log("Consistency Agent","flag_possible_contradictions","REVIEW" if contradictions else "OK",f"{len(contradictions)} possible numeric/frequency conflicts flagged for human review.")
    plan=build_remediation_plan(findings,controls,owner_unavailable=bool(scenario.get("owner_unavailable")))
    log("Planning Agent","create_owned_remediation_tasks","OK",f"Created {len(plan)} remediation task(s), each with owner, evidence gate and retest requirement.")
    # Simulated executor records actions, does not silently falsify evidence or close compliance gaps.
    executed=[]
    fail_once=bool(scenario.get("inject_transient_failure"))
    for i, task in enumerate(plan):
        state=dict(task)
        if fail_once and i==0:
            log("Execution Agent","execute_sandbox_task","RETRY","Injected transient tool failure; retrying same idempotent task once.")
            state["retry_count"]=1
            log("Execution Agent","execute_sandbox_task","RECOVERED",f"Retry succeeded for {task['task_id']}; task creation/execution receipt recorded.")
        else:
            state["retry_count"]=0
            log("Execution Agent","create_sandbox_task","CREATED",f"Created local remediation task {task['task_id']}; no external system was modified.")
        state["status"]="OPEN"
        state["execution_receipt"]=sha(json.dumps({"task_id":state["task_id"],"owner":state["owner"],"task":state["task"]},sort_keys=True))[:16]
        executed.append(state)
    log("Verification Agent","enforce_closure_gate","BLOCKED" if plan else "OK", "Open tasks remain gaps until evidence is uploaded, owner attests, and retest passes." if plan else "No configured gaps found; keep monitoring and human review.")
    metrics=_metrics(obligations,mappings,findings)
    return {"status":"ASSESSMENT_COMPLETE_WITH_OPEN_ACTIONS" if plan else "ASSESSMENT_COMPLETE","obligations":obligations,"mappings":mappings,"findings":findings,"plan":plan,"executed_tasks":executed,"events":events,"changes":changes,"contradictions":contradictions,"metrics":metrics,"controls":controls,"scenario":scenario,"scope":scope or {},"source_name":source_name,"source_hash":sha(regulation_text)}
def _metrics(obs,maps,findings):
    return {"obligations":len(obs),"mapped":sum(bool(x.get("control_id")) for x in maps),"mapping_review":sum(x.get("mapping_status")=="REVIEW_REQUIRED" for x in maps),"gaps":sum(x.get("assessment")=="GAP" for x in findings),"evidence_supported":sum(x.get("assessment")=="EVIDENCE_SUPPORTED" for x in findings),"critical":sum(x.get("severity")=="CRITICAL" for x in findings),"high":sum(x.get("severity")=="HIGH" for x in findings),"actions":sum(x.get("assessment")=="GAP" for x in findings)}
def export_json(result): return json.dumps(result,indent=2,ensure_ascii=False)


def remediate_task(result: dict, task_id: str, action: str, actor: str = "Demo operator") -> dict:
    """Apply one explicit sandbox workflow action and append an auditable event.

    Supported actions: execute, attach_evidence, attest, retest. This mutates only
    the in-memory demo result; it never changes a real bank system.
    """
    task = next((t for t in result.get("executed_tasks", []) if t.get("task_id") == task_id), None)
    if task is None:
        raise ValueError(f"Unknown remediation task: {task_id}")
    if task.get("status") == "CLOSED":
        raise ValueError("This task is already closed.")

    def log(action_name: str, status: str, detail: str):
        events = result.setdefault("events", [])
        events.append({
            "sequence": len(events) + 1,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "agent": "Remediation Workbench",
            "action": action_name,
            "status": status,
            "detail": f"Actor={actor}. {detail}",
        })

    control = next((c for c in result.get("controls", []) if str(c.get("control_id")) == str(task.get("control_id"))), None)
    if action == "execute":
        if control is None:
            task["status"] = "NEEDS_CONTROL_DESIGN"
            log("execute_sandbox_remediation", "BLOCKED", "No mapped control exists. A compliance owner must define a control before automated remediation.")
            return result
        # Apply only synthetic sandbox state. Evidence is deliberately a separate step.
        control["implemented"] = True
        control["test_passed"] = False
        task["remediation_executed"] = True
        task["status"] = "REMEDIATION_EXECUTED"
        log("execute_sandbox_remediation", "APPLIED", f"Updated sandbox control {control.get('control_id')}; evidence and retest are still required.")
    elif action == "attach_evidence":
        if not task.get("remediation_executed"):
            raise ValueError("Execute the remediation in the sandbox before attaching its generated evidence.")
        if control is None:
            raise ValueError("Cannot attach evidence without a mapped control.")
        control["evidence_present"] = True
        control["evidence_age_days"] = 0
        task["evidence_uploaded"] = True
        task["evidence_artifact"] = f"SYNTHETIC-EVIDENCE-{task_id}"
        task["status"] = "EVIDENCE_ATTACHED"
        log("attach_synthetic_evidence", "APPLIED", f"Attached {task['evidence_artifact']}; this is synthetic demo evidence, not a real bank artefact.")
    elif action == "attest":
        if not task.get("evidence_uploaded"):
            raise ValueError("Attach evidence before recording owner attestation.")
        task["owner_attested"] = True
        task["attested_by"] = actor
        task["status"] = "OWNER_ATTESTED"
        log("record_owner_attestation", "RECORDED", "Owner attestation recorded in the local demo workflow.")
    elif action == "retest":
        if not task.get("remediation_executed") or not task.get("evidence_uploaded") or not task.get("owner_attested"):
            raise ValueError("Retest is blocked until remediation, evidence attachment, and owner attestation are complete.")
        if control is None:
            raise ValueError("Cannot retest without a mapped control.")
        control["test_passed"] = True
        task["retest_passed"] = True
        # Only close if the related finding has a valid mapped control and no review flag.
        finding = next((f for f in result.get("findings", []) if f.get("obligation_id") == task.get("obligation_id")), None)
        mapping = next((m for m in result.get("mappings", []) if m.get("obligation_id") == task.get("obligation_id")), None)
        if (finding and mapping and mapping.get("mapping_status") != "REVIEW_REQUIRED"
                and finding.get("applicability") == "APPLICABLE" and control.get("implemented")
                and control.get("evidence_present") and control.get("test_passed")) :
            finding["assessment"] = "EVIDENCE_SUPPORTED"
            finding["severity"] = "LOW"
            finding["risk_score"] = 5
            finding["gap_reasons"] = "Sandbox remediation executed; synthetic evidence attached; owner attested; retest passed."
            task["status"] = "CLOSED"
            log("independent_retest", "PASS", "Retest passed and mapping is not flagged for review; task closed in synthetic state.")
        else:
            task["status"] = "HUMAN_REVIEW_REQUIRED"
            log("independent_retest", "REVIEW", "Retest passed, but mapping is unmapped/ambiguous; task remains open for compliance review.")
    else:
        raise ValueError(f"Unsupported action: {action}")

    # Recalculate dashboard counters from current findings and tasks.
    findings = result.get("findings", [])
    result["metrics"] = _metrics(result.get("obligations", []), result.get("mappings", []), findings)
    open_tasks = sum(t.get("status") != "CLOSED" for t in result.get("executed_tasks", []))
    result["metrics"]["actions"] = open_tasks
    result["status"] = "ASSESSMENT_COMPLETE_WITH_OPEN_ACTIONS" if open_tasks else "ASSESSMENT_COMPLETE"
    return result


def compare_regulatory_sources(primary_text: str, primary_name: str, secondary_text: str, secondary_name: str) -> list[dict[str, Any]]:
    """Cross-source topic comparison; flags similar-domain obligations with differing periods for review."""
    primary = parse_obligations(primary_text, primary_name)
    secondary = parse_obligations(secondary_text, secondary_name)
    rows = []
    for a in primary:
        for b in secondary:
            if a["domain"] != b["domain"] or a["domain"] == "unmapped":
                continue
            nums_a = re.findall(r"\b(\d+)\s*(day|days|month|months|year|years)\b", a["source_clause"].lower())
            nums_b = re.findall(r"\b(\d+)\s*(day|days|month|months|year|years)\b", b["source_clause"].lower())
            if nums_a and nums_b and nums_a != nums_b:
                rows.append({
                    "topic": a["domain"], "primary_source": primary_name,
                    "primary_clause": a["source_clause"], "secondary_source": secondary_name,
                    "secondary_clause": b["source_clause"], "status": "POSSIBLE_CROSS_SOURCE_CONFLICT",
                    "decision": "Human review required; scope and legal hierarchy are not inferred by this prototype.",
                })
            else:
                # Keep the cross-source relationship visible even if the numeric terms agree or are absent.
                rows.append({
                    "topic": a["domain"], "primary_source": primary_name,
                    "primary_clause": a["source_clause"], "secondary_source": secondary_name,
                    "secondary_clause": b["source_clause"], "status": "RELATED_TOPIC_REVIEW",
                    "decision": "Related topic detected; confirm whether both requirements apply to this entity/product.",
                })
    return rows
