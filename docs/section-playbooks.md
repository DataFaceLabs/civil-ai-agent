# Section Playbooks

Per-section guidance for the agent: what data facts to pull, what boilerplate to apply,
what jurisdiction variations exist, and what infeasibility signals to watch for.

Based on analysis of 20 ATXCivil feasibility studies (2022–2025).  Section numbering
follows the standard 3.1–3.19 template used in 17 of 20 studies.

---

## Section 2.1 — General Information / Property Description

**Required facts:**
- Property address (geocoded)
- Gross acreage (from CAD)
- Jurisdiction (from `jurisdiction_current` view)
- CAD source and account number
- Owner of record
- Deed document number and type
- Existing use / improvements description
- Proposed development description (user input)

**Standard opening:**
> "The subject property is located at [address].  The site consists of approximately
> [acreage] acres per [County] CAD (Account No. [id]).  The property is owned by
> [owner] per deed recorded as [deed_type] Document No. [deed_doc].  The subject
> property is located within [jurisdiction]."

**User input required for:** proposed development (the agent must ask the engineer what
the client intends to build before drafting this section).

**Infeasibility signal:** None in this section — but record the proposed development
type for use throughout.

---

## Section 2.2 — Site Characteristics

**Required facts:**
- Min/max elevation (from `terrain_field_facts` or civil-ai-be, or fetched from USGS 3DEP)
- Slope range and slope table (0–5%, 5–10%, 10–15%, 15%+)
- Soil types from SSURGO: map unit symbol, series name, coverage %, hydrologic soil group, drainage class
- Ecoregion (determined by county: Travis/Williamson/Hays = Edwards Plateau / Blackland Prairie; Burnet = Post Oak Savanna)

**Standard opening:**
> "The subject property is located in the [ecoregion] ecoregion.  Elevations on the
> site range from approximately [min_elev] to [max_elev] feet above mean sea level.
> Site slopes range from [min_slope] to [max_slope] percent."

**Soil table format:**
| Map Unit | Symbol | Coverage | Hydrologic Group |
|----------|--------|----------|-----------------|
| [series] | [symbol] | [pct]% | [A/B/C/D] |

**Soil narrative:**
Always include the standard NRCS boilerplate definitions for each HSG group present.
This is non-negotiable per ATXCivil style — every study repeats the Group A/B/C/D
definitions.

**Slope infeasibility signal:**
- Slopes > 15% on > 30% of site → flag for EHZ (Erosion Hazard Zone) study in §3.9

---

## Section 2.3 — Property Identification

**Required facts:**
- CAD account number and link
- Any CAD discrepancy (area, owner, legal description)

**Standard text (no discrepancy):**
> "The subject property is identified in [County] CAD records as Account No. [id].
> No material discrepancies were noted between the CAD records and the property
> information provided for this study."

**Standard text (discrepancy found):**
> "The subject property is identified in [County] CAD records as Account No. [id].
> A discrepancy of [X] acres was noted between the CAD recorded acreage ([CAD value])
> and the [legal description / survey] ([survey value]).  This discrepancy should be
> resolved prior to platting."

---

## Section 3.1 — Zoning

**Required facts:**
- Zoning code (from `zoning_current`)
- Zoning district description (from LDC or jurisdiction code)
- Zoning overlays (NP, MU, V, -CO, etc.)
- Max height (from zoning or compatibility)
- Max impervious cover (zoning-based only here; watershed-based IC goes in §3.4)
- Rezoning required flag
- Any special designations (SMART Housing, HOME Phase 2, WUI overlay, Airport overlay)

**Travis County unincorporated:**
> "Travis County is a non-zoning county.  No zoning applies to the subject property.
> Land use is regulated by Travis County Code Chapter 482."

**CoA Full Purpose:**
Start with the zoning table, then a narrative confirming the proposed use is permitted
by right or requires a special approval.

**Overlays:**
List each overlay code and its practical impact.

> "The subject property carries a Neighborhood Plan (NP) overlay.  Any proposed
> development must be consistent with the [Neighborhood Plan Name] Neighborhood Plan."

**Infeasibility signal:**
If zoning does not permit the proposed use → state this clearly and identify the
rezoning process required.

---

## Section 3.2 — Platting

**Required facts:**
- Is the property already platted? (from `connector_field_facts` or TCCSEARCH lookup)
- Plat document number (if platted)
- Plat type required (Minor Final, Final, Replat)
- Plat exemption eligibility (LGC §212.004(a): > 5 ac with access; > 10 ac)
- LSD (Land Status Determination) required flag (CoA specific)

**Standard options:**

*Already platted, no re-plat needed:*
> "The subject property is platted as [plat name], recorded as Document No. [number].
> No re-plat is required for the proposed development."

*Platting required:*
> "The subject property is unplatted.  Platting will be required prior to the issuance
> of a building permit.  A [Minor Final Plat / Final Plat] will be required through
> [jurisdiction] Development Services."

*Plat exemption applicable:*
> "Per Texas LGC §212.004(a), the subject property may be eligible for a plat
> exemption.  At [acreage] acres, the site exceeds the [5/10]-acre threshold.  A formal
> plat exemption determination from [jurisdiction] is recommended prior to any
> subdivision activity."

*CoA LSD:*
> "A Land Status Determination (LSD) through the City of Austin Development Services
> Department will be required prior to any subdivision of the subject property."

**Infeasibility signal:** None typically — but if property is in a subdivision that
prohibits further subdivision, flag it.

---

## Section 3.3 — Watershed

**Required facts:**
- Watershed name (from `watershed_current`)
- HUC12 code
- CoA watershed classification (Urban / Suburban / Water Supply Rural / Water Supply Suburban) — CoA jurisdiction only
- Edwards Aquifer zone (from `environmental_current` or TCEQ tool)
- Barton Springs Zone flag (if watershed is Barton Creek, Slaughter Creek, etc.)
- WPAP required flag (if Recharge or Contributing Zone)

**Standard structure:**
1. Identify watershed name and HUC12
2. State CoA watershed classification and its IC implications (don't go deep — §3.4 covers IC)
3. State Edwards Aquifer zone
4. State WPAP/CZP requirement if applicable

**Edwards — Recharge Zone:**
> "The subject property is located within the Edwards Aquifer Recharge Zone per the
> TCEQ Edwards Aquifer viewer.  Development is a regulated activity per 30 TAC Chapter
> 213.  A Water Pollution Abatement Plan (WPAP) will be required prior to the issuance
> of a subdivision plat or site plan permit."

**Edwards — Contributing Zone:**
> "The subject property is located within the Edwards Aquifer Contributing Zone per the
> TCEQ Edwards Aquifer viewer.  A Contributing Zone Plan (CZP) must be submitted to
> TCEQ per 30 TAC §213.21 as a prerequisite for any permitted activity."

**Edwards — Outside:**
> Standard "no Edwards permit required" boilerplate (see Writing Guide §3.9).

**Infeasibility signal:**
- Recharge Zone + OSSF → double-permit (WPAP + TCEQ OSSF).  Flag complexity.
- Recharge Zone + impervious surface > regulated thresholds → mention TCEQ regulated activities list.

---

## Section 3.4 — Impervious Cover

**Required facts:**
- Zoning-based IC limit (from zoning code lookup)
- Watershed-based IC limit (from watershed classification + IC table)
- Controlling limit (the more restrictive of the two)
- IC transfer credit availability
- Barton Springs Zone IC limits (if applicable — more restrictive)

**Standard text:**
> "The maximum impervious cover for the subject property is [limit]%.  The zoning
> district [CS / MF-4 / etc.] allows up to [zoning_ic]%, while the [Suburban /
> Water Supply Rural / Urban] watershed classification limits impervious cover to
> [watershed_ic]% per CoA LDC §25-8-[table].  The [zoning / watershed] limit is
> controlling as the more restrictive standard."

**Travis County unincorporated:**
> "Travis County Code §482.216 limits impervious cover to [45% for commercial / 30%
> for residential lots < 1 acre average] for development within the unincorporated
> county."

**LCRA HLWO:**
> "The subject property is within the LCRA Highland Lakes Watershed Ordinance (HLWO)
> service area.  An LCRA BMP Maintenance Permit is required per Travis County Code
> §482.944 for impervious cover additions exceeding [threshold] square feet."

**Infeasibility signal:**
If proposed development exceeds the controlling IC limit → flag clearly with numbers.

---

## Section 3.5 — Utility Location and Availability

This section has four mandatory subsections.  Each should be drafted separately.

### 3.5.1 Water

**Required facts:**
- Water provider name (from `utilities_current`)
- CCN number
- Existing line size and material at site frontage
- SER requirement flag
- Distance to line if not at frontage

### 3.5.2 Wastewater

**Required facts:**
- Wastewater provider name
- Existing line size and material at site frontage
- Distance to line if not at frontage
- SER required flag
- OSSF flag (if no public WW available)
- OSSF minimum lot size (from jurisdiction rules)

### 3.5.3 Electric

**Required facts:**
- Electric provider (from `utilities_current`)
- Austin Energy service requirements (if AE): transformer pad ≤ 6 ft from traffic,
  12 ft truck access, 16 ft vertical clearance, meter ≤ 150 ft line-of-sight

### 3.5.4 Fire Protection

**Required facts:**
- Fire jurisdiction (ESD number and name, or city fire department)
- IFC edition adopted by jurisdiction
- Applicable fire flow requirement (IFC Appendix B)
- Fire hydrant distance requirement (IFC §503.2.1: 400 ft from exterior walls, second
  within 500 ft)
- Fire access road: 25 ft minimum width, 14 ft vertical clearance (IFC §503.2.1)
- Fire sprinkler trigger (if known: typically > 12,000 sf for commercial)
- Fire flow test status (ordered / completed / pending)

**OSSF infeasibility signal:**
> "At [acreage] acres, the subject property [does not meet / is borderline for] the
> minimum lot size requirement for [advanced/conventional] OSSF of [1.0/1.5] acres
> per 30 TAC §285.91.  On-site sewage treatment [is not feasible / should be confirmed
> with a soil evaluation]."

**Critical infeasibility (509 Cresthill pattern):**
> "At 0.48 acres, the subject property does not meet the minimum lot size requirement
> of 1.0 acres for an advanced OSSF system per 30 TAC §285.91.  Public wastewater
> service is not available at this location.  On-site sewage treatment is not feasible
> for the subject property under current regulations.  The proposed subdivision as
> described is not feasible without extension of public wastewater service or connection
> to a regional system."

---

## Section 3.6 — Utility Capacity

**Required facts:**
- Water pressure plane elevation and zone name (if known from provider)
- LUE (Living Unit Equivalent) fee structure (if available from provider)
- Any formal utility feasibility study required by provider (e.g., Manville WSC)
- Fire flow test status and result (gpm @ psi if completed)

**Standard (no capacity issues known):**
> "Water and wastewater capacity for the subject property will be evaluated by
> [provider] as part of the SER review process.  A formal utility capacity study is
> [not anticipated / required by [provider]] at this time."

**Fire flow test ordered:**
> "A fire flow test has been ordered through [ESD name].  Results will be provided to
> [jurisdiction] Development Services prior to site plan approval.  Per IFC [year]
> Appendix B, the required fire flow for [construction type] occupancy is [X] gallons
> per minute at [Y] psi residual."

---

## Section 3.7 — Right of Way

**Required facts:**
- Road name(s) fronting the property
- Road classification (ASMP level / county designation / TxDOT functional class)
- Road maintenance authority (City / County / TxDOT)
- Existing ROW width (feet)
- Required ROW width per governing standard
- ROW dedication required (feet)
- TxDOT driveway permit required (if state highway frontage)
- Sidewalk requirement

**ASMP classification (CoA):**
> "Wonder Drive is classified as a Level 2 Collector per the City of Austin Austin
> Strategic Mobility Plan (ASMP).  The minimum ROW width for a Level 2 Collector is
> 80 feet.  The existing ROW is 25 feet.  A 7.5-foot ROW dedication will be required
> on each side of the street per the ASMP."

**Travis County road:**
> "Hudson Bend Road is classified as a Rural Major Collector and maintained by Travis
> County Transportation and Natural Resources (TNR).  The existing ROW is approximately
> 60 feet.  Travis County requires a minimum ROW of [X] feet for this classification."

**TxDOT state highway:**
> "The subject property fronts [highway name], a state highway maintained by TxDOT.
> A driveway permit (TxDOT Form 1058) will be required from the Austin District office
> prior to any construction access.  The existing ROW is [X] feet."

---

## Section 3.8 — FEMA and Floodplain Maps

**Required facts:**
- FEMA FIRM panel number
- FIRM effective date
- FEMA flood zone at subject property (Zone X, AE, A, AO, etc.)
- Floodway flag

**Standard structure:**
1. Cite FIRM panel number and effective date
2. State the FEMA zone at the subject property
3. State whether the Zone X is shaded or unshaded (different insurance implications)
4. Reference to §3.9 for flood study requirements

**Standard text (Zone X unshaded):**
> "According to FEMA FIRM panel [panel_id], effective [date], the subject property is
> located in Zone X (unshaded), indicating the area is outside the 500-year floodplain.
> Flood insurance is generally not required for Zone X properties, though it is
> available.  See Section 3.9 for floodplain study requirements."

---

## Section 3.9 — Floodplain Study

**Required facts:**
- FEMA zone (repeated from §3.8 for context)
- Atlas 14 FDP required flag (CoA / Travis County with partial Zone AE)
- LOMC (Letter of Map Change) status if applicable
- Drainage easement required flag
- Minimum FFE requirement (2 ft above BFE for Zone AE)
- Erosion Hazard Zone (EHZ) study required (if > 15% slopes on > 30% of site)
- ERI (Erosion and Sedimentation Control Assessment) required
- Waterway setback (from §3.3 waterway classification — minor/intermediate/major)
- CEF (Critical Environmental Feature) buffer if applicable
- Wetlands (NWI) if applicable

**Zone X — No study required:**
See Writing Guide §3.1 standard phrase.

**Zone AE — Study required:**
See Writing Guide §3.2 standard phrase.

**CWQZ/Waterway Setback:**
See Writing Guide §3.11 standard phrase.

**EHZ trigger:**
> "An Erosion Hazard Zone (EHZ) study will be required by [CoA Watershed Protection /
> Travis County TNR-EQ] due to [slopes exceeding 15% on a portion of the site / proximity
> to a classified waterway].  The EHZ study must be accepted prior to site plan approval."

**ERI:**
> "An Erosion and Sedimentation Control Assessment (ERI) [is required / may be required]
> per CoA ECM §1.3.0.  The final determination will be made by CoA Watershed Protection
> at the pre-submittal conference."

---

## Section 3.10 — Drainage Area Map

**Required facts:**
- On-site drainage area (acres)
- Off-site contributing area (acres)
- Drainage direction
- Outfall location

**Standard text:**
> "The subject property drains to [waterway name] within the [watershed name] watershed.
> The site contains approximately [X] acres of on-site drainage.  An off-site
> contributing drainage area of approximately [Y] acres flows through the site.  A
> drainage area map will be prepared as part of the preliminary drainage study."

**Key note:** Drainage area maps are an exhibit (not a full study) at the feasibility
stage.  The full hydrologic analysis comes at site plan / subdivision submittal.

---

## Section 3.11 — Property Location and Adjacent Sites

**Required facts:**
- Adjacent land uses (from visual review / CAD / Austin Land Use Inventory)
- Notable features (schools, churches, single-family — compatibility triggers)

**Standard text:**
> "The subject property is bounded to the north by [use], to the south by [use], to
> the east by [use], and to the west by [use].  [Any compatibility-triggering adjacent
> use noted.]"

**Compatibility trigger:**
If any adjacent use is single-family residential or a school/religious assembly,
note it here and cross-reference §3.12.

---

## Section 3.12 — Compatibility

**Required facts:**
- Compatibility trigger flag (from adjacent site analysis)
- Applicable LDC subchapter (CoA: Subchapter C)

**Not triggered:**
> "No compatibility standards are triggered by the proposed development.  The adjacent
> land uses do not include single-family residential or other triggering uses per CoA
> LDC Subchapter C."

**Triggered:**
> "Compatibility standards per CoA LDC Subchapter C will apply to the proposed
> development due to the presence of [SF-3-NP zoned property / single-family residential]
> along the [north/south/east/west] property boundary.  Height step-backs, setbacks,
> and screening requirements will be evaluated at site plan review."

---

## Section 3.13 — Governing Jurisdictions

**Required facts:**
- Primary jurisdiction (from `jurisdiction_current`)
- ETJ flag and implications
- Co-jurisdiction if applicable (CoA + Travis County in ETJ)
- De-annexation status

**3.13.1 Required Permits:**
Generate as a bulleted list based on proposed development type.  Standard items:
- Subdivision Plat / Site Plan (jurisdiction + Development Services)
- Grading Permit
- Building Permit(s)
- Floodplain Development Permit (if Zone AE)
- FEMA FDP Study acceptance
- TxDOT Driveway Permit (if state highway frontage)
- Austin Water SER
- Fire Flow Test acceptance
- TCEQ permits (WPAP / CZP if Edwards Zone)

**3.13.2 Permitting Contacts:**
Generate as a table based on jurisdiction.  For CoA Full Purpose, standard contacts:

| Agency | Division | Contact Role |
|--------|----------|-------------|
| City of Austin DSD | Land Use Review | Zoning, compatibility, site plan |
| City of Austin DSD | Drainage/Water Quality | Watershed, floodplain, drainage |
| Austin Water | Water/WW Infrastructure | SER, connection permits |
| Austin Fire Department | Fire Review | Fire flow, fire lane, sprinklers |
| Travis County TNR | Floodplain Administration | FEMA FDP coordination |

---

## Section 3.14 — Development Agreements

**Required facts:**
- Development agreement search result (from TCCSEARCH lookup)
- Title commitment recommendation

Use standard phrases from Writing Guide §3.5 (no agreements) or note agreement details
if found.

---

## Section 3.15 — Drainage Design Criteria

**Required facts:**
- Governing drainage manual (from jurisdiction rules)
- NOAA Atlas 14 volume and version
- Design storm events (2-yr, 25-yr, 100-yr per CoA; or jurisdiction-specific)
- Hydrologic method (NRCS TR-20, HEC-HMS, Rational Method for small watersheds)

**Standard CoA text:**
> "The drainage design for the subject property will be governed by the City of Austin
> Drainage Criteria Manual (DCM).  Rainfall data shall be per NOAA Atlas 14, Volume 11,
> Version 2.0, September 2018.  Stormwater runoff will be calculated using the NRCS
> Curve Number Method (SCS) with TR-20 or HEC-HMS for drainage areas greater than
> [threshold] acres.  Design storms include the 2-year, 25-year, and 100-year events
> with a no-net-increase standard at the 2-year and 100-year events."

---

## Section 3.16 — Easements and Setbacks

**Required facts:**
- Known easements (from title/deed search or CAD — PUE, drainage, electric, access)
- Required setbacks from ROW (from zoning or jurisdiction standards)
- Required setbacks from waterways (CWQZ setbacks from §3.9)
- Building setbacks (from zoning code)
- Required setbacks from adjacent uses (compatibility step-backs if applicable)

**Title commitment note:**
> "A title commitment is recommended to identify all recorded easements and restrictive
> covenants affecting the subject property."

---

## Section 3.17 — Water Quality and Detention

**Required facts:**
- Watershed classification (controls WQ/detention thresholds)
- WQ pond required flag (> 20% impervious in suburban watershed for CoA)
- Detention required flag
- CWQZ flag (from §3.9)
- EHZ / ERI (from §3.9)
- TCEQ water quality classification (classified / unclassified)
- WPAP / CZP (from §3.3)
- CEF buffers (from §3.9)
- WQTZ (Water Quality Transition Zone) flag

**Standard CoA suburban text:**
> "The subject property is located within a [Suburban] watershed.  Water quality
> controls are required for development that creates more than 8,000 square feet of
> new impervious cover or increases impervious cover by more than 25% per CoA LDC
> §25-8-213.  A water quality pond or equivalent control system will be required.
> Detention for no-net-increase at the 2-year and 100-year design storms will be
> evaluated at site plan review."

---

## Section 3.18 — Transportation

**Required facts:**
- Road classification and functional class (from §3.7)
- TIA required flag (CoA threshold: > 2,000 daily trips or > 100 peak-hour trips)
- TIA determination worksheet result
- TxDOT involvement flag
- Sidewalk requirements

**TIA not required:**
> "A Traffic Impact Analysis (TIA) determination was made using the City of Austin
> TIA Worksheet.  Based on the proposed [use/intensity], the site will generate
> approximately [X] daily vehicle trips, which is below the 2,000 daily trip threshold.
> A TIA is not required for this project."

**TIA required:**
> "Based on the proposed [use/intensity], a Traffic Impact Analysis (TIA) will be
> required prior to site plan submittal.  The TIA must be conducted per the City of
> Austin TIA Guidelines and submitted to the Austin Transportation Department."

---

## Section 3.19 — Surveys, Title Commitments, Other Documents

**Required facts:**
- Survey available / not available
- Title commitment status
- GIS contours source
- Any other exhibits provided

**Standard text:**
> "The following documents were available for this feasibility study:
> [list what was provided]
>
> The following documents are recommended prior to entitlement submittal:
> • Current ALTA/NSPS boundary survey
> • Title commitment (or title policy) identifying all easements, liens, and
>   restrictive covenants
> • Phase I Environmental Site Assessment (if commercial use proposed)"

---

## Section 4.0 — Summary

**Format:** Numbered list of 3–7 key findings and recommendations.

**Generation rule:** Summarize the most consequential findings from each section.
Priority order:
1. Any infeasibility signals (go first, always)
2. Governing IC limit and controlling standard
3. Required studies not yet completed (flood, fire flow, ERI, EHZ)
4. Platting/LSD requirements
5. Title commitment recommendation
6. Any special designations (Edwards, WPAP, CWQZ)

Each item is one sentence — declarative, no hedging.
