"use client";

import { useState } from "react";
import { decisions, inventoryRows, sources, suppliers, type Decision } from "@/data/mock-data";
import { Badge, Panel, SectionHeading, StatusLabel } from "@/components/shared";

export function DecisionsScreen({ activeDecision, onOpenDecision, reviewed, decisionRows = decisions }: { activeDecision: Decision; onOpenDecision: (decision: Decision) => void; reviewed: string[]; decisionRows?: Decision[] }) {
  return (
    <div className="screen-stack">
      <div className="page-intro"><div><div className="eyebrow">AUTONOMOUS DETECTION / DECISION QUEUE</div><h1>Decisions</h1><p>Review detected conditions, evidence, simulations, and verification before human approval.</p></div><span className="data-origin"><i /> SYNTHETIC CLIENT DATA</span></div>
      <Panel className="queue-panel"><SectionHeading eyebrow="OPEN DECISION PACKAGES" title="Priority queue" note={`${decisionRows.length} DECISIONS · SORTED BY SEVERITY`} />
        <div className="queue-table-wrap"><table className="data-table"><thead><tr><th>Priority / ID</th><th>Medicine & location</th><th>Detected condition</th><th>Verification</th><th>Review</th><th></th></tr></thead><tbody>{decisionRows.map((decision) =>
          <tr className={activeDecision.id === decision.id ? "selected-row" : ""} key={decision.id}>
            <td><div className="table-stack"><Badge tone={decision.priority === "CRITICAL" ? "withheld" : "warning"}>{decision.priority}</Badge><small className="mono">{decision.id}</small></div></td>
            <td><b>{decision.medicine}</b><small>{decision.location}</small></td>
            <td>{decision.trigger}</td>
            <td><StatusLabel status={decision.status} /></td>
            <td>{decision.approvalStatus === "APPROVED" ? <Badge tone="verified">Approved</Badge> : decision.approvalStatus === "REJECTED" ? <Badge tone="withheld">Rejected</Badge> : reviewed.some((item) => item.startsWith(`${decision.id}:`)) ? <Badge tone="neutral">Reviewed locally</Badge> : <span className="muted">Pending</span>}</td>
            <td><button className="table-action" onClick={() => onOpenDecision(decision)}>Open dossier ↗</button></td>
          </tr>
        )}</tbody></table></div>
      </Panel>
      <div className="notice-line"><b>Control boundary</b><span>VERIFIED means the independent recomputation matched. It does not execute an action; human review remains required.</span></div>
    </div>
  );
}

export function InventoryScreen({ onOpenDecision, inventoryData = inventoryRows, decisionData = decisions }: { onOpenDecision: (decision: Decision) => void; inventoryData?: typeof inventoryRows; decisionData?: Decision[] }) {
  const [filter, setFilter] = useState("All inventory");
  const filteredRows = inventoryData.filter((row) => filter === "All inventory" || row.status === filter);
  const focusRow = inventoryData.find((row) => row.status === "Action required" || row.status === "Quarantined") ?? inventoryData[0];
  const relatedDecision = decisionData.find((decision) => focusRow && decision.medicine === focusRow.medicine && decision.location === focusRow.location) ?? decisionData[0];
  return (
    <div className="screen-stack">
      <div className="page-intro"><div><div className="eyebrow">SUPPLY POSITION / INDIA REGION</div><h1>Inventory control</h1><p>Availability, demand runway, and expiry exposure across monitored locations.</p></div><span className="data-origin"><i /> SYNTHETIC CLIENT DATA</span></div>
      <div className="telemetry-strip"><span>LOCATIONS <b>{new Set(inventoryData.map((row) => row.location)).size}</b></span><span>BATCHES <b>{inventoryData.length}</b></span><span>EXPIRY / QUALITY ACTIONS <b>{inventoryData.filter((row) => row.status === "Action required" || row.status === "Quarantined").length}</b></span><span>STOCKOUT WATCH <b>{inventoryData.filter((row) => row.status === "Stockout risk").length}</b></span></div>
      <Panel className="table-panel"><div className="table-toolbar"><SectionHeading eyebrow="BATCH-AWARE INVENTORY" title="Stock position" note={`${filteredRows.length} ROWS`} /><label className="filter-control">FILTER <select value={filter} onChange={(event) => setFilter(event.target.value)}><option>All inventory</option><option>Action required</option><option>Stockout risk</option><option>Monitor</option><option>Within range</option></select></label></div>
        <div className="queue-table-wrap"><table className="data-table inventory-table"><thead><tr><th>Medicine / batch</th><th>Location</th><th className="numeric">Available</th><th className="numeric">Demand</th><th>Days of cover</th><th>Expiry risk</th><th>Status</th></tr></thead><tbody>{filteredRows.map((row) => <tr key={row.batch}><td><b>{row.medicine}</b><small className="mono">{row.batch}</small></td><td>{row.location}</td><td className="numeric mono">{row.available}</td><td className="numeric mono">{row.demand}</td><td><span className={Number.parseInt(row.cover, 10) < 10 ? "text-red" : ""}>{row.cover}</span></td><td>{row.expiry}</td><td><Badge tone={row.status === "Stockout risk" || row.status === "Action required" ? "withheld" : row.status === "Monitor" ? "warning" : "verified"}>{row.status}</Badge></td></tr>)}</tbody></table></div>
        {filteredRows.length === 0 && <div className="empty-state">No inventory rows match this filter.</div>}
        <div className="table-footnote">Synthetic operational snapshot · batch expiry and demand estimates shown for demo use.</div>
      </Panel>
      {focusRow && <Panel className="inventory-focus"><div><div className="eyebrow">DECISION LINK</div><h3>{focusRow.medicine} · {focusRow.location}</h3><p>Batch {focusRow.batch}: {focusRow.expiry}. Current recorded status: {focusRow.status}.</p></div><button className="button button-secondary" disabled={!relatedDecision} onClick={() => relatedDecision && onOpenDecision(relatedDecision)}>Open related decision</button></Panel>}
    </div>
  );
}

export function ProcurementScreen({ supplierData = suppliers, medicineName = "Amoxicillin 500mg", requiredQuantity = 5200, referencePrice = "Unavailable", decisionData = decisions }: { supplierData?: typeof suppliers; medicineName?: string; requiredQuantity?: number | null; referencePrice?: string; decisionData?: Decision[] }) {
  const linkedDecision = decisionData.find((decision) => decision.medicine === medicineName && decision.trigger === "STOCKOUT_RISK");
  const linkedStatus = linkedDecision ? `${linkedDecision.status} · ${linkedDecision.approvalStatus ?? "PENDING REVIEW"}` : "No linked decision";
  return (
    <div className="screen-stack">
      <div className="page-intro"><div><div className="eyebrow">SUPPLIER INTELLIGENCE / {medicineName.toUpperCase()}</div><h1>Procurement comparison</h1><p>{requiredQuantity === null ? "Trade-offs for an unknown replenishment requirement." : `Trade-offs for a ${requiredQuantity.toLocaleString()}-unit replenishment requirement.`}</p></div><span className="data-origin"><i /> SYNTHETIC CLIENT DATA</span></div>
      <div className="procurement-warning"><b>Evidence constraint</b><span>{supplierData.some((supplier) => supplier.status !== "Known") ? "At least one supplier has no completed client order history. Indicative price is not treated as evidence of supplier quality." : "Supplier history and quoted availability are compared; no single supplier is selected without a verified decision."}</span><Badge tone="warning">HUMAN REVIEW REQUIRED</Badge></div>
      <Panel className="table-panel"><div className="table-toolbar"><SectionHeading eyebrow={`QUOTED OPTIONS / ${supplierData.length} SUPPLIERS`} title="Supplier comparison" note="NO OVERALL WINNER ASSIGNED" /><span className="reference-price">NPPA REFERENCE <b>{referencePrice}</b></span></div>
        <div className="queue-table-wrap"><table className="data-table supplier-table"><thead><tr><th>Supplier</th><th>Price / unit</th><th>Quality history</th><th>Reliability</th><th>Lead time</th><th>Availability</th><th>Evidence</th></tr></thead><tbody>{supplierData.map((supplier) =>
          <tr key={supplier.name}>
            <td><b>{supplier.name}</b><small><Badge tone={supplier.status === "Known" ? "verified" : "warning"}>{supplier.status}</Badge></small></td>
            <td className="mono">{supplier.price}</td>
            <td>{supplier.quality}</td>
            <td>{supplier.reliability}</td>
            <td>{supplier.lead}</td>
            <td>{supplier.availability}</td>
            <td>{supplier.evidence}</td>
          </tr>
        )}</tbody></table></div>
        <div className="table-footnote">Supplier quotes, order histories, and quality records shown are synthetic demo data. NPPA is a reference signal, not a supplier quote.</div>
      </Panel>
      <Panel><SectionHeading eyebrow="DECISION RATIONALE" title="Trade-offs to review" /><div className="tradeoff-grid">{supplierData.map((supplier, index) =>
        <div className="tradeoff-item" key={supplier.name}>
          <span className={`tradeoff-index tradeoff-${index}`}>0{index + 1}</span>
          <div>
            <b>{supplier.name}</b>
            <p>{supplier.tradeoff}</p>
          </div>
        </div>
      )}</div></Panel>
      <div className="notice-line"><b>Recommendation status: {linkedStatus}</b><span>{linkedDecision?.whyItMatters ?? "No stockout decision package is currently linked to this medicine."}</span></div>
    </div>
  );
}

export function EvidenceScreen({ sourceData = sources, alertData = [] }: { sourceData?: typeof sources; alertData?: Record<string, unknown>[] }) {
  return (
    <div className="screen-stack">
      <div className="page-intro"><div><div className="eyebrow">EXTERNAL INTELLIGENCE / PROVENANCE</div><h1>Evidence sources</h1><p>Source availability, freshness, and match state for this synthetic demo snapshot.</p></div><span className="data-origin"><i /> EXTERNAL SOURCES LABELED</span></div>
      <div className="evidence-legend"><span><i className="legend-square available" />Available</span><span><i className="legend-square stale" />Stale</span><span><i className="legend-square unavailable" />Unavailable</span><span><i className="legend-square matched" />Matched evidence</span></div>
      <div className="evidence-grid">{sourceData.map((source) =>
        <Panel className="evidence-card" key={source.name}>
          <div className="evidence-card-top"><span className="source-monogram">{source.name.slice(0, 2).toUpperCase()}</span><Badge tone={source.kind === "matched" ? "verified" : source.kind === "stale" ? "warning" : "withheld"}>{source.status}</Badge></div>
          <h3>{source.name}</h3>
          <p>{source.purpose}</p>
          <div className="source-detail"><span>FETCH STATE</span><b>{source.detail}</b></div>
          {source.name === "CDSCO" && <div className="match-callout"><span className="source-state matched" /><div><b>Batch-level alerts</b><small>{alertData.length ? alertData.map((alert) => `${String(alert.productName)} · ${String(alert.batchNumber)} · ${String(alert.result)}`).join("; ") : "No batch-level alert records are available."}</small></div></div>}
          {source.name === "WHO ICD" && <div className="match-callout"><span className="source-state matched" /><div><b>Scope note</b><small>Terminology normalization only; no regional prevalence is inferred from WHO.</small></div></div>}
          {source.name === "NPPA" && <div className="match-callout"><span className="source-state unavailable" /><div><b>Not applied</b><small>Reference price snapshot unavailable. Supplier quotes remain separate.</small></div></div>}
        </Panel>
      )}</div>
      <Panel className="provenance-note"><div className="eyebrow">PROVENANCE RULE</div><p>External evidence is not interchangeable with synthetic client inputs. Unavailable and stale sources are surfaced explicitly and excluded where freshness or a match is required.</p></Panel>
    </div>
  );
}

export function SystemStatusScreen({ sourceData = sources, backendConnected = false, lastAnalysis = "09:42 IST", pipelineData = [] }: { sourceData?: typeof sources; backendConnected?: boolean; lastAnalysis?: string; pipelineData?: { name: string; status: string }[] }) {
  return (
    <div className="screen-stack">
      <div className="page-intro"><div><div className="eyebrow">SYSTEM OBSERVABILITY / {backendConnected ? "API CONNECTED" : "OFFLINE FALLBACK"}</div><h1>System status</h1><p>Operational state and data freshness for the local frontend demonstration.</p></div><Badge tone={backendConnected ? "verified" : "warning"}>{backendConnected ? "DATABASE CONNECTED" : "MOCK DATA"}</Badge></div>
      <div className="system-banner"><span className="status-square good" /><div><b>Autonomous monitoring state: {backendConnected ? "DATABASE-BACKED" : "OFFLINE · MOCK DATA"}</b><span>{backendConnected ? "Analysis and human review are served by the FastAPI backend; consequential actions are not executed." : "Backend API is unavailable. Showing synthetic frontend fallback data."}</span></div><span className="mono">LAST ANALYSIS {lastAnalysis}</span></div>
      <Panel><SectionHeading eyebrow="DECISION PIPELINE" title="Stage readiness" /><div className="stage-list">
        {pipelineData.length > 0 ? (
          pipelineData.map((stage, index) => <div className="stage-row" key={stage.name}><span className="stage-index">0{index + 1}</span><b>{stage.name}</b><span className="stage-connector" /><span>{stage.status}</span><Badge tone={stage.status.includes("REQUIRED") ? "warning" : "verified"}>{stage.status.includes("REQUIRED") ? "REVIEW" : "READY"}</Badge></div>)
        ) : (
          [{ name: "Detection", state: "Ready · demo snapshot", tone: "verified" }, { name: "Analyze", state: "Evidence assembled", tone: "verified" }, { name: "Simulate", state: "Deterministic examples", tone: "verified" }, { name: "Decide", state: "Trade-off package shown", tone: "verified" }, { name: "Verify", state: "Matched or withheld by case", tone: "verified" }, { name: "Human review", state: "UI control only · no execution", tone: "warning" }].map((stage, index) => <div className="stage-row" key={stage.name}><span className="stage-index">0{index + 1}</span><b>{stage.name}</b><span className="stage-connector" /><span>{stage.state}</span><Badge tone={stage.tone}>{stage.tone === "verified" ? "DEMO READY" : "LOCAL ONLY"}</Badge></div>)
        )}
      </div></Panel>
      <Panel><SectionHeading eyebrow="INGESTION FRESHNESS" title="Connected source status" /><div className="source-list">{sourceData.map((source) =>
        <div className="source-row" key={source.name}><span className={`source-state ${source.kind}`} /><div><b>{source.name}</b><small>{source.purpose}</small></div><span className="source-timestamp">{source.detail}</span><StatusLabel status={source.status} /></div>
      )}</div></Panel>
      <div className="notice-line"><b>Deterministic-only frontend</b><span>{backendConnected ? "FastAPI is connected. Numerical authority remains with the deterministic engine and independent verifier; no LLM, database, or external side-effect executes an action." : "No backend API is connected. The UI is showing only its synthetic fallback data."}</span></div>
    </div>
  );
}