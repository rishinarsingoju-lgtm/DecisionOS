from typing import Any

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HealthResponse(ApiModel):
    status: str
    database: str
    version: str


class DecisionActionRow(ApiModel):
    action: str
    loss: str
    stockout: str
    cost: str
    impact: str
    recommendation: bool


class AuditRow(ApiModel):
    id: int
    time: str
    actor: str
    event: str


class DecisionView(ApiModel):
    id: str
    candidateId: str
    medicine: str
    sku: str
    location: str
    region: str
    priority: str
    status: str
    trigger: str
    whyItMatters: str
    recommendation: str
    impact: str
    expiryLoss: str
    stockoutRisk: str
    demand: str
    disease: str
    seasonality: str
    inventory: str
    expiry: str
    leadTime: str
    weather: str
    verificationAi: str
    verificationIndependent: str
    verificationNote: str
    updated: str
    approvalStatus: str
    dataOrigin: str
    actions: list[DecisionActionRow]
    auditEvents: list[AuditRow]
    evidenceItems: list[dict[str, Any]]
    analysis: dict[str, Any]
    simulations: list[dict[str, Any]]
    selectedAction: dict[str, Any] | None
    expectedImpact: dict[str, Any]
    verification: dict[str, Any]
    audit: list[dict[str, Any]]


class OverviewSummary(ApiModel):
    decisionsRequiringAttention: int
    criticalDecisions: int
    emergingRisks: int
    verifiedDecisions: int
    potentialImpact: str


class OverviewResponse(ApiModel):
    summary: OverviewSummary
    decisions: list[DecisionView]
    recentDecisions: list[DecisionView]
    alerts: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    systemStatus: dict[str, Any]


class InventoryRow(ApiModel):
    medicine: str
    batch: str
    location: str
    available: str
    demand: str
    cover: str
    expiry: str
    status: str
    medicineId: int
    locationId: int
    dataOrigin: str


class InventoryResponse(ApiModel):
    rows: list[InventoryRow]
    dataOrigin: str


class SupplierView(ApiModel):
    id: int
    name: str
    price: str
    priceValue: float
    quality: str
    qualityValue: float | None
    reliability: str
    reliabilityValue: float | None
    lead: str
    leadDays: int | None
    availability: str
    availabilityValue: float | None
    evidence: str
    tradeoff: str
    status: str
    sampleSize: int


class ProcurementResponse(ApiModel):
    medicine: str
    medicineId: int
    requiredQuantity: int | None
    referencePrice: str
    suppliers: list[SupplierView]
    dataOrigin: str


class EvidenceResponse(ApiModel):
    sources: list[dict[str, Any]]
    alerts: list[dict[str, Any]]


class SystemStatusResponse(ApiModel):
    status: str
    monitoring: str
    lastAnalysis: str | None
    deterministicOnly: bool
    pipeline: list[dict[str, str]]
    sources: list[dict[str, Any]]


class AnalysisRunResponse(ApiModel):
    candidatesDetected: int
    decisionsProcessed: int
    decisions: list[DecisionView]


class ReviewRequest(ApiModel):
    comment: str | None = None


class ReviewResponse(ApiModel):
    id: str
    verificationStatus: str
    approvalStatus: str
    message: str