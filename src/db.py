"""
SQLite 데이터 저장소
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "../data/pipeline.db")


def get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            inst_code TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS salary_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            year INTEGER,
            avg_salary_10k INTEGER,
            avg_tenure_years REAL,
            total_employees INTEGER,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS career_salary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            career_year INTEGER,
            grade TEXT,
            annual_gross_10k INTEGER,
            monthly_net_10k REAL,
            tax_rate_pct REAL,
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS blind_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT UNIQUE NOT NULL,
            avg_rating REAL,
            review_count INTEGER,
            top_welfare TEXT,
            top_issues TEXT,
            welfare_score REAL,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS evaluator_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT UNIQUE NOT NULL,
            activity_rate_pct REAL,
            growth_score REAL,
            interpretation TEXT,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS job_postings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            job_title TEXT,
            deadline TEXT,
            job_type TEXT,
            region TEXT,
            detail_url TEXT,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS video_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            video_path TEXT,
            card_count INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


def upsert_company(name: str, inst_code: str = None):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO companies (name, inst_code) VALUES (?, ?)",
        (name, inst_code)
    )
    if inst_code:
        conn.execute(
            "UPDATE companies SET inst_code = ? WHERE name = ?",
            (inst_code, name)
        )
    conn.commit()
    conn.close()


def save_salary_records(records: list[dict]):
    conn = get_conn()
    conn.executemany(
        """INSERT OR REPLACE INTO salary_records
           (company_name, year, avg_salary_10k, avg_tenure_years, total_employees)
           VALUES (:company_name, :year, :avg_salary_10k, :avg_tenure_years, :total_employees)""",
        records,
    )
    conn.commit()
    conn.close()


def save_career_salary(company_name: str, salary_list: list):
    conn = get_conn()
    conn.execute("DELETE FROM career_salary WHERE company_name = ?", (company_name,))
    for item in salary_list:
        d = item if isinstance(item, dict) else item.__dict__
        conn.execute(
            """INSERT INTO career_salary
               (company_name, career_year, grade, annual_gross_10k, monthly_net_10k, tax_rate_pct)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (company_name, d["year"], d["grade"], d["annual_gross_10k"],
             d["monthly_net_10k"], d["tax_rate_pct"]),
        )
    conn.commit()
    conn.close()


def save_blind_summary(summary: dict):
    conn = get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO blind_summaries
           (company_name, avg_rating, review_count, top_welfare, top_issues, welfare_score)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            summary["company_name"],
            summary["avg_rating"],
            summary["review_count"],
            json.dumps(summary["top_welfare"], ensure_ascii=False),
            json.dumps(summary["top_issues"], ensure_ascii=False),
            summary["welfare_score"],
        ),
    )
    conn.commit()
    conn.close()


def save_evaluator_stat(stat):
    conn = get_conn()
    d = stat if isinstance(stat, dict) else stat.__dict__
    conn.execute(
        """INSERT OR REPLACE INTO evaluator_stats
           (company_name, activity_rate_pct, growth_score, interpretation)
           VALUES (?, ?, ?, ?)""",
        (d["company_name"], d["activity_rate_pct"], d["growth_score"], d["interpretation"]),
    )
    conn.commit()
    conn.close()


def log_video(company_name: str, video_path: str, card_count: int):
    conn = get_conn()
    conn.execute(
        "INSERT INTO video_log (company_name, video_path, card_count) VALUES (?, ?, ?)",
        (company_name, video_path, card_count),
    )
    conn.commit()
    conn.close()


def get_latest_salary(company_name: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM salary_records WHERE company_name = ? ORDER BY year DESC LIMIT 1",
        (company_name,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
