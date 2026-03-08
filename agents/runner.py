"""Agent Runner — orchestrate all bots in the correct order.

Usage:
    python -m agents.runner all          # Run full pipeline
    python -m agents.runner tier1        # Run just extraction agents
    python -m agents.runner tier2        # Run transformation agents
    python -m agents.runner tier3        # Run analytics agents
    python -m agents.runner tier4        # Run alert agents
    python -m agents.runner digest       # Run weekly digest only
    python -m agents.runner <agent_name> # Run a specific agent
"""

import sys

from agents.pricing_scout import PricingScout
from agents.review_harvester import ReviewHarvester
from agents.social_listener import SocialListener
from agents.shop_watcher import ShopWatcher
from agents.normalizer import Normalizer
from agents.barber_enricher import BarberEnricher
from agents.delta_spotter import DeltaSpotter
from agents.scorecard import Scorecard
from agents.alerts import PriceWarAlert, ReputationRadar, TalentTracker
from agents.digest import WeeklyDigest
from warehouse.db import init_schema


# Agent registry — order matters within tiers
AGENTS = {
    # Tier 1: Extraction (Street-Level Scouts)
    "pricing_scout": PricingScout,
    "review_harvester": ReviewHarvester,
    "social_listener": SocialListener,
    "shop_watcher": ShopWatcher,
    # Tier 2: Transformation (Detail Crew)
    "normalizer": Normalizer,
    "barber_enricher": BarberEnricher,
    "delta_spotter": DeltaSpotter,
    # Tier 3: Analytics (Analytics Team)
    "scorecard": Scorecard,
    # Tier 4: Alerts (Early Warning System)
    "price_war_alert": PriceWarAlert,
    "reputation_radar": ReputationRadar,
    "talent_tracker": TalentTracker,
    "weekly_digest": WeeklyDigest,
}

TIERS = {
    "tier1": ["pricing_scout", "review_harvester", "social_listener", "shop_watcher"],
    "tier2": ["normalizer", "barber_enricher", "delta_spotter"],
    "tier3": ["scorecard"],
    "tier4": ["price_war_alert", "reputation_radar", "talent_tracker", "weekly_digest"],
}


def run_agents(agent_names, **kwargs):
    """Run a list of agents in order."""
    init_schema()  # Ensure schema exists

    results = {}
    for name in agent_names:
        agent_cls = AGENTS.get(name)
        if not agent_cls:
            print(f"Unknown agent: {name}")
            continue

        print(f"\n{'=' * 50}")
        print(f"  RUNNING: {name} (Tier {agent_cls.tier})")
        print(f"{'=' * 50}")

        agent = agent_cls(**kwargs)
        try:
            agent.run()
            results[name] = "completed"
        except Exception as e:
            print(f"  FAILED: {e}")
            results[name] = f"failed: {e}"

    return results


def run_tier(tier_name, **kwargs):
    """Run all agents in a tier."""
    names = TIERS.get(tier_name, [])
    if not names:
        print(f"Unknown tier: {tier_name}")
        return {}
    return run_agents(names, **kwargs)


def run_all(**kwargs):
    """Run the full pipeline: Tier 1 → 2 → 3 → 4."""
    results = {}
    for tier in ["tier1", "tier2", "tier3", "tier4"]:
        print(f"\n{'#' * 50}")
        print(f"  TIER: {tier.upper()}")
        print(f"{'#' * 50}")
        results.update(run_tier(tier, **kwargs))
    return results


def list_agents():
    """Print all available agents."""
    print("\nAvailable Agents:")
    print("-" * 50)
    for tier_name, agent_names in TIERS.items():
        print(f"\n  {tier_name.upper()}")
        for name in agent_names:
            cls = AGENTS[name]
            print(f"    {name:<25} {cls.description}")
    print()


def main():
    if len(sys.argv) < 2:
        list_agents()
        print("Usage: python -m agents.runner <command>")
        print("Commands: all, tier1, tier2, tier3, tier4, digest, list, <agent_name>")
        return

    command = sys.argv[1].lower()

    if command == "all":
        run_all()
    elif command == "list":
        list_agents()
    elif command == "digest":
        run_agents(["weekly_digest"])
    elif command in TIERS:
        run_tier(command)
    elif command in AGENTS:
        run_agents([command])
    else:
        print(f"Unknown command: {command}")
        list_agents()


if __name__ == "__main__":
    main()
