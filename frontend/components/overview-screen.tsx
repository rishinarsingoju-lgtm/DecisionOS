import { decisions, sources, type Decision } from "@/data/mock-data";
import type { Section } from "@/components/decisionos-app";
import { Badge, Panel, SectionHeading } from "@/components/shared";
import type { OverviewPayload } from "@/components/api-client";

export function OverviewScreen({ onOpenDecision, onNavigate, onDemoScan, scanPending = false, sourceData, summary, alertData = [], lastAnalysis = "09:42 IST", decisionRows = decisions }: { onOpenDecision: (decision: Decision) => void; onNavigate: (section: Section) => void; onDemoScan: () => void; scanPending?: boolean; sourceData?: OverviewPayload["sources"]; summary?: OverviewPayload["summary"]; alertData?: OverviewPayload["alerts"]; lastAnalysis?: string; decisionRows?: Decision[] }) {
  const rows = decisionRows;
  const currentSources = sourceData ?? sources;
  const criticalCount = summary?.criticalDecisions ?? rows.filter((decision) => decision.priority === "CRITICAL").length;
  const verifiedCount = summary?.verifiedDecisions ?? rows.filter((decision) => decision.status === "VERIFIED").length;
  const pendingCount = summary?.decisionsRequiringAttention ?? rows.filter((decision) => decision.approvalStatus === "PENDING").length;
  const alertRows = [
    ...alertData.map((alert, index) => ({ id: `alert-${index}`, title: `${String(alert.productName ?? alert.source ?? "Source alert")} · ${String(alert.batchNumber ?? "")}`, detail: String(alert.result ?? alert.status ?? "Evidence record"), status: "Matched", tone: "verified" })),
    ...currentSources.filter((source) => source.status !== "Available" && source.status !== "Matched").map((source) => ({ id: source.name, title: `${source.name} source ${source.status.toLowerCase()}`, detail: source.detail, status: source.status, tone: source.kind === "stale" ? "warning" : "withheld" })),
  ].slice(0, 3);

  return (
    <div className="screen-stack">
      <div className="page-intro">
        <div>
          <div className="eyebrow">AUTONOMOUS OPERATIONS / INDIA REGION</div>
          <h1>Operations overview</h1>
          <p>Decisions discovered from supply, demand and external intelligence signals.</p>
        </div>
        <div className="intro-actions">
          <span className="data-origin"><i /> SYNTHETIC CLIENT DATA</span>
          <button className="button button-primary" onClick={onDemoScan} disabled={scanPending}>{scanPending ? "Analysis running…" : "Run analysis"}</button>
        </div>
      </div>

      <div className="telemetry-strip">
        <span><i className="status-square good" />AUTONOMOUS MONITORING <b>ACTIVE</b></span>
        <span>LAST ANALYSIS <b>{lastAnalysis}</b></span>
        <span>DATA SOURCES <b>{currentSources.filter((source) => source.status === "Available" || source.status === "Matched").length} AVAILABLE · {currentSources.filter((source) => source.status === "Stale").length} STALE · {currentSources.filter((source) => source.status === "Unavailable").length} UNAVAILABLE</b></span>
        <span>HUMAN REVIEW <b>REQUIRED</b></span>
      </div>

      <div className="metric-grid">
        <Metric label="Decisions requiring attention" value={String(pendingCount).padStart(2, "0")} detail="Pending human review" tone="red" />
        <Metric label="Critical decisions" value={String(summary?.criticalDecisions ?? criticalCount).padStart(2, "0")} detail="Expiry and stockout exposure" tone="amber" />
        <Metric label="Verified decisions" value={String(summary?.verifiedDecisions ?? verifiedCount).padStart(2, "0")} detail="Independent recomputation matched" tone="green" />
        <Metric label="Potential impact" value={summary?.potentialImpact ?? "₹3.10L"} detail="Verified expiry loss avoided" tone="blue" />
      </div>

      <div className="overview-grid">
        <section className="decision-list-area">
          <SectionHeading eyebrow="PRIORITY QUEUE" title="Decisions requiring attention" note="SORTED BY SEVERITY / IMPACT" />
          <div className="decision-stack">
            {rows.map((decision, index) => (
              <button className="decision-row" key={decision.id} onClick={() => onOpenDecision(decision)}>
                <span className={`priority-rail ${decision.priority.toLowerCase()}`} />
                <span className="decision-row-main">
                  <span className="decision-row-top"><Badge tone={decision.priority === "CRITICAL" ? "withheld" : "warning"}>{decision.priority}</Badge><span className="mono muted">{decision.id}</span><Badge tone={decision.status === "VERIFIED" ? "verified" : "withheld"}>{decision.status}</Badge></span>
                  <strong>{decision.medicine} <span>· {decision.location}</span></strong>
                  <span className="decision-trigger">{decision.trigger}</span>
                  <span className="recommendation-line"><b>{decision.status === "VERIFIED" ? "RECOMMENDED" : "WITHHELD"}</b>{decision.recommendation}</span>
                </span>
                <span className="decision-row-impact"><span>EXPECTED IMPACT</span><b>{decision.status === "VERIFIED" ? decision.impact.split(";")[0] : "Impact withheld"}</b><span>Updated {decision.updated}</span><span className="row-arrow">View dossier ↗</span></span>
              </button>
            ))}
          </div>
        </section>

        <aside className="overview-rail">
          <Panel>
            <SectionHeading eyebrow="EXTERNAL INTELLIGENCE" title="Source status" />
            <div className="source-list compact-source-list">
              {currentSources.map((source) =>
                <div className="source-row" key={source.name}><span className={`source-state ${source.kind}`} /><div><b>{source.name}</b><small>{source.detail}</small></div><Badge tone={source.kind === "matched" ? "verified" : source.kind === "stale" ? "warning" : "withheld"}>{source.status}</Badge></div>
              )}
            </div>
            <button className="text-action" onClick={() => onNavigate("Evidence")}>View evidence sources <span>→</span></button>
          </Panel>
          <Panel>
            <SectionHeading eyebrow="QUALITY & REGULATORY" title="Alerts" />
            {alertRows.map((alert, index) => <div className="alert-item" key={alert.id}><span className={`alert-index ${alert.tone === "verified" ? "red" : alert.tone === "warning" ? "amber" : "neutral"}`}>{String(index + 1).padStart(2, "0")}</span><div><b>{alert.title}</b><small>{alert.detail}</small></div><Badge tone={alert.tone}>{alert.status}</Badge></div>)}
          </Panel>
        </aside>
      </div>

      <Panel className="recent-panel">
        <SectionHeading eyebrow="AUDITABLE ACTIVITY" title="Recent decisions" note="DEMO SNAPSHOT · TODAY" />
        <div className="recent-grid">
          {rows.map((decision) => <button className="recent-item" key={decision.id} onClick={() => onOpenDecision(decision)}><span className="mono muted">{decision.id}</span><b>{decision.medicine}</b><span>{decision.location}</span><Badge tone={decision.status === "VERIFIED" ? "verified" : "withheld"}>{decision.status}</Badge></button>)}
        </div>
      </Panel>
    </div>
  );
}

function Metric({ label, value, detail, tone }: { label: string; value: string; detail: string; tone: string }) {
  return <div className={`metric-card metric-${tone}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small><div className="metric-rule"><i /></div></div>;
}

// ...existing code...