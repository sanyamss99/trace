export interface ApiKey {
  id: string;
  name: string | null;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export interface ApiKeyCreated {
  id: string;
  name: string | null;
  raw_key: string;
  created_at: string;
}
