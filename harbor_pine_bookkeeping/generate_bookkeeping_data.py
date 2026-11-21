"""
Harbor & Pine Bookkeeping - Synthetic Data Generation Script
=============================================================
Generates a realistic synthetic relational dataset for Harbor & Pine Bookkeeping,
a small bookkeeping firm serving small businesses in the US, UK, Australia, and New Zealand.

Output:
- bookkeeping.db (SQLite database with PK and FK constraints)
- CSV files in output/ directory:
    - clients.csv (~400 rows)
    - staff.csv (~15 rows)
    - documents.csv (~12,000 rows)
    - billing.csv (~3,000 rows)
    - monthly_closes (~4,500 rows)
"""

import os
import sqlite3
import random
from datetime import date, timedelta
import numpy as np
import pandas as pd
from faker import Faker

# Fixed random seeds for full reproducibility
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
Faker.seed(RANDOM_SEED)
fake = Faker()

# Configuration constants
DATASET_START_DATE = date(2022, 1, 1)
DATASET_END_DATE = date(2024, 12, 31)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "bookkeeping.db")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

COUNTRY_CURRENCY = {
    "US": "USD",
    "UK": "GBP",
    "AU": "AUD",
    "NZ": "NZD"
}

INDUSTRIES = [
    "Restaurant", "Retail", "Construction", "Consulting",
    "Healthcare", "E-commerce", "Real Estate", "Trades"
]

ACQUISITION_SOURCES = [
    "Referral", "Google", "LinkedIn", "Accountant Partner", "Facebook"
]

PLAN_TIERS = ["Basic", "Standard", "Premium"]

DOC_TYPES = ["Receipt", "Supplier Invoice", "Bank Statement", "Payroll Report"]
SOURCE_CHANNELS = ["Email", "Upload", "Photo", "Paper Scan"]

def generate_staff():
    """Generates ~15 staff members with realistic roles, hire dates, and hourly costs."""
    staff_records = []
    
    # 2 Managers, 4 Senior Bookkeepers, 9 Bookkeepers
    roles_config = [
        ("Manager", 2, (80.0, 95.0), date(2019, 3, 1), date(2020, 6, 30)),
        ("Senior Bookkeeper", 4, (50.0, 65.0), date(2020, 1, 1), date(2021, 6, 30)),
        ("Bookkeeper", 9, (30.0, 40.0), date(2020, 6, 1), date(2021, 12, 1))
    ]
    
    staff_id = 1
    for role, count, cost_range, min_hire, max_hire in roles_config:
        hire_span = (max_hire - min_hire).days
        for _ in range(count):
            hire_offset = np.random.randint(0, hire_span + 1)
            hire_dt = min_hire + timedelta(days=int(hire_offset))
            cost = round(float(np.random.uniform(cost_range[0], cost_range[1])), 2)
            staff_records.append({
                "staff_id": staff_id,
                "full_name": fake.name(),
                "role": role,
                "hire_date": hire_dt.strftime("%Y-%m-%d"),
                "hourly_cost": cost
            })
            staff_id += 1
            
    return pd.DataFrame(staff_records)

def generate_clients():
    """Generates ~400 clients with realistic industry, country, tier, and status."""
    clients_records = []
    num_clients = 400
    
    # Industry naming elements to produce plausible company names
    industry_keywords = {
        "Restaurant": ["Bistro", "Cafe", "Kitchen", "Eatery", "Grill", "Tavern", "Diner"],
        "Retail": ["Boutique", "Goods", "Apparel", "Outfitters", "Market", "Provisions"],
        "Construction": ["Builders", "Construction", "Contracting", "Developments", "Structures"],
        "Consulting": ["Advisory", "Consulting", "Partners", "Solutions", "Strategy Group"],
        "Healthcare": ["Clinic", "Wellness", "Dental Care", "Health Group", "Medical Practice"],
        "E-commerce": ["Direct", "Commerce", "Supply Co", "Digital Goods", "Online Emporium"],
        "Real Estate": ["Realty", "Properties", "Real Estate", "Estates", "Living Group"],
        "Trades": ["Electrical", "Plumbing", "HVAC Services", "Roofing", "Mechanical"]
    }
    
    # Country distribution: US: 40%, UK: 25%, AU: 20%, NZ: 15%
    country_weights = [0.40, 0.25, 0.20, 0.15]
    countries = ["US", "UK", "AU", "NZ"]
    
    # Signup distribution across 2022-01 to 2024-09
    # Ramp-up: 40 in 2022, 125 in 2023, 235 in 2024 (through Sept 30)
    signups = []
    for _ in range(40):
        signups.append(date(2022, 1, 1) + timedelta(days=int(np.random.randint(0, 365))))
    for _ in range(125):
        signups.append(date(2023, 1, 1) + timedelta(days=int(np.random.randint(0, 365))))
    for _ in range(235):
        signups.append(date(2024, 1, 1) + timedelta(days=int(np.random.randint(0, 274))))
    signups.sort()
    
    for i in range(num_clients):
        client_id = i + 1
        industry = np.random.choice(INDUSTRIES)
        country = np.random.choice(countries, p=country_weights)
        acq_source = np.random.choice(ACQUISITION_SOURCES)
        
        # Tier preference based on acquisition source
        if acq_source in ["Accountant Partner", "Referral"]:
            plan_tier = np.random.choice(PLAN_TIERS, p=[0.25, 0.45, 0.30])
        elif acq_source == "Facebook":
            plan_tier = np.random.choice(PLAN_TIERS, p=[0.65, 0.25, 0.10])
        else:
            plan_tier = np.random.choice(PLAN_TIERS, p=[0.40, 0.40, 0.20])
            
        # Monthly fee based on plan tier using lognormal distributions
        if plan_tier == "Basic":
            fee = float(np.random.lognormal(mean=np.log(220), sigma=0.12))
        elif plan_tier == "Standard":
            fee = float(np.random.lognormal(mean=np.log(480), sigma=0.10))
        else:  # Premium
            fee = float(np.random.lognormal(mean=np.log(950), sigma=0.08))
        fee = round(fee, 2)
        
        signup_dt = signups[i]
        
        # Churn rate by industry & source
        base_churn = 0.25
        if industry in ["Restaurant", "E-commerce"]:
            base_churn += 0.10
        elif industry in ["Healthcare", "Consulting"]:
            base_churn -= 0.12
            
        if acq_source in ["Accountant Partner", "Referral"]:
            base_churn -= 0.08
        elif acq_source == "Facebook":
            base_churn += 0.08
            
        base_churn = max(0.08, min(0.45, base_churn))
        is_churned = (np.random.rand() < base_churn)
        
        days_active_max = (DATASET_END_DATE - signup_dt).days
        if is_churned and days_active_max > 60:
            churn_offset = np.random.randint(60, days_active_max + 1)
            churn_dt = signup_dt + timedelta(days=int(churn_offset))
            status = "Churned"
            churn_str = churn_dt.strftime("%Y-%m-%d")
        else:
            status = "Active"
            churn_str = None
            
        # Realistic business name
        suffix = np.random.choice(industry_keywords[industry])
        root_name = fake.last_name()
        if np.random.rand() < 0.35:
            root_name = f"{root_name} & {fake.last_name()}"
        business_name = f"{root_name} {suffix}"
        
        clients_records.append({
            "client_id": client_id,
            "business_name": business_name,
            "industry": industry,
            "country": country,
            "plan_tier": plan_tier,
            "monthly_fee": fee,
            "signup_date": signup_dt.strftime("%Y-%m-%d"),
            "status": status,
            "churn_date": churn_str,
            "acquisition_source": acq_source
        })
        
    return pd.DataFrame(clients_records)

def generate_monthly_closes(clients_df, staff_df):
    """Generates ~4,500 monthly close records for active client months."""
    closes_records = []
    close_id = 1
    
    staff_dict = staff_df.set_index("staff_id")["role"].to_dict()
    staff_ids = list(staff_df["staff_id"].values)
    
    # Generate all candidate (client, month) pairs
    candidates = []
    for _, client in clients_df.iterrows():
        c_id = client["client_id"]
        s_date = date.fromisoformat(client["signup_date"])
        end_limit = date(2024, 11, 30) # latest completed month close in 2024
        if client["status"] == "Churned" and client["churn_date"] is not None:
            c_date = date.fromisoformat(client["churn_date"])
            end_limit = min(end_limit, c_date)
            
        cur = date(s_date.year, s_date.month, 1)
        while cur <= end_limit:
            candidates.append((c_id, cur.strftime("%Y-%m"), cur, client["acquisition_source"]))
            if cur.month == 12:
                cur = date(cur.year + 1, 1, 1)
            else:
                cur = date(cur.year, cur.month + 1, 1)

    # If candidates count differs slightly from 4,500, sample or calibrate exactly 4,500
    if len(candidates) > 4500:
        # Keep consistent order, randomly select 4500
        chosen_indices = sorted(np.random.choice(len(candidates), size=4500, replace=False))
        candidates = [candidates[idx] for idx in chosen_indices]
    elif len(candidates) < 4500:
        pass # If close to 4,500, it meets (~4,500) requirement

    for c_id, month_str, cur_m, acq_source in candidates:
        # Due date is 15th of month + 1
        if cur_m.month == 12:
            due_dt = date(cur_m.year + 1, 1, 15)
        else:
            due_dt = date(cur_m.year, cur_m.month + 1, 15)
            
        staff_id = int(np.random.choice(staff_ids))
        role = staff_dict[staff_id]
        
        # Days late pattern based on role and tax season crunch
        month_num = cur_m.month
        is_crunch_month = (month_num in [3, 4, 6, 7, 10, 1])
        
        if role == "Manager":
            days_late = 0 if np.random.rand() < 0.95 else int(np.random.geometric(0.6))
        elif role == "Senior Bookkeeper":
            days_late = 0 if np.random.rand() < 0.82 else int(np.random.geometric(0.45))
        else:  # Bookkeeper
            base_prob = 0.50 if is_crunch_month else 0.65
            if np.random.rand() < base_prob:
                days_late = 0
            else:
                scale = 4.5 if is_crunch_month else 3.0
                days_late = int(np.random.geometric(1.0 / scale))
                
        # Completed date
        if days_late == 0:
            early_offset = np.random.randint(0, 4)
            comp_dt = due_dt - timedelta(days=int(early_offset))
        else:
            comp_dt = due_dt + timedelta(days=int(days_late))
            
        # Satisfaction score: 1 to 5, NULL for ~20%
        if np.random.rand() < 0.20:
            sat_score = None
        else:
            # Score influenced by acquisition source and timeliness
            base_weights = [0.03, 0.07, 0.20, 0.40, 0.30]  # scores 1, 2, 3, 4, 5
            if acq_source in ["Accountant Partner", "Referral"]:
                base_weights = [0.01, 0.03, 0.12, 0.44, 0.40]
            elif acq_source == "Facebook":
                base_weights = [0.06, 0.12, 0.28, 0.36, 0.18]
                
            if days_late > 3:
                # shift down
                base_weights = [0.15, 0.25, 0.35, 0.18, 0.07]
            sat_score = int(np.random.choice([1, 2, 3, 4, 5], p=base_weights))
            
        closes_records.append({
            "close_id": close_id,
            "client_id": c_id,
            "staff_id": staff_id,
            "month": month_str,
            "due_date": due_dt.strftime("%Y-%m-%d"),
            "completed_date": comp_dt.strftime("%Y-%m-%d"),
            "days_late": days_late,
            "satisfaction_score": sat_score
        })
        close_id += 1
        
    return pd.DataFrame(closes_records)

def generate_billing(clients_df):
    """Generates ~3,000 billing records tied to client subscription tenure."""
    billing_records = []
    invoice_id = 1
    
    # Generate candidate billing issues per client
    candidates = []
    for _, client in clients_df.iterrows():
        c_id = client["client_id"]
        s_date = date.fromisoformat(client["signup_date"])
        end_limit = DATASET_END_DATE
        if client["status"] == "Churned" and client["churn_date"] is not None:
            c_date = date.fromisoformat(client["churn_date"])
            end_limit = c_date
            
        # Invoices issued periodically (every month or cadence)
        cur = s_date
        while cur <= end_limit:
            candidates.append((c_id, cur, client["country"], client["industry"], client["monthly_fee"]))
            # Step by ~30 days
            cur = cur + timedelta(days=int(np.random.choice([28, 30, 31])))

    # Exactly 3,000 billing records
    if len(candidates) > 3000:
        chosen_indices = sorted(np.random.choice(len(candidates), size=3000, replace=False))
        candidates = [candidates[idx] for idx in chosen_indices]
        
    for c_id, issue_dt, country, industry, monthly_fee in candidates:
        currency = COUNTRY_CURRENCY[country]
        terms = int(np.random.choice([14, 30], p=[0.3, 0.7]))
        due_dt = issue_dt + timedelta(days=terms)
        
        # Amount: lognormal noise around monthly_fee
        noise = float(np.random.lognormal(mean=0, sigma=0.04))
        inv_amount = round(monthly_fee * noise, 2)
        
        # Payment behavior pattern by industry
        if industry in ["Construction", "Trades"]:
            unpaid_prob = 0.16
            late_latency_mean = 24.0
        elif industry in ["Consulting", "Healthcare"]:
            unpaid_prob = 0.03
            late_latency_mean = 6.0
        else:
            unpaid_prob = 0.08
            late_latency_mean = 12.0
            
        # Is invoice unpaid?
        is_unpaid = (np.random.rand() < unpaid_prob)
        if is_unpaid:
            paid_dt_str = None
            if due_dt < DATASET_END_DATE:
                status = "Overdue"
            else:
                status = "Open"
        else:
            # Paid latency from issue date
            pay_days = max(1, int(np.random.lognormal(mean=np.log(late_latency_mean), sigma=0.5)))
            paid_dt = issue_dt + timedelta(days=pay_days)
            if paid_dt > DATASET_END_DATE:
                # Payment has not occurred as of the snapshot cutoff date
                paid_dt_str = None
                if due_dt < DATASET_END_DATE:
                    status = "Overdue"
                else:
                    status = "Open"
            else:
                status = "Paid"
                paid_dt_str = paid_dt.strftime("%Y-%m-%d")
            
        billing_records.append({
            "invoice_id": invoice_id,
            "client_id": c_id,
            "issue_date": issue_dt.strftime("%Y-%m-%d"),
            "due_date": due_dt.strftime("%Y-%m-%d"),
            "paid_date": paid_dt_str,
            "amount": inv_amount,
            "currency": currency,
            "status": status
        })
        invoice_id += 1
        
    return pd.DataFrame(billing_records)

def generate_documents(clients_df, staff_df):
    """Generates ~12,000 documents with realistic distributions and seasonality."""
    doc_records = []
    total_docs = 12000
    
    staff_ids = list(staff_df["staff_id"].values)
    
    # Calculate client document quotas based on active tenure, plan tier, and industry
    client_weights = []
    for _, client in clients_df.iterrows():
        s_date = date.fromisoformat(client["signup_date"])
        c_limit = DATASET_END_DATE
        if client["status"] == "Churned" and client["churn_date"] is not None:
            c_limit = date.fromisoformat(client["churn_date"])
        tenure_days = max(30, (c_limit - s_date).days)
        
        tier_mult = {"Basic": 1.0, "Standard": 2.2, "Premium": 4.5}[client["plan_tier"]]
        ind_mult = 1.6 if client["industry"] in ["Restaurant", "Retail"] else 1.0
        client_weights.append(tenure_days * tier_mult * ind_mult)
        
    client_weights = np.array(client_weights)
    client_weights = client_weights / client_weights.sum()
    
    # Assign doc count per client summing to 12000
    doc_allocations = np.random.multinomial(total_docs, client_weights)
    
    # Tax season month weights per country
    def get_month_weight(c_country, dt):
        m = dt.month
        if c_country == "US":
            return 2.5 if m in [3, 4] else (1.6 if m in [9, 10] else 1.0)
        elif c_country == "UK":
            return 2.6 if m == 1 else (2.2 if m in [3, 4] else 1.0)
        elif c_country == "AU":
            return 2.8 if m in [6, 7] else (2.0 if m == 10 else 1.0)
        elif c_country == "NZ":
            return 2.7 if m in [3, 4] else 1.0
        return 1.0
        
    doc_id = 1
    for i, (_, client) in enumerate(clients_df.iterrows()):
        n_docs = doc_allocations[i]
        if n_docs == 0:
            continue
            
        c_id = client["client_id"]
        c_country = client["country"]
        s_date = date.fromisoformat(client["signup_date"])
        e_date = DATASET_END_DATE
        if client["status"] == "Churned" and client["churn_date"] is not None:
            e_date = date.fromisoformat(client["churn_date"])
            
        total_days = (e_date - s_date).days
        if total_days <= 0:
            days_span = [s_date]
            day_probs = [1.0]
        else:
            all_days = [s_date + timedelta(days=d) for d in range(total_days + 1)]
            weights = [get_month_weight(c_country, d) for d in all_days]
            weights = np.array(weights)
            day_probs = weights / weights.sum()
            days_span = all_days
            
        # Sample received dates for this client
        chosen_days = np.random.choice(days_span, size=n_docs, p=day_probs)
        chosen_days.sort()
        
        for r_dt in chosen_days:
            # Doc type
            doc_type = np.random.choice(DOC_TYPES, p=[0.42, 0.32, 0.16, 0.10])
            
            # Channel distribution
            source_chan = np.random.choice(SOURCE_CHANNELS, p=[0.45, 0.30, 0.15, 0.10])
            
            # Pages distribution based on doc type
            if doc_type == "Receipt":
                pages = 1 if np.random.rand() < 0.90 else 2
            elif doc_type == "Supplier Invoice":
                pages = int(np.random.choice([1, 2, 3, 4], p=[0.55, 0.28, 0.12, 0.05]))
            elif doc_type == "Bank Statement":
                pages = int(np.random.geometric(0.28)) + 1
                pages = min(pages, 10)
            else:  # Payroll Report
                pages = int(np.random.geometric(0.35)) + 1
                pages = min(pages, 8)
                
            # Error and rework rates by source channel
            if source_chan == "Photo":
                rework_prob = 0.17
                failed_prob = 0.05
            elif source_chan == "Paper Scan":
                rework_prob = 0.09
                failed_prob = 0.02
            else: # Email, Upload
                rework_prob = 0.06
                failed_prob = 0.015
                
            rand_stat = np.random.rand()
            if rand_stat < failed_prob:
                status = "Failed"
            elif rand_stat < (failed_prob + rework_prob):
                status = "Rework"
            else:
                status = "Processed"
                
            if status == "Processed":
                error_type = None
            else:
                if source_chan == "Photo":
                    error_type = np.random.choice(
                        ["Unreadable", "Wrong Amount", "Missing Info", "Duplicate"],
                        p=[0.65, 0.10, 0.20, 0.05]
                    )
                else:
                    error_type = np.random.choice(
                        ["Unreadable", "Wrong Amount", "Missing Info", "Duplicate"],
                        p=[0.25, 0.35, 0.25, 0.15]
                    )
                    
            # Processing minutes: lognormal based on doc type, pages, rework
            time_per_page_base = {
                "Receipt": 3.2,
                "Supplier Invoice": 5.0,
                "Bank Statement": 9.2,
                "Payroll Report": 8.5
            }[doc_type]
            
            raw_time = np.random.lognormal(mean=np.log(time_per_page_base * (pages ** 0.8)), sigma=0.25)
            if status == "Rework":
                raw_time *= 1.7
            elif status == "Failed":
                raw_time *= 0.8
                
            proc_mins = round(max(1.0, float(raw_time)), 1)
            
            # Staff assignment
            staff_id = int(np.random.choice(staff_ids))
            
            doc_records.append({
                "doc_id": doc_id,
                "client_id": c_id,
                "staff_id": staff_id,
                "received_date": r_dt.strftime("%Y-%m-%d"),
                "doc_type": doc_type,
                "source_channel": source_chan,
                "pages": pages,
                "processing_minutes": proc_mins,
                "status": status,
                "error_type": error_type
            })
            doc_id += 1
            
    return pd.DataFrame(doc_records)

def create_database(clients_df, staff_df, documents_df, billing_df, monthly_closes_df):
    """Creates SQLite database with explicit PRIMARY and FOREIGN KEY constraints and indexes."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # 1. clients
    cursor.execute("""
    CREATE TABLE clients (
        client_id INTEGER PRIMARY KEY,
        business_name TEXT NOT NULL,
        industry TEXT NOT NULL,
        country TEXT NOT NULL,
        plan_tier TEXT NOT NULL,
        monthly_fee REAL NOT NULL,
        signup_date TEXT NOT NULL,
        status TEXT NOT NULL,
        churn_date TEXT,
        acquisition_source TEXT NOT NULL
    );
    """)
    
    # 2. staff
    cursor.execute("""
    CREATE TABLE staff (
        staff_id INTEGER PRIMARY KEY,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL,
        hire_date TEXT NOT NULL,
        hourly_cost REAL NOT NULL
    );
    """)
    
    # 3. documents
    cursor.execute("""
    CREATE TABLE documents (
        doc_id INTEGER PRIMARY KEY,
        client_id INTEGER NOT NULL,
        staff_id INTEGER NOT NULL,
        received_date TEXT NOT NULL,
        doc_type TEXT NOT NULL,
        source_channel TEXT NOT NULL,
        pages INTEGER NOT NULL,
        processing_minutes REAL NOT NULL,
        status TEXT NOT NULL,
        error_type TEXT,
        FOREIGN KEY (client_id) REFERENCES clients(client_id),
        FOREIGN KEY (staff_id) REFERENCES staff(staff_id)
    );
    """)
    
    # 4. billing
    cursor.execute("""
    CREATE TABLE billing (
        invoice_id INTEGER PRIMARY KEY,
        client_id INTEGER NOT NULL,
        issue_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        paid_date TEXT,
        amount REAL NOT NULL,
        currency TEXT NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (client_id) REFERENCES clients(client_id)
    );
    """)
    
    # 5. monthly_closes
    cursor.execute("""
    CREATE TABLE monthly_closes (
        close_id INTEGER PRIMARY KEY,
        client_id INTEGER NOT NULL,
        staff_id INTEGER NOT NULL,
        month TEXT NOT NULL,
        due_date TEXT NOT NULL,
        completed_date TEXT NOT NULL,
        days_late INTEGER NOT NULL,
        satisfaction_score INTEGER,
        FOREIGN KEY (client_id) REFERENCES clients(client_id),
        FOREIGN KEY (staff_id) REFERENCES staff(staff_id)
    );
    """)
    
    # Insert data
    clients_df.to_sql("clients", conn, if_exists="append", index=False)
    staff_df.to_sql("staff", conn, if_exists="append", index=False)
    documents_df.to_sql("documents", conn, if_exists="append", index=False)
    billing_df.to_sql("billing", conn, if_exists="append", index=False)
    monthly_closes_df.to_sql("monthly_closes", conn, if_exists="append", index=False)
    
    conn.commit()
    return conn

def export_csvs(dataframes_dict):
    """Exports each DataFrame to a clean CSV in the output/ directory."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for name, df in dataframes_dict.items():
        csv_path = os.path.join(OUTPUT_DIR, f"{name}.csv")
        df.to_csv(csv_path, index=False)

def run_sanity_checks(conn, clients_df, documents_df, billing_df, monthly_closes_df):
    """Executes thorough sanity and data integrity checks."""
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print(" HARBOR & PINE BOOKKEEPING - GENERATION & SANITY REPORT")
    print("="*60)
    
    # 1. Row counts
    tables = ["clients", "staff", "documents", "billing", "monthly_closes"]
    counts = {}
    total_rows = 0
    print("\n[1] Row Count per Table:")
    for tbl in tables:
        cnt = cursor.execute(f"SELECT COUNT(*) FROM {tbl};").fetchone()[0]
        counts[tbl] = cnt
        total_rows += cnt
        print(f"  - {tbl:<16}: {cnt:>6,} rows")
    print(f"  * GRAND TOTAL     : {total_rows:>6,} rows")
    
    # 2. Date ranges
    print("\n[2] Date Ranges per Table:")
    date_queries = {
        "clients (signup)" : "SELECT MIN(signup_date), MAX(signup_date) FROM clients",
        "clients (churn)"  : "SELECT MIN(churn_date), MAX(churn_date) FROM clients WHERE churn_date IS NOT NULL",
        "staff (hire)"     : "SELECT MIN(hire_date), MAX(hire_date) FROM staff",
        "documents (recv)" : "SELECT MIN(received_date), MAX(received_date) FROM documents",
        "billing (issue)"  : "SELECT MIN(issue_date), MAX(issue_date) FROM billing",
        "billing (paid)"   : "SELECT MIN(paid_date), MAX(paid_date) FROM billing WHERE paid_date IS NOT NULL",
        "monthly_closes"   : "SELECT MIN(month), MAX(month) FROM monthly_closes"
    }
    for label, query in date_queries.items():
        min_d, max_d = cursor.execute(query).fetchone()
        print(f"  - {label:<18}: {min_d} to {max_d}")
        
    # 3. Foreign Key Integrity Check
    print("\n[3] Foreign Key Integrity Check:")
    cursor.execute("PRAGMA foreign_key_check;")
    fk_violations = cursor.fetchall()
    if not fk_violations:
        print("  - PRAGMA foreign_key_check: 0 violations found. (PASSED)")
    else:
        print(f"  - PRAGMA foreign_key_check: {len(fk_violations)} violations found! (FAILED)")
        
    # 4. Document dates vs Client Active Period
    print("\n[4] Document Date vs Client Active Window Integrity:")
    cursor.execute("""
    SELECT COUNT(*)
    FROM documents d
    JOIN clients c ON d.client_id = c.client_id
    WHERE d.received_date < c.signup_date
       OR (c.churn_date IS NOT NULL AND d.received_date > c.churn_date);
    """)
    out_of_bounds_docs = cursor.fetchone()[0]
    if out_of_bounds_docs == 0:
        print("  - Documents dated outside client active period: 0. (PASSED)")
    else:
        print(f"  - Documents dated outside client active period: {out_of_bounds_docs}. (FAILED)")
        
    # 5. Share of Active vs Churned clients
    print("\n[5] Client Churn Distribution:")
    cursor.execute("""
    SELECT status, COUNT(*) AS cnt, ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM clients), 2) AS pct
    FROM clients
    GROUP BY status;
    """)
    for row in cursor.fetchall():
        print(f"  - {row[0]:<10}: {row[1]:>4} clients ({row[2]}%)")
        
    # 6. Additional logical sanity checks
    print("\n[6] Logical Consistency Checks:")
    # Billing paid_date >= issue_date
    cursor.execute("SELECT COUNT(*) FROM billing WHERE paid_date IS NOT NULL AND paid_date < issue_date;")
    invalid_paid = cursor.fetchone()[0]
    print(f"  - Invoices with paid_date < issue_date: {invalid_paid} (PASSED: {invalid_paid == 0})")
    
    # Billing currency match
    cursor.execute("""
    SELECT COUNT(*)
    FROM billing b
    JOIN clients c ON b.client_id = c.client_id
    WHERE (c.country = 'US' AND b.currency != 'USD')
       OR (c.country = 'UK' AND b.currency != 'GBP')
       OR (c.country = 'AU' AND b.currency != 'AUD')
       OR (c.country = 'NZ' AND b.currency != 'NZD');
    """)
    currency_mismatch = cursor.fetchone()[0]
    print(f"  - Currency vs Country mismatches: {currency_mismatch} (PASSED: {currency_mismatch == 0})")

    # Closes days_late consistency
    cursor.execute("""
    SELECT COUNT(*)
    FROM monthly_closes
    WHERE days_late != MAX(0, CAST(JULIANDAY(completed_date) - JULIANDAY(due_date) AS INTEGER));
    """)
    late_mismatch = cursor.fetchone()[0]
    print(f"  - Closes with days_late calculation mismatch: {late_mismatch} (PASSED: {late_mismatch == 0})")
    
    # Null rules checks
    cursor.execute("SELECT COUNT(*) FROM clients WHERE (status = 'Active' AND churn_date IS NOT NULL) OR (status = 'Churned' AND churn_date IS NULL);")
    client_null_viol = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM documents WHERE (status = 'Processed' AND error_type IS NOT NULL) OR (status IN ('Rework', 'Failed') AND error_type IS NULL);")
    doc_null_viol = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM billing WHERE (status = 'Paid' AND paid_date IS NULL) OR (status IN ('Open', 'Overdue') AND paid_date IS NOT NULL);")
    bill_null_viol = cursor.fetchone()[0]
    cursor.execute("SELECT ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM monthly_closes), 1) FROM monthly_closes WHERE satisfaction_score IS NULL;")
    null_sat_pct = cursor.fetchone()[0]
    
    print(f"  - Client churn_date NULL rules violations: {client_null_viol} (PASSED: {client_null_viol == 0})")
    print(f"  - Document error_type NULL rules violations: {doc_null_viol} (PASSED: {doc_null_viol == 0})")
    print(f"  - Billing paid_date NULL rules violations: {bill_null_viol} (PASSED: {bill_null_viol == 0})")
    print(f"  - Monthly closes NULL satisfaction score share: {null_sat_pct}% (~20% expected)")
    print("="*60 + "\n")

def main():
    print("Starting Harbor & Pine Bookkeeping synthetic data generation...")
    staff_df = generate_staff()
    clients_df = generate_clients()
    monthly_closes_df = generate_monthly_closes(clients_df, staff_df)
    billing_df = generate_billing(clients_df)
    documents_df = generate_documents(clients_df, staff_df)
    
    # Export CSVs
    dfs = {
        "clients": clients_df,
        "staff": staff_df,
        "documents": documents_df,
        "billing": billing_df,
        "monthly_closes": monthly_closes_df
    }
    print("Exporting CSVs to output/ folder...")
    export_csvs(dfs)
    
    # Create SQLite database
    print(f"Populating SQLite database {DB_PATH}...")
    conn = create_database(clients_df, staff_df, documents_df, billing_df, monthly_closes_df)
    
    # Sanity checks
    run_sanity_checks(conn, clients_df, documents_df, billing_df, monthly_closes_df)
    conn.close()
    print("Data generation and database creation completed successfully.")

if __name__ == "__main__":
    main()
