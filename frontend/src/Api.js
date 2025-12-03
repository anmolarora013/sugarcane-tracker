const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;//process.env.API_BASE_URL;

async function safeFetch(url, opts = {}) {
  const res = await fetch(url, opts);
  const text = await res.text();

  // Try to parse JSON, but don't fail if parsing fails for successful responses.
  let json = null;
  try {
    if (text) json = JSON.parse(text);
  } catch (e) {
    // If response is NOT ok, we want to include the body in the error.
    if (!res.ok) {
      // Include the raw text in the thrown error for debugging.
      const err = new Error(`HTTP ${res.status}: ${text}`);
      err.status = res.status;
      err.bodyText = text;
      throw err;
    }
    // If response was ok (2xx) and body isn't valid JSON, just return null below.
    json = null;
  }

  if (!res.ok) {
    const msg = (json && json.message) ? json.message : `HTTP ${res.status}`;
    const err = new Error(msg);
    err.status = res.status;
    err.body = json || text;
    throw err;
  }

  return json;
}

/* Accounts */
export async function getAccounts() {
  return safeFetch(`${API_BASE_URL}/accounts`);
}

export async function addAccount(accountData) {
  return safeFetch(`${API_BASE_URL}/accounts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(accountData),
  });
}

/* Purchy add */
export async function addPurchy(purchy) {
  return safeFetch(`${API_BASE_URL}/purchies`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(purchy),
  });
}

/* Delete purchy */
export async function deletePurchy(account_id, purchy_ts) {
  if (!account_id || !purchy_ts) {
    throw new Error("account_id and purchy_ts are required");
  }
  const url = `${API_BASE_URL}/purchies?account_id=${encodeURIComponent(account_id)}&purchy_ts=${encodeURIComponent(purchy_ts)}`;
  return safeFetch(url, { method: "DELETE" });
}

/* Get purchies with optional filters */
export async function getPurchies({ account_id = "ALL", from, to } = {}) {
  const params = new URLSearchParams();
  params.set("account_id", account_id || "ALL");
  if (from) params.set("from", from);
  if (to) params.set("to", to);
  const url = `${API_BASE_URL}/purchies?${params.toString()}`;
  return safeFetch(url);
}

/* Update purchy - stub (dummy URL / payload). The user will integrate real endpoint later. */
export async function updatePurchy(account_id, purchy_ts, updates = {}) {
  if (!account_id || !purchy_ts) throw new Error("account_id and purchy_ts are required");
  const url = `${API_BASE_URL}/purchies`;
  const payload = { account_id, purchy_ts, ...updates };
  return safeFetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
