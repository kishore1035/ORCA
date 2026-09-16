# backend/app/demo_seed.py
"""Seeds high-fidelity evaluation demo data into the SQLite database.

Provides real-time marine hazard simulations across all risk tiers:
1. Low Risk (Kochi Sector / Munambam PFZ, Risk Score 16/100, Safe departure approved)
2. Moderate Risk (Mumbai Sector / Alibaug, Risk Score 47/100, Marginal chop & current caution)
3. High Risk (Mangaluru Coastal Sector 06:00, Risk Score 68/100, Breaking swell & squall alert)
4. Extreme Hazard (Paradip / Bay of Bengal, Risk Score 92/100, Severe cyclonic storm & gale)
5. What-If Departure Shift (Mangaluru 06:00 vs 11:00, 68 -> 22 temporal risk avoidance)
"""

from app import auth, db


DEMO_EMAIL = "demo@orca.marine"
DEMO_PASSWORD = "demopass123"
DEMO_SESSION_ID = "demo-session-evaluation"


def seed_demo_data() -> None:
    # 1. Ensure demo user exists
    user = db.get_user_by_email(DEMO_EMAIL)
    if user is None:
        p_hash, p_salt = auth.hash_password(DEMO_PASSWORD)
        user_id = db.create_user(DEMO_EMAIL, p_hash, p_salt)
    else:
        user_id = user["id"]

    # 2. Ensure session exists and is owned by demo user
    db.ensure_session(DEMO_SESSION_ID, user_id)
    db.set_last_location(DEMO_SESSION_ID, 12.8698, 74.8430)

    # 3. Check if session already has all 10 demo messages (5 turns)
    history = db.get_history(DEMO_SESSION_ID)
    if len(history) >= 10:
        return  # Already fully seeded

    # Clear prior messages to re-seed complete 5-tier suite
    conn = db._connect()
    try:
        conn.execute("DELETE FROM messages WHERE session_id = ?", (DEMO_SESSION_ID,))
        conn.commit()
    finally:
        conn.close()

    # -------------------------------------------------------------------------
    # SCENARIO 1: HIGH RISK (Mangaluru Coastal Sector - Morning Squall)
    # -------------------------------------------------------------------------
    db.append_message(
        DEMO_SESSION_ID,
        "user",
        "Can I go fishing near Mangaluru tomorrow at 6 AM?",
    )
    turn1_answer = (
        "### ⚠️ HIGH MARINE RISK: ORCA recommends postponing departure at 06:00\n"
        "Current and forecast marine conditions off the Mangaluru coast indicate rough, squally sea conditions exceeding operational safety thresholds for motorized and traditional fishing vessels.\n\n"
        "#### 🌊 Why (Contributing Risk Factors & Physical Hazards):\n"
        "- **Significant Wave Height:** **2.4 m** (exceeds safety threshold of 2.0 m, +30 risk points)\n"
        "- **Sustained Wind Speed:** **32.5 km/h** from West-Southwest (WSW) (+12 risk points)\n"
        "- **Elevated Swell:** **1.9 m at 8.2s period** creating heavy breaking surf over coastal bar mouths (+10 risk points)\n"
        "- **IMD Coastal Advisory:** Active **Yellow Warning** for squally weather along Dakshina Kannada coast (+10 risk points)\n"
        "- *Capsizing Hazard:* Steep swell breaking over nearshore sandbars poses extreme swamping risk during harbor exit.\n\n"
        "#### 📊 Transparent Metrics & Grounding:\n"
        "- **Risk Score:** **68/100 (HIGH RISK)**\n"
        "- **Evidence Confidence:** **94% Multi-source Consensus**\n"
        "- **Authoritative Sources:** INCOIS Marine Forecast, IMD Coastal Warning, ISRO-MOSDAC Satellite\n"
        "- **Data Status:** FORECAST (validated against regional buoy telemetry)\n\n"
        "💡 *Recommendation:* Delay departure until late morning (after 10:30 AM), when wind and wave heights subside below alert thresholds."
    )
    turn1_meta = {
        "risk": {
            "risk_score": 68,
            "risk_level": "HIGH",
            "factors": [
                "High wave height 2.4m exceeds cautionary limit 2.0m (+30)",
                "Moderate wind 32.5 km/h above threshold 25.0 km/h (+12)",
                "Elevated swell height 1.9m creates rough coastal break (+10)",
                "Active IMD Yellow Warning (Watch - Squally Weather Advisory) (+10)",
            ],
            "recommendation": "ORCA recommends postponing departure at 06:00. Elevated wave height and strong winds present hazardous conditions for small craft.",
            "confidence": 0.94,
        },
        "verification": {
            "is_verified": True,
            "sources": ["INCOIS", "IMD", "ISRO-MOSDAC", "Open-Meteo"],
            "data_status": "FORECAST",
            "checks_passed": [
                "Multi-source parameter consensus verified",
                "Offshore grid distance 3.8 km within marine coverage",
                "Threshold boundary audit passed (IMD Yellow match)",
            ],
            "issues": [],
            "confidence": 0.95,
            "nearest_grid_distance_km": 3.8,
        },
        "evidence": [
            {
                "parameter": "significant_wave_height",
                "value": 2.4,
                "unit": "m",
                "latitude": 12.8698,
                "longitude": 74.843,
                "timestamp": "2026-09-17T06:00:00Z",
                "source": "INCOIS",
                "data_status": "FORECAST",
                "confidence": 0.94,
            },
            {
                "parameter": "wind_speed",
                "value": 32.5,
                "unit": "km/h",
                "latitude": 12.8698,
                "longitude": 74.843,
                "timestamp": "2026-09-17T06:00:00Z",
                "source": "IMD",
                "data_status": "FORECAST",
                "confidence": 0.92,
            },
            {
                "parameter": "swell_height",
                "value": 1.9,
                "unit": "m",
                "latitude": 12.8698,
                "longitude": 74.843,
                "timestamp": "2026-09-17T06:00:00Z",
                "source": "Open-Meteo",
                "data_status": "FORECAST",
                "confidence": 0.91,
            },
            {
                "parameter": "weather_warning_level",
                "value": "Yellow Warning",
                "unit": "alert",
                "latitude": 12.8698,
                "longitude": 74.843,
                "timestamp": "2026-09-16T12:00:00Z",
                "source": "IMD",
                "data_status": "LIVE",
                "confidence": 0.96,
            },
        ],
        "location": {
            "latitude": 12.8698,
            "longitude": 74.843,
            "display_name": "Mangaluru Coastal Sector, Karnataka",
            "district": "Dakshina Kannada",
            "state": "Karnataka",
            "country": "India",
            "source": "MANUAL",
            "distance_to_coast_km": 4.2,
            "is_offshore": True,
            "in_marine_coverage": True,
        },
    }
    db.append_message(DEMO_SESSION_ID, "assistant", turn1_answer, metadata=turn1_meta)

    # -------------------------------------------------------------------------
    # SCENARIO 2: WHAT-IF DEPARTURE SHIFT (Mangaluru 06:00 -> 11:00 AM)
    # -------------------------------------------------------------------------
    db.append_message(
        DEMO_SESSION_ID,
        "user",
        "What if I leave at 11 AM instead?",
    )
    turn2_answer = (
        "### ✅ LOW MARINE RISK: Departure at 11:00 AM is favorable\n"
        "Shifting your departure from 06:00 AM to 11:00 AM provides a significant safety window as the morning swell dissipates and offshore wind speeds decrease by more than 54%.\n\n"
        "#### ⏰ What-If Temporal Analysis:\n"
        "- **Risk Score Improvement:** Drops from **68 (HIGH)** down to **22 (LOW)** — a **46-point risk reduction**\n"
        "- **Significant Wave Height:** Eases from **2.4 m** down to **1.3 m** (well within safe operational limits)\n"
        "- **Wind Speed:** Subsides from **32.5 km/h** down to **14.8 km/h**\n"
        "- **IMD Status:** Yellow advisory cleared (returns to Green/Safe)\n\n"
        "#### 📊 Verified Condition Delta:\n"
        "- **Original Window (06:00):** Rough breaking sea state, strong offshore chop\n"
        "- **Alternative Window (11:00):** Calm surface, gentle breeze, favorable for pelagic operations\n\n"
        "💡 *Actionable Verdict:* Approved for departure at 11:00 AM. Favorable return window remains open until 17:30."
    )
    turn2_meta = {
        "risk": {
            "risk_score": 22,
            "risk_level": "LOW",
            "factors": [
                "Wave height 1.3m is within manageable limits",
                "Wind speed 14.8 km/h is favorable",
                "IMD coastal advisory expired (Normal Green state)",
            ],
            "recommendation": "ORCA approves departure at 11:00. Marine and weather conditions are calm and favorable.",
            "confidence": 0.95,
        },
        "verification": {
            "is_verified": True,
            "sources": ["INCOIS", "IMD"],
            "data_status": "FORECAST",
            "checks_passed": [
                "Temporal gradient verified across ECMWF & INCOIS models",
                "Yellow advisory expiry confirmed with IMD coastal bulletin",
            ],
            "issues": [],
            "confidence": 0.96,
            "nearest_grid_distance_km": 3.8,
        },
        "what_if": {
            "original_time": "06:00",
            "original_risk_score": 68,
            "original_risk_level": "HIGH",
            "alternative_time": "11:00",
            "alternative_risk_score": 22,
            "alternative_risk_level": "LOW",
            "verdict": "Significant safety improvement. Delaying departure by 5 hours avoids morning storm swell and gusty winds.",
            "differences": [
                {
                    "parameter": "Significant Wave Height",
                    "original": "2.4 m",
                    "alternative": "1.3 m",
                    "delta": "-1.1 m",
                    "impact": "Favorable (Below Threshold)",
                },
                {
                    "parameter": "Wind Speed",
                    "original": "32.5 km/h",
                    "alternative": "14.8 km/h",
                    "delta": "-17.7 km/h",
                    "impact": "Calm (Safe)",
                },
                {
                    "parameter": "Alert Level",
                    "original": "Yellow Warning",
                    "alternative": "Green (Normal)",
                    "delta": "Advisory Cleared",
                    "impact": "Safe Operations",
                },
            ],
        },
        "location": {
            "latitude": 12.8698,
            "longitude": 74.843,
            "display_name": "Mangaluru Coastal Sector, Karnataka",
            "district": "Dakshina Kannada",
            "state": "Karnataka",
            "country": "India",
            "source": "MANUAL",
            "distance_to_coast_km": 4.2,
            "is_offshore": True,
            "in_marine_coverage": True,
        },
    }
    db.append_message(DEMO_SESSION_ID, "assistant", turn2_answer, metadata=turn2_meta)

    # -------------------------------------------------------------------------
    # SCENARIO 3: MODERATE RISK (Mumbai Coastal Sector - Chop & Current)
    # -------------------------------------------------------------------------
    db.append_message(
        DEMO_SESSION_ID,
        "user",
        "Check marine risk and hazard conditions off Mumbai at 14:00",
    )
    turn3_answer = (
        "### ⚠️ MODERATE MARINE RISK: Exercise caution offshore off Mumbai\n"
        "Borderline sea state detected off the Mumbai/Konkan coastal sector. Mechanized and decked commercial vessels may operate with vigilance, but small motorized and non-motorized artisanal boats should stay within protected harbor waters.\n\n"
        "#### 🌊 Why (Contributing Risk Factors & Physical Hazards):\n"
        "- **Moderate Wave Height:** **1.8 m** (above baseline limit of 1.5 m, +18 risk points)\n"
        "- **Coastal Wind:** **28.0 km/h** with cross-swell chop (+12 risk points)\n"
        "- **Short Steep Wave Period:** **4.9 seconds** creating sharp, irregular coastal chop (+5 risk points)\n"
        "- **Elevated Surface Current:** **0.72 m/s** inducing noticeable lateral vessel drift across navigation lanes (+5 risk points)\n"
        "- **IMD Advisory:** Yellow Watch (Squally weather advisory for Konkan coast, +10 risk points)\n\n"
        "#### 📊 Transparent Metrics & Grounding:\n"
        "- **Risk Score:** **47/100 (MODERATE RISK)**\n"
        "- **Evidence Confidence:** **92% Multi-source Consensus**\n"
        "- **Sources:** INCOIS Marine Model, IMD Coastal Bulletin, Open-Meteo\n"
        "- **Data Status:** FORECAST\n\n"
        "💡 *Operational Advice:* Avoid nearshore shoals and shallow rocky heads off Colaba and Prongs Reef where swell steepness doubles."
    )
    turn3_meta = {
        "risk": {
            "risk_score": 47,
            "risk_level": "MODERATE",
            "factors": [
                "Moderate wave height 1.8m above baseline 1.5m (+18)",
                "Moderate wind 28.0 km/h above threshold 25.0 km/h (+12)",
                "Short wave period 4.9s indicates steep, choppy seas (+5)",
                "Moderate surface drift 0.72 m/s (+5)",
                "Active IMD Yellow Warning (Watch - Squally Weather Advisory) (+10)",
            ],
            "recommendation": "ORCA advises caution at 14:00. Borderline conditions; mechanized vessels may operate with vigilance, but small crafts should stay near shore.",
            "confidence": 0.92,
        },
        "verification": {
            "is_verified": True,
            "sources": ["INCOIS", "IMD", "Open-Meteo"],
            "data_status": "FORECAST",
            "checks_passed": [
                "Wave and wind parameter consensus verified",
                "Grid point 4.1 km within Konkan marine zone",
            ],
            "issues": [],
            "confidence": 0.92,
            "nearest_grid_distance_km": 4.1,
        },
        "evidence": [
            {
                "parameter": "significant_wave_height",
                "value": 1.8,
                "unit": "m",
                "latitude": 18.922,
                "longitude": 72.834,
                "timestamp": "2026-09-16T14:00:00Z",
                "source": "INCOIS",
                "data_status": "FORECAST",
                "confidence": 0.93,
            },
            {
                "parameter": "wind_speed",
                "value": 28.0,
                "unit": "km/h",
                "latitude": 18.922,
                "longitude": 72.834,
                "timestamp": "2026-09-16T14:00:00Z",
                "source": "IMD",
                "data_status": "FORECAST",
                "confidence": 0.91,
            },
            {
                "parameter": "surface_current_speed",
                "value": 0.72,
                "unit": "m/s",
                "latitude": 18.922,
                "longitude": 72.834,
                "timestamp": "2026-09-16T14:00:00Z",
                "source": "Open-Meteo",
                "data_status": "FORECAST",
                "confidence": 0.88,
            },
        ],
        "location": {
            "latitude": 18.922,
            "longitude": 72.834,
            "display_name": "Mumbai Offshore Sector, Maharashtra",
            "district": "Mumbai",
            "state": "Maharashtra",
            "country": "India",
            "source": "MANUAL",
            "distance_to_coast_km": 5.0,
            "is_offshore": True,
            "in_marine_coverage": True,
        },
    }
    db.append_message(DEMO_SESSION_ID, "assistant", turn3_answer, metadata=turn3_meta)

    # -------------------------------------------------------------------------
    # SCENARIO 4: EXTREME RISK (Paradip - Tropical Cyclone & Gale Warning)
    # -------------------------------------------------------------------------
    db.append_message(
        DEMO_SESSION_ID,
        "user",
        "Simulate extreme cyclone hazard and squall alert off Paradip",
    )
    turn4_answer = (
        "### 🚨 EXTREME MARITIME HAZARD: Operations strictly prohibited off Paradip\n"
        "Extreme meteorological and oceanographic conditions exceed vessel survivability thresholds. Severe tropical cyclonic circulation producing violent storm seas and heavy squalls across the Odisha coastal zone.\n\n"
        "#### 🌊 Why (Contributing Risk Factors & Physical Hazards):\n"
        "- **Extreme Wave Height:** **3.8 m** (severely exceeds critical 2.8 m threshold, +40 risk points)\n"
        "- **Gale-Force Coastal Winds:** **58.0 km/h** with gusts exceeding 75 km/h (+30 risk points)\n"
        "- **Active Tropical Cyclone Advisory:** JTWC/GDACS tracked cyclonic system in Bay of Bengal (+35 risk points)\n"
        "- **IMD Coastal Warning:** Active **Red Warning** (Severe Weather Alert - Total Suspension of Maritime Operations, +30 risk points)\n"
        "- **Violent Sea State:** Breaking waves, zero visibility in squalls, and severe storm surge.\n\n"
        "#### 📊 Transparent Metrics & Grounding:\n"
        "- **Risk Score:** **95/100 (EXTREME RISK)**\n"
        "- **Evidence Confidence:** **97% Multi-source Verification**\n"
        "- **Authoritative Sources:** GDACS Cyclone Tracker, IMD Severe Weather Warning, INCOIS High Sea Wave Bulletin\n"
        "- **Data Status:** LIVE & FORECAST\n\n"
        "🚨 *Mandatory Directive:* Absolute suspension of all fishing, shipping, and port operations. All crafts must remain secured in harbor moorings."
    )
    turn4_meta = {
        "risk": {
            "risk_score": 95,
            "risk_level": "EXTREME",
            "factors": [
                "Extreme wave height 3.8m exceeds severe threshold 2.8m (+40)",
                "Gale-force wind speed 58.0 km/h (+30)",
                "Active Tropical Cyclone Advisory (Bay of Bengal TC-02) (+35)",
                "Active IMD Red Warning (Severe Weather Alert) (+30)",
            ],
            "recommendation": "ORCA strictly recommends postponing departure. Dangerous sea state and active meteorological advisories.",
            "confidence": 0.97,
        },
        "verification": {
            "is_verified": True,
            "sources": ["GDACS", "IMD", "INCOIS"],
            "data_status": "LIVE",
            "checks_passed": [
                "JTWC/GDACS Tropical Cyclone telemetry matched",
                "IMD Red Warning bulletin confirmed",
                "INCOIS High Wave warning validated",
            ],
            "issues": [],
            "confidence": 0.97,
            "nearest_grid_distance_km": 2.8,
        },
        "evidence": [
            {
                "parameter": "significant_wave_height",
                "value": 3.8,
                "unit": "m",
                "latitude": 20.316,
                "longitude": 86.611,
                "timestamp": "2026-09-16T08:00:00Z",
                "source": "INCOIS",
                "data_status": "FORECAST",
                "confidence": 0.98,
            },
            {
                "parameter": "wind_speed",
                "value": 58.0,
                "unit": "km/h",
                "latitude": 20.316,
                "longitude": 86.611,
                "timestamp": "2026-09-16T08:00:00Z",
                "source": "IMD",
                "data_status": "LIVE",
                "confidence": 0.97,
            },
            {
                "parameter": "weather_warning_level",
                "value": "Red Alert (Severe Cyclone)",
                "unit": "alert",
                "latitude": 20.316,
                "longitude": 86.611,
                "timestamp": "2026-09-16T08:00:00Z",
                "source": "IMD",
                "data_status": "LIVE",
                "confidence": 0.99,
            },
        ],
        "location": {
            "latitude": 20.316,
            "longitude": 86.611,
            "display_name": "Paradip Coastal Sector, Odisha",
            "district": "Jagatsinghpur",
            "state": "Odisha",
            "country": "India",
            "source": "MANUAL",
            "distance_to_coast_km": 3.2,
            "is_offshore": True,
            "in_marine_coverage": True,
        },
    }
    db.append_message(DEMO_SESSION_ID, "assistant", turn4_answer, metadata=turn4_meta)

    # -------------------------------------------------------------------------
    # SCENARIO 5: LOW RISK & PFZ ADVISORY (Kochi / Munambam Marine Sector)
    # -------------------------------------------------------------------------
    db.append_message(
        DEMO_SESSION_ID,
        "user",
        "Where is the nearest safe fishing zone near Kochi?",
    )
    turn5_answer = (
        "### ✅ LOW MARINE RISK: Conditions are favorable for fishing departure\n"
        "Sea state and meteorological indicators off the Kochi coast are calm and within safe operating limits. Authoritative Potential Fishing Zone (PFZ) advisory retrieved from official INCOIS ocean telemetry and ISRO satellite observations.\n\n"
        "#### 🌊 Why (Contributing Safety Factors):\n"
        "- **Calm Significant Wave Height:** **0.8 m** (well below 1.5 m baseline limit)\n"
        "- **Gentle Coastal Breeze:** **11.5 km/h** from West-Northwest (WNW)\n"
        "- **Swell State:** Mild 0.6 m at 8.5s period, smooth sea surface\n"
        "- **IMD Status:** Normal (Green) — no weather warnings or squall alerts along Kerala coast\n\n"
        "#### 🐟 Authoritative INCOIS PFZ Advisory:\n"
        "- **Reference Landing Center:** **Munambam / Kochi Harbor**\n"
        "- **Advisory Bearing:** **252° (West-Southwest)**\n"
        "- **Distance Offshore:** **19.4 km (10.5 Nautical Miles)**\n"
        "- **Target Depth Band:** **32 – 38 meters**\n"
        "- **Oceanographic Front:** Thermal SST front at **28.1°C** and high chlorophyll primary productivity bloom (**1.92 mg/m³**)\n\n"
        "#### 📊 Transparent Metrics & Grounding:\n"
        "- **Risk Score:** **16/100 (LOW RISK)**\n"
        "- **Evidence Confidence:** **96% Multi-source Verification Consensus**\n"
        "- **Authoritative Sources:** INCOIS PFZ Bulletin, ISRO OCM-3 Satellite, IMD Coastal Station"
    )
    turn5_meta = {
        "risk": {
            "risk_score": 16,
            "risk_level": "LOW",
            "factors": [
                "Wave height 0.8m is within manageable limits",
                "Wind speed 11.5 km/h is favorable",
                "No active IMD advisories (Green/Normal state)",
                "SST and chlorophyll thermal front optimal for pelagic aggregation",
            ],
            "recommendation": "ORCA approves departure. Marine and weather conditions are calm and favorable.",
            "confidence": 0.96,
        },
        "verification": {
            "is_verified": True,
            "sources": ["INCOIS", "ISRO-MOSDAC", "IMD"],
            "data_status": "LIVE",
            "checks_passed": [
                "INCOIS official Marine Fisheries PFZ bulletin cross-referenced",
                "ISRO OCM-3 thermal-biological front overlap confirmed",
                "Calm sea state verified against regional buoy telemetry",
            ],
            "issues": [],
            "confidence": 0.96,
            "nearest_grid_distance_km": 2.1,
        },
        "evidence": [
            {
                "parameter": "significant_wave_height",
                "value": 0.8,
                "unit": "m",
                "latitude": 9.9679,
                "longitude": 76.2444,
                "timestamp": "2026-09-16T04:00:00Z",
                "source": "INCOIS",
                "data_status": "LIVE",
                "confidence": 0.96,
            },
            {
                "parameter": "wind_speed",
                "value": 11.5,
                "unit": "km/h",
                "latitude": 9.9679,
                "longitude": 76.2444,
                "timestamp": "2026-09-16T04:00:00Z",
                "source": "IMD",
                "data_status": "LIVE",
                "confidence": 0.95,
            },
            {
                "parameter": "surface_current_speed",
                "value": 0.22,
                "unit": "m/s",
                "latitude": 9.9679,
                "longitude": 76.2444,
                "timestamp": "2026-09-16T04:00:00Z",
                "source": "Open-Meteo",
                "data_status": "LIVE",
                "confidence": 0.92,
            },
            {
                "parameter": "sst_celsius",
                "value": 28.1,
                "unit": "°C",
                "latitude": 9.9679,
                "longitude": 76.2444,
                "timestamp": "2026-09-16T04:00:00Z",
                "source": "ISRO-MOSDAC",
                "data_status": "LIVE",
                "confidence": 0.95,
            },
            {
                "parameter": "chlorophyll_mg_m3",
                "value": 1.92,
                "unit": "mg/m³",
                "latitude": 9.9679,
                "longitude": 76.2444,
                "timestamp": "2026-09-16T04:00:00Z",
                "source": "ISRO-MOSDAC",
                "data_status": "LIVE",
                "confidence": 0.94,
            },
        ],
        "location": {
            "latitude": 9.9679,
            "longitude": 76.2444,
            "display_name": "Kochi Marine Sector, Kerala",
            "district": "Ernakulam",
            "state": "Kerala",
            "country": "India",
            "source": "MANUAL",
            "distance_to_coast_km": 2.1,
            "is_offshore": True,
            "in_marine_coverage": True,
        },
    }
    db.append_message(DEMO_SESSION_ID, "assistant", turn5_answer, metadata=turn5_meta)

    # 4. Also make sure existing user pkishore530@gmail.com has access to this session
    existing_user = db.get_user_by_email("pkishore530@gmail.com")
    if existing_user:
        try:
            db.ensure_session(DEMO_SESSION_ID, existing_user["id"])
        except Exception:
            pass
