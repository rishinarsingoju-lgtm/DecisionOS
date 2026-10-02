"use client";

import { useState } from "react";
import { auditEvents, decisionActions, sources, type Decision } from "@/data/mock-data";
import type { Section } from "@/components/decisionos-app";
import { Badge, Panel, SectionHeading } from "@/components/shared";

const detailTabs = ["Analysis", "Simulation", "Decision", "Verification", "Audit trail", "Provenance"];

export function DecisionDetail({ decision, onNavigate, onReview, reviewed, reviewPending, sourceData }: {
  decision: Decision;
  onNavigate: (section: Section) => void;
  onReview: (decision: Decision, action: "approved" | "rejected") => void | Promise<void>;
  reviewed: string[];
  reviewPending?: "approved" | "rejected" | null;
  sourceData?: typeof sources;
}) {
  const [tab, setTab] = useState("Analysis");
  const reviewRecord = reviewed.find((entry) => entry.startsWith(`${decision.id}:`));
  const isVerified = decision.status === "VERIFIED";
  const verificationClaims = decision.verification?.claims;
  const currentSources = sourceData ?? sources;
  const simulationRows = decision.actions?.length ? decision.actions : decision.dataOrigin ? [] : decisionActions;

  const jumpTo = (name: string) => {
    setTab(name);
    document.getElementById(`detail-${name.toLowerCase().replaceAll(" ", "-")}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="detail-wrap">
      <div className="detail-context">
        <div className="breadcrumbs"><button onClick={() => onNavigate("Overview")}>OVERVIEW</button><span>/</span><span>DECISIONS</span><span>/</span><b>{decision.id}</b></div>
        <div className="context-meta"><span>GENERATED {decision.updated}</span><span>·</span><span>DATA ORIGIN: {decision.dataOrigin ?? "SYNTHETIC_CLIENT"}</span><span>·</span><span>REGION: {decision.region.toUpperCase()}</span></div>
      </div>

      <div className={`dossier-heading ${isVerified ? "dossier-verified" : "dossier-withheld"}`}>
        <div className="dossier-title">
          <div className="eyebrow">DECISION DOSSIER <span className="mono">{decision.id}</span></div>
          <h2>{decision.medicine} <span>— {decision.location}</span></h2>
          <p>{decision.trigger}</p>
        </div>
        <div className="dossier-status">
          <Badge tone={decision.priority === "CRITICAL" ? "withheld" : "warning"}>{decision.priority} PRIORITY</Badge>
          <Badge tone={isVerified ? "verified" : "withheld"}>{decision.status}</Badge>
        </div>
      </div>

      <nav className="detail-tabs" aria-label="Decision dossier sections">
        {detailTabs.map((name) => <button className={tab === name ? "selected" : ""} key={name} onClick={() => jumpTo(name)}>{name}</button>)}
      </nav>

      <section className="detail-section" id="detail-analysis">
        <SectionHeading eyebrow="01 / DETECTION & ANALYSIS" title="What was detected" note="EVIDENCE-LED ANALYSIS" />
        <div className="signal-grid">
          <Signal label="Demand trend" value={decision.demand} detail="7-day moving average" tone="blue" />
          <Signal label="Disease concentration" value={decision.disease} detail="Synthetic client disease signal" tone="amber" />
          <Signal label="Seasonality" value={decision.seasonality} detail="Configured model factor" tone="blue" />
          <Signal label="Available inventory" value={decision.inventory} detail={decision.sku} tone="neutral" />
          <Signal label="Expiry exposure" value={decision.expiry} detail={decision.expiryLoss} tone="red" />
          <Signal label="Supplier lead time" value={decision.leadTime} detail="Primary supplier baseline" tone="neutral" />
          <Signal label="Weather" value={decision.weather} detail="External context; not authoritative" tone="blue" />
        </div>
        <div className="analysis-explanation">
          <Panel><div className="eyebrow">WHY IT MATTERS</div><p>{decision.whyItMatters}</p></Panel>
          <Panel><div className="eyebrow">EVIDENCE & CONSTRAINTS</div><p>Inventory and demand values are attributed to their recorded sources. Missing and stale signals are called out rather than treated as zero.</p>{decision.evidenceItems?.length ? <div className="evidence-record-list">{decision.evidenceItems.map((item) => <div className="evidence-record" key={item.source_ref}><span>{item.type?.replaceAll("_", " ")}</span><b>{item.summary ?? item.source_ref}</b><small>{item.source_ref} · {item.data_origin} · {item.freshness}</small></div>)}</div> : decision.dataOrigin ? <div className="empty-state">No evidence items were returned for this decision.</div> : <div className="inline-tags"><Badge tone="neutral">SYNTHETIC INVENTORY</Badge><Badge tone="matched">CDSCO CHECKED</Badge><Badge tone="warning">WEATHER STALE</Badge></div>}</Panel>
        </div>
      </section>

      <section className="detail-section" id="detail-simulation">
        <SectionHeading eyebrow="02 / DETERMINISTIC SIMULATION" title="Actions considered" note="VALUES SHOWN AS DEMO ESTIMATES" />
        <Panel className="table-panel">
          <div className="table-scroll"><table className="data-table simulation-table">
            <thead><tr><th>Action</th><th>Expiry loss</th><th>Stockout risk</th><th>Cost</th><th>Expected impact</th></tr></thead>
            <tbody>{simulationRows.length ? simulationRows.map((action) => <tr className={action.recommendation && isVerified ? "recommended-row" : ""} key={action.action}><td><b>{action.action}</b>{action.recommendation && isVerified && <Badge tone="verified">SELECTED</Badge>}</td><td>{action.loss}</td><td>{action.stockout}</td><td>{action.cost}</td><td>{action.impact}</td></tr>) : <tr><td colSpan={5}><div className="empty-state">No simulation results were returned for this decision.</div></td></tr>}</tbody>
          </table></div>
          <div className="table-footnote">Baseline comparison uses the same synthetic demand and inventory snapshot. These figures are not live customer data.</div>
        </Panel>
      </section>

      <section className="detail-section" id="detail-decision">
        <SectionHeading eyebrow="03 / DECISION PACKAGE" title="Recommended action" />
        <Panel className={`recommendation-panel ${isVerified ? "recommendation-ok" : "recommendation-blocked"}`}>
          <div className="recommendation-heading"><span className="recommendation-icon">{isVerified ? "✓" : "!"}</span><div><div className="eyebrow">{isVerified ? "VERIFIED RECOMMENDATION · AWAITING HUMAN REVIEW" : "RECOMMENDATION WITHHELD"}</div><h3>{isVerified ? decision.recommendation : "No action released for approval"}</h3></div></div>
          <div className="impact-row"><div><span>EXPECTED IMPACT</span><b>{isVerified ? decision.impact : "Impact estimate withheld until the mismatch is resolved."}</b></div><div><span>WHY THIS ACTION</span><b>{isVerified ? "Best verified trade-off across expiry exposure, stockout risk, and execution cost." : "Demand and quote quantities differ between the proposed calculation and independent recomputation."}</b></div></div>
          <div className="review-actions">
            <span className="human-control">HUMAN REVIEW REQUIRED · CONSEQUENTIAL ACTION IS NOT EXECUTED BY THIS SYSTEM</span>
            <div><button className="button button-secondary" disabled={Boolean(reviewPending)} onClick={() => onReview(decision, "rejected")}>{reviewPending === "rejected" ? "Rejecting…" : "Reject"}</button><button className="button button-primary" disabled={!isVerified || Boolean(reviewPending)} onClick={() => onReview(decision, "approved")}>{reviewPending === "approved" ? "Approving…" : isVerified ? "Approve recommendation" : "Approval unavailable"}</button></div>
          </div>
          {reviewRecord && <div className="review-result">{reviewRecord.endsWith("approved") ? "Approved" : "Rejected"} in this demo session. No inventory or procurement action was executed.</div>}
        </Panel>
      </section>

      <section className="detail-section" id="detail-verification">
        <SectionHeading eyebrow="04 / INDEPENDENT VERIFICATION" title="Calculation integrity" note="LLM OUTPUT IS NOT NUMERIC AUTHORITY" />
        <div className={`verification-console ${isVerified ? "verification-pass" : "verification-fail"}`}>
          <div className="verification-compare"><div><span>AI / DECISION CALCULATION</span><b>{decision.verificationAi}</b></div><span className="versus">VS</span><div><span>INDEPENDENT RECOMPUTATION</span><b>{decision.verificationIndependent}</b></div></div>
          <div className="verification-outcome"><strong>{isVerified ? "MATCH" : "MISMATCH"}</strong><span>→</span><b>{isVerified ? "VERIFIED" : "RECOMMENDATION WITHHELD"}</b></div>
          <p>{decision.verificationNote}</p>
          {!isVerified && <div className="withheld-rule">Mismatch detected → recommendation withheld. A proposed action is not presented as approved or authoritative.</div>}
        </div>
        <div className="claim-list"><div className="claim-row claim-header"><span>VERIFIED CLAIM</span><span>ENGINE VALUE</span><span>INDEPENDENT VALUE</span><span>RESULT</span></div>
          {verificationClaims?.length ? verificationClaims.map((claim) => <div className="claim-row" key={claim.claim}><b>{claim.claim.replaceAll("_", " ")}</b><span>{claim.ai_calculation ?? "Unknown"}</span><span>{claim.independent_recomputation ?? "Unknown"}</span><Badge tone={claim.status === "MATCH" ? "verified" : "withheld"}>{claim.status}</Badge></div>) : decision.dataOrigin ? <div className="empty-state">No verification claims were returned for this decision.</div> : (isVerified ? [["Expiry loss avoided", "₹3,10,400", "₹3,10,400"], ["Transfer quantity", "1,800 units", "1,800 units"], ["Residual stockout risk", "8%", "8%"], ["Execution cost", "₹24,600", "₹24,600"]] : [["Procurement quantity", "5,200 units", "4,700 units"], ["Expected impact", "₹1,82,000", "₹1,64,500"]]).map((claim) => <div className="claim-row" key={claim[0]}><b>{claim[0]}</b><span>{claim[1]}</span><span>{claim[2]}</span><Badge tone={isVerified ? "verified" : "withheld"}>{isVerified ? "MATCH" : "MISMATCH"}</Badge></div>)}
        </div>
      </section>

      <section className="detail-section" id="detail-audit-trail">
        <SectionHeading eyebrow="05 / AUDIT TRAIL" title="Decision history" note="ORDERED · IMMUTABLE DEMO LOG" />
        <Panel className="audit-panel">{decision.auditEvents?.length ? decision.auditEvents.map((event, index) => <div className="audit-event" key={event.id ?? `${event.time}-${event.actor}-${event.event}-${index}`}><div className="audit-time">{event.time}<span>IST</span></div><div className={`audit-node ${index === 0 ? "current" : ""}`} /><div className="audit-copy"><b>{event.actor}</b><span>{event.event}</span></div><span className="audit-hash">{event.id === undefined ? "DEMO EVENT" : `EVT-${event.id}`}</span></div>) : decision.dataOrigin ? <div className="empty-state">No audit events were returned for this decision.</div> : auditEvents.map((event, index) => <div className="audit-event" key={`${event.time}-${event.actor}-${event.event}-${index}`}><div className="audit-time">{event.time}<span>IST</span></div><div className={`audit-node ${index === 0 ? "current" : ""}`} /><div className="audit-copy"><b>{event.actor}</b><span>{index === 0 && !isVerified ? "Verification mismatch detected; package withheld." : event.event}</span></div><span className="audit-hash">DEMO EVENT</span></div>)}</Panel>
      </section>

      <section className="detail-section" id="detail-provenance">
        <SectionHeading eyebrow="06 / DATA PROVENANCE" title="Inputs & freshness" />
        <Panel className="provenance-grid"><div><span>CLIENT INVENTORY + DEMAND</span><b>{decision.dataOrigin ?? "SYNTHETIC_CLIENT"}</b><small>Snapshot · {decision.updated}</small></div>{currentSources.map((source) => <div key={source.name}><span>{source.name.toUpperCase()}</span><b>{source.status}</b><small>{source.detail}</small></div>)}</Panel>
      </section>
      <div className="detail-bottom-actions"><button className="button button-secondary" onClick={() => onNavigate("Procurement")}>View procurement comparison</button><span>Decision package generated from synthetic inputs · no external action executed</span></div>
    </div>
  );
}

function Signal({ label, value, detail, tone }: { label: string; value: string; detail: string; tone: string }) {
  return <div className={`signal-card signal-${tone}`}><span>{label}</span><b>{value}</b><small>{detail}</small></div>;
}