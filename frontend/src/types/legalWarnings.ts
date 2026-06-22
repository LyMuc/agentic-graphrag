export interface ExpiredValidityRow {
  basis_id: string;
  basis_name: string;
  expiry_date: string;
  replacement_id?: string | null;
  replacement_name: string;
  replacement_effective_date: string;
  replacement_content_url?: string | null;
}

export interface FutureValidityRow {
  source_id: string;
  basis_name: string;
  issued_date: string;
  effective_date: string;
  impact_type: string;
  impacted_basis_id: string;
  impacted_basis_name: string;
  content_url?: string | null;
}

export interface ConflictProvisionRef {
  id: string;
  name: string;
}

export interface ConflictDetailBlock {
  id: string;
  name: string;
  content: string;
}

export interface ConflictWarningItem {
  provisions: ConflictProvisionRef[];
  summary: string;
  details: ConflictDetailBlock[];
}

export interface ValidityWarningPayload {
  expired_rows?: ExpiredValidityRow[];
  future_rows?: FutureValidityRow[];
}

export interface ConflictWarningPayload {
  items: ConflictWarningItem[];
}

export interface LegalWarningsMetadata {
  validity?: ValidityWarningPayload;
  conflict?: ConflictWarningPayload;
}

export function parseLegalWarnings(
  metadata: Record<string, unknown> | undefined | null
): LegalWarningsMetadata | null {
  if (!metadata || typeof metadata !== 'object') {
    return null;
  }
  const raw = metadata.legal_warnings;
  if (!raw || typeof raw !== 'object') {
    return null;
  }
  return raw as LegalWarningsMetadata;
}
