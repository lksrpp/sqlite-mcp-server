#!/usr/bin/env python3
"""
Database seeding script for CRM sample data.

Creates a SQLite database with a standard CRM schema and populates it
with realistic sample data using Faker.

Usage:
    uv run python seed_database.py [database_path]

If no path is provided, defaults to 'crm.db' in the current directory.
"""

import sqlite3
import sys
import random
from datetime import datetime, timedelta
from faker import Faker

# Initialize Faker
fake = Faker()

# Default database path
DEFAULT_DB_PATH = "crm.db"

# Schema definition
SCHEMA = """
-- Users table (sales reps/agents)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Companies table (customer accounts)
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    industry TEXT,
    website TEXT,
    address TEXT,
    owner_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

-- Contacts table (people at companies)
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    job_title TEXT,
    company_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- Deals table (sales opportunities)
CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    value REAL,
    stage TEXT NOT NULL,
    probability INTEGER,
    contact_id INTEGER,
    owner_id INTEGER,
    expected_close_date DATE,
    actual_close_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

-- Activities table (tasks/interactions)
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    description TEXT,
    contact_id INTEGER,
    deal_id INTEGER,
    due_date DATE,
    completed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (deal_id) REFERENCES deals(id)
);
"""

# Sample data configuration
INDUSTRIES = [
    "Technology", "Healthcare", "Finance", "Manufacturing", 
    "Retail", "Education", "Real Estate", "Consulting",
    "Marketing", "Legal Services"
]

ROLES = ["Sales Rep", "Account Executive", "Sales Manager", "SDR", "VP Sales"]

DEAL_STAGES = [
    ("Prospecting", 10), # 10% chance of being closed won
    ("Qualification", 20),
    ("Proposal", 40),
    ("Negotiation", 60),
    ("Closed Won", 100),
    ("Closed Lost", 0)
]

ACTIVITY_TYPES = ["Call", "Email", "Meeting", "Demo", "Follow-up", "Proposal Review"]


def create_database(db_path: str) -> sqlite3.Connection:
    """Create database and schema."""
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def clear_data(conn: sqlite3.Connection) -> None:
    """Clear all existing data from tables."""
    tables = ["activities", "deals", "contacts", "companies", "users"]
    for table in tables:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()


def seed_users(conn: sqlite3.Connection, count: int = 5) -> list[int]:
    """Seed users table and return list of user IDs."""
    users = []
    for _ in range(count):
        name = fake.name()
        email = fake.email()
        role = random.choice(ROLES)
        
        cursor = conn.execute(
            "INSERT INTO users (name, email, role) VALUES (?, ?, ?)",
            (name, email, role)
        )
        users.append(cursor.lastrowid)
    
    conn.commit()
    return users


def seed_companies(conn: sqlite3.Connection, user_ids: list[int], count: int = 20) -> list[int]:
    """Seed companies table and return list of company IDs."""
    companies = []
    for _ in range(count):
        name = fake.company()
        industry = random.choice(INDUSTRIES)
        website = fake.url()
        address = fake.address().replace("\n", ", ")
        owner_id = random.choice(user_ids)
        
        cursor = conn.execute(
            "INSERT INTO companies (name, industry, website, address, owner_id) VALUES (?, ?, ?, ?, ?)",
            (name, industry, website, address, owner_id)
        )
        companies.append(cursor.lastrowid)
    
    conn.commit()
    return companies


def seed_contacts(conn: sqlite3.Connection, company_ids: list[int], count: int = 40) -> list[int]:
    """Seed contacts table and return list of contact IDs."""
    contacts = []
    job_titles = ["CEO", "CTO", "CFO", "VP Engineering", "Director of Sales", 
                  "Product Manager", "Marketing Director", "IT Manager", "Buyer"]
    
    for _ in range(count):
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = fake.email()
        phone = fake.phone_number()
        job_title = random.choice(job_titles)
        company_id = random.choice(company_ids)
        
        cursor = conn.execute(
            "INSERT INTO contacts (first_name, last_name, email, phone, job_title, company_id) VALUES (?, ?, ?, ?, ?, ?)",
            (first_name, last_name, email, phone, job_title, company_id)
        )
        contacts.append(cursor.lastrowid)
    
    conn.commit()
    return contacts


def seed_deals(conn: sqlite3.Connection, contact_ids: list[int], user_ids: list[int], count: int = 25) -> list[int]:
    """Seed deals table and return list of deal IDs."""
    deals = []
    deal_prefixes = ["Enterprise License", "Annual Contract", "Pilot Program", 
                     "Expansion Deal", "New Business", "Renewal"]
    
    for _ in range(count):
        stage, probability = random.choice(DEAL_STAGES)
        title = f"{random.choice(deal_prefixes)} - {fake.company()}"
        value = round(random.uniform(5000, 500000), 2)
        contact_id = random.choice(contact_ids)
        owner_id = random.choice(user_ids)
        expected_close = datetime.now() + timedelta(days=random.randint(-30, 90))
        
        # Set actual_close_date for closed deals (won or lost)
        actual_close = None
        if stage in ("Closed Won", "Closed Lost"):
            # Closed deals: actual close is in the past (0-60 days ago)
            actual_close = datetime.now() - timedelta(days=random.randint(0, 60))
        
        cursor = conn.execute(
            "INSERT INTO deals (title, value, stage, probability, contact_id, owner_id, expected_close_date, actual_close_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (title, value, stage, probability, contact_id, owner_id, 
             expected_close.strftime("%Y-%m-%d"),
             actual_close.strftime("%Y-%m-%d") if actual_close else None)
        )
        deals.append(cursor.lastrowid)
    
    conn.commit()
    return deals


def seed_activities(conn: sqlite3.Connection, contact_ids: list[int], deal_ids: list[int], count: int = 30) -> list[int]:
    """Seed activities table and return list of activity IDs."""
    activities = []
    for _ in range(count):
        activity_type = random.choice(ACTIVITY_TYPES)
        description = fake.sentence()
        contact_id = random.choice(contact_ids)
        deal_id = random.choice(deal_ids) if random.random() > 0.3 else None
        due_date = datetime.now() + timedelta(days=random.randint(-14, 30))
        completed = 1 if due_date < datetime.now() else random.choice([0, 0, 0, 1])
        
        cursor = conn.execute(
            "INSERT INTO activities (type, description, contact_id, deal_id, due_date, completed) VALUES (?, ?, ?, ?, ?, ?)",
            (activity_type, description, contact_id, deal_id, due_date.strftime("%Y-%m-%d"), completed)
        )
        activities.append(cursor.lastrowid)
    
    conn.commit()
    return activities


def main():
    """Main entry point."""
    # Get database path from command line or use default
    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB_PATH
    
    print(f"Creating database: {db_path}")
    conn = create_database(db_path)
    
    print("Clearing existing data...")
    clear_data(conn)
    
    print("Seeding users...")
    user_ids = seed_users(conn, count=10)
    print(f"  Created {len(user_ids)} users")
    
    print("Seeding companies...")
    company_ids = seed_companies(conn, user_ids, count=40)
    print(f"  Created {len(company_ids)} companies")
    
    print("Seeding contacts...")
    contact_ids = seed_contacts(conn, company_ids, count=80)
    print(f"  Created {len(contact_ids)} contacts")
    
    print("Seeding deals...")
    deal_ids = seed_deals(conn, contact_ids, user_ids, count=50)
    print(f"  Created {len(deal_ids)} deals")
    
    print("Seeding activities...")
    activity_ids = seed_activities(conn, contact_ids, deal_ids, count=60)
    print(f"  Created {len(activity_ids)} activities")
    
    conn.close()
    
    total_records = len(user_ids) + len(company_ids) + len(contact_ids) + len(deal_ids) + len(activity_ids)
    print(f"\nDatabase seeded successfully: {db_path}")
    print(f"Total records: {total_records}")


if __name__ == "__main__":
    main()

