import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

function nullableNumber(value) {
  if (value === '' || value === null || value === undefined) return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

function cleanOptional(value) {
  const text = String(value ?? '').trim()
  return text || null
}

function severityClass(value) {
  if (!value) return 'neutral'
  const v = value.toLowerCase()
  if (v.includes('major') || v.includes('high')) return 'danger'
  if (v.includes('moderate') || v.includes('review')) return 'warning'
  if (v.includes('minor') || v.includes('standard')) return 'success'
  return 'neutral'
}

function reviewFlagLabel(flag) {
  const labels = {
    PGX_MATCHED_VARIANT: 'PGX MATCHED VARIANT',
    PGX_RULE_PRESENT: 'PGX RULE PRESENT',
    RENAL_ADJUSTMENT_AVAILABLE: 'RENAL ADJUSTMENT AVAILABLE',
    DOSAGE_INFORMATION_REQUIRES_CLINICIAN_REVIEW: 'DOSAGE INFORMATION REQUIRES CLINICIAN REVIEW',
    DOSAGE_RULE_MISSING_FOR_ONE_OR_MORE_MEDICINES: 'DOSAGE INFORMATION REQUIRES CLINICIAN REVIEW',
    UNRESOLVED_MEDICINE: 'UNRESOLVED MEDICINE',
  }
  return labels[flag] || String(flag || '').replaceAll('_', ' ')
}

function ddiDisplayStatus(ddi) {
  if (!ddi) return 'Not Run'
  if (!ddi.highest_severity && !ddi.known_interaction_count && !ddi.predicted_interaction_count) {
    return 'No Known Interaction Detected'
  }
  return ddi.highest_severity || 'Interaction Review Required'
}

function Badge({ children, tone = 'neutral' }) {
  return <span className={`badge ${tone}`}>{children}</span>
}

function Metric({ label, value, tone = 'neutral', hint }) {
  return (
    <div className={`metric metric-${tone}`}>
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
      {hint && <div className="metric-hint">{hint}</div>}
    </div>
  )
}

function Section({ title, subtitle, children, right }) {
  return (
    <section className="section-card">
      <div className="section-heading">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {right}
      </div>
      {children}
    </section>
  )
}

function EmptyState({ children }) {
  return <div className="empty-state">{children}</div>
}

function MedicinePicker({ medicines, setMedicines }) {
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const trimmed = query.trim()
    if (trimmed.length < 2) {
      setSuggestions([])
      return
    }
    const controller = new AbortController()
    const timer = setTimeout(async () => {
      setLoading(true)
      try {
        const res = await fetch(`${API_BASE}/api/medicines/search?q=${encodeURIComponent(trimmed)}&limit=8`, {
          signal: controller.signal,
        })
        if (!res.ok) throw new Error('Search failed')
        const data = await res.json()
        setSuggestions(data)
      } catch (err) {
        if (err.name !== 'AbortError') setSuggestions([])
      } finally {
        setLoading(false)
      }
    }, 250)
    return () => {
      clearTimeout(timer)
      controller.abort()
    }
  }, [query])

  const addMedicine = (name) => {
    const clean = String(name || '').trim()
    if (!clean || medicines.includes(clean) || medicines.length >= 20) return
    setMedicines([...medicines, clean])
    setQuery('')
    setSuggestions([])
  }

  return (
    <div className="medicine-picker">
      <div className="chips">
        {medicines.map((m) => (
          <button key={m} type="button" className="chip" onClick={() => setMedicines(medicines.filter((x) => x !== m))} title="Remove">
            <span>{m}</span><strong>×</strong>
          </button>
        ))}
      </div>
      <div className="search-wrap">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              if (suggestions[0]) addMedicine(suggestions[0].product_name)
              else addMedicine(query)
            }
          }}
          placeholder="Search medicine product name..."
        />
        {loading && <span className="search-status">Searching…</span>}
        {suggestions.length > 0 && (
          <div className="suggestions">
            {suggestions.map((item) => (
              <button key={item.product_id} type="button" onClick={() => addMedicine(item.product_name)}>
                <span className="suggestion-name">{item.product_name}</span>
                <span className="suggestion-meta">{item.generic_name || 'Generic not listed'}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="field-help">Add 1–20 medicines. Click a chip to remove it.</div>
    </div>
  )
}

function MappingPanel({ items }) {
  if (!items?.length) return <EmptyState>No medicine mappings returned.</EmptyState>
  return <div className="stack-list">{items.map((item) => (
    <article className="mapping-item" key={`${item.input_name}-${item.product_id}`}>
      <div className="row-between">
        <div>
          <h3>{item.product_name || item.input_name}</h3>
          <p>{item.generic_name || 'Generic name unavailable'}</p>
        </div>
        <Badge tone={item.mapping_status === 'RESOLVED' ? 'success' : 'warning'}>{item.mapping_status}</Badge>
      </div>
      <div className="ingredient-grid">
        {item.ingredients?.map((ing, i) => (
          <div className="ingredient" key={`${ing.canonical_drug_id}-${i}`}>
            <strong>{ing.canonical_name || ing.ingredient_raw || 'Unresolved ingredient'}</strong>
            <span>{ing.canonical_drug_id || 'No canonical ID'}</span>
            <span>{ing.drugbank_id || 'No DrugBank ID'}</span>
            <span>{ing.ddinter_id || 'No DDInter ID'}</span>
          </div>
        ))}
      </div>
    </article>
  ))}</div>
}

function DDIContent({ ddi }) {
  if (!ddi) return <EmptyState>DDI analysis was not run for a single medicine.</EmptyState>
  return (
    <>
      <div className="mini-metrics">
        <Metric label="Pairs checked" value={ddi.pairs_checked} />
        <Metric label="Known interactions" value={ddi.known_interaction_count} tone={ddi.known_interaction_count ? 'warning' : 'success'} />
        <Metric label="Predicted interactions" value={ddi.predicted_interaction_count} />
        <Metric label="DDI Assessment" value={ddiDisplayStatus(ddi)} tone={!ddi.highest_severity && !ddi.known_interaction_count && !ddi.predicted_interaction_count ? 'success' : severityClass(ddi.highest_severity)} />
      </div>
      <div className="stack-list compact">
        {ddi.interactions?.map((x, i) => (
          <article className="interaction" key={`${x.drug_a}-${x.drug_b}-${i}`}>
            <div className="row-between">
              <strong>{x.drug_a || x.medicine_a} ↔ {x.drug_b || x.medicine_b}</strong>
              <Badge tone={!x.severity && x.status === 'NO_KNOWN_INTERACTION' ? 'success' : severityClass(x.severity)}>{!x.severity && x.status === 'NO_KNOWN_INTERACTION' ? 'No Known Interaction Detected' : (x.severity || x.status)}</Badge>
            </div>
            <p>{x.source}</p>
            <div className="meta-row">
              <span>{x.ddi_id || 'No known DDI ID'}</span>
              <span>{x.model_status}</span>
            </div>
          </article>
        ))}
      </div>
    </>
  )
}

function DosageContent({ analyses, officialLabels = {}, officialLabelLoading = {} }) {
  if (!analyses?.length) return <EmptyState>No dosage analyses returned.</EmptyState>
  return <div className="stack-list">{analyses.map((a) => {
    const found = a.standard_or_disease_rules?.length > 0
    const lookupName = a.canonical_drug_names?.[0] || a.medicine_resolution?.input_name
    const official = officialLabels[lookupName]
    const labelLoading = officialLabelLoading[lookupName]
    return (
      <article className="dosage-card" key={a.medicine_resolution?.input_name}>
        <div className="row-between">
          <div>
            <h3>{a.canonical_drug_names?.join(', ') || a.medicine_resolution?.input_name}</h3>
            <p>{found ? 'Dosage information found' : 'Checking official drug labeling'}</p>
          </div>
          <Badge tone={found ? 'success' : (official?.status === 'OFFICIAL_LABEL_FOUND' ? 'success' : 'warning')}>
            {found ? 'DOSAGE INFORMATION FOUND' : (official?.status === 'OFFICIAL_LABEL_FOUND' ? 'OFFICIAL LABEL FOUND' : 'REFERENCE LOOKUP')}
          </Badge>
        </div>
        {found ? (
          <div className="rule-grid">
            {a.standard_or_disease_rules.map((r) => (
              <div className="rule-box" key={r.record_id}>
                <strong>{r.rule_type}</strong>
                <span>Disease: {r.disease || '—'}</span>
                <span>Route: {r.route || '—'}</span>
                <span>Dose fields: {Object.entries(r.dose_fields || {}).map(([k,v]) => `${k}=${v}`).join(' · ') || '—'}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="official-label-wrap">
            {labelLoading && <div className="dosage-review-box"><strong>Checking FDA drug labeling…</strong><p>Looking for an official reference record for {lookupName}.</p></div>}
            {!labelLoading && official?.status === 'OFFICIAL_LABEL_FOUND' && (
              <div className="official-label-card">
                <div className="official-label-title">
                  <div>
                    <strong>Official Drug Label Found</strong>
                    <span>{official.source}</span>
                  </div>
                  <Badge tone="success">OFFICIAL_LABEL_FOUND</Badge>
                </div>
                <div className="label-detail-grid">
                  <div><span>Medicine</span><strong>{lookupName}</strong></div>
                  <div><span>Route</span><strong>{official.route || 'Not listed'}</strong></div>
                </div>
                <div className="label-section">
                  <strong>Indication</strong>
                  <p>{official.indication || 'Indication text was not available in the matched openFDA record.'}</p>
                </div>
                <div className="label-section">
                  <strong>Dosage Form / Strength</strong>
                  <p>{official.dosage_form_strength || 'Dosage form and strength were not available in the matched openFDA record.'}</p>
                </div>
                
                <div className="label-source">Source: {official.source}</div>
              </div>
            )}
            {!labelLoading && official && official.status !== 'OFFICIAL_LABEL_FOUND' && (
              <div className="dosage-review-box">
                <strong>Official dosage reference not found</strong>
                <p>{official.warnings?.[0] || 'No matching official FDA drug-label record was available for this medicine.'}</p>
                <span>Status: {official.status}</span>
              </div>
            )}
            {!labelLoading && !official && (
              <div className="dosage-review-box">
                <strong>Dosage information not available</strong>
                <p>No matching dosage information is available for the supplied medicine and patient context.</p>
                <span>An official-label reference lookup will be attempted when the backend is reachable.</span>
              </div>
            )}
          </div>
        )}
        {a.renal_adjustments?.length > 0 && (
          <div className="renal-box">
            <strong>Renal adjustment information available</strong>
            {a.renal_adjustments.map((r) => (
              <div key={r.record_id}>
                CrCl {r.crcl_range_ml_min?.min ?? '—'}–{r.crcl_range_ml_min?.max ?? '—'} mL/min · {Object.entries(r.dose_fields || {}).map(([k,v]) => `${k}=${v}`).join(' · ')}
              </div>
            ))}
          </div>
        )}
      </article>
    )
  })}</div>
}

function PGxContent({ analyses }) {
  if (!analyses?.length) return <EmptyState>No PGx analyses returned.</EmptyState>
  return <div className="stack-list">{analyses.map((a) => (
    <article className="pgx-card" key={a.medicine_resolution?.input_name}>
      <div className="row-between">
        <div>
          <h3>{a.canonical_drug_names?.join(', ') || a.medicine_resolution?.input_name}</h3>
          <p>{a.gene_symbol} · {a.implementation_scope}</p>
        </div>
        <Badge tone={a.pgx_relevant ? 'warning' : 'neutral'}>{a.status}</Badge>
      </div>
      {a.matched_variants?.length > 0 && (
        <div className="variant-row">
          {a.matched_variants.map((v) => <Badge key={v.pgx_variant_id} tone="warning">{v.rsid} · {v.defining_allele_relationship}</Badge>)}
        </div>
      )}
      {a.drug_rules?.map((r) => (
        <div className="recommendation-box" key={r.pgx_rule_id}>
          <strong>{r.guideline_name || 'PGx guideline'}</strong>
          <p>{r.recommendation_summary}</p>
          <span>Source: {r.source || '—'} · {r.validation_status || '—'}</span>
        </div>
      ))}
    </article>
  ))}</div>
}

function AlternativesContent({ status, analyses }) {
  if (!analyses?.length) return <EmptyState>Alternative analysis status: {status}</EmptyState>
  return <div className="stack-list">{analyses.map((group, gi) => (
    <article className="alternative-group" key={`${group.source_product_id}-${gi}`}>
      <h3>Source: {group.source_product_name}</h3>
      <div className="alternative-grid">
        {group.alternatives?.map((a) => (
          <div className="alternative-card" key={a.alternative_id}>
            <div className="row-between">
              <strong>{a.alternative_product_name}</strong>
              <Badge tone={severityClass(a.highest_severity)}>{a.recommendation_class}</Badge>
            </div>
            <span>DDI re-check: {a.ddi_recheck_status}</span>
            <span>Highest severity: {a.highest_severity || 'None'}</span>
            <span>Known interactions: {a.known_interaction_count}</span>
          </div>
        ))}
      </div>
    </article>
  ))}</div>
}

function App() {
  const [medicines, setMedicines] = useState(["Aretha 50mg Tablet 10'S", "ADDTREX 50 Tablet 10's"])
  const [form, setForm] = useState({
    age_years: '30', weight_kg: '70', disease: '', route: '', crcl_ml_min: '80', gene_symbol: 'TPMT', variants: 'rs1142345',
    use_gnn_fallback: false, include_alternatives: true, max_alternative_sources: 2, max_alternatives_per_medicine: 3,
  })
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('summary')
  const [officialLabels, setOfficialLabels] = useState({})
  const [officialLabelLoading, setOfficialLabelLoading] = useState({})

  const tabs = useMemo(() => [
    ['summary', 'Summary'], ['mapping', 'Medicine Mapping'], ['ddi', 'DDI'], ['dosage', 'Dosage'], ['pgx', 'PGx'], ['alternatives', 'Alternatives']
  ], [])

  useEffect(() => {
    if (!result?.dosage_analyses?.length) {
      setOfficialLabels({})
      setOfficialLabelLoading({})
      return
    }
    const missingNames = [...new Set(result.dosage_analyses
      .filter((a) => !(a.standard_or_disease_rules?.length > 0))
      .map((a) => a.canonical_drug_names?.[0] || a.medicine_resolution?.input_name)
      .filter(Boolean))]
    if (!missingNames.length) return

    const controllers = []
    missingNames.forEach((name) => {
      const controller = new AbortController()
      controllers.push(controller)
      setOfficialLabelLoading((prev) => ({ ...prev, [name]: true }))
      fetch(`${API_BASE}/api/dosage/official-label?medicine_name=${encodeURIComponent(name)}`, { signal: controller.signal })
        .then(async (res) => {
          const data = await res.json().catch(() => null)
          if (!res.ok) throw new Error(`Official label lookup failed with HTTP ${res.status}`)
          return data
        })
        .then((data) => setOfficialLabels((prev) => ({ ...prev, [name]: data })))
        .catch((err) => {
          if (err.name !== 'AbortError') {
            setOfficialLabels((prev) => ({
              ...prev,
              [name]: { status: 'OFFICIAL_LABEL_LOOKUP_UNAVAILABLE', source: 'FDA Drug Labeling (openFDA)', warnings: [err.message] },
            }))
          }
        })
        .finally(() => setOfficialLabelLoading((prev) => ({ ...prev, [name]: false })))
    })
    return () => controllers.forEach((c) => c.abort())
  }, [result])

  const update = (key, value) => setForm((f) => ({ ...f, [key]: value }))

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (!medicines.length) {
      setError('Add at least one medicine before analysis.')
      return
    }
    const payload = {
      medicines,
      age_years: nullableNumber(form.age_years),
      weight_kg: nullableNumber(form.weight_kg),
      disease: cleanOptional(form.disease),
      route: cleanOptional(form.route),
      crcl_ml_min: nullableNumber(form.crcl_ml_min),
      gene_symbol: cleanOptional(form.gene_symbol) || 'TPMT',
      variants: form.variants.split(',').map((x) => x.trim()).filter(Boolean),
      use_gnn_fallback: form.use_gnn_fallback,
      include_alternatives: form.include_alternatives,
      max_alternative_sources: Number(form.max_alternative_sources),
      max_alternatives_per_medicine: Number(form.max_alternatives_per_medicine),
    }
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/clinical/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', accept: 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json().catch(() => null)
      if (!res.ok) {
        throw new Error(data?.detail ? JSON.stringify(data.detail) : `Request failed with HTTP ${res.status}`)
      }
      setResult(data)
      setActiveTab('summary')
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (err) {
      setError(err.message || 'Unable to connect to the backend.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">Rx</div>
          <div><strong>Clinical Drug Intelligence</strong><span>AI-assisted educational decision support</span></div>
        </div>
        <div className="api-pill"><span className="dot" /> Backend: {API_BASE.replace('http://', '')}</div>
      </header>

      <main className="layout">
        <aside className="form-panel">
          <div className="eyebrow">Patient assessment</div>
          <h1>Clinical Analysis</h1>
          <p className="intro">Enter patient context and medicines. The system combines mapping, DDI, dosage, TPMT PGx, and alternative re-checks.</p>

          <form onSubmit={submit}>
            <label className="field full"><span>Medicines *</span><MedicinePicker medicines={medicines} setMedicines={setMedicines} /></label>
            <div className="two-col">
              <label className="field"><span>Age (years)</span><input type="number" min="0" max="130" step="0.1" value={form.age_years} onChange={(e) => update('age_years', e.target.value)} /></label>
              <label className="field"><span>Weight (kg)</span><input type="number" min="0.1" max="500" step="0.1" value={form.weight_kg} onChange={(e) => update('weight_kg', e.target.value)} /></label>
              <label className="field"><span>Disease</span><input value={form.disease} onChange={(e) => update('disease', e.target.value)} placeholder="e.g. Bacteremia" /></label>
              <label className="field"><span>Route</span><input value={form.route} onChange={(e) => update('route', e.target.value)} placeholder="e.g. IV" /></label>
              <label className="field"><span>CrCl (mL/min)</span><input type="number" min="0" max="300" step="0.1" value={form.crcl_ml_min} onChange={(e) => update('crcl_ml_min', e.target.value)} /></label>
              <label className="field"><span>Gene</span><input value={form.gene_symbol} onChange={(e) => update('gene_symbol', e.target.value)} /></label>
            </div>
            <label className="field full"><span>Genetic variants</span><input value={form.variants} onChange={(e) => update('variants', e.target.value)} placeholder="rs1142345, rs1800460" /><small>Comma-separated. Current implementation scope is TPMT.</small></label>

            <div className="options-box">
              <label className="toggle"><input type="checkbox" checked={form.use_gnn_fallback} onChange={(e) => update('use_gnn_fallback', e.target.checked)} /><span />Use GNN fallback for unknown DDI pairs</label>
              <label className="toggle"><input type="checkbox" checked={form.include_alternatives} onChange={(e) => update('include_alternatives', e.target.checked)} /><span />Evaluate alternatives for Moderate/Major DDI</label>
              <div className="two-col option-numbers">
                <label className="field"><span>Alternative source limit</span><input type="number" min="1" max="5" value={form.max_alternative_sources} onChange={(e) => update('max_alternative_sources', e.target.value)} /></label>
                <label className="field"><span>Alternatives / medicine</span><input type="number" min="1" max="10" value={form.max_alternatives_per_medicine} onChange={(e) => update('max_alternatives_per_medicine', e.target.value)} /></label>
              </div>
            </div>

            {error && <div className="error-box">{error}</div>}
            <button className="primary-btn" disabled={loading} type="submit">{loading ? 'Analyzing clinical data…' : 'Run Clinical Analysis'}</button>
          </form>
        </aside>

        <section className="results-panel">
          {!result ? (
            <div className="welcome-card">
              <div className="welcome-icon">+</div>
              <h2>Ready for analysis</h2>
              <p>Run the form to generate a structured clinical report from the unified drug dataset.</p>
              <div className="feature-grid">
                <span>Medicine Mapping</span><span>DDI Analysis</span><span>Dosage + Renal</span><span>TPMT PGx</span><span>Alternatives</span><span>Clinical Summary</span>
              </div>
            </div>
          ) : (
            <>
              <div className="report-header">
                <div>
                  <div className="eyebrow">Integrated report</div>
                  <h1>Clinical Decision Summary</h1>
                  <p>{result.status}</p>
                </div>
                <Badge tone={severityClass(result.summary?.attention_level)}>{result.summary?.attention_level}</Badge>
              </div>

              <div className="summary-metrics">
                <Metric label="Resolved" value={`${result.summary.medicines_resolved}/${result.summary.medicines_requested}`} tone="success" />
                <Metric label="DDI Assessment" value={ddiDisplayStatus(result.ddi_analysis)} tone={!result.summary.highest_ddi_severity && !result.summary.known_interactions && !result.summary.predicted_interactions ? 'success' : severityClass(result.summary.highest_ddi_severity)} />
                <Metric label="Dosage rules" value={result.summary.dosage_rules_found_for} />
                <Metric label="Renal matches" value={result.summary.renal_adjustments_found_for} tone={result.summary.renal_adjustments_found_for ? 'warning' : 'neutral'} />
                <Metric label="PGx matches" value={result.summary.pgx_variant_matches_for} tone={result.summary.pgx_variant_matches_for ? 'warning' : 'neutral'} />
                <Metric label="Alternatives" value={result.summary.alternatives_evaluated_for} />
              </div>

              <nav className="tabs">
                {tabs.map(([key, label]) => <button className={activeTab === key ? 'active' : ''} onClick={() => setActiveTab(key)} key={key}>{label}</button>)}
              </nav>

              {activeTab === 'summary' && <Section title="Clinical Summary" subtitle="Combined review signals from all backend modules" right={<Badge tone={severityClass(result.summary.attention_level)}>{result.summary.attention_level}</Badge>}>
                <div className="flag-row">{result.summary.review_flags?.length ? result.summary.review_flags.map((f) => <Badge key={f} tone="warning">{reviewFlagLabel(f)}</Badge>) : <Badge tone="success">NO SPECIAL FLAGS</Badge>}</div>
                <div className="narrative">{result.summary.narrative?.map((n, i) => <p key={i}>{n}</p>)}</div>
                {result.warnings?.length > 0 && <div className="warnings"><strong>Warnings</strong>{result.warnings.map((w, i) => <p key={i}>• {w}</p>)}</div>}
                <div className="disclaimer">{result.disclaimer}</div>
              </Section>}
              {activeTab === 'mapping' && <Section title="Medicine Mapping" subtitle="Product → ingredient → canonical drug identifiers"><MappingPanel items={result.medicine_resolutions} /></Section>}
              {activeTab === 'ddi' && <Section title="Drug–Drug Interaction Analysis" subtitle="Known DDInter records are preferred over model predictions"><DDIContent ddi={result.ddi_analysis} /></Section>}
              {activeTab === 'dosage' && <Section title="Dosage Analysis" subtitle="Dosage information and renal adjustments for the supplied patient context"><DosageContent analyses={result.dosage_analyses} officialLabels={officialLabels} officialLabelLoading={officialLabelLoading} /></Section>}
              {activeTab === 'pgx' && <Section title="Pharmacogenomics" subtitle="Current supplied implementation scope: TPMT"><PGxContent analyses={result.pgx_analyses} /></Section>}
              {activeTab === 'alternatives' && <Section title="Alternative Recommendations" subtitle="Alternatives are re-checked against the other medicines"><AlternativesContent status={result.alternatives_status} analyses={result.alternative_analyses} /></Section>}
            </>
          )}
        </section>
      </main>
    </div>
  )
}

createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>)
