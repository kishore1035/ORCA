# ORCA Official Data Sources Documentation

This document specifies the verified, official data sources integrated into the ORCA Marine EcOsystem Reasoning with Collaborative Agents platform (SIH Problem Statement SIH26176).

---

## 1. INCOIS (Indian National Centre for Ocean Information Services)

**Agency**: Earth System Science Organization (ESSO) - INCOIS, Ministry of Earth Sciences (MoES), Govt. of India.  
**Role**: Primary marine and ocean intelligence provider for Indian coastal waters and the EEZ.

### Verified Official Interfaces
- **THREDDS Data Server & NCSS**:
  - Base URL: `https://incois.gov.in/thredds/`
  - Catalog URL: `https://incois.gov.in/thredds/catalog/catalog.html`
  - Catalog XML: `https://incois.gov.in/thredds/catalog/catalog.xml`
  - Services: OPeNDAP (`/thredds/dodsC/`), HTTPServer (`/thredds/fileServer/`), WMS (`/thredds/wms/`), NetCDF Subset Service (`/thredds/ncss/grid/` and `/thredds/ncss/point/`).
- **GeoServer WMS Services**:
  - Endpoint: `https://incois.gov.in/geoserver/OSF_CoastalForecast/wms`
- **Ocean State Forecast (OSF) & SARAT Port Services**:
  - WebGIS Portal: `https://incois.gov.in/oceanservices/osfforecast.jsp`
  - Port & Sector Bulletins: `https://sarat.incois.gov.in/OSF/`

### Primary Parameters & Variables
| Parameter | Variable / Layer Name | Unit | Source Model / Instrument | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Significant Wave Height** | `HS` / `SWH` | meters (`m`) | WaveWatch III (WW3) | Mean height of highest third of waves |
| **Wave Period** | `T02` / `MAXW` | seconds (`s`) | WaveWatch III (WW3) | Mean zero-crossing wave period |
| **Swell Height** | `PHS01` / `SWELL` | meters (`m`) | WaveWatch III (WW3) | Primary swell wave height |
| **Swell Period** | `PTP01` | seconds (`s`) | WaveWatch III (WW3) | Primary swell wave peak period |
| **Wind Speed** | `UWND:VWND-mag` / `WSM` | km/h or m/s | ECMWF / NCMRWF Unified Model | Near-surface wind speed magnitude |
| **Wind Direction** | `WDIR` | degrees (`°`) | ECMWF / NCMRWF Unified Model | Direction wind is coming from (0° = North) |
| **Surface Current Speed** | `CURRENTS` | m/s | Regional Ocean Modeling System (ROMS) | Ocean surface current velocity |
| **Surface Current Direction**| `CUR_DIR` | degrees (`°`) | ROMS | Direction of current flow |
| **Sea Surface Temperature** | `SST` | Celsius (`°C`) | In-situ Moorings & Satellite Blends | Sea surface water temperature |

### Data Access Method in ORCA
1. **Live Query**: Calls INCOIS THREDDS NCSS / WMS endpoint with query bounding box or coordinate point for the requested coastal location.
2. **Snapshot / Fallback**: When external INCOIS THREDDS endpoints are unreachable or undergoing scheduled maintenance, the connector uses verified committed forecast snapshots (`backend/data/snapshots/incois_mangalore.json`).
3. **Data Status Tagging**:
   - `FORECAST`: Model forecast output with future validity window.
   - `LIVE`: Near-real-time in-situ mooring or buoy observation.
   - `CACHED`: Fallback snapshot from local cache.
   - `HISTORICAL`: Archived observational dataset.

---

## 2. IMD (India Meteorological Department)

**Agency**: India Meteorological Department (IMD), Ministry of Earth Sciences (MoES), Govt. of India.  
**Role**: Primary weather, rainfall, severe storm, and cyclone warning authority.

### Verified Official Interfaces
- **IMD API Management Platform**:
  - Portal: `https://api.imd.gov.in/`
  - Reference Documentation: `https://api.imd.gov.in/public/api_reference.html`
- **Documented Endpoints**:
  - `https://api.imd.gov.in/api/v1/coastalbulletin`: Coastal weather conditions and squally weather advisories.
  - `https://api.imd.gov.in/api/v1/portwarning`: Marine port storm warning signals (Signals 1 through 11).
  - `https://api.imd.gov.in/api/v1/cyclone_cou`: Cyclone operational updates.
  - `https://api.imd.gov.in/api/v1/cyclone_track`: Cyclone center positions, forecast track points, and intensity stages.
  - `https://api.imd.gov.in/api/v1/cyclone_wind`: Gale wind radius distribution.
  - `https://api.imd.gov.in/api/v1/districtwarning`: Multi-hazard color-coded district warnings (Green / Yellow / Orange / Red).
  - `https://api.imd.gov.in/api/v1/districtnowcast`: 3-hour localized nowcast warnings for thunderstorm and squall.

### Primary Parameters & Variables
| Parameter | Key Field | Unit | Description |
| :--- | :--- | :--- | :--- |
| **Weather Warning Level** | `warning_level` | Categorical | `No Warning` (Green), `Watch` (Yellow), `Alert` (Orange), `Warning` (Red) |
| **Coastal Advisory** | `coastal_bulletin` | Text | Squally wind warnings, fisherman warnings |
| **Port Warning Signal** | `port_signal` | Integer (1-11) | Standard Indian port danger signals |
| **Rainfall Forecast** | `rainfall_mm` | mm | Expected 24-hour precipitation |
| **Cyclone Risk Flag** | `cyclone_active` | Boolean | True if active cyclone alert exists within coastal sector |

### Data Access Method in ORCA
1. **Live Query**: Hits `https://api.imd.gov.in/api/v1/` endpoints when configured with valid API key.
2. **Fallback**: If IMD API authentication is pending or endpoint times out, utilizes the verified IMD warning snapshot (`backend/data/snapshots/imd_mangalore.json`) alongside Open-Meteo for supplementary meteorological parameters.
3. **Data Status Tagging**: Labeled strictly as `FORECAST` or `CACHED`.

---

## 3. ISRO / MOSDAC / NRSC (Satellite & Marine Ecosystem)

**Agency**: Space Applications Centre (SAC) - ISRO / National Remote Sensing Centre (NRSC).  
**Role**: Satellite-derived ocean ecology, ocean color, and bio-optical data.

### Verified Official Interfaces
- **MOSDAC Web Portal**: `https://mosdac.gov.in/`
- **Mission Products**:
  - **Oceansat-3 (EOS-06)**: Ocean Colour Monitor (OCM-3) and Scatterometer (SCAT-3).
  - **Oceansat-2**: OCM-2 historical series.
- **Product Parameters**:
  - Chlorophyll-a concentration (`chlorophyll_mg_m3`)
  - Diffuse Attenuation Coefficient at 490nm ($K_d 490$)
  - Total Suspended Matter (TSM)
  - Sea Surface Temperature (SST from thermal bands and AVHRR/MODIS cross-calibration)

### PFZ (Potential Fishing Zone) Compliance Notice
> [!IMPORTANT]
> **Advisory-Aware Heuristic, Not Statutory PFZ**:
> Official PFZ advisories in India are exclusively produced by INCOIS based on ocean color and thermal front analysis.
> ORCA integrates chlorophyll and SST data to provide **PFZ/advisory-aware fishing analysis**, identifying favorable bio-optical ocean fronts for fish aggregation. ORCA never claims to independently fabricate or supersede statutory INCOIS PFZ forecasts.

### Data Access Method in ORCA
1. **Access Model**: MOSDAC API requires credentials and user approval via `mdapi.py` / user token.
2. **Non-Blocking Architecture**: MOSDAC integration is designed as an optional, graceful layer. If live credentials are not present, ORCA falls back to verified committed Oceansat-3 OCM-3 snapshot data (`backend/data/snapshots/mosdac_ocm3.json`) or NOAA ERDDAP chlorophyll.
3. **Data Status Tagging**: Labeled strictly as `HISTORICAL` or `CACHED` (never deceptively labeled as LIVE).

---

## 4. Supporting & Fallback Providers

- **Open-Meteo Marine & Weather API**:
  - Free, publicly accessible without API keys.
  - Used as secondary fallback when primary national portals are undergoing maintenance.
  - Endpoints: `https://marine-api.open-meteo.com/v1/marine` and `https://api.open-meteo.com/v1/forecast`.
- **NOAA CoastWatch ERDDAP**:
  - Used for 7-day SST trend analysis (`jplMURSST41`) and chlorophyll fallback (`erdMH1chla1day`).
  - Endpoint: `https://coastwatch.pfeg.noaa.gov/erddap/griddap/`.
- **Global Disaster Alert and Coordination System (GDACS)**:
  - Free disaster alert feed for tropical cyclones (`TC`).
  - Endpoint: `https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH`.
- **Blitzortung.org (via MQTT Broker)**:
  - Unauthenticated real-time lightning sample feed (`blitzortung.ha.sed.pl:1883`).
  - Labeled as a real-time sample window.
- **OpenStreetMap & Overpass API**:
  - Nominatim for geocoding (`nominatim.openstreetmap.org/search`).
  - Overpass API for Marine Protected Area (MPA) and sanctuary boundaries (`overpass-api.de/api/interpreter`).
