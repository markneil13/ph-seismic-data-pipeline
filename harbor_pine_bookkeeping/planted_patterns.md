# ⚠️ SPOILER ALERT: DO NOT OPEN OR READ UNTIL YOU HAVE FINISHED YOUR ANALYSIS! ⚠️

> [!CAUTION]
> **STOP! Do not read this file if you are conducting an exploratory analysis or SQL practice session.**
>
> This document describes the ground-truth patterns, business dynamics, and operational anomalies intentionally planted inside the Harbor & Pine Bookkeeping dataset. 
>
> Opening this file beforehand will ruin the discovery process. First write your SQL queries, inspect distributions, build your dashboards or aggregations, and formulate your findings. Return to this file only when you are ready to check your answers!

---

# Planted Patterns & Analytical Solutions

This dataset contains **7 realistic operational and commercial patterns**. None are exaggerated or caricatured; they reflect genuine small-business dynamics, human workflow variations, and geographic accounting seasonality.

---

### Pattern 1: Document Error & Rework Rate Driven by Mobile "Photo" Intake

* **Business Context**: Harbor & Pine allows clients to submit documents through four channels: Email, Web Upload, Mobile Photo snap, and Paper Scan. Small business owners taking quick photos of crumpled receipts with their mobile phones often suffer from poor lighting, blurry focus, tilted angles, and truncated receipt edges.
* **Ground Truth Planted**:
  * Documents submitted via `Photo` have an error/rework rate of **~22%** (`17% Rework` + `5% Failed`), compared to **~7.5%** for `Upload`, **~7.5%** for `Email`, and **~11.0%** for `Paper Scan`.
  * For `Photo` documents encountering issues, **65%** of errors are flagged as `Unreadable` (compared to 25% across other channels where errors are evenly split among `Wrong Amount`, `Missing Info`, and `Duplicate`).
* **Analytical SQL Query**:
```sql
SELECT 
    source_channel,
    COUNT(*) AS total_docs,
    ROUND(SUM(CASE WHEN status IN ('Rework', 'Failed') THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS issue_rate_pct,
    ROUND(SUM(CASE WHEN status = 'Rework' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS rework_pct,
    ROUND(SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS failed_pct,
    ROUND(SUM(CASE WHEN error_type = 'Unreadable' THEN 1 ELSE 0 END) * 100.0 / 
          NULLIF(SUM(CASE WHEN status IN ('Rework', 'Failed') THEN 1 ELSE 0 END), 0), 2) AS unreadable_share_of_errors_pct
FROM documents
GROUP BY source_channel
ORDER BY issue_rate_pct DESC;
```

---

### Pattern 2: Client Churn Disparity Across Industry Sectors

* **Business Context**: Small business failure rates and cash flow instability vary widely by sector. Fast-casual dining and direct-to-consumer e-commerce suffer from high mortality and volatile margins, whereas healthcare practices and professional consulting firms enjoy stable recurring demand and high client retention.
* **Ground Truth Planted**:
  * `Restaurant` (~34%) and `E-commerce` (~31%) show the highest churn rates.
  * `Healthcare` (~12%) and `Consulting` (~14%) show the lowest churn rates.
  * Baseline industries (`Retail`, `Real Estate`, `Construction`, `Trades`) sit between 22% and 27%.
* **Analytical SQL Query**:
```sql
SELECT 
    industry,
    COUNT(*) AS total_clients,
    SUM(CASE WHEN status = 'Churned' THEN 1 ELSE 0 END) AS churned_clients,
    ROUND(SUM(CASE WHEN status = 'Churned' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS churn_rate_pct
FROM clients
GROUP BY industry
ORDER BY churn_rate_pct DESC;
```

---

### Pattern 3: Acquisition Channel Quality: High-Value Partners vs. Volatile Social Ads

* **Business Context**: Clients referred by professional accounting partners or peer referrals are pre-qualified, understand the value of professional bookkeeping, and select higher-tier packages. In contrast, clients acquired through direct Facebook ads are typically price-sensitive micro-businesses seeking minimum compliance at lowest cost.
* **Ground Truth Planted**:
  * `Accountant Partner` & `Referral`:
    * Plan Tier: ~75% choose `Standard` or `Premium` (only ~25% on `Basic`).
    * Churn: Low churn rate (~15-17%).
    * Average Satisfaction: **~4.2 - 4.4 / 5.0**.
  * `Facebook`:
    * Plan Tier: Skews heavily to `Basic` (~65%).
    * Churn: High churn rate (~33-36%).
    * Average Satisfaction: **~3.6 - 3.8 / 5.0**.
* **Analytical SQL Query**:
```sql
SELECT 
    c.acquisition_source,
    COUNT(DISTINCT c.client_id) AS total_clients,
    ROUND(SUM(CASE WHEN c.plan_tier = 'Basic' THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT c.client_id), 1) AS pct_basic_tier,
    ROUND(SUM(CASE WHEN c.plan_tier = 'Premium' THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT c.client_id), 1) AS pct_premium_tier,
    ROUND(SUM(CASE WHEN c.status = 'Churned' THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT c.client_id), 1) AS churn_rate_pct,
    ROUND(AVG(mc.satisfaction_score), 2) AS avg_satisfaction_score
FROM clients c
LEFT JOIN monthly_closes mc ON c.client_id = mc.client_id
GROUP BY c.acquisition_source
ORDER BY avg_satisfaction_score DESC;
```

---

### Pattern 4: Monthly Close Delays Driven by Staff Seniority and Crunch Months

* **Business Context**: Senior bookkeepers and managers have the expertise and speed to resolve discrepancies quickly. Junior bookkeepers struggle during high-volume periods, resulting in deadline slippage.
* **Ground Truth Planted**:
  * `Manager`: On-time delivery rate is **~95%**; average `days_late` is **~0.3 days**.
  * `Senior Bookkeeper`: On-time delivery rate is **~82%**; average `days_late` is **~1.1 days**.
  * `Bookkeeper`: On-time delivery rate is **~58-65%**; average `days_late` is **~3.4 days**.
  * During peak tax deadline crunch months (March, April, June, July, October), `Bookkeeper` late closes increase significantly, averaging **~5.5 to 6.5 days late**.
* **Analytical SQL Query**:
```sql
SELECT 
    s.role,
    COUNT(*) AS total_closes,
    ROUND(SUM(CASE WHEN mc.days_late = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS on_time_close_pct,
    ROUND(AVG(mc.days_late), 2) AS avg_days_late,
    ROUND(MAX(mc.days_late), 1) AS max_days_late,
    ROUND(AVG(CASE 
        WHEN CAST(SUBSTR(mc.month, 6, 2) AS INTEGER) IN (3, 4, 6, 7, 10) 
        THEN mc.days_late END), 2) AS avg_days_late_crunch_months
FROM monthly_closes mc
JOIN staff s ON mc.staff_id = s.staff_id
GROUP BY s.role
ORDER BY avg_days_late ASC;
```

---

### Pattern 5: Document Processing Time Scaling by Document Complexity and Page Count

* **Business Context**: Document verification requires vastly different intellectual effort depending on the document type. A single-page retail receipt requires simple payee/amount entry, whereas multi-page bank statements and payroll reports require line-by-line reconciliation and ledger balance cross-referencing. Rework items consume extra clarification time.
* **Ground Truth Planted**:
  * Average processing time per page:
    * `Receipt`: **~3.2 minutes / page** (average total time ~3.5 min).
    * `Supplier Invoice`: **~5.0 minutes / page** (average total time ~8.5 min).
    * `Bank Statement`: **~9.2 minutes / page** (average total time ~26.0 min).
    * `Payroll Report`: **~8.5 minutes / page** (average total time ~22.0 min).
  * Documents requiring `Rework` experience a **~1.7x** time penalty over first-pass processed documents.
* **Analytical SQL Query**:
```sql
SELECT 
    doc_type,
    COUNT(*) AS total_docs,
    ROUND(AVG(pages), 2) AS avg_pages,
    ROUND(AVG(processing_minutes), 2) AS avg_total_minutes,
    ROUND(AVG(processing_minutes / pages), 2) AS avg_minutes_per_page,
    ROUND(AVG(CASE WHEN status = 'Rework' THEN processing_minutes END), 2) AS avg_minutes_rework,
    ROUND(AVG(CASE WHEN status = 'Processed' THEN processing_minutes END), 2) AS avg_minutes_processed
FROM documents
GROUP BY doc_type
ORDER BY avg_minutes_per_page ASC;
```

---

### Pattern 6: Accounts Receivable Aging and Payment Delays in Construction & Trades

* **Business Context**: Subcontractors and trades businesses operate under milestone progress payments and delayed general contractor disbursements ("paid-when-paid"). This downstream cash flow delay forces them to delay paying vendor and bookkeeping invoices, resulting in extended payment latency and overdue bills.
* **Ground Truth Planted**:
  * `Construction` and `Trades`:
    * Unpaid / Overdue invoice share: **~15-17%**.
    * Average days to pay for settled invoices: **~22 to 26 days** from issue date (with frequent 30+ day delays).
  * `Consulting` and `Healthcare`:
    * Unpaid / Overdue invoice share: **~3-4%**.
    * Average days to pay: **~6 to 9 days** from issue date.
* **Analytical SQL Query**:
```sql
SELECT 
    c.industry,
    COUNT(b.invoice_id) AS total_invoices,
    ROUND(SUM(CASE WHEN b.status = 'Overdue' THEN 1 ELSE 0 END) * 100.0 / COUNT(b.invoice_id), 2) AS overdue_rate_pct,
    ROUND(AVG(CASE WHEN b.paid_date IS NOT NULL 
                   THEN JULIANDAY(b.paid_date) - JULIANDAY(b.issue_date) END), 1) AS avg_days_to_pay,
    ROUND(SUM(b.amount), 2) AS total_billed,
    ROUND(SUM(CASE WHEN b.status = 'Overdue' THEN b.amount ELSE 0 END), 2) AS total_overdue_amount
FROM billing b
JOIN clients c ON b.client_id = c.client_id
GROUP BY c.industry
ORDER BY overdue_rate_pct DESC;
```

---

### Pattern 7: Geographic Document Seasonality Correlated with National Tax Deadlines

* **Business Context**: Small business owners submit document backlogs when statutory tax filing deadlines approach in their respective jurisdictions.
* **Ground Truth Planted**:
  * **United States (US)**: Tax filing deadline April 15. Inflow peaks sharply in **March and April** (+150% volume spike), with a secondary bump in **September/October** for extension filings.
  * **United Kingdom (UK)**: Self-Assessment deadline January 31, financial year end April 5. Document inflow peaks in **January** (+160%) and **March/April** (+120%).
  * **Australia (AU)**: Financial year ends June 30, individual/sole trader tax returns due October 31. Document inflow surges in **June and July** (+180%) and **October** (+100%).
  * **New Zealand (NZ)**: Financial year ends March 31, terminal tax obligations due in March/April. Inflow surges in **March and April** (+170%).
* **Analytical SQL Query**:
```sql
SELECT 
    c.country,
    SUBSTR(d.received_date, 6, 2) AS month_num,
    COUNT(d.doc_id) AS doc_count
FROM documents d
JOIN clients c ON d.client_id = c.client_id
GROUP BY c.country, month_num
ORDER BY c.country, month_num;
```
