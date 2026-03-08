#!/usr/bin/env python3
"""CLI interface for the Competitive Intelligence Warehouse."""

import sys
from warehouse.db import init_schema
from warehouse.competitors import add_competitor, list_competitors, update_competitor, delete_competitor
from warehouse.intel import add_product, add_financial, add_move, add_social
from warehouse.reports import print_competitor_file, print_landscape, print_recent_moves, export_competitor_json

USAGE = """
Competitive Intelligence Warehouse CLI
=======================================

Commands:
  init                          Initialize/reset the database schema
  add       <name>              Add a new competitor (interactive)
  file      <name or id>        Pull a competitor's full file
  list                          List all competitors
  landscape                     Show competitive landscape overview
  moves                         Show recent moves across all competitors
  export    <name or id>        Export competitor file to JSON
  help                          Show this help message

Examples:
  python cli.py init
  python cli.py add "Acme Corp"
  python cli.py file "Acme"
  python cli.py landscape
"""


def cmd_add(args):
    if not args:
        print("Usage: python cli.py add <company_name>")
        return
    name = " ".join(args)
    print(f"\nAdding competitor: {name}")
    print("(Leave blank to skip optional fields)\n")

    industry = input("  Industry: ").strip() or None
    website = input("  Website: ").strip() or None
    hq = input("  HQ Location: ").strip() or None
    founded = input("  Founded Year: ").strip()
    founded = int(founded) if founded else None
    employees = input("  Employee Count: ").strip()
    employees = int(employees) if employees else None
    revenue = input("  Annual Revenue: ").strip() or None
    model = input("  Business Model (B2B/B2C/SaaS/etc): ").strip() or None
    notes = input("  Notes: ").strip() or None

    add_competitor(name, industry=industry, website=website, hq_location=hq,
                   founded_year=founded, employee_count=employees,
                   annual_revenue=revenue, business_model=model, notes=notes)


def cmd_file(args):
    if not args:
        print("Usage: python cli.py file <name or id>")
        return
    identifier = " ".join(args)
    try:
        identifier = int(identifier)
    except ValueError:
        pass
    print_competitor_file(identifier)


def main():
    if len(sys.argv) < 2:
        print(USAGE)
        return

    command = sys.argv[1].lower()
    args = sys.argv[2:]

    if command == "init":
        init_schema()
    elif command == "add":
        cmd_add(args)
    elif command == "file":
        cmd_file(args)
    elif command == "list":
        data = list_competitors()
        if not data:
            print("No competitors in the warehouse yet. Run: python cli.py add <name>")
        else:
            from tabulate import tabulate
            print(tabulate(data, headers="keys", tablefmt="simple_outline"))
    elif command == "landscape":
        print_landscape()
    elif command == "moves":
        print_recent_moves()
    elif command == "export":
        if not args:
            print("Usage: python cli.py export <name or id>")
            return
        identifier = " ".join(args)
        try:
            identifier = int(identifier)
        except ValueError:
            pass
        export_competitor_json(identifier)
    elif command == "help":
        print(USAGE)
    else:
        print(f"Unknown command: {command}")
        print(USAGE)


if __name__ == "__main__":
    main()
