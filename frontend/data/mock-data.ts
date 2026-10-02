export type VerificationStatus = "VERIFIED" | "WITHHELD" | "INSUFFICIENT_EVIDENCE";

export type Decision = {
  id: string;
  medicine: string;
  sku: string;
  location: string;
  region: string;
  priority: string;
  status: VerificationStatus;
  trigger: string;
  whyItMatters: string;
  recommendation: string;
  impact: string;
  expiryLoss: string;
  stockoutRisk: string;
  demand: string;
  disease: string;
  seasonality: string;
  inventory: string;
  expiry: string;
  leadTime: string;
  weather: string;
  verificationAi: string;
  verificationIndependent: string;
  verificationNote: string;
  updated: string;
  candidateId?: string;
  approvalStatus?: string;
  dataOrigin?: string;
  actions?: { action: string; loss: string; stockout: string; cost: string; impact: string; recommendation: boolean }[];
  auditEvents?: { id?: number; time: string; actor: string; event: string }[];
  evidenceItems?: { type?: string; source_ref?: string; data_origin?: string; freshness?: string; summary?: string; source_url?: string }[];
  analysis?: Record<string, unknown>;
  simulations?: Record<string, unknown>[];
  selectedAction?: Record<string, unknown> | null;
  expectedImpact?: Record<string, unknown>;
  verification?: {
    status?: string;
    claims?: { claim: string; ai_calculation: string | number | null; independent_recomputation: string | number | null; status: string }[];
    [key: string]: unknown;
  };
  audit?: Record<string, unknown>[];
};

export const decisions: Decision[] = [
  {
    id: "DEC-2025-0842",
    medicine: "Azithromycin 500mg",
    sku: "AZ-500-TAB",
    location: "Hyderabad Central Depot",
    region: "Telangana",
    priority: "CRITICAL",
    status: "VERIFIED",
    trigger: "3,100 units in batch AZ-9021 reach expiry in 42 days while feeder depots are trending toward a stockout.",
    whyItMatters: "Without a transfer, projected expiry exposure is ₹4.82L. Warangal and Nizamabad together may run short before standard replenishment arrives.",
    recommendation: "Redistribute 1,800 units to Warangal and Nizamabad; prioritize FEFO for the remaining Hyderabad stock.",
    impact: "₹3.10L expiry loss avoided; feeder stockout risk falls from 31% to 8%.",
    expiryLoss: "₹4.82L",
    stockoutRisk: "31% → 8%",
    demand: "+18.4%",
    disease: "High · ILI cluster",
    seasonality: "1.24× baseline",
    inventory: "12,400 units",
    expiry: "3,100 units · 42 days",
    leadTime: "9 days",
    weather: "+64 mm precipitation",
    verificationAi: "₹3,10,400 avoided",
    verificationIndependent: "₹3,10,400 avoided",
    verificationNote: "Independent recomputation matched across 4 critical claims.",
    updated: "09:42 IST",
  },
  {
    id: "DEC-2025-0847",
    medicine: "Amoxicillin 500mg",
    sku: "AMX-500-CAP",
    location: "Bengaluru Regional Hub",
    region: "Karnataka",
    priority: "CRITICAL",
    status: "WITHHELD",
    trigger: "Forecast demand exceeds available stock before the standard supplier lead time completes.",
    whyItMatters: "Projected 5,200-unit deficit could affect 38 clinics. Supplier quote and demand snapshot disagree on the evaluated quantity.",
    recommendation: "No released recommendation. Resolve the demand snapshot mismatch and rerun independent verification.",
    impact: "Potential 5,200-unit shortfall in 6 days; impact estimate withheld pending verification.",
    expiryLoss: "₹0.84L",
    stockoutRisk: "38% → withheld",
    demand: "+26.1%",
    disease: "Elevated · ARI cases",
    seasonality: "1.16× baseline",
    inventory: "8,600 units",
    expiry: "620 units · 71 days",
    leadTime: "9 days",
    weather: "Unavailable · source stale",
    verificationAi: "₹1,82,000 / 5,200 units",
    verificationIndependent: "₹1,64,500 / 4,700 units",
    verificationNote: "Mismatch detected. Recommendation withheld; no action is approved for dispatch.",
    updated: "09:38 IST",
  },
  {
    id: "DEC-2025-0839",
    medicine: "Cefixime 200mg",
    sku: "CFX-200-TAB",
    location: "Vijayawada Distribution Centre",
    region: "Andhra Pradesh",
    priority: "HIGH",
    status: "VERIFIED",
    trigger: "Rising regional demand overlaps with an uneven depot inventory position.",
    whyItMatters: "Rebalancing inventory now preserves coverage without triggering an unnecessary purchase order.",
    recommendation: "Transfer 740 units from Guntur to Vijayawada and apply FEFO sequencing.",
    impact: "Estimated 11-day coverage restored; no additional procurement required.",
    expiryLoss: "₹0.32L",
    stockoutRisk: "19% → 6%",
    demand: "+11.2%",
    disease: "Moderate · fever cluster",
    seasonality: "1.08× baseline",
    inventory: "5,240 units",
    expiry: "310 units · 88 days",
    leadTime: "7 days",
    weather: "Matched · Open-Meteo",
    verificationAi: "740 units transferred",
    verificationIndependent: "740 units transferred",
    verificationNote: "Independent recomputation matched across 3 critical claims.",
    updated: "08:56 IST",
  },
];

export const inventoryRows = [
  { medicine: "Azithromycin 500mg", batch: "AZ-9021", location: "Hyderabad Central", available: "12,400", demand: "286 / day", cover: "43 days", expiry: "High · 3,100 units", status: "Action required" },
  { medicine: "Amoxicillin 500mg", batch: "AMX-4482", location: "Bengaluru Regional", available: "8,600", demand: "1,420 / day", cover: "6 days", expiry: "Low · 620 units", status: "Stockout risk" },
  { medicine: "Cefixime 200mg", batch: "CFX-1820", location: "Vijayawada DC", available: "5,240", demand: "318 / day", cover: "16 days", expiry: "Low · 310 units", status: "Monitor" },
  { medicine: "Metformin 500mg", batch: "MET-7093", location: "Chennai Central", available: "21,800", demand: "760 / day", cover: "29 days", expiry: "None · 0 units", status: "Within range" },
  { medicine: "ORS Sachet", batch: "ORS-3116", location: "Warangal Feeder", available: "3,980", demand: "244 / day", cover: "16 days", expiry: "Watch · 420 units", status: "Monitor" },
  { medicine: "Paracetamol 650mg", batch: "PCM-8814", location: "Hyderabad Central", available: "18,200", demand: "920 / day", cover: "20 days", expiry: "None · 0 units", status: "Within range" },
];

export const suppliers = [
  { name: "Asterion Pharma Ltd.", price: "₹2.84 / cap", quality: "98.7% · 3 lots", reliability: "96% · 24 orders", lead: "7 days", availability: "6,000 units", evidence: "3 quality records", tradeoff: "Lowest quoted price; medium lead-time variability", status: "Known" },
  { name: "Medline Therapeutics", price: "₹2.96 / cap", quality: "99.4% · 8 lots", reliability: "98% · 42 orders", lead: "5 days", availability: "4,500 units", evidence: "8 quality records", tradeoff: "Strongest observed quality and reliability; higher unit cost", status: "Known" },
  { name: "Northstar Remedies", price: "₹2.71 / cap", quality: "Unknown", reliability: "Unknown", lead: "11 days est.", availability: "2,000 units est.", evidence: "No completed orders", tradeoff: "Lowest indicative price, but limited supplier history; evidence insufficient", status: "Limited evidence" },
];

export const sources = [
  { name: "WHO ICD", purpose: "Disease terminology normalization", status: "Available", detail: "Synced 08:55 IST", kind: "matched" },
  { name: "Open-Meteo", purpose: "Weather context for demand signals", status: "Stale", detail: "Last successful pull 6h ago", kind: "stale" },
  { name: "CDSCO", purpose: "NSQ batch alerts", status: "Available", detail: "Snapshot matched · 09:12 IST", kind: "matched" },
  { name: "NPPA", purpose: "Reference price context", status: "Unavailable", detail: "Snapshot endpoint did not respond", kind: "unavailable" },
];

export const auditEvents = [
  { time: "09:42:18", actor: "Verifier · independent ledger replay", event: "Matched 4 critical claims; package marked VERIFIED." },
  { time: "09:42:16", actor: "Decision engine · deterministic", event: "FEFO + redistribution selected from 6 simulated actions." },
  { time: "09:42:11", actor: "Simulation engine · deterministic", event: "Compared expiry, stockout, and cost outcomes against baseline." },
  { time: "09:41:54", actor: "Detection scan · synthetic client data", event: "Expiry exposure and feeder demand imbalance exceeded thresholds." },
];

export const decisionActions = [
  { action: "Do nothing", loss: "₹4.82L", stockout: "31%", cost: "₹0", impact: "Baseline exposure remains", recommendation: false },
  { action: "Prioritize FEFO", loss: "₹3.96L", stockout: "29%", cost: "₹8,000", impact: "Reduces local expiry only", recommendation: false },
  { action: "Redistribute", loss: "₹1.72L", stockout: "8%", cost: "₹24,600", impact: "Moves surplus to feeder demand", recommendation: true },
  { action: "Reorder", loss: "₹4.82L", stockout: "16%", cost: "₹1.42L", impact: "New supply arrives after first risk window", recommendation: false },
  { action: "Change supplier", loss: "₹4.82L", stockout: "13%", cost: "₹1.86L", impact: "Faster replenishment at higher unit cost", recommendation: false },
  { action: "Split procurement", loss: "₹4.82L", stockout: "10%", cost: "₹1.57L", impact: "Diversifies supply; does not reduce current expiry", recommendation: false },
];