export type Market = "A" | "H";

export interface Listing {
  market: Market;
  code: string;
  exchange?: "SSE" | "SZSE" | "HKEX";
  name: string;
  peTtm: number | null;
  peAsOf: string | null;
}

export interface AnnualFinancial {
  year: number;
  currency: string;
  revenue: number | null;
  revenueYoY: number | null;
  netProfit: number | null;
  netProfitYoY: number | null;
  grossMargin: number | null;
  roe: number | null;
  operatingCashFlow: number | null;
  debtRatio: number | null;
}

export interface Company {
  id: string;
  name: string;
  nodeIds: string[];
  screenshotSlots: number;
  listings: Listing[];
  financials: AnnualFinancial[];
  status: "ok" | "partial" | "unresolved";
  auditNotes: string[];
}

export interface ChainNode {
  id: string;
  chainId: string;
  name: string;
  stage: string;
  description: string;
  coreProducts: string;
  valuePosition: string;
  upstream: string;
  downstream: string;
  companies: string[];
  auditNote?: string;
}

export interface SourceRecord {
  id: string;
  name: string;
  url: string;
  role: string;
}
