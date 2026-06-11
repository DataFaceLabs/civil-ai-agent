# Data Catalog

What the civil-ai-be data lake provides today, what it does not, and where the agent
should look for missing values.

Full technical detail is in the civil-ai-be
[Data Requirements Document](https://github.com/DataFaceLabs/civil-ai-be/blob/main/docs/reference/data_requirements.md).

---

## How the Agent Accesses Data

The agent's primary data source is the `civil-ai-be` FastAPI `/report` endpoint, which
queries the Athena serving layer and returns structured section facts with citations.
The endpoint fan-outs 9 Athena queries in parallel (one per section) and returns all
facts within ~7s (post-Sprint 1 performance work).

**Endpoint:** `POST /report` with `{"address": "..."}` → returns `run_id`  
**Section fetch:** `GET /report/{run_id}/domain/{section_id}` → returns section facts  

For fields not yet in the data lake, the agent falls back to the live lookup tools
described in [architecture.md](architecture.md).

---

## Field Coverage by Section

### 2.1 General Information / 2.3 Property Identification

| Field | Status | Source |
|-------|--------|--------|
| Property address | ✅ LIVE | Geocoder + `parcels_unified` |
| Gross acreage | ✅ LIVE | TravisCAD / county CAD → `parcels_unified.lot_acres` |
| Legal description | ✅ LIVE | CAD → `parcels_unified.legal_description` |
| CAD account number | ✅ LIVE | CAD → `parcels_unified.source_record_id` |
| Owner of record | ❌ MISSING | TCAD lookup (not yet in lake) |
| Deed document number | ❌ MISSING | TCAD lookup (not yet in lake) |
| Deed type | ❌ MISSING | TCAD lookup (not yet in lake) |
| Existing use description | ⚠️ PARTIAL | Connector facts; text form only |
| Proposed development | ❌ USER INPUT | Must be provided by engineer |
| CAD discrepancy flag | ⚠️ PARTIAL | Connector facts field `tcad_discrepancies` |

### 2.2 Site Characteristics

| Field | Status | Source |
|-------|--------|--------|
| Min / max elevation | ⚠️ PARTIAL | `terrain_field_facts` (Travis only, 2026-06-07 snapshot — not wired to service view yet) |
| Slope range | ⚠️ PARTIAL | Same — stored but not surfaced |
| Slope table (4 bands) | ❌ MISSING | Derivable from `terrain_field_facts` |
| Soil map unit symbol | ✅ LIVE | SSURGO → `soils_current.mukey`, `soil_series` |
| Soil series name | ✅ LIVE | SSURGO → `soils_current.soil_series_name` |
| Soil coverage % | ✅ LIVE | SSURGO → `soils_current.coverage_pct` |
| Hydrologic soil group | ✅ LIVE | SSURGO → `soils_current.hydro_group` |
| Drainage class | ✅ LIVE | SSURGO → `soils_current.drainage_class` |
| Ecoregion | ❌ MISSING | Derivable from county + jurisdiction lookup |

### 3.1 Zoning

| Field | Status | Source |
|-------|--------|--------|
| Zoning code | ✅ LIVE | CoA GIS overlay → `zoning_current.zoning_code` |
| Zoning category/description | ✅ LIVE | `zoning_current.zoning_base` |
| Zoning overlays (NP, MU, V) | ✅ LIVE | `zoning_current.overlays` |
| Max impervious cover (zoning-based) | ⚠️ PARTIAL | Derivable via E2-S3 (not yet live) |
| Max height | ❌ MISSING | Requires LDC lookup or reference table |
| Rezoning required flag | ❌ USER INPUT | Depends on proposed use |
| WUI / Airport overlay | ❌ MISSING | CoA GIS layers not yet ingested |
| HOME Phase 2 eligibility | ❌ MISSING | Derivable from zoning code |

### 3.2 Platting

| Field | Status | Source |
|-------|--------|--------|
| Plat status | ❌ MISSING | TCCSEARCH connector (E5-S1) |
| Plat document number | ❌ MISSING | TCCSEARCH connector (E5-S1) |
| Plat type required | ❌ USER INPUT / DERIVED | Depends on proposed development |
| Plat exemption eligibility | ⚠️ PARTIAL | Derivable from acreage (E5-S4) |
| LSD required | ❌ MISSING | CoA DSD lookup |

### 3.3 Watershed

| Field | Status | Source |
|-------|--------|--------|
| Watershed name | ✅ LIVE | NHD+ → `watershed_current.watershed_name` |
| HUC12 code | ✅ LIVE | `watershed_current.huc12` |
| CoA watershed classification | ✅ LIVE | `watershed_current.watershed_classification` |
| Edwards Aquifer zone | ❌ MISSING | TCEQ GIS (E3-S1) |
| Barton Springs Zone flag | ❌ MISSING | Derivable from watershed name (E3-S1) |
| WPAP / CZP required flag | ❌ MISSING | Derivable from Edwards zone (E3-S1) |

### 3.4 Impervious Cover

| Field | Status | Source |
|-------|--------|--------|
| Zoning-based IC limit | ❌ MISSING | Derivable from zoning code + jurisdiction table (E2-S3) |
| Watershed-based IC limit | ❌ MISSING | Derivable from watershed classification (E2-S3) |
| Controlling IC limit | ❌ MISSING | Derived value (E2-S3) |
| IC transfer credit available | ❌ MISSING | Jurisdiction rule table (E2-S1) |
| Existing IC % | ❌ MISSING | Not yet in schema |

### 3.5 Utilities

| Field | Status | Source |
|-------|--------|--------|
| Water provider name | ✅ LIVE | TCEQ CCN → `utilities_current.water_provider` |
| Water CCN number | ✅ LIVE | `utilities_current.water_ccn_no` |
| Wastewater provider name | ✅ LIVE | TCEQ CCN → `utilities_current.sewer_provider` |
| Sewer CCN number | ✅ LIVE | `utilities_current.sewer_ccn_no` |
| Electric provider | ✅ LIVE | TCEQ Electric CCN → `utilities_current.electric_provider` |
| Water line size / material | ❌ MISSING | Austin Water grid maps (connector needed) |
| WW line size / material | ❌ MISSING | Austin Water grid maps (connector needed) |
| Distance to nearest main | ❌ MISSING | Spatial analysis needed |
| SER required flag | ❌ MISSING | Derivable from distance to main |
| OSSF flag | ❌ MISSING | Derivable from WW distance (E5-S2) |
| OSSF minimum lot size | ❌ MISSING | Jurisdiction rule table (E5-S2) |
| OSSF permit IDs | ❌ MISSING | Austin Water OSSF lookup |
| Fire jurisdiction (ESD#) | ❌ MISSING | ESD reference table (E2-S2) |
| IFC edition | ❌ MISSING | Jurisdiction reference table (E2-S1, E2-S2) |
| Fire hydrant distance requirement | ❌ MISSING | Derivable from IFC edition + §503.2.1 (E2-S2) |
| Fire flow test status | ❌ MISSING | User input / ESD contact |
| Fire sprinkler trigger | ❌ MISSING | Derivable from IFC + building type |
| Pressure plane / zone | ❌ MISSING | Austin Water (not public) |

### 3.7 Right of Way

| Field | Status | Source |
|-------|--------|--------|
| Road name | ❌ MISSING | TxDOT overlay (E4-S1) |
| Road classification | ❌ MISSING | TxDOT overlay (E4-S1) |
| Road maintenance authority | ❌ MISSING | TxDOT overlay (E4-S1) |
| Existing ROW width | ❌ MISSING | TxDOT overlay (E4-S1) |
| Required ROW width | ❌ MISSING | ASMP / jurisdiction standard (E4-S2) |
| ROW dedication required | ❌ MISSING | Derivable from existing vs. required (E4-S2) |
| TxDOT driveway permit required | ❌ MISSING | Derivable from highway classification (E4-S2) |

### 3.8 / 3.9 Floodplain

| Field | Status | Source |
|-------|--------|--------|
| FEMA zone | ✅ LIVE | FEMA NFHL → `flood_current.fema_zone` |
| Floodway flag | ✅ LIVE | `flood_current.floodway_flag` |
| SFHA flag (100-yr) | ✅ LIVE | `flood_current.sfha` |
| Flood risk score | ✅ LIVE | `flood_current.flood_risk_score` |
| FIRM panel number | ❌ MISSING | FEMA NFHL `fld_ar_id` resolves zone; panel from S_FIRM_PAN layer (not ingested) |
| FIRM effective date | ❌ MISSING | S_FIRM_PAN layer (not ingested) |
| Atlas 14 FDP required | ❌ MISSING | Derivable from zone + jurisdiction |
| EHZ study required | ❌ MISSING | Derivable from slope data |
| ERI required | ❌ MISSING | Derivable from watershed + site area |
| Waterway setback (ft) | ❌ MISSING | Derivable from waterway classification (E3-S4) |
| CEF buffer | ❌ MISSING | CoA GIS (not yet ingested) |
| CWQZ flag | ❌ MISSING | E3-S4 |

### 3.13 Jurisdiction / Governance

| Field | Status | Source |
|-------|--------|--------|
| Primary jurisdiction label | ✅ LIVE | `jurisdiction_current.jurisdiction_label` |
| County | ✅ LIVE | `parcel_overview_current.county` |
| ETJ flag | ⚠️ PARTIAL | From jurisdiction overlay |
| De-annexation status | ❌ MISSING | Not yet in schema |
| IFC edition by jurisdiction | ❌ MISSING | Jurisdiction reference table (E2-S1) |

---

## Summary Scorecard

| Status | Count | Notes |
|--------|-------|-------|
| ✅ LIVE | ~18 fields | Core parcel, zoning, soils, watershed, utilities (provider), flood zone |
| ⚠️ PARTIAL | ~6 fields | Data exists in S3 but not wired to service view (terrain, connector facts) |
| ❌ MISSING | ~70 fields | Not yet in data lake; see roadmap for sprint assignments |

**Total required fields per DRD:** 104  
**Currently LIVE:** ~18 (~17%)

---

## What to Do When a Field Is Missing

The agent should follow this decision tree for each missing value:

```
1. Can it be DERIVED from live fields?
   (IC limit from watershed class, OSSF from WW distance, EHZ from slope)
   → Apply the rule, cite the governing statute, note it's derived

2. Can it be fetched from a LIVE TOOL?
   (TCAD lookup, TCEQ Edwards viewer, MuniCode section text)
   → Call the tool, surface the result with citation

3. Is it USER INPUT?
   (Proposed development, fire flow test result, title commitment)
   → Ask the engineer directly; do not guess

4. Is it UNAVAILABLE for this parcel?
   (Terrain data only for Travis; zoning only for CoA; FIRM panel not in lake)
   → State it clearly: "FIRM panel effective date is not available in the current
     data lake; confirm with the FEMA MSC for panel [fld_ar_id]."
```

Never assert a value that isn't sourced from one of these four paths.

---

## County Coverage Status

| County | FIPS | Zoning | Soils | Jurisdiction | Road/ROW |
|--------|------|--------|-------|-------------|---------|
| Travis | 48453 | ✅ | ✅ | ✅ | ❌ |
| Williamson | 48491 | ❌ | ❌ | ❌ | ❌ |
| Hays | 48209 | ❌ | ❌ | ❌ | ❌ |
| Bastrop | 48021 | ❌ | ❌ | ❌ | ❌ |
| Caldwell | 48055 | ❌ | ❌ | ❌ | ❌ |

All five counties have: parcels ✅, flood ✅, watershed ✅, utilities (provider) ✅

For non-Travis parcels, the agent should be explicit:
> "Zoning data for Williamson County parcels is not yet available in the data lake.
> Zoning must be confirmed directly with [jurisdiction] Development Services or via
> the [jurisdiction] GIS portal."

---

## Citation URL Templates (Quick Reference)

Full registry at [civil-ai-be/docs/reference/source_templates.yaml](https://github.com/DataFaceLabs/civil-ai-be/blob/main/docs/reference/source_templates.yaml)

| Source | URL Template |
|--------|-------------|
| TravisCAD | `https://traviscad.org/propertysearch?query={account_no}` |
| FEMA NFHL | `https://www.fema.gov/flood-maps/national-flood-hazard-layer` |
| USDA Web Soil Survey | `https://websoilsurvey.sc.egov.usda.gov/App/HomePage.htm` |
| TCEQ CCN Viewer | `https://www.tceq.texas.gov/permitting/eapp/viewer.html` |
| CoA ArcGIS Zoning Viewer | `https://austin.maps.arcgis.com/apps/webappviewer/index.html?id=2a3c539da76b4f49906a3524ed4a2cc9` |
| Austin Property Profile | `https://maps.austintexas.gov/PropertyProfile/?search={address}` |
| Austin FloodPro | `https://maps.austintexas.gov/floodpro/` |
| CoA LDC (MuniCode) | `https://library.municode.com/TX/Austin/codes/land_development_code` |
| Travis County Code (EncodePlus) | `https://online.encodeplus.com/regs/traviscounty-tx/index.aspx` |
| Texas TAC | `https://texas-sos.appianportalsgov.com/rules-and-meetings?interface=VIEW_TAC` |
| TCEQ Edwards Viewer | `https://www.tceq.texas.gov/gis/segments-viewer` |
| Travis County Clerk (TCCSEARCH) | `https://www.tccsearch.org/RealEstate/SearchEntry.aspx` |
| USGS NHD+ | `https://www.usgs.gov/national-hydrography/nhdplus-high-resolution` |
