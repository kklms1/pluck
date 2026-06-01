/** 숫자/통화 포맷 + props 타입 */

export type CareerPoint = {
  career_year: number;
  grade: string;
  hobong: number;
  annual_gross_10k: number;
  monthly_gross_10k: number;
  monthly_net_10k: number;
  tax_rate_pct: number;
  insurance_10k?: number;
  income_tax_10k?: number;
  // 항목별 명세 (만원/월)
  base_salary_10k?: number;
  fixed_allow_10k?: number;
  perform_allow_10k?: number;
  welfare_10k?: number;
  bonus_10k?: number;
  monthly_regular_net_10k?: number;
};

export type DeepDiveProps = {
  company: string;
  brandColor: string;
  career: CareerPoint[];
  asset?: { total_assets_100m?: number; asset_rank?: number };
  blind?: {
    overall?: number;
    salary_benefit?: number;
    work_life?: number;
    culture?: number;
    review_count?: number;
  };
  location?: {
    region?: string;
    hq_address?: string;
    relocated?: boolean;
    innovation_city?: string;
    rotation?: string;
    rotation_note?: string;
    branch_scope?: string;
  };
  welfare?: { total_per_person_10k?: number };
};

/** 만원 → "1.08억" / "4,200만" 자연어 */
export function won(man: number): string {
  const v = Math.round(man);
  if (v >= 10000) {
    const eok = v / 10000;
    const s = eok.toFixed(2).replace(/\.00$/, "").replace(/0$/, "");
    return `${s}억`;
  }
  return `${v.toLocaleString()}만`;
}

export function comma(n: number): string {
  return Math.round(n).toLocaleString();
}

/** 만원(float) → "3,157,000" 원 단위 표기 (천원 반올림) */
export function manToWon(man: number): string {
  const won = Math.round((man * 10000) / 1000) * 1000;
  return won.toLocaleString();
}
