"""
Task C: Cross-Portfolio Revenue Attribution & Forecasting — Sample Data Generator
Run this script to regenerate the sample data files in the /data directory.
"""

import csv
import json
import os
import random
import uuid
from datetime import datetime, timedelta

random.seed(99)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)


def generate_months(start_year, start_month, count):
    months = []
    y, m = start_year, start_month
    for _ in range(count):
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def random_date_in_month(y, m):
    start = datetime(y, m, 1)
    if m == 12:
        end = datetime(y + 1, 1, 1)
    else:
        end = datetime(y, m + 1, 1)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta - 1))


# ═══════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════

CHANNELS = ["youtube", "twitter", "instagram", "newsletter", "podcast", "blog"]

COMPANIES = [
    {"id": "CTC-001", "name": "GreenLeaf Landscaping", "industry": "Home Services", "avg_revenue_per_user": 120},
    {"id": "CTC-002", "name": "BrightPath Education", "industry": "Education", "avg_revenue_per_user": 85},
    {"id": "CTC-003", "name": "QuickFix Auto Repair", "industry": "Automotive", "avg_revenue_per_user": 210},
    {"id": "CTC-004", "name": "Summit Dental Group", "industry": "Healthcare", "avg_revenue_per_user": 165},
]

CAMPAIGNS = [
    {"id": "CMP-001", "name": "Spring Launch 2023", "channel": "youtube", "budget": 15000, "start": "2023-03-01", "end": "2023-04-30", "target_company": "CTC-001"},
    {"id": "CMP-002", "name": "Newsletter Growth Q2", "channel": "newsletter", "budget": 5000, "start": "2023-04-01", "end": "2023-06-30", "target_company": None},
    {"id": "CMP-003", "name": "Summer Education Push", "channel": "instagram", "budget": 12000, "start": "2023-06-15", "end": "2023-08-31", "target_company": "CTC-002"},
    {"id": "CMP-004", "name": "Auto Repair Awareness", "channel": "youtube", "budget": 18000, "start": "2023-07-01", "end": "2023-09-30", "target_company": "CTC-003"},
    {"id": "CMP-005", "name": "Podcast Sponsorship S1", "channel": "podcast", "budget": 8000, "start": "2023-01-01", "end": "2023-06-30", "target_company": None},
    {"id": "CMP-006", "name": "Blog SEO Push", "channel": "blog", "budget": 4000, "start": "2023-03-01", "end": "2023-12-31", "target_company": None},
    {"id": "CMP-007", "name": "Holiday Dental Promo", "channel": "twitter", "budget": 9000, "start": "2023-11-01", "end": "2023-12-31", "target_company": "CTC-004"},
    {"id": "CMP-008", "name": "New Year Push 2024", "channel": "youtube", "budget": 22000, "start": "2024-01-01", "end": "2024-02-28", "target_company": None},
    {"id": "CMP-009", "name": "Twitter Engagement Q1 24", "channel": "twitter", "budget": 6500, "start": "2024-01-15", "end": "2024-03-31", "target_company": None},
    {"id": "CMP-010", "name": "Instagram Stories Blitz", "channel": "instagram", "budget": 11000, "start": "2024-02-01", "end": "2024-04-30", "target_company": "CTC-001"},
    {"id": "CMP-011", "name": "Podcast Sponsorship S2", "channel": "podcast", "budget": 10000, "start": "2023-07-01", "end": "2023-12-31", "target_company": None},
    {"id": "CMP-012", "name": "Spring Services 2024", "channel": "blog", "budget": 5500, "start": "2024-03-01", "end": "2024-05-31", "target_company": "CTC-001"},
    {"id": "CMP-013", "name": "Auto Summer Campaign", "channel": "youtube", "budget": 16000, "start": "2024-05-01", "end": "2024-07-31", "target_company": "CTC-003"},
    {"id": "CMP-014", "name": "Education Fall Enrollment", "channel": "newsletter", "budget": 7000, "start": "2024-08-01", "end": "2024-10-31", "target_company": "CTC-002"},
    {"id": "CMP-015", "name": "Year-End Portfolio Push", "channel": "instagram", "budget": 13000, "start": "2024-10-01", "end": "2024-12-31", "target_company": None},
    {"id": "CMP-016", "name": "Newsletter Referral Program", "channel": "newsletter", "budget": 3500, "start": "2023-09-01", "end": "2023-11-30", "target_company": None},
    {"id": "CMP-017", "name": "Dental Awareness Month", "channel": "blog", "budget": 4500, "start": "2024-02-01", "end": "2024-02-28", "target_company": "CTC-004"},
    {"id": "CMP-018", "name": "YouTube Shorts Experiment", "channel": "youtube", "budget": 8500, "start": "2024-04-01", "end": "2024-06-30", "target_company": None},
    {"id": "CMP-019", "name": "Cross-Promo Landscaping x Auto", "channel": "twitter", "budget": 5000, "start": "2024-06-01", "end": "2024-08-31", "target_company": "CTC-001"},
    {"id": "CMP-020", "name": "Back to School 2024", "channel": "instagram", "budget": 9500, "start": "2024-08-15", "end": "2024-09-30", "target_company": "CTC-002"},
    {"id": "CMP-021", "name": "Podcast Guest Series", "channel": "podcast", "budget": 6000, "start": "2024-03-01", "end": "2024-06-30", "target_company": None},
    {"id": "CMP-022", "name": "LinkedIn Thought Leadership", "channel": "blog", "budget": 3000, "start": "2024-07-01", "end": "2024-09-30", "target_company": None},
    {"id": "CMP-023", "name": "Holiday Season 2024", "channel": "youtube", "budget": 25000, "start": "2024-11-01", "end": "2024-12-31", "target_company": None},
    {"id": "CMP-024", "name": "Q4 Newsletter Blast", "channel": "newsletter", "budget": 4000, "start": "2024-10-01", "end": "2024-12-31", "target_company": None},
    {"id": "CMP-025", "name": "Summit Dental Rebrand", "channel": "twitter", "budget": 7500, "start": "2024-06-01", "end": "2024-08-31", "target_company": "CTC-004"},
    {"id": "CMP-026", "name": "Auto Repair Winter Prep", "channel": "blog", "budget": 3800, "start": "2024-09-01", "end": "2024-11-30", "target_company": "CTC-003"},
    {"id": "CMP-027", "name": "Portfolio Awareness General", "channel": "youtube", "budget": 12000, "start": "2023-08-01", "end": "2023-10-31", "target_company": None},
    {"id": "CMP-028", "name": "Instagram Reel Strategy", "channel": "instagram", "budget": 8000, "start": "2023-09-01", "end": "2023-11-30", "target_company": None},
    {"id": "CMP-029", "name": "Podcast Ad Insert Q3 24", "channel": "podcast", "budget": 5500, "start": "2024-07-01", "end": "2024-09-30", "target_company": None},
    {"id": "CMP-030", "name": "Multi-Channel Black Friday", "channel": "newsletter", "budget": 15000, "start": "2024-11-15", "end": "2024-12-02", "target_company": None},
]


# ═══════════════════════════════════════════════════════════════════
# CONTENT PERFORMANCE DATA (CSV)
# ═══════════════════════════════════════════════════════════════════

def generate_content_performance():
    print("Generating content performance data...")
    months = generate_months(2023, 1, 18)

    channel_baselines = {
        "youtube": {"views": 50000, "clicks": 2500, "pieces_per_month": 8},
        "twitter": {"views": 25000, "clicks": 1200, "pieces_per_month": 30},
        "instagram": {"views": 35000, "clicks": 1800, "pieces_per_month": 20},
        "newsletter": {"views": 15000, "clicks": 3000, "pieces_per_month": 4},
        "podcast": {"views": 8000, "clicks": 800, "pieces_per_month": 4},
        "blog": {"views": 12000, "clicks": 1500, "pieces_per_month": 6},
    }

    rows = []
    content_counter = 0

    for i, (y, m) in enumerate(months):
        for channel, baseline in channel_baselines.items():
            num_pieces = baseline["pieces_per_month"] + random.randint(-2, 3)
            num_pieces = max(1, num_pieces)

            for _ in range(num_pieces):
                content_counter += 1
                content_id = f"CNT-{content_counter:05d}"
                publish_date = random_date_in_month(y, m)
                views = int(baseline["views"] / num_pieces * random.uniform(0.3, 2.5))
                clicks = int(baseline["clicks"] / num_pieces * random.uniform(0.2, 3.0))

                # Find active campaigns for this channel/month
                active_campaigns = [
                    c for c in CAMPAIGNS
                    if c["channel"] == channel
                    and datetime.strptime(c["start"], "%Y-%m-%d") <= publish_date
                    and datetime.strptime(c["end"], "%Y-%m-%d") >= publish_date
                ]

                utm_campaign = active_campaigns[0]["name"].lower().replace(" ", "_") if active_campaigns else ""
                utm_source = channel if random.random() > 0.08 else ""  # 8% missing utm_source

                rows.append({
                    "content_id": content_id,
                    "channel": channel,
                    "publish_date": publish_date.strftime("%Y-%m-%d"),
                    "views": views,
                    "clicks": clicks,
                    "utm_source": utm_source,
                    "utm_campaign": utm_campaign,
                })

    filepath = os.path.join(DATA_DIR, "content_performance.csv")
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["content_id", "channel", "publish_date", "views", "clicks", "utm_source", "utm_campaign"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"  → {filepath} ({len(rows)} content records)")
    return rows


# ═══════════════════════════════════════════════════════════════════
# USER SIGNUPS (JSON)
# ═══════════════════════════════════════════════════════════════════

def generate_user_signups(content_data):
    print("Generating user signup data...")
    months = generate_months(2023, 1, 18)

    channel_weights = {
        "youtube": 0.25, "twitter": 0.12, "instagram": 0.18,
        "newsletter": 0.20, "podcast": 0.08, "blog": 0.10,
        "organic": 0.05, "referral": 0.02,
    }
    channels = list(channel_weights.keys())
    weights = list(channel_weights.values())

    users = []
    user_counter = 0

    for i, (y, m) in enumerate(months):
        # More signups over time (growth)
        num_signups = int(random.uniform(200, 380) * (1 + 0.02 * i))

        for _ in range(num_signups):
            user_counter += 1
            user_id = f"USR-{user_counter:06d}"
            signup_date = random_date_in_month(y, m)
            company = random.choice(COMPANIES)

            first_touch = random.choices(channels, weights=weights, k=1)[0]
            last_touch = first_touch if random.random() < 0.55 else random.choices(channels, weights=weights, k=1)[0]

            # UTM params — sometimes missing or conflicting
            utm_source = first_touch if random.random() > 0.12 else ""  # 12% missing
            utm_medium = random.choice(["social", "email", "organic", "paid", "referral", ""])

            # Find relevant campaign
            active_campaigns = [
                c for c in CAMPAIGNS
                if c["channel"] == first_touch
                and datetime.strptime(c["start"], "%Y-%m-%d") <= signup_date
                and datetime.strptime(c["end"], "%Y-%m-%d") >= signup_date
            ]
            utm_campaign = active_campaigns[0]["name"].lower().replace(" ", "_") if active_campaigns and random.random() > 0.15 else ""

            user = {
                "user_id": user_id,
                "signup_date": signup_date.strftime("%Y-%m-%d"),
                "company_id": company["id"],
                "referral_source": random.choice([first_touch, "direct", "word_of_mouth", ""]),
                "utm_source": utm_source,
                "utm_medium": utm_medium,
                "utm_campaign": utm_campaign,
                "first_touch_channel": first_touch,
                "last_touch_channel": last_touch,
            }
            users.append(user)

    filepath = os.path.join(DATA_DIR, "user_signups.json")
    with open(filepath, "w") as f:
        json.dump({"signups": users}, f, indent=2)
    print(f"  → {filepath} ({len(users)} users)")
    return users


# ═══════════════════════════════════════════════════════════════════
# PORTFOLIO REVENUE (CSV)
# ═══════════════════════════════════════════════════════════════════

def generate_revenue(users):
    print("Generating portfolio revenue data...")

    revenue_rows = []
    rev_counter = 0

    for user in users:
        company = next(c for c in COMPANIES if c["id"] == user["company_id"])
        signup_date = datetime.strptime(user["signup_date"], "%Y-%m-%d")

        # Each user generates revenue for some number of months after signup
        months_active = random.choices(
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            weights=[15, 12, 10, 9, 8, 8, 7, 7, 6, 6, 6, 6],
            k=1
        )[0]

        for month_offset in range(months_active):
            rev_month = signup_date + timedelta(days=30 * month_offset)
            # Don't generate revenue past June 2024
            if rev_month > datetime(2024, 6, 30):
                break

            rev_counter += 1
            base_rev = company["avg_revenue_per_user"]
            amount = round(base_rev * random.uniform(0.4, 2.0), 2)
            is_recurring = month_offset > 0

            revenue_rows.append({
                "revenue_id": f"REV-{rev_counter:07d}",
                "company_id": user["company_id"],
                "user_id": user["user_id"],
                "month": f"{rev_month.year}-{rev_month.month:02d}",
                "revenue_amount": amount,
                "is_recurring": is_recurring,
            })

    filepath = os.path.join(DATA_DIR, "portfolio_revenue.csv")
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["revenue_id", "company_id", "user_id", "month", "revenue_amount", "is_recurring"])
        writer.writeheader()
        writer.writerows(revenue_rows)
    print(f"  → {filepath} ({len(revenue_rows)} revenue records)")


# ═══════════════════════════════════════════════════════════════════
# CAMPAIGN METADATA (CSV)
# ═══════════════════════════════════════════════════════════════════

def generate_campaigns():
    print("Generating campaign metadata...")

    rows = []
    for c in CAMPAIGNS:
        rows.append({
            "campaign_id": c["id"],
            "campaign_name": c["name"],
            "channel": c["channel"],
            "budget_usd": c["budget"],
            "start_date": c["start"],
            "end_date": c["end"],
            "target_company_id": c["target_company"] or "",
        })

    filepath = os.path.join(DATA_DIR, "campaign_metadata.csv")
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["campaign_id", "campaign_name", "channel", "budget_usd", "start_date", "end_date", "target_company_id"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"  → {filepath} ({len(rows)} campaigns)")


# ═══════════════════════════════════════════════════════════════════
# RUN ALL
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("Task C: Revenue Attribution & Forecasting — Data Generator")
    print("=" * 60)
    content = generate_content_performance()
    users = generate_user_signups(content)
    generate_revenue(users)
    generate_campaigns()
    print("\n✅ All Task C data generated successfully.")
    print(f"   Data directory: {DATA_DIR}")
