# Northbay Capital - Intentional Dirty Data Log

This document logs all intentionally injected anomalies (~2–3% noise level) in `northbay_finance_dataset.xlsx`. These issues were designed for data quality inspection, pipeline validation, and data cleaning practice.

## 1. Summary of Injected Anomalies

| Sheet | Anomaly Category | Count |
|---|---|---|
| `customers` | **Duplicate Row** | 4 |
| `customers` | **Extreme Outlier (Placeholder Glitch)** | 1 |
| `customers` | **Missing Value** | 45 |
| `customers` | **Mixed Date Format** | 25 |
| `customers` | **Text Inconsistency** | 70 |
| `loans` | **Missing Value** | 15 |
| `loans` | **Negative Principal Anomaly** | 2 |
| `trades` | **Duplicate Row** | 10 |
| `trades` | **Extreme Outlier (Fat-Finger)** | 1 |
| `trades` | **Missing Value** | 145 |
| `trades` | **Negative Lot Size Anomaly** | 3 |
| `transactions` | **Duplicate Row** | 20 |
| `transactions` | **Extreme Outlier (Fat-Finger)** | 1 |
| `transactions` | **Missing Value** | 300 |
| `transactions` | **Mixed Date Format** | 60 |
| `transactions` | **Negative Amount Anomaly** | 6 |
| `transactions` | **Text Inconsistency** | 174 |
| **TOTAL INJECTED ANOMALIES** | | **882** |

## 2. Injected Issues Breakdown & Cleaning Recommendations

1. **Duplicate Rows**:
   - *Where*: `transactions` (20 rows), `trades` (10 rows), `customers` (4 rows).
   - *Recommended Fix*: Use `df.drop_duplicates(subset=[primary_key])`.

2. **Missing Values in Non-Key Columns**:
   - *Where*: `customers.occupation`, `customers.acquisition_channel`, `transactions.payment_method`, `transactions.description`, `trades.close_reason`, `trades.swap_fee`, `loans.credit_score`.
   - *Recommended Fix*: Impute categories with `'Unknown'` or domain heuristics (e.g., infer `close_reason` by comparing `close_price` to `stop_loss` and `take_profit`).

3. **Inconsistent Text Formatting**:
   - *Where*: `city` (e.g., `'manila '`, `'MNL'`, `'QUEZON CITY'`), `gender` (`'M'`, `'male'`, `' Female'`), `payment_method` (`'gcash'`, `'G-CASH'`, `' PayMaya'`).
   - *Recommended Fix*: Strip whitespace (`str.strip()`), standardize casing (`str.title()`), and use mapping dictionaries.

4. **Mixed Date Formats in Timestamp/Date Columns**:
   - *Where*: `transactions.timestamp` and `customers.signup_date` containing mixed formats (`MM/DD/YYYY`, `DD-MM-YYYY`, `YYYY-MM-DD`).
   - *Recommended Fix*: Use `pd.to_datetime(col, format='mixed')` and enforce ISO-8601 formatting.

5. **Negative Values in Strictly Positive Columns**:
   - *Where*: `transactions.amount` (negative signs from debit exports), `loans.principal`, `trades.lot_size`.
   - *Recommended Fix*: Verify transaction debit/credit context, or apply `df[col] = df[col].abs()`.

6. **Extreme Outliers / Fat-Finger Errors**:
   - *Where*: 1000x transaction amount (PHP 50M+ single retail cash-in), 500 lot CFD trade, PHP 999,999,999 customer income.
   - *Recommended Fix*: Compute IQR / Z-score filters or apply business threshold caps.

## 3. Sample Itemized Audit Trail (First 60 Log Entries)

| Sheet | Record ID | Column | Original Value | Dirty Injected Value | Category | Strategy |
|---|---|---|---|---|---|---|
| `transactions` | `TXN-002163` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `transactions` | `TXN-001776` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `transactions` | `TXN-001808` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `transactions` | `TXN-007379` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `transactions` | `TXN-003036` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `transactions` | `TXN-000024` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `transactions` | `TXN-006654` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `transactions` | `TXN-000072` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `transactions` | `TXN-000822` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `transactions` | `TXN-002241` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `transactions` | `TXN-003297` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `transactions` | `TXN-000003` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `transactions` | `TXN-000179` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `transactions` | `TXN-002811` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `transactions` | `TXN-007358` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `transactions` | `TXN-008452` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `transactions` | `TXN-001570` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `transactions` | `TXN-004763` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `transactions` | `TXN-005084` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `transactions` | `TXN-007341` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on transaction_id or all columns via df.drop_duplicates() |
| `trades` | `TRD-02607` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on trade_id via df.drop_duplicates(subset=['trade_id']) |
| `trades` | `TRD-04397` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on trade_id via df.drop_duplicates(subset=['trade_id']) |
| `trades` | `TRD-04193` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on trade_id via df.drop_duplicates(subset=['trade_id']) |
| `trades` | `TRD-00487` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on trade_id via df.drop_duplicates(subset=['trade_id']) |
| `trades` | `TRD-04222` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on trade_id via df.drop_duplicates(subset=['trade_id']) |
| `trades` | `TRD-00764` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on trade_id via df.drop_duplicates(subset=['trade_id']) |
| `trades` | `TRD-01663` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on trade_id via df.drop_duplicates(subset=['trade_id']) |
| `trades` | `TRD-03807` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on trade_id via df.drop_duplicates(subset=['trade_id']) |
| `trades` | `TRD-02518` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on trade_id via df.drop_duplicates(subset=['trade_id']) |
| `trades` | `TRD-00013` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on trade_id via df.drop_duplicates(subset=['trade_id']) |
| `customers` | `CUST-00745` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on customer_id |
| `customers` | `CUST-00742` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on customer_id |
| `customers` | `CUST-00922` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on customer_id |
| `customers` | `CUST-00682` | `ALL` | `Single record` | `Duplicate row inserted` | Duplicate Row | Deduplicate on customer_id |
| `customers` | `CUST-00559` | `occupation` | `Logistics Coordinator` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00326` | `occupation` | `Virtual Assistant` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00664` | `occupation` | `Logistics Coordinator` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00187` | `occupation` | `Software Engineer` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00885` | `occupation` | `Civil Engineer` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00698` | `occupation` | `High School Teacher` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00075` | `occupation` | `Registered Nurse` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00312` | `occupation` | `Sales Executive` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00677` | `occupation` | `Customer Service Specialist` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00456` | `occupation` | `Customer Service Specialist` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00097` | `occupation` | `Virtual Assistant` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00319` | `occupation` | `Architect` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00434` | `occupation` | `Customer Service Specialist` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00932` | `occupation` | `Data Analyst` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00160` | `occupation` | `Sales Executive` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00363` | `occupation` | `High School Teacher` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00833` | `occupation` | `Sales Executive` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00225` | `occupation` | `BPO Operations Manager` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00461` | `occupation` | `SME Retail Owner` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00781` | `occupation` | `Customer Service Specialist` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00828` | `occupation` | `Certified Public Accountant` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00128` | `occupation` | `High School Teacher` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00768` | `occupation` | `Registered Nurse` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00627` | `occupation` | `E-Commerce Merchant` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00470` | `occupation` | `Sales Executive` | `NaN` | Missing Value | Impute with 'Unknown' or mode occupation |
| `customers` | `CUST-00079` | `acquisition_channel` | `Google` | `NaN` | Missing Value | Impute with 'Unknown' or direct attribution |

*(Full audit log contains all 882 injected modifications)*
