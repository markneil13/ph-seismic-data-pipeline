#!/usr/bin/env python3
"""
Northbay Capital - Synthetic Finance Dataset Generator
======================================================
Author: Senior Data Engineer
Target Environment: Low-memory laptop (<= 8 GB RAM)
License: Synthetic Data for Educational / Practice Use Only

This script generates a realistic, synthetic financial dataset for "Northbay Capital",
a fictional retail brokerage and lending institution based in the Philippines serving
clients across Asia.

Features:
- Configurable row counts, seeds, and date ranges
- Relational integrity across 6 domain sheets + 1 data dictionary sheet
- Vectorized, low-memory operations using numpy and pandas
- Geometric Brownian Motion (GBM) for realistic equity indices with market shock/drawdown
- Financial domain logic (payday seasonality, risk-profiled trading, logistic loan defaults)
- Intentional dirty data injection (~2-3%) for data cleaning practice
- Formatted Excel export via openpyxl (frozen panes, auto column widths, currency formats)
- Clean CSV and compressed Parquet exports in /output folder
- Detailed dirty data log in markdown format
- Terminal execution summary with memory profiling and 10 suggested practice tasks
"""

import os
import sys
import time
import math
import random
import tracemalloc
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ==============================================================================
# CONFIGURATION SECTION
# ==============================================================================
RANDOM_SEED = 42

# Target row counts across sheets (~20,000 rows total)
N_CUSTOMERS = 1000
N_ACCOUNTS = 1400
N_TRANSACTIONS = 8800
N_TRADES = 5000
N_LOANS = 600

# Date boundaries
INDEX_START_DATE = "2025-01-01"
INDEX_END_DATE = "2026-09-30"
CUSTOMER_SIGNUP_START = "2023-01-01"
CUSTOMER_SIGNUP_END = "2025-06-30"
REFERENCE_DATE = "2026-09-30"

# Output paths
OUTPUT_DIR = "output"
EXCEL_RAW_PATH = "northbay_finance_dataset.xlsx"
EXCEL_CLEAN_PATH = "northbay_finance_dataset_clean.xlsx"
DIRTY_LOG_PATH = "dirty_data_log.md"

# Supported Trading Symbols
INDEX_SYMBOLS = ["US500", "US30", "NAS100", "GER40", "JPN225", "HK50", "UK100"]

# Initialize Faker with Asian / Southeast Asian regional coverage
fake_ph = Faker('en_PH')
fake_en = Faker('en_US')
Faker.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


# ==============================================================================
# 1. SHEET GENERATION FUNCTIONS
# ==============================================================================

def generate_customers(n_rows: int = N_CUSTOMERS, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Generate the customers table with realistic Asian/Filipino demographics."""
    rng = np.random.default_rng(seed)
    faker_local = Faker('en_PH')
    faker_local.seed_instance(seed)

    customer_ids = [f"CUST-{i:05d}" for i in range(1, n_rows + 1)]

    # Demographics distribution: 70% Philippines, 30% other Asian hubs
    countries_weights = [
        ("Philippines", 0.70),
        ("Singapore", 0.08),
        ("Malaysia", 0.06),
        ("Indonesia", 0.05),
        ("Thailand", 0.04),
        ("Vietnam", 0.03),
        ("Hong Kong", 0.02),
        ("Japan", 0.02),
    ]
    countries, c_weights = zip(*countries_weights)
    assigned_countries = rng.choice(countries, size=n_rows, p=c_weights)

    city_region_map = {
        "Philippines": [
            ("Manila", "National Capital Region (NCR)"),
            ("Quezon City", "National Capital Region (NCR)"),
            ("Makati", "National Capital Region (NCR)"),
            ("Taguig", "National Capital Region (NCR)"),
            ("Pasig", "National Capital Region (NCR)"),
            ("Cebu City", "Central Visayas (Region VII)"),
            ("Davao City", "Davao Region (Region XI)"),
            ("Iloilo City", "Western Visayas (Region VI)"),
            ("Cagayan de Oro", "Northern Mindanao (Region X)"),
            ("Baguio City", "Cordillera Administrative Region (CAR)"),
            ("Calamba", "Calabarzon (Region IV-A)"),
            ("Angeles City", "Central Luzon (Region III)"),
        ],
        "Singapore": [("Singapore", "Central")],
        "Malaysia": [("Kuala Lumpur", "Federal Territories"), ("Penang", "Penang"), ("Johor Bahru", "Johor")],
        "Indonesia": [("Jakarta", "DKI Jakarta"), ("Surabaya", "East Java"), ("Bandung", "West Java")],
        "Thailand": [("Bangkok", "Central"), ("Chiang Mai", "North"), ("Phuket", "South")],
        "Vietnam": [("Ho Chi Minh City", "Southeast"), ("Hanoi", "Red River Delta"), ("Da Nang", "South Central")],
        "Hong Kong": [("Hong Kong", "Hong Kong Island"), ("Kowloon", "Kowloon")],
        "Japan": [("Tokyo", "Kanto"), ("Osaka", "Kansai")],
    }

    cities = []
    regions = []
    for c in assigned_countries:
        opts = city_region_map[c]
        chosen = opts[rng.integers(0, len(opts))]
        cities.append(chosen[0])
        regions.append(chosen[1])

    # Gender
    genders = rng.choice(["Male", "Female"], size=n_rows, p=[0.53, 0.47])

    # Names (realistic synthesis)
    names = []
    for g in genders:
        if g == "Male":
            first = faker_local.first_name_male()
        else:
            first = faker_local.first_name_female()
        last = faker_local.last_name()
        names.append(f"{first} {last}")

    # Birth dates: Ages 21 to 68 relative to 2025
    days_offset = rng.integers(21 * 365, 68 * 365, size=n_rows)
    ref_dt = np.datetime64("2025-01-01")
    birth_dates = pd.to_datetime(ref_dt - days_offset.astype("timedelta64[D]")).strftime("%Y-%m-%d")

    # Occupations (mix of professional, BPO, SME, medical, tech, gig)
    occupations_pool = [
        "Software Engineer", "BPO Operations Manager", "Registered Nurse", "Certified Public Accountant",
        "Digital Marketing Lead", "SME Retail Owner", "Virtual Assistant", "Financial Analyst",
        "Civil Engineer", "Physician", "Data Analyst", "High School Teacher", "Sales Executive",
        "E-Commerce Merchant", "Logistics Coordinator", "Graphic Designer", "Bank Branch Officer",
        "Customer Service Specialist", "Corporate Lawyer", "Architect"
    ]
    occupations = rng.choice(occupations_pool, size=n_rows)

    # Annual Income (PHP): Lognormal distribution (realistic Philippine white-collar & middle/upper-middle class)
    # Median ~ PHP 520,000, 25th percentile ~ PHP 340,000, 90th percentile ~ PHP 1,450,000, tail up to 8M+
    log_income = rng.normal(loc=13.15, scale=0.68, size=n_rows)
    annual_income = np.round(np.exp(log_income), -2).astype(np.float32)
    # Clip extreme lows to minimum wage floor ~ PHP 180,000
    annual_income = np.clip(annual_income, 180000.0, 15000000.0)

    # Risk Profile
    risk_profiles = rng.choice(["Conservative", "Moderate", "Aggressive"], size=n_rows, p=[0.30, 0.46, 0.24])

    # KYC Status
    kyc_statuses = rng.choice(["Verified", "Pending", "Rejected"], size=n_rows, p=[0.89, 0.08, 0.03])

    # Signup Date
    start_ts = pd.to_datetime(CUSTOMER_SIGNUP_START).value // 10**9
    end_ts = pd.to_datetime(CUSTOMER_SIGNUP_END).value // 10**9
    rand_ts = rng.integers(start_ts, end_ts, size=n_rows)
    signup_dates = pd.to_datetime(rand_ts, unit='s').strftime("%Y-%m-%d")

    # Acquisition Channel
    channels = ["Facebook", "Referral", "Google", "LinkedIn", "Organic", "IB Partner"]
    channel_weights = [0.28, 0.22, 0.20, 0.12, 0.10, 0.08]
    acquisition_channels = rng.choice(channels, size=n_rows, p=channel_weights)

    # is_active (Rejected KYC customers are inactive)
    is_active_flags = rng.choice([True, False], size=n_rows, p=[0.87, 0.13])
    for i, kyc in enumerate(kyc_statuses):
        if kyc == "Rejected":
            is_active_flags[i] = False

    df = pd.DataFrame({
        "customer_id": customer_ids,
        "full_name": names,
        "gender": genders,
        "birth_date": birth_dates,
        "city": cities,
        "region": regions,
        "country": assigned_countries,
        "occupation": occupations,
        "annual_income_php": annual_income,
        "risk_profile": risk_profiles,
        "kyc_status": kyc_statuses,
        "signup_date": signup_dates,
        "acquisition_channel": acquisition_channels,
        "is_active": is_active_flags
    })

    return df


def generate_accounts(customers_df: pd.DataFrame, n_rows: int = N_ACCOUNTS, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Generate accounts ensuring relational integrity with customers."""
    rng = np.random.default_rng(seed)
    account_ids = [f"ACC-{i:05d}" for i in range(1, n_rows + 1)]

    # Guarantee 1 primary account for each of the 1,000 customers
    cust_ids = customers_df["customer_id"].tolist()
    signup_map = dict(zip(customers_df["customer_id"], pd.to_datetime(customers_df["signup_date"])))
    is_active_map = dict(zip(customers_df["customer_id"], customers_df["is_active"]))
    kyc_map = dict(zip(customers_df["customer_id"], customers_df["kyc_status"]))

    assigned_cust = list(cust_ids)

    # Remaining accounts assigned to verified/active customers
    eligible_cust = [cid for cid in cust_ids if kyc_map[cid] == "Verified" and is_active_map[cid]]
    extra_cust = rng.choice(eligible_cust, size=n_rows - len(cust_ids), replace=True).tolist()
    assigned_cust.extend(extra_cust)

    # Account types: Savings (~45%), Trading (~37%), Loan (~18%)
    # Let's target roughly: 620 Savings, 510 Trading, 270 Loan accounts
    type_pool = (
        ["Savings"] * 620 +
        ["Trading"] * 510 +
        ["Loan"] * 270
    )
    rng.shuffle(type_pool)
    account_types = type_pool[:n_rows]

    # Currency selection:
    # Savings: mostly PHP (90% PHP, 10% USD)
    # Trading: international indices trade in USD or PHP (65% USD, 35% PHP)
    # Loan: 100% PHP
    currencies = []
    for at in account_types:
        if at == "Loan":
            currencies.append("PHP")
        elif at == "Trading":
            currencies.append("USD" if rng.random() < 0.65 else "PHP")
        else:
            currencies.append("PHP" if rng.random() < 0.90 else "USD")

    # Dates: open_date >= signup_date
    open_dates = []
    close_dates = []
    statuses = []

    ref_end = pd.to_datetime(REFERENCE_DATE)

    for i in range(n_rows):
        cid = assigned_cust[i]
        c_signup = signup_map[cid]
        # Open delay: 0 to 45 days after customer signup
        days_delay = int(rng.integers(0, 46))
        a_open = c_signup + timedelta(days=days_delay)
        if a_open > ref_end:
            a_open = ref_end - timedelta(days=int(rng.integers(10, 60)))
        open_dates.append(a_open)

        # Status: Active (83%), Inactive (10%), Closed (7%)
        st = rng.choice(["Active", "Inactive", "Closed"], p=[0.83, 0.10, 0.07])
        if not is_active_map[cid]:
            st = rng.choice(["Inactive", "Closed"], p=[0.60, 0.40])

        if st == "Closed":
            dur_days = int(rng.integers(90, 450))
            a_close = a_open + timedelta(days=dur_days)
            if a_close > ref_end:
                a_close = ref_end - timedelta(days=int(rng.integers(1, 30)))
            close_dates.append(a_close)
        else:
            close_dates.append(pd.NaT)

        statuses.append(st)

    df = pd.DataFrame({
        "account_id": account_ids,
        "customer_id": assigned_cust,
        "account_type": account_types,
        "currency": currencies,
        "open_date": [d.strftime("%Y-%m-%d") for d in open_dates],
        "close_date": [d.strftime("%Y-%m-%d") if pd.notna(d) else None for d in close_dates],
        "status": statuses,
        "current_balance": np.zeros(n_rows, dtype=np.float32)  # Will be reconciled after transactions
    })

    return df


def generate_index_prices(start_date: str = INDEX_START_DATE, end_date: str = INDEX_END_DATE, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """
    Generate daily OHLC prices for 7 global equity indices using Geometric Brownian Motion (GBM).
    Weekdays only, including a sharp drawdown period (e.g. August 2025 liquidity squeeze).
    """
    rng = np.random.default_rng(seed)

    # Weekdays only
    b_dates = pd.bdate_range(start=start_date, end=end_date)
    n_days = len(b_dates)
    dt = 1.0 / 252.0  # Daily step in annual trading year

    # Index parameters: (initial_price, annual_drift_mu, annual_volatility_sigma, point_value)
    index_params = {
        "US500":  {"S0": 5880.0, "mu": 0.085, "sigma": 0.155, "spread": 0.50},
        "US30":   {"S0": 42500.0, "mu": 0.070, "sigma": 0.138, "spread": 2.00},
        "NAS100": {"S0": 21050.0, "mu": 0.115, "sigma": 0.225, "spread": 1.20},
        "GER40":  {"S0": 19950.0, "mu": 0.075, "sigma": 0.175, "spread": 1.50},
        "JPN225": {"S0": 39200.0, "mu": 0.070, "sigma": 0.210, "spread": 5.00},
        "HK50":   {"S0": 19650.0, "mu": 0.045, "sigma": 0.255, "spread": 3.00},
        "UK100":  {"S0": 8280.0,  "mu": 0.055, "sigma": 0.128, "spread": 1.00},
    }

    all_rows = []

    # Market drawdown period: August 1, 2025 to August 18, 2025 (Yen carry-trade & tech unwind shock)
    drawdown_start = pd.to_datetime("2025-08-01")
    drawdown_end = pd.to_datetime("2025-08-18")

    for symbol in INDEX_SYMBOLS:
        p = index_params[symbol]
        S0 = p["S0"]
        mu = p["mu"]
        sigma = p["sigma"]

        prices_close = np.zeros(n_days, dtype=np.float64)
        prices_close[0] = S0

        # Generate standard normal increments
        Z = rng.standard_normal(n_days)

        # Apply drawdown shock to increments during the crash window
        for t, d in enumerate(b_dates):
            if drawdown_start <= d <= drawdown_end:
                # Severe negative drift shock and 2.5x volatility
                Z[t] = Z[t] * 2.2 - 2.8

        for t in range(1, n_days):
            drift = (mu - 0.5 * sigma**2) * dt
            diffusion = sigma * math.sqrt(dt) * Z[t]
            prices_close[t] = prices_close[t - 1] * math.exp(drift + diffusion)

        # Generate Open, High, Low, Volume
        for t in range(n_days):
            c = prices_close[t]
            if t == 0:
                o = S0 * (1.0 + rng.normal(0, 0.001))
            else:
                # Open with small overnight gap from yesterday's close
                prev_c = prices_close[t - 1]
                gap = rng.normal(0, 0.0025 * (sigma / 0.15))
                o = prev_c * (1.0 + gap)

            # Daily intraday range proportional to volatility
            daily_vol = sigma * math.sqrt(dt)
            high_wiggle = abs(rng.normal(0, daily_vol * 1.2))
            low_wiggle = abs(rng.normal(0, daily_vol * 1.2))

            h = max(o, c) * (1.0 + high_wiggle) + p["spread"] * 0.5
            l = min(o, c) * (1.0 - low_wiggle) - p["spread"] * 0.5

            # Volume: base lognormal scaled up during drawdown/high volatility
            vol_multiplier = 2.4 if (drawdown_start <= b_dates[t] <= drawdown_end) else 1.0
            base_vol = rng.lognormal(mean=11.5, sigma=0.45) * vol_multiplier
            volume = int(round(base_vol))

            all_rows.append({
                "date": b_dates[t].strftime("%Y-%m-%d"),
                "symbol": symbol,
                "open": round(float(o), 2),
                "high": round(float(h), 2),
                "low": round(float(l), 2),
                "close": round(float(c), 2),
                "volume": volume
            })

    df = pd.DataFrame(all_rows)
    # Sort by date and symbol
    df.sort_values(by=["date", "symbol"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def generate_transactions(accounts_df: pd.DataFrame, n_rows: int = N_TRANSACTIONS, seed: int = RANDOM_SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate realistic transactions with payday seasonality, account compatibility,
    and update current_balance on accounts_df to accurately reconcile.
    """
    rng = np.random.default_rng(seed)

    # Filter eligible accounts (Active and Inactive, Closed can have past transactions)
    acc_records = accounts_df[["account_id", "customer_id", "account_type", "currency", "open_date", "close_date", "status"]].to_dict("records")
    n_accounts = len(acc_records)

    # Initial ledger accumulator per account
    ledger_balance = {acc["account_id"]: 0.0 for acc in acc_records}

    transaction_ids = [f"TXN-{i:06d}" for i in range(1, n_rows + 1)]

    # Transaction type distributions per account type
    type_options = {
        "Savings": ["Deposit", "Withdrawal", "Transfer", "Interest", "Fee"],
        "Savings_p": [0.46, 0.34, 0.12, 0.05, 0.03],
        "Trading": ["Deposit", "Withdrawal", "Transfer", "Fee"],
        "Trading_p": [0.48, 0.32, 0.14, 0.06],
        "Loan": ["Loan Disbursement", "Loan Repayment", "Fee", "Interest"],
        "Loan_p": [0.10, 0.82, 0.04, 0.04],
    }

    payment_methods_php = ["GCash", "Maya", "Bank Transfer", "Card"]
    payment_methods_php_p = [0.42, 0.28, 0.22, 0.08]
    payment_methods_usd = ["Bank Transfer", "Card", "Crypto"]
    payment_methods_usd_p = [0.55, 0.30, 0.15]

    statuses = ["Completed", "Pending", "Failed", "Reversed"]
    status_weights = [0.93, 0.03, 0.025, 0.015]

    ref_end = pd.to_datetime(REFERENCE_DATE)

    # Pre-parse account dates to avoid costly re-parsing inside the loop
    for a in acc_records:
        a["_o_dt"] = pd.to_datetime(a["open_date"])
        c_val = a["close_date"]
        if pd.isna(c_val) or c_val is None or str(c_val).strip() in ("", "None", "NaT"):
            a["_max_dt"] = ref_end
        else:
            c_date = pd.to_datetime(c_val)
            a["_max_dt"] = min(c_date, ref_end) if pd.notna(c_date) else ref_end
        a["_days_span"] = max(int((a["_max_dt"] - a["_o_dt"]).days), 1)

    rows = []

    # Pre-sample account indices weighted toward active accounts
    acc_weights = np.array([1.2 if a["status"] == "Active" else 0.4 if a["status"] == "Inactive" else 0.2 for a in acc_records])
    acc_weights /= acc_weights.sum()
    chosen_indices = rng.choice(n_accounts, size=n_rows, p=acc_weights)

    for i in range(n_rows):
        txn_id = transaction_ids[i]
        acc = acc_records[chosen_indices[i]]
        acc_id = acc["account_id"]
        acc_type = acc["account_type"]
        curr = acc["currency"]
        o_date = acc["_o_dt"]
        days_span = acc["_days_span"]

        # Date sampling with payday & seasonal weighting
        # Payday logic: 15th and 30th (quincena in the Philippines)
        # December bonus: 13th month pay in the Philippines
        for _ in range(3):
            candidate_day = o_date + timedelta(days=int(rng.integers(0, days_span)))
            day_of_month = candidate_day.day
            month = candidate_day.month
            prob = 0.35
            if day_of_month in [14, 15, 16, 28, 29, 30, 31]:
                prob *= 2.8  # Payday surge
            if month == 12:
                prob *= 1.8  # December holiday & 13th-month bonus surge
            if rng.random() < min(prob, 1.0):
                final_date = candidate_day
                break
        else:
            final_date = o_date + timedelta(days=int(rng.integers(0, days_span)))

        # Add realistic business hour timestamp (08:00 to 22:00)
        hour = int(rng.integers(8, 22))
        minute = int(rng.integers(0, 60))
        second = int(rng.integers(0, 60))
        txn_ts = final_date.replace(hour=hour, minute=minute, second=second)

        # Transaction type
        types = type_options[acc_type]
        t_weights = type_options[f"{acc_type}_p"]
        t_type = rng.choice(types, p=t_weights)

        # Amount synthesis (Lognormal, scaled by currency and transaction type)
        if curr == "PHP":
            if t_type in ["Deposit", "Transfer"]:
                # Normal deposits: median ~ PHP 15,000, 90th percentile ~ PHP 85,000
                amt = float(np.round(rng.lognormal(mean=9.6, sigma=0.85), -1))
                amt = max(amt, 200.0)
            elif t_type == "Withdrawal":
                amt = float(np.round(rng.lognormal(mean=9.2, sigma=0.80), -1))
                amt = max(amt, 100.0)
            elif t_type == "Loan Disbursement":
                amt = float(np.round(rng.lognormal(mean=11.5, sigma=0.75), -2))
            elif t_type == "Loan Repayment":
                amt = float(np.round(rng.lognormal(mean=8.8, sigma=0.55), -1))
                amt = max(amt, 1000.0)
            elif t_type == "Fee":
                amt = float(rng.choice([25.0, 50.0, 100.0, 150.0, 250.0, 500.0]))
            else:  # Interest
                amt = float(round(rng.uniform(12.50, 850.00), 2))
        else:  # USD
            if t_type in ["Deposit", "Transfer"]:
                amt = float(np.round(rng.lognormal(mean=6.2, sigma=0.85), 0))
                amt = max(amt, 50.0)
            elif t_type == "Withdrawal":
                amt = float(np.round(rng.lognormal(mean=5.8, sigma=0.80), 0))
                amt = max(amt, 20.0)
            elif t_type == "Fee":
                amt = float(rng.choice([5.0, 10.0, 15.0, 25.0]))
            else:  # Interest / other
                amt = float(round(rng.uniform(1.50, 45.00), 2))

        # Payment method
        if curr == "PHP":
            pm = rng.choice(payment_methods_php, p=payment_methods_php_p)
        else:
            pm = rng.choice(payment_methods_usd, p=payment_methods_usd_p)

        # Status
        st = rng.choice(statuses, p=status_weights)

        # Description
        desc_map = {
            "Deposit": {
                "GCash": "GCash Cash-In via App",
                "Maya": "Maya Wallet Transfer to Account",
                "Bank Transfer": "PESONet / InstaPay Inward Deposit",
                "Card": "Debit/Credit Card Online Top-Up",
                "Crypto": "USDT/BTC Deposit to Brokerage"
            },
            "Withdrawal": {
                "GCash": "Express Withdrawal to GCash",
                "Maya": "Withdrawal to Maya Wallet",
                "Bank Transfer": "Outward Remittance to Local Bank",
                "Card": "Card Payout Refund",
                "Crypto": "Crypto Withdrawal to External Wallet"
            },
            "Transfer": {
                "Bank Transfer": "Inter-account Portfolio Transfer",
                "GCash": "Transfer via GCash Partner Gateway",
                "Maya": "Internal Maya Settlement",
                "Card": "Fund Transfer via Card Network",
                "Crypto": "Internal Trading Wallet Allocation"
            },
            "Fee": {
                "Bank Transfer": "Monthly Maintenance Fee",
                "Card": "Card Processing Fee",
                "GCash": "Platform Convenience Fee",
                "Maya": "Gateway Transaction Charge",
                "Crypto": "Network Gas / Routing Fee"
            },
            "Interest": {
                "Bank Transfer": "Monthly High-Yield Savings Interest",
                "GCash": "Yield Interest Credited",
                "Maya": "Digital Savings Interest Payout",
                "Card": "Interest Adjustment",
                "Crypto": "Staking / Holding Yield"
            },
            "Loan Disbursement": {
                "Bank Transfer": "Initial Principal Loan Disbursement",
                "GCash": "Loan Proceeds to GCash Account",
                "Maya": "Loan Proceeds to Maya Account",
                "Card": "Loan Credit Allocation",
                "Crypto": "Loan Liquidity Transfer"
            },
            "Loan Repayment": {
                "GCash": "Auto-Debit Loan Amortization (GCash)",
                "Maya": "Monthly Amortization (Maya)",
                "Bank Transfer": "Over-the-Counter / ADA Loan Payment",
                "Card": "Scheduled Card Loan Payment",
                "Crypto": "Digital Repayment Settlement"
            }
        }
        desc = desc_map.get(t_type, {}).get(pm, f"{t_type} via {pm}")

        # Ledger balance tracking (only completed transactions impact current_balance)
        if st == "Completed":
            if t_type in ["Deposit", "Interest", "Loan Disbursement"]:
                ledger_balance[acc_id] += amt
            elif t_type in ["Withdrawal", "Fee", "Loan Repayment"]:
                ledger_balance[acc_id] -= amt
            elif t_type == "Transfer":
                # Outward transfer net reduction
                ledger_balance[acc_id] -= amt * 0.4

        rows.append({
            "transaction_id": txn_id,
            "account_id": acc_id,
            "timestamp": txn_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "transaction_type": t_type,
            "amount": round(amt, 2),
            "currency": curr,
            "payment_method": pm,
            "status": st,
            "description": desc
        })

    txn_df = pd.DataFrame(rows)
    # Sort chronologically
    txn_df.sort_values(by="timestamp", inplace=True)
    txn_df.reset_index(drop=True, inplace=True)

    # Reconcile accounts current_balance:
    # Ensure positive balance for savings/trading, and realistic remaining balance for loans
    updated_accs = accounts_df.copy()
    bal_list = []
    for _, a in updated_accs.iterrows():
        aid = a["account_id"]
        atype = a["account_type"]
        cur = a["currency"]
        net_flow = ledger_balance[aid]

        if atype in ["Savings", "Trading"]:
            # If net flow is zero or negative, add an initial seed deposit buffer
            if net_flow <= 0:
                base = rng.uniform(5000, 50000) if cur == "PHP" else rng.uniform(150, 1500)
                final_bal = round(base + max(net_flow, -base * 0.8), 2)
            else:
                final_bal = round(net_flow, 2)
            # If account is closed, final balance is typically 0
            if a["status"] == "Closed":
                final_bal = 0.0
        else:  # Loan account
            # Loan balance is remaining unpaid principal
            base_loan = rng.uniform(25000, 250000)
            final_bal = round(max(base_loan - max(net_flow, 0), 0.0), 2)
            if a["status"] == "Closed":
                final_bal = 0.0

        bal_list.append(float(final_bal))

    updated_accs["current_balance"] = np.array(bal_list, dtype=np.float32)

    return txn_df, updated_accs


def generate_trades(
    accounts_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    index_prices_df: pd.DataFrame,
    n_rows: int = N_TRADES,
    seed: int = RANDOM_SEED
) -> pd.DataFrame:
    """
    Generate CFD trades on global indices.
    Prices strictly map to index_prices on trade dates.
    Aggressive customers trade larger lots, use higher leverage, and lose more often.
    """
    rng = np.random.default_rng(seed)

    trade_ids = [f"TRD-{i:05d}" for i in range(1, n_rows + 1)]

    # Filter Trading accounts only
    trading_accs = accounts_df[accounts_df["account_type"] == "Trading"].copy()
    # Join with customers to obtain risk profile
    trading_accs = trading_accs.merge(
        customers_df[["customer_id", "risk_profile"]],
        on="customer_id",
        how="inner"
    )

    acc_pool = trading_accs.to_dict("records")
    n_trading_accs = len(acc_pool)

    # Index price lookup table by (symbol, date)
    price_lookup = {}
    for r in index_prices_df.to_dict("records"):
        price_lookup[(r["symbol"], r["date"])] = r

    unique_dates = sorted(index_prices_df["date"].unique())
    n_dates = len(unique_dates)

    # Precompute valid trading date index window for each trading account
    acc_date_ranges = {}
    for acc in acc_pool:
        aid = acc["account_id"]
        o_dt = acc["open_date"]
        c_val = acc["close_date"]
        c_dt = None if (pd.isna(c_val) or c_val is None or str(c_val).strip() in ("", "None", "NaT")) else str(c_val)

        start_i = 0
        for idx, d_str in enumerate(unique_dates):
            if d_str >= o_dt:
                start_i = idx
                break

        end_i = n_dates - 1
        if c_dt:
            for idx in range(n_dates - 1, -1, -1):
                if unique_dates[idx] <= c_dt:
                    end_i = idx
                    break

        if end_i - start_i < 5:
            start_i = max(0, min(start_i, n_dates - 7))
            end_i = min(n_dates - 1, start_i + 6)

        acc_date_ranges[aid] = (start_i, end_i)

    rows = []

    # Pre-select accounts
    chosen_acc_indices = rng.choice(n_trading_accs, size=n_rows)

    for i in range(n_rows):
        trd_id = trade_ids[i]
        acc = acc_pool[chosen_acc_indices[i]]
        acc_id = acc["account_id"]
        risk_profile = acc["risk_profile"]

        # Symbol selection
        symbol = rng.choice(INDEX_SYMBOLS)

        # Direction
        direction = rng.choice(["Buy", "Sell"], p=[0.52, 0.48])

        # Pick open date and close date respecting account dates
        start_i, end_i = acc_date_ranges[acc_id]
        max_open = max(start_i, end_i - 5)
        if max_open > start_i:
            open_idx = int(rng.integers(start_i, max_open + 1))
        else:
            open_idx = start_i

        open_date_str = unique_dates[open_idx]

        # Trade duration: 0 (intraday) to 5 days, capped at end_i
        max_hold = min(5, end_i - open_idx)
        holding_days = int(rng.integers(0, max_hold + 1)) if max_hold > 0 else 0
        close_idx = open_idx + holding_days
        close_date_str = unique_dates[close_idx]

        open_p_record = price_lookup[(symbol, open_date_str)]
        close_p_record = price_lookup[(symbol, close_date_str)]

        # Timestamps
        o_hour = int(rng.integers(9, 16))
        o_min = int(rng.integers(0, 60))
        o_sec = int(rng.integers(0, 60))
        open_time = f"{open_date_str} {o_hour:02d}:{o_min:02d}:{o_sec:02d}"

        if holding_days == 0:
            c_hour = min(o_hour + int(rng.integers(1, 6)), 23)
            c_min = int(rng.integers(0, 60))
            c_sec = int(rng.integers(0, 60))
        else:
            c_hour = int(rng.integers(9, 21))
            c_min = int(rng.integers(0, 60))
            c_sec = int(rng.integers(0, 60))
        close_time = f"{close_date_str} {c_hour:02d}:{c_min:02d}:{c_sec:02d}"

        # Risk-profile differentiation
        if risk_profile == "Aggressive":
            # Trade bigger lots, higher leverage, lower win rate (~35%)
            lot_size = float(round(rng.lognormal(mean=0.2, sigma=0.65), 2))
            lot_size = np.clip(lot_size, 0.20, 8.00)
            leverage = int(rng.choice([100, 200, 500], p=[0.40, 0.45, 0.15]))
            is_winner = rng.random() < 0.35
            possible_reasons = ["SL Hit", "Manual", "Margin Call"]
            reason_p = [0.45, 0.35, 0.20]
        elif risk_profile == "Moderate":
            # Medium lots, balanced leverage, ~48% win rate
            lot_size = float(round(rng.lognormal(mean=-0.8, sigma=0.55), 2))
            lot_size = np.clip(lot_size, 0.05, 2.50)
            leverage = int(rng.choice([50, 100, 200], p=[0.40, 0.45, 0.15]))
            is_winner = rng.random() < 0.48
            possible_reasons = ["TP Hit", "SL Hit", "Manual"]
            reason_p = [0.42, 0.38, 0.20]
        else:  # Conservative
            # Small lots, conservative leverage, ~53% win rate
            lot_size = float(round(rng.lognormal(mean=-1.8, sigma=0.45), 2))
            lot_size = np.clip(lot_size, 0.01, 0.80)
            leverage = int(rng.choice([20, 50, 100], p=[0.50, 0.40, 0.10]))
            is_winner = rng.random() < 0.53
            possible_reasons = ["TP Hit", "SL Hit", "Manual"]
            reason_p = [0.48, 0.32, 0.20]

        # Determine Open Price from index OHLC
        o_high = max(float(open_p_record["high"]), float(open_p_record["low"]))
        o_low = min(float(open_p_record["high"]), float(open_p_record["low"]))
        open_price = round(float(rng.uniform(o_low, o_high)), 2)

        # SL and TP levels relative to open_price
        atr_approx = max(open_price * 0.015, 1.0)
        if direction == "Buy":
            stop_loss = round(open_price - rng.uniform(1.0, 2.5) * atr_approx, 2)
            take_profit = round(open_price + rng.uniform(1.5, 3.5) * atr_approx, 2)
        else:
            stop_loss = round(open_price + rng.uniform(1.0, 2.5) * atr_approx, 2)
            take_profit = round(open_price - rng.uniform(1.5, 3.5) * atr_approx, 2)

        # Close session price bounds
        c_low = min(float(close_p_record["low"]), float(close_p_record["high"]))
        c_high = max(float(close_p_record["low"]), float(close_p_record["high"]))

        # Close reason and Close Price
        if is_winner:
            close_reason = rng.choice(["TP Hit", "Manual"], p=[0.65, 0.35])
            if close_reason == "TP Hit":
                close_price = take_profit
            else:
                # Favorable intraday price
                if direction == "Buy":
                    b_low = min(max(c_low, open_price), c_high)
                    b_high = c_high
                else:
                    b_low = c_low
                    b_high = max(min(c_high, open_price), c_low)
                close_price = round(float(rng.uniform(min(b_low, b_high), max(b_low, b_high))), 2)
        else:
            close_reason = rng.choice(possible_reasons, p=reason_p)
            if close_reason == "SL Hit":
                close_price = stop_loss
            elif close_reason == "Margin Call":
                close_price = round(stop_loss * 0.985 if direction == "Buy" else stop_loss * 1.015, 2)
            else:  # Manual exit in loss
                if direction == "Buy":
                    b_low = c_low
                    b_high = max(min(c_high, open_price), c_low)
                else:
                    b_low = min(max(c_low, open_price), c_high)
                    b_high = c_high
                close_price = round(float(rng.uniform(min(b_low, b_high), max(b_low, b_high))), 2)

        # Fees
        commission = round(float(lot_size * 5.0), 2)  # $5 per lot
        swap_fee = round(float(lot_size * holding_days * 1.85), 2) if holding_days > 0 else 0.00

        # Profit / Loss calculation (standard index CFD point contract multiplier)
        # Point multiplier: US500, US30, NAS100 = 1 USD per point per lot
        multiplier = 1.0
        if direction == "Buy":
            gross_pnl = (close_price - open_price) * lot_size * multiplier
        else:
            gross_pnl = (open_price - close_price) * lot_size * multiplier

        net_pnl = round(float(gross_pnl - commission - swap_fee), 2)

        rows.append({
            "trade_id": trd_id,
            "account_id": acc_id,
            "symbol": symbol,
            "direction": direction,
            "open_time": open_time,
            "close_time": close_time,
            "lot_size": lot_size,
            "open_price": open_price,
            "close_price": close_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "leverage": leverage,
            "swap_fee": swap_fee,
            "commission": commission,
            "profit_loss": net_pnl,
            "close_reason": close_reason
        })

    df = pd.DataFrame(rows)
    df.sort_values(by="open_time", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def generate_loans(customers_df: pd.DataFrame, n_rows: int = N_LOANS, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """
    Generate loans with realistic amortization and predictive default correlation.
    Default correlates strongly with low income, low credit score, and high DTI.
    """
    rng = np.random.default_rng(seed)

    loan_ids = [f"LN-{i:05d}" for i in range(1, n_rows + 1)]

    # Sample customers for loans (favor Verified, active customers)
    eligible_cust = customers_df[customers_df["kyc_status"] == "Verified"].copy()
    cust_records = eligible_cust.to_dict("records")
    chosen_cust = rng.choice(cust_records, size=n_rows, replace=False)

    loan_types = ["Salary", "Personal", "SME"]
    type_p = [0.45, 0.40, 0.15]

    terms_months_pool = [6, 12, 18, 24, 36, 48, 60]

    rows = []
    ref_dt = pd.to_datetime(REFERENCE_DATE)

    for i in range(n_rows):
        lid = loan_ids[i]
        c = chosen_cust[i]
        cid = c["customer_id"]
        annual_inc = float(c["annual_income_php"])
        monthly_inc = annual_inc / 12.0
        c_signup = pd.to_datetime(c["signup_date"])

        l_type = rng.choice(loan_types, p=type_p)

        # Principal scaling based on loan type and income
        if l_type == "Salary":
            principal = float(round(rng.uniform(0.5, 2.5) * monthly_inc, -2))
            principal = np.clip(principal, 20000.0, 150000.0)
            term = int(rng.choice([6, 12, 18, 24]))
        elif l_type == "Personal":
            principal = float(round(rng.uniform(1.5, 6.0) * monthly_inc, -3))
            principal = np.clip(principal, 50000.0, 600000.0)
            term = int(rng.choice([12, 24, 36, 48]))
        else:  # SME
            principal = float(round(rng.uniform(4.0, 15.0) * monthly_inc, -4))
            principal = np.clip(principal, 250000.0, 2500000.0)
            term = int(rng.choice([24, 36, 48, 60]))

        # Credit Score (300 to 850, mean ~660, std ~75)
        # Correlated weakly with income
        inc_boost = math.log10(max(annual_inc, 180000.0) / 400000.0) * 45.0
        raw_score = rng.normal(loc=650.0 + inc_boost, scale=68.0)
        credit_score = int(np.clip(round(raw_score), 320, 850))

        # Interest Rate (annual): higher for lower credit score, SME slightly lower
        base_rate = 0.22 - ((credit_score - 300) / 550.0) * 0.13
        interest_rate = float(round(base_rate + rng.normal(0, 0.015), 4))
        interest_rate = np.clip(interest_rate, 0.065, 0.260)

        # Monthly Amortization Formula: P * [ r*(1+r)^n ] / [ (1+r)^n - 1 ]
        monthly_r = interest_rate / 12.0
        n_periods = term
        if monthly_r > 0:
            factor = (1.0 + monthly_r)**n_periods
            monthly_payment = float(round(principal * (monthly_r * factor) / (factor - 1.0), 2))
        else:
            monthly_payment = float(round(principal / n_periods, 2))

        # Loan Start Date: between signup_date and 2026-03-31
        max_start = pd.to_datetime("2026-03-31")
        min_start = max(c_signup, pd.to_datetime("2023-06-01"))
        days_window = max((max_start - min_start).days, 1)
        start_date = min_start + timedelta(days=int(rng.integers(0, days_window)))

        # Elapsed months up to reference date
        elapsed_months = max(int((ref_dt.year - start_date.year) * 12 + (ref_dt.month - start_date.month)), 1)

        # Predictive Default Modeling (for realistic ML classification)
        # Features: DTI, credit_score, income, term
        dti = (monthly_payment * 12.0) / annual_inc
        # Logistic formula: z = beta0 + beta1*DTI + beta2*(score - 650)/100 + beta3*log(inc)
        z = -2.8 + 4.2 * dti - 1.4 * ((credit_score - 650.0) / 100.0) - 0.4 * math.log(annual_inc / 500000.0)
        p_default = 1.0 / (1.0 + math.exp(-z))
        p_default = np.clip(p_default, 0.02, 0.88)

        is_default = rng.random() < p_default

        # Loan Status determination
        if elapsed_months >= term:
            if is_default:
                status = "Default"
                days_past_due = int(rng.integers(91, 365))
                paid_periods = max(int(rng.integers(1, max(term // 2, 2))), 1)
                amount_paid = float(round(monthly_payment * paid_periods, 2))
            else:
                status = "Paid Off"
                days_past_due = 0
                amount_paid = float(round(monthly_payment * term, 2))
        else:
            # Loan still ongoing
            if is_default:
                status = "Default"
                days_past_due = int(rng.integers(91, 240))
                paid_periods = max(int(rng.integers(0, max(elapsed_months - 3, 1))), 0)
                amount_paid = float(round(monthly_payment * paid_periods, 2))
            else:
                # High DTI or borderline score might be "Late"
                if dti > 0.40 and rng.random() < 0.25:
                    status = "Late"
                    days_past_due = int(rng.integers(15, 89))
                    paid_periods = max(elapsed_months - 2, 0)
                    amount_paid = float(round(monthly_payment * paid_periods, 2))
                else:
                    status = "Current"
                    days_past_due = 0
                    amount_paid = float(round(monthly_payment * elapsed_months, 2))

        rows.append({
            "loan_id": lid,
            "customer_id": cid,
            "loan_type": l_type,
            "principal": principal,
            "interest_rate": interest_rate,
            "term_months": term,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "monthly_payment": monthly_payment,
            "amount_paid": amount_paid,
            "days_past_due": days_past_due,
            "status": status,
            "credit_score": credit_score
        })

    df = pd.DataFrame(rows)
    df.sort_values(by="start_date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def generate_data_dictionary() -> pd.DataFrame:
    """Generate the full relational data dictionary."""
    dict_data = [
        # customers
        ("customers", "customer_id", "string", "Unique identifier for each customer (Primary Key)", "CUST-00001"),
        ("customers", "full_name", "string", "Customer's full legal name", "Maria Santos"),
        ("customers", "gender", "string", "Customer self-identified gender (Male/Female)", "Female"),
        ("customers", "birth_date", "date", "Customer date of birth (YYYY-MM-DD)", "1988-04-15"),
        ("customers", "city", "string", "Residential city of customer", "Quezon City"),
        ("customers", "region", "string", "Administrative province/region", "National Capital Region (NCR)"),
        ("customers", "country", "string", "Country of residence across Asia", "Philippines"),
        ("customers", "occupation", "string", "Primary occupation / profession", "Software Engineer"),
        ("customers", "annual_income_php", "float", "Gross annual income in Philippine Pesos (PHP)", "780000.00"),
        ("customers", "risk_profile", "string", "Investment risk tolerance profile (Conservative/Moderate/Aggressive)", "Moderate"),
        ("customers", "kyc_status", "string", "Customer due diligence status (Verified/Pending/Rejected)", "Verified"),
        ("customers", "signup_date", "date", "Platform account registration date (YYYY-MM-DD)", "2023-08-14"),
        ("customers", "acquisition_channel", "string", "Marketing attribution source (Facebook, Referral, Google, etc.)", "Referral"),
        ("customers", "is_active", "boolean", "Current platform active engagement flag (True/False)", "True"),

        # accounts
        ("accounts", "account_id", "string", "Unique account number (Primary Key)", "ACC-00001"),
        ("accounts", "customer_id", "string", "Customer reference ID (Foreign Key -> customers.customer_id)", "CUST-00012"),
        ("accounts", "account_type", "string", "Account product tier (Trading, Savings, Loan)", "Trading"),
        ("accounts", "currency", "string", "Base operating currency of the account (PHP or USD)", "USD"),
        ("accounts", "open_date", "date", "Account activation date (YYYY-MM-DD)", "2023-08-20"),
        ("accounts", "close_date", "date", "Account deactivation date (nullable)", "2024-11-12"),
        ("accounts", "status", "string", "Account operational status (Active/Inactive/Closed)", "Active"),
        ("accounts", "current_balance", "float", "Reconciled ledger cash balance in base currency", "12540.50"),

        # transactions
        ("transactions", "transaction_id", "string", "Unique transaction reference ID (Primary Key)", "TXN-000001"),
        ("transactions", "account_id", "string", "Target account reference (Foreign Key -> accounts.account_id)", "ACC-00045"),
        ("transactions", "timestamp", "datetime", "Transaction execution timestamp (YYYY-MM-DD HH:MM:SS)", "2025-03-15 14:22:10"),
        ("transactions", "transaction_type", "string", "Transaction event type (Deposit, Withdrawal, Transfer, Fee, Interest, Loan Disbursement, Loan Repayment)", "Deposit"),
        ("transactions", "amount", "float", "Gross transaction monetary magnitude in account currency", "15000.00"),
        ("transactions", "currency", "string", "Currency denomination matching target account", "PHP"),
        ("transactions", "payment_method", "string", "Funding rail/channel (GCash, Maya, Bank Transfer, Card, Crypto)", "GCash"),
        ("transactions", "status", "string", "Settlement state (Completed, Pending, Failed, Reversed)", "Completed"),
        ("transactions", "description", "string", "Narrative ledger memo / payment description", "GCash Express Cash-In via App"),

        # index_prices
        ("index_prices", "date", "date", "Trading session business date (YYYY-MM-DD)", "2025-01-02"),
        ("index_prices", "symbol", "string", "Global CFD index ticker symbol (US500, US30, NAS100, GER40, JPN225, HK50, UK100)", "US500"),
        ("index_prices", "open", "float", "Session opening price", "5882.10"),
        ("index_prices", "high", "float", "Highest recorded intraday session price", "5925.40"),
        ("index_prices", "low", "float", "Lowest recorded intraday session price", "5871.20"),
        ("index_prices", "close", "float", "Session closing settlement price", "5910.80"),
        ("index_prices", "volume", "integer", "Total estimated daily contract trading volume", "145200"),

        # trades
        ("trades", "trade_id", "string", "Unique CFD order ticket ID (Primary Key)", "TRD-00001"),
        ("trades", "account_id", "string", "Trading account reference (Foreign Key -> accounts.account_id)", "ACC-00015"),
        ("trades", "symbol", "string", "Tradable index asset ticker (e.g., NAS100)", "NAS100"),
        ("trades", "direction", "string", "Order market side (Buy/Long or Sell/Short)", "Buy"),
        ("trades", "open_time", "datetime", "Order execution entry timestamp (YYYY-MM-DD HH:MM:SS)", "2025-04-10 10:15:30"),
        ("trades", "close_time", "datetime", "Order settlement exit timestamp (YYYY-MM-DD HH:MM:SS)", "2025-04-10 15:45:00"),
        ("trades", "lot_size", "float", "CFD contract trade volume in standard lots", "1.25"),
        ("trades", "open_price", "float", "Order execution entry fill price", "21150.20"),
        ("trades", "close_price", "float", "Order settlement exit fill price", "21310.50"),
        ("trades", "stop_loss", "float", "Predefined risk limit stop loss price level", "20980.00"),
        ("trades", "take_profit", "float", "Predefined profit target price level", "21450.00"),
        ("trades", "leverage", "integer", "Account leverage multiplier utilized (20, 50, 100, 200)", "100"),
        ("trades", "swap_fee", "float", "Financing overnight rollover interest fee in USD", "4.62"),
        ("trades", "commission", "float", "Brokerage execution commission fee in USD", "6.25"),
        ("trades", "profit_loss", "float", "Realized net financial profit or loss after fees in USD", "189.38"),
        ("trades", "close_reason", "string", "Order exit trigger condition (TP Hit, SL Hit, Manual, Margin Call)", "TP Hit"),

        # loans
        ("loans", "loan_id", "string", "Unique credit agreement ID (Primary Key)", "LN-00001"),
        ("loans", "customer_id", "string", "Borrower customer ID (Foreign Key -> customers.customer_id)", "CUST-00108"),
        ("loans", "loan_type", "string", "Credit product category (Salary, Personal, SME)", "Personal"),
        ("loans", "principal", "float", "Original loan principal amount disbursed in PHP", "150000.00"),
        ("loans", "interest_rate", "float", "Fixed annual contractual interest rate", "0.1450"),
        ("loans", "term_months", "integer", "Contract repayment tenure in months", "24"),
        ("loans", "start_date", "date", "Loan origination date (YYYY-MM-DD)", "2024-02-01"),
        ("loans", "monthly_payment", "float", "Contractual fixed monthly amortization payment in PHP", "7236.42"),
        ("loans", "amount_paid", "float", "Cumulative principal and interest amount repaid to date", "115782.72"),
        ("loans", "days_past_due", "integer", "Current delinquency tracking counter in days", "0"),
        ("loans", "status", "string", "Loan repayment status (Current, Late, Default, Paid Off)", "Current"),
        ("loans", "credit_score", "integer", "Credit bureau risk score at underwriting (300-850)", "685"),
    ]

    return pd.DataFrame(dict_data, columns=["sheet", "column", "data_type", "description", "example_value"])


# ==============================================================================
# 2. INTENTIONAL DIRTY DATA INJECTION (2-3% MESSINESS)
# ==============================================================================

def inject_dirty_data(clean_sheets: dict[str, pd.DataFrame], seed: int = RANDOM_SEED) -> tuple[dict[str, pd.DataFrame], list[dict]]:
    """
    Inject intentional anomalies (~2-3%) for data cleaning practice.
    Logs every single injected anomaly into a detailed log table.
    """
    rng = np.random.default_rng(seed)
    dirty_sheets = {k: v.copy(deep=True) for k, v in clean_sheets.items()}
    log_entries = []

    def log_issue(sheet, pkey_col, pkey_val, col, original, dirty, issue_type, cleaning_hint):
        log_entries.append({
            "sheet": sheet,
            "record_id": str(pkey_val),
            "column": col,
            "original_value": str(original),
            "dirty_value": str(dirty),
            "issue_category": issue_type,
            "cleaning_strategy": cleaning_hint
        })

    # ----------------------------------------------------
    # A. DUPLICATE ROWS
    # ----------------------------------------------------
    # 1. Transactions: 20 exact duplicate rows
    txns = dirty_sheets["transactions"]
    dup_txn_indices = rng.choice(len(txns), size=20, replace=False)
    dup_txn_rows = txns.iloc[dup_txn_indices].copy()
    for _, r in dup_txn_rows.iterrows():
        log_issue("transactions", "transaction_id", r["transaction_id"], "ALL", "Single record", "Duplicate row inserted", "Duplicate Row", "Deduplicate on transaction_id or all columns via df.drop_duplicates()")
    dirty_sheets["transactions"] = pd.concat([txns, dup_txn_rows], ignore_index=True)

    # 2. Trades: 10 duplicate rows
    trds = dirty_sheets["trades"]
    dup_trd_indices = rng.choice(len(trds), size=10, replace=False)
    dup_trd_rows = trds.iloc[dup_trd_indices].copy()
    for _, r in dup_trd_rows.iterrows():
        log_issue("trades", "trade_id", r["trade_id"], "ALL", "Single record", "Duplicate row inserted", "Duplicate Row", "Deduplicate on trade_id via df.drop_duplicates(subset=['trade_id'])")
    dirty_sheets["trades"] = pd.concat([trds, dup_trd_rows], ignore_index=True)

    # 3. Customers: 4 duplicate rows
    custs = dirty_sheets["customers"]
    dup_cust_indices = rng.choice(len(custs), size=4, replace=False)
    dup_cust_rows = custs.iloc[dup_cust_indices].copy()
    for _, r in dup_cust_rows.iterrows():
        log_issue("customers", "customer_id", r["customer_id"], "ALL", "Single record", "Duplicate row inserted", "Duplicate Row", "Deduplicate on customer_id")
    dirty_sheets["customers"] = pd.concat([custs, dup_cust_rows], ignore_index=True)

    # ----------------------------------------------------
    # B. MISSING VALUES IN NON-KEY COLUMNS (~2%)
    # ----------------------------------------------------
    # Customers: Missing occupation (25 rows) & acquisition_channel (20 rows)
    c_df = dirty_sheets["customers"]
    null_occ_idx = rng.choice(len(clean_sheets["customers"]), size=25, replace=False)
    for idx in null_occ_idx:
        orig = c_df.at[idx, "occupation"]
        c_df.at[idx, "occupation"] = np.nan
        log_issue("customers", "customer_id", c_df.at[idx, "customer_id"], "occupation", orig, "NaN", "Missing Value", "Impute with 'Unknown' or mode occupation")

    null_chan_idx = rng.choice(len(clean_sheets["customers"]), size=20, replace=False)
    for idx in null_chan_idx:
        orig = c_df.at[idx, "acquisition_channel"]
        c_df.at[idx, "acquisition_channel"] = np.nan
        log_issue("customers", "customer_id", c_df.at[idx, "customer_id"], "acquisition_channel", orig, "NaN", "Missing Value", "Impute with 'Unknown' or direct attribution")

    # Transactions: Missing payment_method (180 rows) & description (120 rows)
    t_df = dirty_sheets["transactions"]
    null_pm_idx = rng.choice(len(clean_sheets["transactions"]), size=180, replace=False)
    for idx in null_pm_idx:
        orig = t_df.at[idx, "payment_method"]
        t_df.at[idx, "payment_method"] = np.nan
        log_issue("transactions", "transaction_id", t_df.at[idx, "transaction_id"], "payment_method", orig, "NaN", "Missing Value", "Infer from description or default to 'Unspecified'")

    null_desc_idx = rng.choice(len(clean_sheets["transactions"]), size=120, replace=False)
    for idx in null_desc_idx:
        orig = t_df.at[idx, "description"]
        t_df.at[idx, "description"] = np.nan
        log_issue("transactions", "transaction_id", t_df.at[idx, "transaction_id"], "description", orig, "NaN", "Missing Value", "Impute standard transaction description from type and currency")

    # Trades: Missing close_reason (85 rows) & swap_fee (60 rows)
    tr_df = dirty_sheets["trades"]
    null_cr_idx = rng.choice(len(clean_sheets["trades"]), size=85, replace=False)
    for idx in null_cr_idx:
        orig = tr_df.at[idx, "close_reason"]
        tr_df.at[idx, "close_reason"] = np.nan
        log_issue("trades", "trade_id", tr_df.at[idx, "trade_id"], "close_reason", orig, "NaN", "Missing Value", "Infer from close_price vs stop_loss and take_profit")

    null_swap_idx = rng.choice(len(clean_sheets["trades"]), size=60, replace=False)
    for idx in null_swap_idx:
        orig = tr_df.at[idx, "swap_fee"]
        tr_df.at[idx, "swap_fee"] = np.nan
        log_issue("trades", "trade_id", tr_df.at[idx, "trade_id"], "swap_fee", orig, "NaN", "Missing Value", "Impute 0.0 for intraday or calculate based on lot size and duration")

    # Loans: Missing credit_score (15 rows)
    l_df = dirty_sheets["loans"]
    null_cs_idx = rng.choice(len(clean_sheets["loans"]), size=15, replace=False)
    for idx in null_cs_idx:
        orig = l_df.at[idx, "credit_score"]
        # Use None/NaN for missing credit score
        l_df.at[idx, "credit_score"] = np.nan
        log_issue("loans", "loan_id", l_df.at[idx, "loan_id"], "credit_score", orig, "NaN", "Missing Value", "Impute using median credit score or predictive regression")

    # ----------------------------------------------------
    # C. INCONSISTENT TEXT VALUES
    # ----------------------------------------------------
    # Customers city: "Manila" variants ("manila ", "MNL", " Manila", "QUEZON CITY", " Quezon City")
    for idx, row in c_df.iterrows():
        if row["city"] == "Manila" and rng.random() < 0.25:
            orig = row["city"]
            variant = rng.choice(["manila ", "MNL", " Manila", "manila", "Metro Manila"])
            c_df.at[idx, "city"] = variant
            log_issue("customers", "customer_id", row["customer_id"], "city", orig, variant, "Text Inconsistency", "Trim whitespace and normalize city names via dictionary or str.title()")
        elif row["city"] == "Quezon City" and rng.random() < 0.20:
            orig = row["city"]
            variant = rng.choice(["QUEZON CITY", " Quezon City", "quezon city", "QC"])
            c_df.at[idx, "city"] = variant
            log_issue("customers", "customer_id", row["customer_id"], "city", orig, variant, "Text Inconsistency", "Clean whitespace and apply standardized casing")

    # Customers gender: "Male" -> "M", "male", " Female" -> "F", "female"
    for idx, row in c_df.iterrows():
        if row["gender"] == "Male" and rng.random() < 0.05:
            orig = row["gender"]
            variant = rng.choice(["M", "male", " Male"])
            c_df.at[idx, "gender"] = variant
            log_issue("customers", "customer_id", row["customer_id"], "gender", orig, variant, "Text Inconsistency", "Map 'M'/'male' to 'Male' and trim leading spaces")
        elif row["gender"] == "Female" and rng.random() < 0.05:
            orig = row["gender"]
            variant = rng.choice(["F", "female", " Female"])
            c_df.at[idx, "gender"] = variant
            log_issue("customers", "customer_id", row["customer_id"], "gender", orig, variant, "Text Inconsistency", "Map 'F'/'female' to 'Female' and trim leading spaces")

    # Transactions payment_method: "GCash" -> "gcash", "G-CASH", " Maya" -> "MAYA"
    for idx, row in t_df.iterrows():
        pm = str(row["payment_method"])
        if pm == "GCash" and rng.random() < 0.04:
            orig = pm
            variant = rng.choice(["gcash", "G-CASH", "GCASH ", "G-Cash"])
            t_df.at[idx, "payment_method"] = variant
            log_issue("transactions", "transaction_id", row["transaction_id"], "payment_method", orig, variant, "Text Inconsistency", "Standardize e-wallet nomenclature to 'GCash'")
        elif pm == "Maya" and rng.random() < 0.04:
            orig = pm
            variant = rng.choice(["maya", "MAYA", " PayMaya", "Maya "])
            t_df.at[idx, "payment_method"] = variant
            log_issue("transactions", "transaction_id", row["transaction_id"], "payment_method", orig, variant, "Text Inconsistency", "Standardize e-wallet nomenclature to 'Maya'")

    # ----------------------------------------------------
    # D. MIXED DATE FORMATS IN ONE COLUMN
    # ----------------------------------------------------
    # Transactions timestamp: ~60 timestamps stored as string formatted "MM/DD/YYYY HH:MM:SS" or "DD-MM-YYYY"
    date_noise_indices = rng.choice(len(clean_sheets["transactions"]), size=60, replace=False)
    for idx in date_noise_indices:
        orig = t_df.at[idx, "timestamp"]
        try:
            dt_obj = pd.to_datetime(orig)
            pattern = rng.choice(["%m/%d/%Y %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%Y/%m/%d %H:%M:%S"])
            dirty_date = dt_obj.strftime(pattern)
            t_df.at[idx, "timestamp"] = dirty_date
            log_issue("transactions", "transaction_id", t_df.at[idx, "transaction_id"], "timestamp", orig, dirty_date, "Mixed Date Format", "Parse dates using pd.to_datetime(..., format='mixed')")
        except Exception:
            pass

    # Customers signup_date: ~25 signup dates stored as "MM/DD/YYYY"
    signup_noise_indices = rng.choice(len(clean_sheets["customers"]), size=25, replace=False)
    for idx in signup_noise_indices:
        orig = c_df.at[idx, "signup_date"]
        try:
            dt_obj = pd.to_datetime(orig)
            pattern = rng.choice(["%m/%d/%Y", "%d/%m/%Y"])
            dirty_signup = dt_obj.strftime(pattern)
            c_df.at[idx, "signup_date"] = dirty_signup
            log_issue("customers", "customer_id", c_df.at[idx, "customer_id"], "signup_date", orig, dirty_signup, "Mixed Date Format", "Normalize dates to ISO-8601 YYYY-MM-DD via pd.to_datetime")
        except Exception:
            pass

    # ----------------------------------------------------
    # E. NEGATIVE AMOUNTS WHERE THEY SHOULDN'T BE
    # ----------------------------------------------------
    # Transactions amount: 6 rows made negative (accidental accounting sign flip)
    neg_txn_indices = rng.choice(len(clean_sheets["transactions"]), size=6, replace=False)
    for idx in neg_txn_indices:
        orig = t_df.at[idx, "amount"]
        dirty_amt = -abs(float(orig))
        t_df.at[idx, "amount"] = dirty_amt
        log_issue("transactions", "transaction_id", t_df.at[idx, "transaction_id"], "amount", orig, dirty_amt, "Negative Amount Anomaly", "Apply abs(amount) or verify against transaction_type debit/credit conventions")

    # Loans principal: 2 rows made negative
    neg_loan_indices = rng.choice(len(clean_sheets["loans"]), size=2, replace=False)
    for idx in neg_loan_indices:
        orig = l_df.at[idx, "principal"]
        dirty_amt = -abs(float(orig))
        l_df.at[idx, "principal"] = dirty_amt
        log_issue("loans", "loan_id", l_df.at[idx, "loan_id"], "principal", orig, dirty_amt, "Negative Principal Anomaly", "Principals must be positive; take abs(principal)")

    # Trades lot_size: 3 rows made negative
    neg_trd_indices = rng.choice(len(clean_sheets["trades"]), size=3, replace=False)
    for idx in neg_trd_indices:
        orig = tr_df.at[idx, "lot_size"]
        dirty_lot = -abs(float(orig))
        tr_df.at[idx, "lot_size"] = dirty_lot
        log_issue("trades", "trade_id", tr_df.at[idx, "trade_id"], "lot_size", orig, dirty_lot, "Negative Lot Size Anomaly", "Lot sizes must be strictly positive; take abs(lot_size)")

    # ----------------------------------------------------
    # F. EXTREME OUTLIERS (FAT-FINGER ERRORS)
    # ----------------------------------------------------
    # 1 transaction with 1,000x normal amount (e.g. 50,000,000 PHP fat-finger deposit)
    outlier_txn_idx = int(rng.integers(0, len(clean_sheets["transactions"])))
    orig_txn_amt = t_df.at[outlier_txn_idx, "amount"]
    outlier_txn_amt = float(round(orig_txn_amt * 1000.0, 2))
    t_df.at[outlier_txn_idx, "amount"] = outlier_txn_amt
    log_issue("transactions", "transaction_id", t_df.at[outlier_txn_idx, "transaction_id"], "amount", orig_txn_amt, outlier_txn_amt, "Extreme Outlier (Fat-Finger)", "Detect via IQR / Z-score filters or domain boundary caps (>10M PHP)")

    # 1 trade with 1,000x lot size (fat finger 500.0 lots instead of 0.50)
    outlier_trd_idx = int(rng.integers(0, len(clean_sheets["trades"])))
    orig_trd_lot = tr_df.at[outlier_trd_idx, "lot_size"]
    outlier_trd_lot = 500.0
    tr_df.at[outlier_trd_idx, "lot_size"] = outlier_trd_lot
    log_issue("trades", "trade_id", tr_df.at[outlier_trd_idx, "trade_id"], "lot_size", orig_trd_lot, outlier_trd_lot, "Extreme Outlier (Fat-Finger)", "Detect via leverage/account margin sanity checks; cap maximum retail lot size")

    # 1 customer with annual income 999,999,999 PHP (placeholder glitch)
    outlier_cust_idx = int(rng.integers(0, len(clean_sheets["customers"])))
    orig_cust_inc = c_df.at[outlier_cust_idx, "annual_income_php"]
    outlier_cust_inc = 999999999.0
    c_df.at[outlier_cust_idx, "annual_income_php"] = outlier_cust_inc
    log_issue("customers", "customer_id", c_df.at[outlier_cust_idx, "customer_id"], "annual_income_php", orig_cust_inc, outlier_cust_inc, "Extreme Outlier (Placeholder Glitch)", "Filter sentinel values (e.g. 999999999) and replace with median or null")

    return dirty_sheets, log_entries


def write_dirty_data_log(log_entries: list[dict], file_path: str = DIRTY_LOG_PATH) -> None:
    """Write comprehensive log of all injected dirty data to markdown."""
    df_log = pd.DataFrame(log_entries)

    # Summary by issue category
    summary = df_log.groupby(["sheet", "issue_category"]).size().reset_index(name="count")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("# Northbay Capital - Intentional Dirty Data Log\n\n")
        f.write("This document logs all intentionally injected anomalies (~2–3% noise level) in `northbay_finance_dataset.xlsx`. ")
        f.write("These issues were designed for data quality inspection, pipeline validation, and data cleaning practice.\n\n")

        f.write("## 1. Summary of Injected Anomalies\n\n")
        f.write("| Sheet | Anomaly Category | Count |\n")
        f.write("|---|---|---|\n")
        for _, r in summary.iterrows():
            f.write(f"| `{r['sheet']}` | **{r['issue_category']}** | {r['count']} |\n")
        f.write(f"| **TOTAL INJECTED ANOMALIES** | | **{len(df_log)}** |\n\n")

        f.write("## 2. Injected Issues Breakdown & Cleaning Recommendations\n\n")
        f.write("1. **Duplicate Rows**:\n")
        f.write("   - *Where*: `transactions` (20 rows), `trades` (10 rows), `customers` (4 rows).\n")
        f.write("   - *Recommended Fix*: Use `df.drop_duplicates(subset=[primary_key])`.\n\n")

        f.write("2. **Missing Values in Non-Key Columns**:\n")
        f.write("   - *Where*: `customers.occupation`, `customers.acquisition_channel`, `transactions.payment_method`, `transactions.description`, `trades.close_reason`, `trades.swap_fee`, `loans.credit_score`.\n")
        f.write("   - *Recommended Fix*: Impute categories with `'Unknown'` or domain heuristics (e.g., infer `close_reason` by comparing `close_price` to `stop_loss` and `take_profit`).\n\n")

        f.write("3. **Inconsistent Text Formatting**:\n")
        f.write("   - *Where*: `city` (e.g., `'manila '`, `'MNL'`, `'QUEZON CITY'`), `gender` (`'M'`, `'male'`, `' Female'`), `payment_method` (`'gcash'`, `'G-CASH'`, `' PayMaya'`).\n")
        f.write("   - *Recommended Fix*: Strip whitespace (`str.strip()`), standardize casing (`str.title()`), and use mapping dictionaries.\n\n")

        f.write("4. **Mixed Date Formats in Timestamp/Date Columns**:\n")
        f.write("   - *Where*: `transactions.timestamp` and `customers.signup_date` containing mixed formats (`MM/DD/YYYY`, `DD-MM-YYYY`, `YYYY-MM-DD`).\n")
        f.write("   - *Recommended Fix*: Use `pd.to_datetime(col, format='mixed')` and enforce ISO-8601 formatting.\n\n")

        f.write("5. **Negative Values in Strictly Positive Columns**:\n")
        f.write("   - *Where*: `transactions.amount` (negative signs from debit exports), `loans.principal`, `trades.lot_size`.\n")
        f.write("   - *Recommended Fix*: Verify transaction debit/credit context, or apply `df[col] = df[col].abs()`.\n\n")

        f.write("6. **Extreme Outliers / Fat-Finger Errors**:\n")
        f.write("   - *Where*: 1000x transaction amount (PHP 50M+ single retail cash-in), 500 lot CFD trade, PHP 999,999,999 customer income.\n")
        f.write("   - *Recommended Fix*: Compute IQR / Z-score filters or apply business threshold caps.\n\n")

        f.write("## 3. Sample Itemized Audit Trail (First 60 Log Entries)\n\n")
        f.write("| Sheet | Record ID | Column | Original Value | Dirty Injected Value | Category | Strategy |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        sample_df = df_log.head(60)
        for _, r in sample_df.iterrows():
            f.write(f"| `{r['sheet']}` | `{r['record_id']}` | `{r['column']}` | `{r['original_value']}` | `{r['dirty_value']}` | {r['issue_category']} | {r['cleaning_strategy']} |\n")

        f.write("\n*(Full audit log contains all " + str(len(df_log)) + " injected modifications)*\n")


# ==============================================================================
# 3. EXCEL FORMATTING & EXPORT (OPENPYXL)
# ==============================================================================

def export_excel_styled(sheets_dict: dict[str, pd.DataFrame], file_path: str) -> None:
    """
    Export all sheets to an Excel workbook with professional corporate formatting:
    - Frozen header panes
    - Bold navy headers with white typography
    - Auto-fitted column widths
    - Proper accounting currency and date format masks
    """
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # Styles
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")  # Corporate Navy
    data_font = Font(name="Calibri", size=10)
    thin_border = Border(
        left=Side(style="thin", color="E0E0E0"),
        right=Side(style="thin", color="E0E0E0"),
        top=Side(style="thin", color="E0E0E0"),
        bottom=Side(style="thin", color="E0E0E0")
    )
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=False)

    align_center = Alignment(horizontal="center", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")

    for sheet_name, df in sheets_dict.items():
        ws = wb.create_sheet(title=sheet_name)
        ws.views.sheetView[0].showGridLines = True
        ws.freeze_panes = "A2"

        # Write Headers
        headers = list(df.columns)
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

        # Determine column formats
        currency_cols = {
            "annual_income_php", "current_balance", "amount", "profit_loss",
            "swap_fee", "commission", "principal", "monthly_payment", "amount_paid"
        }
        price_cols = {"open", "high", "low", "close", "open_price", "close_price", "stop_loss", "take_profit"}
        rate_cols = {"interest_rate"}
        integer_cols = {"volume", "leverage", "term_months", "days_past_due", "credit_score"}

        # Write data rows using fast openpyxl append
        for row_data in df.itertuples(index=False):
            row_cells = []
            for col_idx, val in enumerate(row_data, 1):
                col_name = headers[col_idx - 1]
                if pd.isna(val) or val is None:
                    c_val = ""
                else:
                    c_val = val
                row_cells.append(c_val)
            ws.append(row_cells)

        # Style data cells and apply formats
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=len(headers)):
            for col_idx, cell in enumerate(row, 1):
                col_name = headers[col_idx - 1]
                cell.font = data_font
                cell.border = thin_border

                if col_name in currency_cols:
                    cell.number_format = '#,##0.00'
                    cell.alignment = align_right
                elif col_name in price_cols:
                    cell.number_format = '#,##0.00'
                    cell.alignment = align_right
                elif col_name in rate_cols:
                    cell.number_format = '0.00%'
                    cell.alignment = align_right
                elif col_name in integer_cols:
                    cell.number_format = '#,##0'
                    cell.alignment = align_right
                elif "date" in col_name or "time" in col_name or "id" in col_name:
                    cell.alignment = align_center

        # Fast auto-fit column widths from dataframe directly
        for col_idx, col_name in enumerate(headers, 1):
            col_letter = get_column_letter(col_idx)
            sample_vals = df[col_name].dropna().head(40).astype(str)
            max_len = max([len(str(col_name))] + [len(s) for s in sample_vals])
            ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 35)

    wb.save(file_path)


# ==============================================================================
# 4. CSV & PARQUET EXPORT
# ==============================================================================

def export_csv_and_parquet(sheets_dict: dict[str, pd.DataFrame], output_dir: str = OUTPUT_DIR) -> dict[str, dict[str, str]]:
    """
    Export every sheet as CSV and Parquet with optimized memory dtypes.
    """
    os.makedirs(output_dir, exist_ok=True)
    file_manifest = {}

    for sheet_name, df in sheets_dict.items():
        csv_path = os.path.join(output_dir, f"{sheet_name}.csv")
        parquet_path = os.path.join(output_dir, f"{sheet_name}.parquet")

        # CSV export (UTF-8, no index)
        df.to_csv(csv_path, index=False, encoding="utf-8")

        # Parquet optimization: prepare dtypes for arrow serialization
        pq_df = df.copy()
        for col in pq_df.columns:
            if pq_df[col].dtype == "object":
                # Convert string columns to string dtype for clean pyarrow handling
                pq_df[col] = pq_df[col].astype("string")

        pq_df.to_parquet(parquet_path, engine="pyarrow", compression="snappy", index=False)

        file_manifest[sheet_name] = {
            "csv": csv_path,
            "parquet": parquet_path
        }

    return file_manifest


# ==============================================================================
# 5. MAIN EXECUTION PIPELINE
# ==============================================================================

def main():
    print("=" * 80)
    print("NORTHBAY CAPITAL - SYNTHETIC FINANCE DATASET GENERATION")
    print("=" * 80)
    print(f"Seed: {RANDOM_SEED}")
    print(f"Date Window: {INDEX_START_DATE} to {INDEX_END_DATE}")
    print(f"Target Rows: ~20,000 across core sheets")
    print("-" * 80)

    # Start memory profiling
    tracemalloc.start()
    start_time = time.time()

    # Step 1: Generate domain sheets
    print("--> [1/6] Generating Customers (Demographics & Profiles)...")
    customers_df = generate_customers(n_rows=N_CUSTOMERS, seed=RANDOM_SEED)

    print("--> [2/6] Generating Accounts (Savings, Trading, Loans)...")
    accounts_df = generate_accounts(customers_df, n_rows=N_ACCOUNTS, seed=RANDOM_SEED)

    print("--> [3/6] Generating Index Prices (GBM Simulation with Market Shock)...")
    index_prices_df = generate_index_prices(start_date=INDEX_START_DATE, end_date=INDEX_END_DATE, seed=RANDOM_SEED)

    print("--> [4/6] Generating Transactions & Reconciling Balances (Payday Seasonality)...")
    transactions_df, accounts_df = generate_transactions(accounts_df, n_rows=N_TRANSACTIONS, seed=RANDOM_SEED)

    print("--> [5/6] Generating Trades (Risk Profile Dynamics & Index Mapping)...")
    trades_df = generate_trades(accounts_df, customers_df, index_prices_df, n_rows=N_TRADES, seed=RANDOM_SEED)

    print("--> [6/6] Generating Loans (ML-Ready Credit Amortization & Default)...")
    loans_df = generate_loans(customers_df, n_rows=N_LOANS, seed=RANDOM_SEED)

    data_dict_df = generate_data_dictionary()

    clean_sheets = {
        "customers": customers_df,
        "accounts": accounts_df,
        "transactions": transactions_df,
        "index_prices": index_prices_df,
        "trades": trades_df,
        "loans": loans_df,
        "data_dictionary": data_dict_df
    }

    # Step 2: Inject intentional dirty data (~2-3% noise)
    print("\n--> Injecting intentional dirty data (~2-3% messiness for cleaning practice)...")
    dirty_sheets, log_entries = inject_dirty_data(clean_sheets, seed=RANDOM_SEED)

    # Step 3: Write dirty data log
    print(f"--> Writing dirty data log to {DIRTY_LOG_PATH}...")
    write_dirty_data_log(log_entries, DIRTY_LOG_PATH)

    # Step 4: Export Excel files
    print(f"--> Exporting styled dirty Excel workbook to {EXCEL_RAW_PATH}...")
    export_excel_styled(dirty_sheets, EXCEL_RAW_PATH)

    print(f"--> Exporting styled clean Excel workbook to {EXCEL_CLEAN_PATH}...")
    export_excel_styled(clean_sheets, EXCEL_CLEAN_PATH)

    # Step 5: Export CSV and Parquet
    print(f"--> Exporting CSV and Parquet files to ./{OUTPUT_DIR}/...")
    file_manifest = export_csv_and_parquet(dirty_sheets, OUTPUT_DIR)

    # Profiling results
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    elapsed_time = time.time() - start_time

    # ==============================================================================
    # 6. TERMINAL REPORT & SUMMARY
    # ==============================================================================
    print("\n" + "=" * 80)
    print("DATASET GENERATION SUMMARY")
    print("=" * 80)

    total_data_rows = 0
    print(f"{'Sheet Name':<20} | {'Clean Rows':<12} | {'Dirty Rows':<12} | {'Columns':<8}")
    print("-" * 60)
    for name in ["customers", "accounts", "transactions", "index_prices", "trades", "loans"]:
        c_count = len(clean_sheets[name])
        d_count = len(dirty_sheets[name])
        n_cols = len(clean_sheets[name].columns)
        total_data_rows += d_count
        print(f"{name:<20} | {c_count:<12,d} | {d_count:<12,d} | {n_cols:<8d}")
    print("-" * 60)
    dict_rows = len(clean_sheets["data_dictionary"])
    print(f"{'data_dictionary':<20} | {dict_rows:<12,d} | {dict_rows:<12,d} | {len(clean_sheets['data_dictionary'].columns):<8d}")
    print("=" * 60)
    print(f"GRAND TOTAL (Core Data Sheets): {total_data_rows:,d} rows (~20,000 target)")

    # File size report
    print("\n" + "=" * 80)
    print("FILE SIZE AUDIT")
    print("=" * 80)
    def fmt_sz(path):
        if os.path.exists(path):
            sz = os.path.getsize(path)
            if sz > 1024 * 1024:
                return f"{sz / (1024 * 1024):.2f} MB"
            return f"{sz / 1024:.1f} KB"
        return "N/A"

    print(f"Excel (Dataset with Injected Noise): {EXCEL_RAW_PATH:<34} ({fmt_sz(EXCEL_RAW_PATH)})")
    print(f"Excel (Clean Benchmark Version):     {EXCEL_CLEAN_PATH:<34} ({fmt_sz(EXCEL_CLEAN_PATH)})")
    print(f"Dirty Data Markdown Log:             {DIRTY_LOG_PATH:<34} ({fmt_sz(DIRTY_LOG_PATH)})")
    print("-" * 80)
    print(f"{'Sheet':<20} | {'CSV Size':<15} | {'Parquet Size':<15} | {'Parquet Compression Ratio'}")
    print("-" * 80)
    for name in clean_sheets.keys():
        c_path = file_manifest[name]["csv"]
        p_path = file_manifest[name]["parquet"]
        c_sz = os.path.getsize(c_path)
        p_sz = os.path.getsize(p_path)
        ratio = f"{c_sz / max(p_sz, 1):.2f}x"
        print(f"{name:<20} | {fmt_sz(c_path):<15} | {fmt_sz(p_path):<15} | {ratio}")

    print("-" * 80)
    print(f"Peak Memory Usage : {peak_mem / (1024 * 1024):.2f} MB (Well within 8 GB laptop RAM limit)")
    print(f"Execution Time    : {elapsed_time:.2f} seconds")
    print("=" * 80)

    # ==============================================================================
    # 7. 10 PRACTICE TASKS (DA / DE / DS)
    # ==============================================================================
    print("\n" + "=" * 80)
    print("10 SUGGESTED PRACTICE TASKS")
    print("=" * 80)
    tasks = [
        # Data Analysis
        ("DATA ANALYSIS", "Cohort Retention Analysis",
         "Group customers by signup month and analyze monthly active engagement and transaction frequency over a 12-month window."),
        ("DATA ANALYSIS", "Trader P&L by Risk Profile & Leverage",
         "Analyze whether aggressive traders actually make more money or suffer higher drawdowns and margin calls compared to conservative peers."),
        ("DATA ANALYSIS", "Payday & Seasonal Liquidity Analysis",
         "Visualize daily deposit flows across GCash, Maya, and Bank Transfers to verify quincena (15th/30th) and December bonus liquidity peaks."),
        ("DATA ANALYSIS", "Regional Wealth & Product Affinity",
         "Evaluate average balance and loan demand across Philippine regions (NCR, Central Visayas, Davao) vs. international hubs (SG, MY)."),

        # Data Engineering
        ("DATA ENGINEERING", "Automated Cleaning Pipeline & Log Validation",
         "Write a Python/Polars or DuckDB script that automatically parses dirty_data_log.md, cleans the raw dataset, and asserts equality against clean benchmark."),
        ("DATA ENGINEERING", "Relational Database Schema & Ingestion (SQLite / PostgreSQL)",
         "Create a normalized DDL schema with primary and foreign key constraints, then load the CSV files using batch transactions."),
        ("DATA ENGINEERING", "SCD Type 2 Dimension Table Implementation",
         "Implement Slowly Changing Dimensions (SCD Type 2) tracking customer KYC and account status transitions over time."),

        # Data Science / Machine Learning
        ("DATA SCIENCE / ML", "Loan Default Classification Model",
         "Build an XGBoost / LightGBM model predicting loan default using income, credit score, DTI, and loan term; achieve ROC-AUC > 0.80."),
        ("DATA SCIENCE / ML", "Margin Call Early-Warning System",
         "Develop a binary classification model on trades and market volatility to predict margin calls before trade settlement."),
        ("DATA SCIENCE / ML", "Customer Segmentation & Lifetime Value (LTV)",
         "Apply K-Means or GMM clustering on customer demographics, deposit habits, and trading volumes to segment users into VIP wealth tiers.")
    ]

    for i, (track, title, desc) in enumerate(tasks, 1):
        print(f"\n[{track}] Task {i}: {title}")
        print(f"   -> {desc}")

    print("\n" + "=" * 80)
    print("Generation complete! All files generated and ready for analysis.")
    print("=" * 80)


if __name__ == "__main__":
    main()
