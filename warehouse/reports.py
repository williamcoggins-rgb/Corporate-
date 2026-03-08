"""Report generation — pull formatted competitor files and summaries."""

import json
import os
from tabulate import tabulate
from warehouse.competitors import get_competitor, list_competitors
from warehouse.intel import competitive_landscape, recent_moves, compare_products


def print_competitor_file(identifier):
    """Print a full competitor dossier."""
    data = get_competitor(identifier)
    if not data:
        return

    print("=" * 60)
    print(f"  COMPETITOR FILE: {data['company_name']}")
    print("=" * 60)
    print(f"  Industry:       {data.get('industry', 'N/A')}")
    print(f"  Website:        {data.get('website', 'N/A')}")
    print(f"  HQ:             {data.get('hq_location', 'N/A')}")
    print(f"  Founded:        {data.get('founded_year', 'N/A')}")
    print(f"  Employees:      {data.get('employee_count', 'N/A')}")
    print(f"  Revenue:        {data.get('annual_revenue', 'N/A')}")
    print(f"  Business Model: {data.get('business_model', 'N/A')}")
    print(f"  Status:         {data.get('status', 'N/A')}")
    if data.get("notes"):
        print(f"\n  Notes: {data['notes']}")

    if data["products"]:
        print(f"\n{'─' * 60}")
        print("  PRODUCTS")
        print(tabulate(data["products"], headers="keys", tablefmt="simple_outline"))

    if data["financials"]:
        print(f"\n{'─' * 60}")
        print("  FINANCIALS")
        print(tabulate(data["financials"], headers="keys", tablefmt="simple_outline"))

    if data["recent_moves"]:
        print(f"\n{'─' * 60}")
        print("  RECENT MOVES")
        for m in data["recent_moves"]:
            impact = f" [Impact: {m['impact_rating']}/5]" if m.get("impact_rating") else ""
            print(f"  {m.get('move_date', '?')} | {m.get('move_type', '?')}: {m.get('description', '')}{impact}")

    if data["social"]:
        print(f"\n{'─' * 60}")
        print("  SOCIAL PRESENCE")
        print(tabulate(data["social"], headers="keys", tablefmt="simple_outline"))

    print("=" * 60)


def print_landscape():
    """Print the full competitive landscape overview."""
    data = competitive_landscape()
    if not data:
        print("No competitors in the warehouse yet.")
        return
    print("\nCOMPETITIVE LANDSCAPE")
    print(tabulate(data, headers="keys", tablefmt="simple_outline"))


def print_recent_moves(limit=20):
    """Print recent moves across all competitors."""
    data = recent_moves(limit)
    if not data:
        print("No moves tracked yet.")
        return
    print("\nRECENT COMPETITIVE MOVES")
    print(tabulate(data, headers="keys", tablefmt="simple_outline"))


def export_competitor_json(identifier, filepath=None):
    """Export a competitor's full file to JSON."""
    data = get_competitor(identifier)
    if not data:
        return
    if not filepath:
        safe_name = data["company_name"].lower().replace(" ", "_")
        filepath = f"data/exports/{safe_name}.json"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"Exported to {filepath}")
