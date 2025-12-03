// src/Summary.jsx
import React, { useState, useEffect } from "react";
import { getAccounts, getPurchies, deletePurchy, updatePurchy } from "./Api"; // updatePurchy added

export default function Summary() {
  const [accounts, setAccounts] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState("ALL");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState([]);
  const [totals, setTotals] = useState({ total_weight: 0, total_amount: 0 });
  const [message, setMessage] = useState("");
  const [editOpen, setEditOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [editValues, setEditValues] = useState({});
  const [initialValues, setInitialValues] = useState({});

  // Load accounts for the dropdown (safe)
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const data = await getAccounts();
        // your getAccounts returns an array — fall back safely
        const arr = Array.isArray(data) ? data : data?.data || [];
        if (mounted) setAccounts(arr);
      } catch (err) {
        console.error("Failed to load accounts:", err);
        // keep accounts empty (ALL still works)
      }
    })();
    return () => (mounted = false);
  }, []);

  async function fetchPurchies() {
    setMessage("");
    setLoading(true);
    setItems([]);
    setTotals({ total_weight: 0, total_amount: 0 });
    try {
      const payload = { account_id: selectedAccount || "ALL" };
      if (fromDate) payload.from = fromDate;
      if (toDate) payload.to = toDate;

      const data = await getPurchies(payload);
      const safeItems = Array.isArray(data.items) ? data.items : [];
      // Sort by purchy_date ascending
      safeItems.sort((a, b) => {
        const dateA = new Date(a.purchy_date || "");
        const dateB = new Date(b.purchy_date || "");
        return dateA - dateB;
      });
      setItems(safeItems);
      setTotals({
        total_weight: data.total_weight ?? 0,
        total_amount: data.total_amount ?? 0,
      });
      if (safeItems.length === 0) setMessage("No purchies found for the selected filters.");
    } catch (err) {
      console.error("Error fetching purchies:", err);
      setMessage("❌ Failed to fetch purchies");
    } finally {
      setLoading(false);
    }
  }

  function exportCsv() {
    if (!items || items.length === 0) {
      alert("No rows to export");
      return;
    }

    const headers = ["Date", "Purchy Number", "Account", "Weight", "Rate", "Amount", "Purchy TS"];
    const escapeCell = (v) => {
      if (v === null || v === undefined) return "";
      const s = String(v);
      if (s.includes('"')) return '"' + s.replace(/"/g, '""') + '"';
      if (s.includes(",") || s.includes("\n") || s.includes("\r")) return '"' + s + '"';
      return s;
    };

    const rows = items.map((p) => {
      const amount = p.amount ?? (p.weight != null && p.rate != null ? Number(p.weight) * Number(p.rate) : "");
      return [p.purchy_date || "", p.purchy_id ?? "", p.account_name || p.account_id || "", p.weight ?? "", p.rate ?? "", amount, p.purchy_ts || ""];
    });

    const csvLines = [headers.map(escapeCell).join(',')].concat(rows.map(r => r.map(escapeCell).join(',')));
    const csvContent = csvLines.join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    // Build filename: purchies_<Account>_YYYY-MM-DD.csv
    let accountLabel = "ALL";
    if (selectedAccount && selectedAccount !== "ALL") {
      const acct = (accounts || []).find((a) => a.account_id === selectedAccount);
      accountLabel = acct ? acct.account_name : selectedAccount;
    }
    // sanitize and normalize
    accountLabel = String(accountLabel)
      .trim()
      .replace(/\s+/g, "_")
      .replace(/[^A-Za-z0-9_\-]/g, "");
    const filename = `Purchies_${accountLabel}_${new Date().toISOString().slice(0,10)}.csv`;
    a.href = url;
    a.setAttribute('download', filename);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async function handleDelete(accId, ts) {
    if (!accId || !ts) return alert("Missing keys for delete");
    if (!window.confirm("Delete this purchy?")) return;
    try {
      await deletePurchy(accId, ts);
      // refresh list
      await fetchPurchies();
    } catch (err) {
      console.error("Delete failed:", err);
      alert("Failed to delete purchy");
    }
  }

  function openEdit(p) {
    const vals = {
      purchy_date: p.purchy_date || "",
      weight: p.weight ?? "",
      purchy_id: p.purchy_id ?? "",
      account_id: p.account_id || "",
    };
    setEditItem(p);
    setEditValues(vals);
    setInitialValues(vals);
    setEditOpen(true);
  }

  function closeEdit() {
    setEditOpen(false);
    setEditItem(null);
    setEditValues({});
    setInitialValues({});
  }

  async function handleSaveEdit() {
    if (!editItem) return;
    // compare initial vs current
    const changed = {};
    if ((editValues.purchy_date || "") !== (initialValues.purchy_date || "")) changed.purchy_date = editValues.purchy_date;
    if ((String(editValues.weight) || "") !== (String(initialValues.weight) || "")) changed.weight = editValues.weight;
      if ((String(editValues.purchy_id) || "") !== (String(initialValues.purchy_id) || "")) changed.purchy_id = editValues.purchy_id;
      if ((editValues.account_id || "") !== (initialValues.account_id || "")) changed.new_account_id = editValues.account_id;

    if (Object.keys(changed).length === 0) {
      alert("Please change at least one value before saving.");
      return;
    }

    try {
      setLoading(true);
      // call the API stub
      await updatePurchy(editItem.account_id, editItem.purchy_ts, changed);
      closeEdit();
      await fetchPurchies();
    } catch (err) {
      console.error("Update failed:", err);
      alert("Failed to update purchy");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h2 className="section-title">Purchy Summary</h2>

      <div className="field" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        <div style={{ display: "flex", gap: "12px", alignItems: "flex-end" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1 }}>
            <label style={{ fontSize: "13px", color: "#475569", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.5px" }}>Account</label>
            <select value={selectedAccount} onChange={(e) => setSelectedAccount(e.target.value)}>
              <option value="ALL">ALL</option>
              {(accounts || []).map((a) => (
                <option key={a.account_id} value={a.account_id}>
                  {a.account_name}
                </option>
              ))}
            </select>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button className="btn-primary" onClick={fetchPurchies} disabled={loading} style={{ marginTop: "0", flex: 0, minWidth: "90px" }}>
              {loading ? "Fetching..." : "Fetch"}
            </button>
            <button className="btn-secondary" onClick={exportCsv} disabled={loading || !items || items.length === 0} style={{ marginTop: 0, flex: 0 }}>
              Export CSV
            </button>
          </div>
        </div>

        <div style={{ display: "flex", gap: "12px", alignItems: "flex-end" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1 }}>
            <label style={{ fontSize: "13px", color: "#475569", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.5px" }}>From</label>
            <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1 }}>
            <label style={{ fontSize: "13px", color: "#475569", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.5px" }}>To</label>
            <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} />
          </div>
        </div>
      </div>

      {message && <p className="message">{message}</p>}

      <div style={{ marginTop: 16, padding: "12px 14px", background: "#ecfdf5", borderRadius: "12px", border: "1px solid #a7f3d0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <p style={{ fontSize: "12px", color: "#047857", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.5px", margin: "0 0 4px 0" }}>Total Weight</p>
          <p style={{ fontSize: "18px", fontWeight: "800", color: "#047857", margin: 0 }}>{totals.total_weight}</p>
        </div>
        <div style={{ textAlign: "right" }}>
          <p style={{ fontSize: "12px", color: "#047857", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.5px", margin: "0 0 4px 0" }}>Total Amount</p>
          <p style={{ fontSize: "18px", fontWeight: "800", color: "#047857", margin: 0 }}>{totals.total_amount}</p>
        </div>
      </div>

      <div style={{ marginTop: 12, overflowX: "auto" }}>
        <table className="summary-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Purchy Number</th>
              <th>Account</th>
              <th>Weight</th>
              <th>Rate</th>
              <th>Amount</th>
              <th>Action</th>
            </tr>
          </thead>

          <tbody>
            {(items || []).map((p) => (
              <tr key={`${p.account_id}#${p.purchy_ts}`}>
                <td>{p.purchy_date}</td>
                <td>{p.purchy_id ?? "-"}</td>
                <td>{p.account_name}</td>
                <td>{p.weight ?? "-"}</td>
                <td>{p.rate ?? "-"}</td>
                <td>
                  {p.amount ?? (p.weight != null && p.rate != null ? Number(p.weight) * Number(p.rate) : "-")}
                </td>
                <td>
                  <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
                    <button className="btn-secondary" onClick={() => openEdit(p)}>
                      Edit
                    </button>
                    <button className="delete-btn" onClick={() => handleDelete(p.account_id, p.purchy_ts)}>
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {/* Edit modal */}
      {editOpen && editItem && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ width: "92%", maxWidth: 520, background: "var(--surface)", borderRadius: 12, padding: 18, boxShadow: "0 12px 40px rgba(2,6,23,0.4)" }}>
            <h3 style={{ marginTop: 0 }}>Edit Purchy</h3>

            <div className="field">
                <span>Account</span>
                <select value={editValues.account_id} onChange={(e) => setEditValues((s) => ({ ...s, account_id: e.target.value }))}>
                  {(accounts || []).map((a) => (
                    <option key={a.account_id} value={a.account_id}>{a.account_name}</option>
                  ))}
                </select>
            </div>

            <div className="field">
              <span>Date</span>
              <input type="date" value={editValues.purchy_date} onChange={(e) => setEditValues((s) => ({ ...s, purchy_date: e.target.value }))} />
            </div>

            <div style={{ display: "flex", gap: 12 }}>
              <div style={{ flex: 1 }} className="field">
                <span>Weight</span>
                <input type="number" value={editValues.weight} onChange={(e) => setEditValues((s) => ({ ...s, weight: e.target.value }))} />
              </div>
              <div style={{ flex: 1 }} className="field">
                <span>Purchy Number</span>
                <input type="text" value={editValues.purchy_id} onChange={(e) => setEditValues((s) => ({ ...s, purchy_id: e.target.value }))} />
              </div>
            </div>

            

            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
              <button className="btn-primary" onClick={handleSaveEdit} disabled={loading}>{loading ? "Saving..." : "Save"}</button>
              <button onClick={closeEdit} style={{ padding: "10px 14px", borderRadius: 10, background: "transparent", border: "1px solid rgba(15,23,42,0.08)" }}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

