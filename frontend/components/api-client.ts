export const API_BASE = process.env.NEXT_PUBLIC_DECISIONOS_API_URL ?? (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "");

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}/api/${path}`, { cache: "no-store" });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `API request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, payload: unknown = {}): Promise<T> {
  const response = await fetch(`${API_BASE}/api/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `API request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export type OverviewPayload = {
  summary: {
    decisionsRequiringAttention: number;
    criticalDecisions: number;
    emergingRisks: number;
    verifiedDecisions: number;
    potentialImpact: string;
  };
  decisions: import("@/data/mock-data").Decision[];
  recentDecisions: import("@/data/mock-data").Decision[];
  alerts: Record<string, unknown>[];
  sources: typeof import("@/data/mock-data").sources;
  systemStatus: { status: string; lastAnalysis: string | null };
};

export type InventoryPayload = { rows: typeof import("@/data/mock-data").inventoryRows; dataOrigin: string };
export type ProcurementPayload = {
  medicine: string;
  medicineId: number;
  requiredQuantity: number | null;
  referencePrice: string;
  suppliers: typeof import("@/data/mock-data").suppliers;
};
export type EvidencePayload = { sources: typeof import("@/data/mock-data").sources; alerts: Record<string, unknown>[] };
export type SystemStatusPayload = {
  status: string;
  monitoring: string;
  lastAnalysis: string | null;
  deterministicOnly: boolean;
  pipeline: { name: string; status: string }[];
};
