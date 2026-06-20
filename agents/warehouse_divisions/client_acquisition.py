"""RETIRED — Division 2 — Client Acquisition Intelligence

STATUS: RETIRED as of Phase One (June 2026).
BLOCKED ON: booking-OS integration (requires client_origins table, not in schema).
Planned for Phase Two once booking-OS feeds exist.
NOT registered, NOT scheduled. See agents/warehouse_divisions/README.md to revive.

Original description:
Matches new client geography from your booking OS against the competitor
map in the warehouse to answer: Where are we winning clients, and where
are we invisible?

Scout       — Collects client zip codes and first-visit data from booking OS
Researcher  — Cross-references client origins with competitor presence and weakness scores
Analyst     — Produces acquisition heat maps and opportunity scores by zip code
Auditor     — Validates geographic data completeness and flags zip codes with no coverage
"""

import json
from agents.base import BaseAgent
from warehouse.db import get_connection


class ClientAcquisitionScout(BaseAgent):
    name = "client_acq_scout"
    description = "Collects client origin data from booking OS and maps to competitor zones"
    tier = 1

    def execute(self):
        self.log("Ready to ingest client origin data from booking OS.")
        self.log("Use ingest_client_origin() to feed zip code + first visit data.")

    def ingest_client_origin(self, client_id, zip_code, first_visit_date, referral_source=None):
        """Record where a new client came from."""
        con = get_connection()
        con.execute(
            """INSERT INTO client_origins (client_id, zip_code, first_visit_date, referral_source)
               VALUES (?, ?, ?, ?)""",
            [client_id, zip_code, first_visit_date, referral_source],
        )
        con.close()
        self.records_processed += 1
        self.log(f"Recorded client {client_id} from zip {zip_code}")

    def get_origin_summary(self):
        """Summarize client origins by zip code."""
        con = get_connection()
        rows = con.execute("""
            SELECT zip_code, COUNT(*) as client_count,
                   MIN(first_visit_date) as earliest, MAX(first_visit_date) as latest
            FROM client_origins
            GROUP BY zip_code
            ORDER BY client_count DESC
        """).fetchall()
        con.close()
        return rows


class ClientAcquisitionResearcher(BaseAgent):
    name = "client_acq_researcher"
    description = "Maps client origins against competitor density and weakness"
    tier = 2

    def execute(self):
        self.log("Cross-referencing client geography with competitor map...")
        self.log("Requires client_origins table + competitors table populated.")

    def find_conquest_zones(self):
        """Zip codes where you're pulling clients FROM competitors."""
        con = get_connection()
        rows = con.execute("""
            WITH your_clients AS (
                SELECT zip_code, COUNT(*) as your_count
                FROM client_origins
                GROUP BY zip_code
            ),
            competitor_density AS (
                SELECT hq_zip as zip_code, COUNT(*) as competitor_count,
                       ROUND(AVG(cs.score), 1) as avg_threat
                FROM competitors c
                LEFT JOIN competitor_scores cs ON cs.competitor_id = c.competitor_id
                    AND cs.score_type = 'threat_level'
                WHERE c.status = 'Active'
                GROUP BY hq_zip
            )
            SELECT yc.zip_code, yc.your_count, cd.competitor_count, cd.avg_threat
            FROM your_clients yc
            LEFT JOIN competitor_density cd ON cd.zip_code = yc.zip_code
            WHERE cd.competitor_count IS NOT NULL
            ORDER BY yc.your_count DESC
        """).fetchall()
        con.close()
        return rows

    def find_blind_spots(self):
        """Zip codes with weak competitors but zero of your clients."""
        con = get_connection()
        rows = con.execute("""
            WITH your_zips AS (SELECT DISTINCT zip_code FROM client_origins),
            weak_zones AS (
                SELECT hq_zip as zip_code, COUNT(*) as shops,
                       ROUND(AVG(cs.score), 1) as avg_threat
                FROM competitors c
                LEFT JOIN competitor_scores cs ON cs.competitor_id = c.competitor_id
                    AND cs.score_type = 'threat_level'
                WHERE c.status = 'Active'
                GROUP BY hq_zip
                HAVING avg_threat < 5
            )
            SELECT wz.zip_code, wz.shops, wz.avg_threat
            FROM weak_zones wz
            LEFT JOIN your_zips yz ON yz.zip_code = wz.zip_code
            WHERE yz.zip_code IS NULL
            ORDER BY wz.avg_threat ASC
        """).fetchall()
        con.close()
        return rows


class ClientAcquisitionAnalyst(BaseAgent):
    name = "client_acq_analyst"
    description = "Produces opportunity scores and acquisition strategy per zip code"
    tier = 3

    def execute(self):
        self.log("Scoring zip codes for acquisition opportunity...")
        scores = self.score_zip_codes()
        for s in scores[:10]:
            self.log(f"  Zip {s['zip_code']}: opportunity={s['opportunity_score']}")
        self.log(f"Scored {len(scores)} zip codes.")

    def score_zip_codes(self):
        """Score each zip code: high client potential + weak competition = high opportunity."""
        con = get_connection()
        rows = con.execute("""
            WITH client_counts AS (
                SELECT zip_code, COUNT(*) as your_clients FROM client_origins GROUP BY zip_code
            ),
            comp_data AS (
                SELECT hq_zip as zip_code, COUNT(*) as competitors,
                       COALESCE(AVG(cs.score), 0) as avg_threat
                FROM competitors c
                LEFT JOIN competitor_scores cs ON cs.competitor_id = c.competitor_id AND cs.score_type = 'threat_level'
                WHERE c.status = 'Active'
                GROUP BY hq_zip
            )
            SELECT COALESCE(cc.zip_code, cd.zip_code) as zip_code,
                   COALESCE(cc.your_clients, 0) as your_clients,
                   COALESCE(cd.competitors, 0) as competitors,
                   COALESCE(cd.avg_threat, 0) as avg_threat
            FROM client_counts cc
            FULL OUTER JOIN comp_data cd ON cc.zip_code = cd.zip_code
        """).fetchall()
        con.close()

        scores = []
        for zip_code, clients, competitors, threat in rows:
            # High opportunity = many of your clients + weak competition
            # Low opportunity = no clients + strong competition
            client_signal = min(10, clients)  # cap at 10
            weakness_signal = max(0, 10 - threat)  # invert threat
            density_penalty = min(5, competitors)  # more competitors = harder
            opportunity = round((client_signal + weakness_signal - density_penalty) / 2, 1)
            scores.append({
                "zip_code": zip_code,
                "your_clients": clients,
                "competitors": competitors,
                "avg_threat": float(threat),
                "opportunity_score": max(0, opportunity),
            })
        scores.sort(key=lambda x: x["opportunity_score"], reverse=True)
        return scores


class ClientAcquisitionAuditor(BaseAgent):
    name = "client_acq_auditor"
    description = "Validates geographic data completeness and client origin accuracy"
    tier = 4

    def execute(self):
        self.log("Auditing client acquisition data...")
        issues = self.audit()
        for issue in issues:
            self.create_alert(
                alert_type="data_quality",
                title=issue["title"],
                detail=issue["detail"],
                severity=issue["severity"],
            )
        self.log(f"Audit complete. {len(issues)} issues found.")

    def audit(self):
        """Check for data gaps in client origin tracking."""
        issues = []
        con = get_connection()

        # Check for clients without zip codes
        missing = con.execute("""
            SELECT COUNT(*) FROM client_origins WHERE zip_code IS NULL OR zip_code = ''
        """).fetchone()[0]
        if missing > 0:
            issues.append({
                "title": f"{missing} clients missing zip code",
                "detail": "Client origin records without geographic data reduce analysis quality",
                "severity": "warning",
            })

        # Check for zip codes outside Charlotte metro
        charlotte_zips = [
            '28201','28202','28203','28204','28205','28206','28207','28208','28209','28210',
            '28211','28212','28213','28214','28215','28216','28217','28226','28227','28244',
            '28262','28269','28270','28273','28274','28277','28278','28280','28281','28282',
        ]
        outliers = con.execute("""
            SELECT zip_code, COUNT(*) as cnt FROM client_origins
            WHERE zip_code NOT IN ({})
            AND zip_code IS NOT NULL
            GROUP BY zip_code
        """.format(",".join(f"'{z}'" for z in charlotte_zips))).fetchall()
        if outliers:
            issues.append({
                "title": f"{len(outliers)} zip codes outside Charlotte metro",
                "detail": f"Clients from non-Charlotte zips: {', '.join(r[0] for r in outliers[:5])}",
                "severity": "info",
            })

        # Check competitor coverage: are there zips with clients but no competitor data?
        gaps = con.execute("""
            WITH client_zips AS (SELECT DISTINCT zip_code FROM client_origins WHERE zip_code IS NOT NULL),
            comp_zips AS (SELECT DISTINCT hq_zip FROM competitors WHERE status = 'Active')
            SELECT cz.zip_code FROM client_zips cz
            LEFT JOIN comp_zips coz ON coz.hq_zip = cz.zip_code
            WHERE coz.hq_zip IS NULL
        """).fetchall()
        if gaps:
            issues.append({
                "title": f"{len(gaps)} client zip codes have no competitor intel",
                "detail": f"Blind spots: {', '.join(r[0] for r in gaps[:5])}",
                "severity": "warning",
            })

        con.close()
        return issues
