"""
Source registry for ME energy tender tracker.
Every URL below was verified via live search (June 2026) to carry real,
current tender/RFP/PPA/award content for the target sectors.

Trust tiers:
  0 = official primary source (utility/ministry/state-owned offtaker) -> auto-confirmed
  1 = major wire / trade press with consistent Gulf project coverage -> auto-confirmed
  2 = secondary press -> needs a second independent source to upgrade to "Confirmed"
"""

SOURCES = [
    # ================= SAUDI ARABIA =================
    {
        "name": "Saudi Press Agency (SPA) - Economy",
        "url": "https://www.spa.gov.sa/en/category/economy",
        "country": "Saudi Arabia",
        "tier": 0,
        "notes": "Direct PPA/tender signing announcements from the Ministry of Energy.",
    },
    {
        "name": "Principal Buyer (formerly SPPC) - News",
        "url": "https://pb.com.sa/news/",
        "country": "Saudi Arabia",
        "tier": 0,
        "notes": "Sole IPP procurer for Saudi power/renewables; rebranded from SPPC.",
    },

    # ================= UAE =================
    {
        "name": "EWEC (Emirates Water and Electricity Co) - Media",
        "url": "https://www.ewec.ae/en/media",
        "country": "UAE",
        "tier": 0,
        "notes": "Sole procurer for Abu Dhabi; publishes RFP launches directly.",
    },

    # ================= QATAR =================
    {
        "name": "QatarEnergy - Tenders",
        "url": "https://www.qatarenergy.qa/en/SupplyManagement/Tenders/Pages/default.aspx",
        "country": "Qatar",
        "tier": 0,
    },
    {
        "name": "Kahramaa - Tenders",
        "url": "https://www.km.qa/Business/pages/tenders.aspx",
        "country": "Qatar",
        "tier": 0,
    },

    # ================= OMAN =================
    {
        "name": "Nama Power & Water Procurement (OPWP) - News",
        "url": "https://omanpwp.om/news",
        "country": "Oman",
        "tier": 0,
        "notes": "Sole IPP/IWPP procurer for Oman.",
    },

    # ================= KUWAIT =================
    # No clean public Tier-0 news feed identified for KAPP/MEW directly;
    # rely on Tier 1 trade press below, which covers Kuwait tenders consistently.

    # ================= BAHRAIN =================
    {
        "name": "EWA Bahrain - News",
        "url": "https://www.ewa.bh/en/media-center/news",
        "country": "Bahrain",
        "tier": 0,
    },
    {
        "name": "Bahrain News Agency (BNA)",
        "url": "https://www.bna.bh/en",
        "country": "Bahrain",
        "tier": 0,
    },

    # ================= REGIONAL / TRADE PRESS (Tier 1) =================
    {
        "name": "Zawya Projects - Utilities",
        "url": "https://www.zawya.com/en/projects/utilities",
        "country": "regional",
        "tier": 1,
        "notes": "Best single source: project-level MW, value, stage detail across all 6 countries.",
    },
    {
        "name": "SaudiGulf Projects",
        "url": "https://www.saudigulfprojects.com/",
        "country": "regional",
        "tier": 1,
        "notes": "Tracks RFQ -> RFP -> Qualified Bidders -> Award stages consistently, Gulf-wide.",
    },
    {
        "name": "MEED",
        "url": "https://www.meed.com/",
        "country": "regional",
        "tier": 1,
        "notes": "Paywalled beyond headline/summary - usable for headline-level signal only.",
    },
    {
        "name": "Reuters",
        "url": "https://www.reuters.com/site-search/?query={query}",
        "country": "regional",
        "tier": 1,
    },
    {
        "name": "Argaam",
        "url": "https://www.argaam.com/en/search?keyword={query}",
        "country": "Saudi Arabia",
        "tier": 1,
    },
    {
        "name": "MEP Middle East",
        "url": "https://www.mepmiddleeast.com/search?q={query}",
        "country": "regional",
        "tier": 1,
    },

    # ================= SECONDARY CORROBORATION (Tier 2) =================
    {
        "name": "PV Magazine",
        "url": "https://www.pv-magazine.com/?s={query}",
        "country": "regional",
        "tier": 2,
    },
    {
        "name": "SolarQuarter",
        "url": "https://solarquarter.com/?s={query}",
        "country": "regional",
        "tier": 2,
    },
    {
        "name": "Enerdata",
        "url": "https://www.enerdata.net/publications/daily-energy-news.html",
        "country": "regional",
        "tier": 2,
    },
    {
        "name": "IPP Journal",
        "url": "https://ippjournal.com/?s={query}",
        "country": "regional",
        "tier": 2,
    },
    {
        "name": "Power Technology",
        "url": "https://www.power-technology.com/?s={query}",
        "country": "regional",
        "tier": 2,
    },
    {
        "name": "NS Energy Business",
        "url": "https://www.nsenergybusiness.com/?s={query}",
        "country": "regional",
        "tier": 2,
    },
]

SECTOR_KEYWORDS = {
    "Renewables": ["solar tender", "solar PV IPP", "wind power IPP", "renewable energy PPA", "NREP"],
    "Power & Distribution": ["power plant tender", "IPP project RFP", "transmission grid contract", "substation tender", "CCGT IPP"],
    "EV": ["EV charging tender", "electric vehicle infrastructure contract", "EV fleet procurement"],
}

COUNTRIES = ["Saudi Arabia", "UAE", "Qatar", "Oman", "Kuwait", "Bahrain"]

# VERIFICATION LOG (June 2026):
# - All Tier 0 URLs above confirmed live via search to carry real, current
#   tender/RFP/PPA content matching target sectors.
# - Kuwait has no equivalent clean Tier-0 feed; KAPP/MEW announcements surface
#   reliably via SaudiGulf Projects, PV Magazine, and Enerdata instead.
# - MEED requires subscription for full articles; headline/summary still useful
#   as a corroboration signal, not a primary extraction source.
# - Each scraper script must still be tested against its live page structure -
#   verifying the URL returns real content is not the same as confirming the
#   HTML is parseable; that's the next build step.
