import { useState, useEffect } from "react";
import { getAccounts, addAccount, addPurchy } from "./Api";
import "./App.css";
import Summary from "./Summary";

function App() {
  const [activeTab, setActiveTab] = useState("addPurchy");

  return (
    <div className="app">
      <h1 className="app-title">🧾 Sugarcane Purchy Tracker</h1>

      <div className="tabs">
        <button
          className={activeTab === "addPurchy" ? "tab active" : "tab"}
          onClick={() => setActiveTab("addPurchy")}
        >
          Add Purchy
        </button>
        <button
          className={activeTab === "addAccount" ? "tab active" : "tab"}
          onClick={() => setActiveTab("addAccount")}
        >
          Add Account
        </button>
        <button
          className={activeTab === "summary" ? "tab active" : "tab"}
          onClick={() => setActiveTab("summary")}
        >
          Summary
        </button>
      </div>

      <div className="card">
        {activeTab === "addAccount" ? (<AddAccountForm />) : activeTab === "addPurchy" ? (<AddPurchyForm />) : (<Summary />)}
      </div>
    </div>
  );
}

function AddAccountForm() {
  const [accountName, setAccountName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setMessage("");
    if (!accountName.trim()) {
      setMessage("Account name is required");
      return;
    }
    setLoading(true);
    try {
      await addAccount({
        account_name: accountName.trim(),
        description: description.trim() || undefined,
      });
      setMessage("✅ Account added successfully");
      setAccountName("");
      setDescription("");
    } catch (err) {
      console.error(err);
      setMessage("❌ Failed to add account");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2 className="section-title">Add Account</h2>

      <label className="field">
        <span>Account Name</span>
        <input
          type="text"
          value={accountName}
          onChange={(e) => setAccountName(e.target.value)}
          placeholder="e.g. Main Farm, Factory Account 1"
        />
      </label>

      <label className="field">
        <span>Description (optional)</span>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Any extra details"
          rows={3}
        />
      </label>

      <button type="submit" className="btn-primary" disabled={loading}>
        {loading ? "Saving..." : "Save Account"}
      </button>

      {message && <p className="message">{message}</p>}
    </form>
  );
}

function AddPurchyForm() {
  const [accounts, setAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState("");
  const [selectedAccountName, setSelectedAccountName] = useState("");

  const [date, setDate] = useState(() => {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, "0");
    const dd = String(today.getDate()).padStart(2, "0");
    return `${yyyy}-${mm}-${dd}`;
  });

  const [weight, setWeight] = useState("");
  const [purchyNumber, setPurchyNumber] = useState("");
  const [rate, setRate] = useState("");
  const [notes, setNotes] = useState("");

  const [loadingAccounts, setLoadingAccounts] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    async function fetchAccounts() {
      setLoadingAccounts(true);
      try {
        const data = await getAccounts();
        setAccounts(data || []);
        if (data && data.length > 0) {
          setSelectedAccountId(data[0].account_id);
          setSelectedAccountName(data[0].account_name);
        }
      } catch (err) {
        console.error(err);
        setMessage("❌ Failed to load accounts");
      } finally {
        setLoadingAccounts(false);
      }
    }
    fetchAccounts();
  }, []);

  function handleAccountChange(e) {
    const accountId = e.target.value;
    setSelectedAccountId(accountId);
    const acc = accounts.find((a) => a.account_id === accountId);
    setSelectedAccountName(acc ? acc.account_name : "");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setMessage("");

    if (!selectedAccountId) {
      setMessage("Please select an account");
      return;
    }
    if (!weight) {
      setMessage("Weight is required");
      return;
    }

    setSaving(true);
    try {
      const payload = {
        account_id: selectedAccountId,
        account_name: selectedAccountName,
        date,
        weight: parseFloat(weight),
        purchy_id: purchyNumber || undefined,
        rate: rate ? parseFloat(rate) : undefined,
        note: notes || undefined,
      };

      await addPurchy(payload);

      setMessage("✅ Purchy added successfully");
      setWeight("");
      setPurchyNumber("");
      //setRate("");
      setNotes("");
    } catch (err) {
      console.error(err);
      setMessage("❌ Failed to add purchy");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2 className="section-title">Add Purchy</h2>

      {loadingAccounts ? (
        <p>Loading accounts...</p>
      ) : accounts.length === 0 ? (
        <p className="message">
          No accounts found. Please add an account first.
        </p>
      ) : (
        <>
          <label className="field">
            <span>Account</span>
            <select value={selectedAccountId} onChange={handleAccountChange}>
              {accounts.map((acc) => (
                <option key={acc.account_id} value={acc.account_id}>
                  {acc.account_name}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Date</span>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </label>

          <label className="field">
            <span>Weight</span>
            <input
              type="number"
              step="0.01"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
              placeholder="e.g. 12.5"
            />
          </label>
          <label className="field">
            <span>Purchy Number (optional)</span>
            <input
              type="text"
              value={purchyNumber}
              onChange={(e) => setPurchyNumber(e.target.value)}
              placeholder="Purchy Number"
            />
          </label>
          {/* <label className="field">
            <span>Factory Name (optional)</span>
            <input
              type="text"
              value={factoryName}
              onChange={(e) => setFactoryName(e.target.value)}
              placeholder="e.g. XYZ Sugar Mill"
            />
          </label>

          <label className="field">
            <span>Rate (optional)</span>
            <input
              type="number"
              step="0.01"
              value={rate}
              onChange={(e) => setRate(e.target.value)}
              placeholder="Rate per ton/quintal"
            />
          </label> */}

          <label className="field">
            <span>Notes (optional)</span>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Any special info"
            />
          </label>

          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? "Saving..." : "Save Purchy"}
          </button>

          {message && <p className="message">{message}</p>}
        </>
      )}
    </form>
  );
}

export default App;