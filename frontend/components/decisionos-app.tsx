"use client";

import { useEffect, useState } from "react";
import { decisions, inventoryRows, sources, suppliers, type Decision } from "@/data/mock-data";
import { apiGet, apiPost, type EvidencePayload, type InventoryPayload, type OverviewPayload, type ProcurementPayload, type SystemStatusPayload } from "@/components/api-client";
import { DecisionDetail } from "@/components/decision-detail";
import { DecisionsScreen, EvidenceScreen, InventoryScreen, ProcurementScreen, SystemStatusScreen } from "@/components/operations-screens";
import { OverviewScreen } from "@/components/overview-screen";

export type Section = "Overview" | "Decisions" | "Inventory" | "Procurement" | "Evidence" | "System Status";

const navigation: { name: Section; icon: string }[] = [
  { name: "Overview", icon: "OV" },
  { name: "Decisions", icon: "DQ" },
  { name: "Inventory", icon: "IN" },
  { name: "Procurement", icon: "PR" },
  { name: "Evidence", icon: "EV" },
  { name: "System Status", icon: "SY" },
];

export function DecisionOSApp() {
  const [section, setSection] = useState<Section>("Overview");
  const [decisionRows, setDecisionRows] = useState<Decision[]>(decisions);
  const [activeDecision, setActiveDecision] = useState<Decision>(decisions[0]);
  const [inventoryData, setInventoryData] = useState(inventoryRows);
  const [supplierData, setSupplierData] = useState(suppliers);
  const [sourceData, setSourceData] = useState(sources);
  const [alerts, setAlerts] = useState<Record<string, unknown>[]>([]);
  const [summary, setSummary] = useState<OverviewPayload["summary"]>();
  const [pipelineData, setPipelineData] = useState<SystemStatusPayload["pipeline"]>([]);
  const [requiredQuantity, setRequiredQuantity] = useState<number | null>(5200);
  const [procurementMedicine, setProcurementMedicine] = useState("Amoxicillin 500mg");
  const [referencePrice, setReferencePrice] = useState("Unavailable");
  const [backendConnected, setBackendConnected] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [apiError, setApiError] = useState("");
  const [lastAnalysis, setLastAnalysis] = useState("Unknown");
  const [notice, setNotice] = useState("");
  const [reviewed, setReviewed] = useState<string[]>([]);
  const [analysisRunning, setAnalysisRunning] = useState(false);
  const [reviewPending, setReviewPending] = useState<{ id: string; action: "approved" | "rejected" } | null>(null);

  async function refreshBackendData() {
    try {
      const [overview, decisionsFromApi, inventory, procurement, evidence, system] = await Promise.all([
      apiGet<OverviewPayload>("overview"),
      apiGet<Decision[]>("decisions"),
      apiGet<InventoryPayload>("inventory"),
      apiGet<ProcurementPayload>("procurement"),
      apiGet<EvidencePayload>("evidence"),
      apiGet<SystemStatusPayload>("system-status"),
      ]);
      setDecisionRows(decisionsFromApi);
      setActiveDecision((current) => decisionsFromApi.find((decision) => decision.id === current.id) ?? decisionsFromApi[0] ?? current);
      setInventoryData(inventory.rows);
      setSupplierData(procurement.suppliers);
      setProcurementMedicine(procurement.medicine);
      setRequiredQuantity(procurement.requiredQuantity);
      setReferencePrice(procurement.referencePrice);
      setSourceData(evidence.sources);
      setAlerts(evidence.alerts);
      setSummary(overview.summary);
      setPipelineData(system.pipeline);
      setLastAnalysis(system.lastAnalysis ?? "No completed scan");
      setBackendConnected(true);
      setApiError("");
    } catch (error) {
      setBackendConnected(false);
      setApiError(error instanceof Error ? error.message : "The DecisionOS API could not be reached.");
      throw error;
    }
  }

  useEffect(() => {
    void refreshBackendData().catch(() => undefined).finally(() => setInitialLoading(false));
  }, []);

  const openDecision = async (decision: Decision) => {
    setActiveDecision(decision);
    setSection("Decisions");
    if (!backendConnected) return;
    try {
      const detail = await apiGet<Decision>(`decisions/${encodeURIComponent(decision.id)}`);
      setActiveDecision(detail);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Could not load the decision dossier.");
    }
  };

  const flashNotice = (message: string) => {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 4200);
  };

  const runAnalysis = async () => {
    setAnalysisRunning(true);
    try {
      if (!backendConnected) throw new Error("FastAPI is unavailable. Showing the offline synthetic dataset; no scan was run.");
      const result = await apiPost<{ candidatesDetected: number; decisionsProcessed: number }>("analysis/run");
      await refreshBackendData();
      flashNotice(`Analysis complete: ${result.candidatesDetected} candidates processed and independently verified.`);
    } catch (error) {
      flashNotice(error instanceof Error ? error.message : "Analysis request failed.");
    } finally {
      setAnalysisRunning(false);
    }
  };

  const markReviewed = async (decision: Decision, action: "approved" | "rejected") => {
    setReviewPending({ id: decision.id, action });
    try {
      if (!backendConnected) throw new Error("FastAPI is unavailable. Review was not recorded.");
      const route = action === "approved" ? "approve" : "reject";
      const result = await apiPost<{ message: string }>(`decisions/${encodeURIComponent(decision.id)}/${route}`, {});
      setReviewed((current) => [...current.filter((item) => item !== decision.id), `${decision.id}:${action}`]);
      await refreshBackendData();
      flashNotice(result.message);
    } catch (error) {
      flashNotice(error instanceof Error ? error.message : "Review request failed.");
    } finally {
      setReviewPending(null);
    }
  };

  const analysisTime = lastAnalysis === "Unknown" || lastAnalysis === "No completed scan"
    ? lastAnalysis
    : new Date(lastAnalysis).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", hour12: false }) + " IST";

  return (
    <div className="app-frame">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark">D<span>O</span></div>
          <div className="brand-name">DecisionOS <span>OPERATIONS CONTROL</span></div>
        </div>
        <nav className="main-nav" aria-label="Main navigation">
          {navigation.map((item) => (
            <button className={`nav-item ${section === item.name ? "is-active" : ""}`} key={item.name} onClick={() => setSection(item.name)}>
              <span className="nav-code">{item.icon}</span>{item.name}
            </button>
          ))}
        </nav>
        <div className="topbar-status">
          <span className={`live-marker ${backendConnected ? "" : "status-square"}`} />
          <span>{backendConnected ? "API CONNECTED" : "OFFLINE FALLBACK"}</span>
          <span className="topbar-divider" />
          <span>Last analysis <b>{analysisTime}</b></span>
        </div>
      </header>

      <div className="pipeline-bar">
        <div className="pipeline-label">AUTONOMOUS DETECTION</div>
        {(["ANALYZE", "SIMULATE", "DECIDE", "VERIFY", "HUMAN REVIEW"] as const).map((stage, index) => (
          <div className={`pipeline-step pipeline-step-${index}`} key={stage}>
            {index > 0 && <span className="pipeline-arrow">›</span>}<span>{stage}</span>
          </div>
        ))}
        <span className="pipeline-right">Human approval required for consequential action</span>
      </div>

      <main className="workspace">
        {initialLoading ? <div className="panel" role="status">Connecting to the DecisionOS API…</div> : <>
        {apiError && <div className="notice-line" role="alert"><b>API request failed</b><span>{apiError}. {backendConnected ? "Showing the last successfully loaded database records." : "Showing the labeled offline synthetic fallback."}</span></div>}
        {section === "Overview" && <OverviewScreen onOpenDecision={openDecision} onNavigate={setSection} onDemoScan={runAnalysis} scanPending={analysisRunning} sourceData={sourceData} summary={summary} alertData={alerts} lastAnalysis={analysisTime} decisionRows={decisionRows} />}
        {section === "Decisions" && <DecisionsScreen activeDecision={activeDecision} onOpenDecision={openDecision} reviewed={reviewed} decisionRows={decisionRows} />}
        {section === "Inventory" && <InventoryScreen onOpenDecision={openDecision} inventoryData={inventoryData} decisionData={decisionRows} />}
        {section === "Procurement" && <ProcurementScreen supplierData={supplierData} medicineName={procurementMedicine} requiredQuantity={requiredQuantity} referencePrice={referencePrice} decisionData={decisionRows} />}
        {section === "Evidence" && <EvidenceScreen sourceData={sourceData} alertData={alerts} />}
        {section === "System Status" && <SystemStatusScreen sourceData={sourceData} backendConnected={backendConnected} lastAnalysis={analysisTime} pipelineData={pipelineData} />}
        {section === "Decisions" && activeDecision && <DecisionDetail decision={activeDecision} onNavigate={setSection} onReview={markReviewed} reviewed={reviewed} reviewPending={reviewPending?.id === activeDecision.id ? reviewPending.action : null} sourceData={sourceData} />}
        </>}
      </main>

      <footer className="app-footer">
        <span>DECISIONOS · PHARMACEUTICAL SUPPLY-CHAIN DECISION SYSTEM</span>
        <span>{backendConnected ? "Database-backed records · synthetic seed data clearly labeled" : "Offline fallback · all displayed records are synthetic client demo data"}</span>
      </footer>
      {notice && <div className="toast" role="status">{notice}</div>}
    </div>
  );
}