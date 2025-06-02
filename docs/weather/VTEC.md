This document, "NATIONAL WEATHER SERVICE INSTRUCTION 10-1703," dated April 6, 2021, outlines the structure and application of the Valid Time Event Code (VTEC) within National Weather Service (NWS) products.

## 1. Introduction

The VTEC is used in conjunction with the Universal Geographic Code (UGC) to enhance automated delivery of NWS text products. It provides information on the event itself, while the UGC describes the affected geographic area.

### Two Forms of VTEC:

1.  **Primary VTEC (P-VTEC)**: For general event characteristics.
2.  **Hydrologic VTEC (H-VTEC)**: A supplementary VTEC for certain hydrologic products, always appearing immediately after the P-VTEC.

NWS text product generation software automatically includes P-VTEC and H-VTEC strings.

### 1.1 References

The VTEC builds on formats described in:

- **NWSI 10-1701**: Text Product Formats and Codes.
- **NWSI 10-1702**: Universal Geographic Code (UGC).

Relevant product specification NWSI documents containing VTEC are:

- NWSI 10-3 series: Marine and Coastal Weather Services
- NWSI 10-4 series: Products and Services to Support Fire and Other Incidents
- NWSI 10-5 series: Public Weather Services
- NWSI 10-6 series: Tropical Cyclone Weather Services Program
- NWSI 10-9 series: Water Resources Services Program

### 1.2 Mission Connection

VTEC aids in the timely delivery of warnings, watches, and forecasts, crucial for protecting life and property and enhancing the national economy, by allowing users to select, process, and redistribute information efficiently.

### 1.3 Implementation

P-VTEC was operationally implemented on February 8, 2005, for short-duration warning products and national Convective Watch products. It has since been expanded to other Watch/Warning/Advisory (W/W/A) products and non-routine products. Further VTEC implementation will be announced via Service Change Notices. Current VTEC-enabled products are listed at [https://www.weather.gov/vtec/](https://www.weather.gov/vtec/).

### 1.4 Definitions

- **P-VTEC**: Identifies event status, type, tracking number, and beginning/ending times.
- **H-VTEC**: Present when P-VTEC phenomenon is FL (Flood), FA (Flood), FF (Flash Flood), or HY (Hydrologic). It summarizes flood event details (cause, NWS location ID for point products, severity, timing of beginning, crest, and end, and relation to record floods).
- **Event**: A specific combination of phenomenon and significance level (e.g., Tornado Warning).
- **Event Beginning Time**: First date-time group of P-VTEC. Usually when criteria are met or adverse effects begin. Coded as zeros if the event has already begun.
- **Flood Beginning Time**: First date-time group of H-VTEC. When a forecast point is expected to (or did) exceed flood stage. Coded as zeros for certain hydrologic events.
- **Flood Crest Time**: Second date-time group of H-VTEC. When a forecast point is expected to (or did) reach its flood crest. Coded as zeros for certain hydrologic events.
- **Event Ending Time**: Last date-time group of P-VTEC. When W/W/A conditions are no longer expected. Coded as zeros for "Until Further Notice" events (e.g., long-duration flooding, tropical cyclones).
- **Flood Ending Time**: Last date-time group of H-VTEC. When a forecast point is expected to (or did) fall below flood stage. Coded as zeros for "Until Further Notice" events.
- **Segment**: A part of a segmented product containing event-driven information specific to a geographic area.
- **Product**: The entire message under a single Mass News Disseminator (MND) header.
- **Product Issuance Time**: Actual time message is disseminated.
- **Product Expiration Time**: Time the product or segment should no longer be used. For long-duration W/W/A products, it indicates when an update can be expected.

### 1.5 Event versus Segment versus Product

It's crucial to distinguish between an "event," "segment," and "product" for proper P-VTEC and H-VTEC usage. Short-duration events often have product titles matching event names (e.g., Tornado Warning). Long-duration W/W/A products may include multiple events or segments with different titles. Multiple segments within a product can cover the same event but for different areas, potentially sharing the same Event Tracking Number (ETN).

### 1.6 Product Issuance Time versus Event Beginning Time

Event Beginning Time can be the same as or later than Product Issuance Time, but never earlier. If an event has begun, Event Beginning Time is coded as zeros.

### 1.7 Product Expiration Time versus Event Ending Time

For short-duration events, Product Expiration Time often matches Event Ending Time. For longer events (over 12 hours), Product Expiration Time is usually earlier than Event Ending Time. It can be earlier than Event Beginning Time for future-starting events (e.g., Winter Storm Watch). Product Expiration Time is only later than Event Ending Time for final/follow-up products after an event has expired or been canceled. VTEC helps track W/W/A events from issuance to cancellation/expiration, ensuring forecasters issue follow-up products before current products expire to avoid "orphaned" events.

---

## 2. Primary VTEC (P-VTEC) Format

P-VTEC (and H-VTEC if applicable) strings appear immediately after the UGC string(s). Their placement varies depending on whether the product is segmented.

### Non-Segmented Products (Figure 1):

UGC and VTEC strings appear after the NWS Communications Identifier and before the MND.

### Segmented Products (Figure 2):

UGC and VTEC strings appear at the beginning of each segment, immediately followed by plain language geographic listings. All segments appear after the MND header block.

### Generic Structure of P-VTEC Elements (Figure 3):

`/k.aaa.cccc.pp.s.####.yymmddThhnnZB-yymmddThhnnZE/`

- **k**: Product/VTEC String Type Identifier
- **aaa**: Action
- **cccc**: Office ID
- **pp**: Phenomenon
- **s**: Significance
- **####**: Event Tracking Number (ETN)
- **yymmddThhnnZB**: Event Beginning Date/Time Group (UTC)
- **yymmddThhnnZE**: Event Ending Date/Time Group (UTC)

### 2.1 P-VTEC Element Definitions/Explanations

#### 2.1.1 k (Fixed Identifier)

- **O**: Operational Product (validated, real-time environmental conditions/events).
- **T**: Test Product (evaluation, communications test, weather drill; content does not reflect real-time events).
- **E**: Experimental Product (evaluation, user feedback; content not validated but generally reflects real-time events).
- **X**: Experimental VTEC in an Operational Product (non-operational VTEC in an otherwise operational product for evaluation).
    - **Note**: In multi-segmented products, "T" or "E" VTEC segments should not be mixed with "O" or "X".

#### 2.1.2 aaa (Action) - Table 1 provides summary of use

- **NEW (New)**: Initial issuance of an event. Includes upgrades, downgrades, or replacements of other events. If starting in multiple segments, NEW appears in all. ETN increments from the last one used (except for convective watches or tropical cyclones).
- **CON (Continued)**: Updates to an existing event with no changes to area or valid time. Applies only to the continued UGC area.
- **EXA (Extended in Area)**: Valid area of existing event expanded, no change to valid time. Usually involves two segments (one EXA for new area, one CON for continued area, both with same ETN). Not used in short-duration warnings.
- **EXT (Extended in Time)**: Valid time period of an existing event made longer or shorter, no change to area. Not used to change times once reached. Not used in SVR, TOR, EWW, SMW, or tropical hazards.
- **EXB (Extended in Area and Changed in Time)**: Valid time period of existing event changed AND valid area expanded. Usually involves two segments (one EXB for new area, one EXT/CON for continued area, both with same ETN). Not used in short-duration warnings or tropical hazards.
- **UPG (Upgraded)**: Existing event upgraded for the same area to a higher significance level or higher discrete criteria (e.g., watch to warning, Small Craft Advisory to Gale Warning). Uses two P-VTEC strings (UPG for old, NEW/EXA/EXB for new). Not used in convective or hydrologic events.
- **CAN (Canceled)**:
    - Cancel still-active event before scheduled end.
    - Identify when a non-convective/non-water resources event was downgraded (e.g., warning to advisory) or replaced by another event of similar/lower significance. Uses two P-VTEC strings (CAN for old, NEW/EXA/EXB for new).
    - If an event is cancelled in error, it must be restarted with NEW and a new ETN (for entire event). For partial cancellation error, EXA/EXB with still-valid ETN can restart.
- **EXP (Expired)**:
    - Notify users an active event will expire at its scheduled time.
    - Issued after an event has expired (final/follow-up message).
- **ROU (Routine)**: VTEC placeholder for segments in VTEC-enabled products that do not contain an ongoing or future VTEC event. Appears only in Flood Warnings for Forecast Points products (including follow-up statements) when points not expected to reach flood stage are included.
- **COR (Correction)**: Used for correcting non-VTEC or non-UGC errors/omissions. P-VTEC strings with COR appear in each corrected segment. For UPG/CAN corrections, COR appears only in the second P-VTEC string (the NEW/EXA/EXB one).

#### 2.1.3 cccc (Office ID)

Standard four-letter NWS office identifier responsible for the affected area.

#### 2.1.4 pp (Phenomenon) - See Appendix A for complete list

Identifies the type of weather, flood, marine, fire weather, or non-weather occurrence.

#### 2.1.5 s (Significance) - See Appendix A for complete list

Identifies the level of importance (watch, warning, advisory, etc.). For follow-up statements, the significance code matches the original product.

#### 2.1.6 #### (Event Tracking Number - ETN)

A four-digit number to track an event through its lifetime. Assigned sequentially by NWS applications software, starting with 0001 annually for each event type per office. Events spanning across years retain the old ETN. One ETN list per specific event (phenomenon + significance level) is used for all products/segments containing that event.

- **2.1.6.1 ETNs in Nationally-originated Events**: Special rules for events from National Centers.
    - **Tornado and Severe Thunderstorm Watches**: SPC watches use a single sequential ETN list (e.g., SV.A.0047, TO.A.0047). Local WFO watch products use the same ETNs as corresponding SPC watches. SPC uses 9000-9999 for test watches.
    - **Tropical Cyclone Watches and Warnings**: ETN determined by storm ID from issuing center (e.g., 1xxx for Atlantic, 2xxx for Eastern Pacific). ETN doesn't change if the system upgrades, downgrades, or changes basin.

#### 2.1.7 yymmddThhnnZB and yymmddThhnnZE (Event Beginning and Ending Date/Time Groups)

Identify the valid time span of the event in UTC.

- **Event Beginning Date/Time**: Can only be changed before the scheduled start using EXT or EXB. If the event has begun, it's coded as ten zeros (`000000T0000Z`).
- **Event Ending Date/Time**: Can only be changed before scheduled expiration using EXT or EXB. If entire event inadvertently ends, it's reissued with NEW and a new ETN. For "Until Further Notice" events (very long duration/open-ended), it's coded as ten zeros (`000000T0000Z`).

---

## 3. Special P-VTEC Rules, Applications and Interpretations

### 3.1 Event Significance Level Change or Replacement in Products

Two P-VTEC strings are required for WSW, NPW, Fire Weather Watch/Warning, convective watches, and certain marine products when an event's significance level changes (upgrade/downgrade) or it's replaced by a similar event.

- **Table 2**: P-VTEC Action Code Pairs Used for Different Upgrade, Downgrade, and Replacement Situations. (e.g., UPG/NEW, CAN/NEW)
    - First string: UPG/CAN (old event).
    - Second string: NEW/EXA/EXB (new event).
    - COR for corrections appears only in the second string.

### 3.2 Multiple P-VTEC Events Contained in a Single Unsegmented Product or Segment

Most products contain one or two P-VTEC strings. However, some long-duration W/W/A products and MWW may contain more. P-VTEC strings are sorted by:

1.  **Action Code**: CAN, EXP, UPG, NEW, EXB, EXA, EXT, COR, CON (ROU appears by itself). Exception: UPG/NEW, UPG/EXA, etc. pairs appear together.
2.  **Significance Level (if same action code)**: W, Y, A, S, O, F, N.
3.  **Chronological Order by Event Beginning Time (if same action and significance)**.
4.  **Phenomenon Code (alphabetical order if same action, significance, and beginning time)**.
    H-VTEC strings follow their corresponding P-VTEC strings.

### 3.3 Short Duration Watch and Warning Products

P-VTEC appears in Severe Thunderstorm and Tornado Warning products and follow-up statements, and in WOU (SPC) and WCN (WFO) watch products.

- **3.3.1 Watch County Notification (WCN) Product**: WCNs handle all aspects of SPC Severe Thunderstorm/Tornado Watch issuances within WFO areas. WCNs in contiguous US use the SPC WOU watch number as ETN. Outside contiguous US, WFOs use sequential ETNs.
- **3.3.2 Follow-up Warning Products (SVS, MWS)**: SVS (for TOR, SVR, EWW) and MWS (for SMW) use the phenomenon, significance, ETN, and event ending time from the original warning.

### 3.4 Marine and Coastal Weather Products

Follow illustrations and interpretations for various marine products.

- **3.4.1 Event-Driven Marine and Coastal Products**: CFW, MWW, SMW, and MWS follow the same VTEC rules as other event-driven products.

### 3.5 Pacific Basin National Tropical Cyclone Product for VTEC (TCV)

TCV provides VTEC strings for tropical storm/hurricane watches/warnings for Eastern Pacific basins. It includes UGC for coastal public zones and lat/lon for breakpoints. Uses NEW, CON, CAN action codes. ETN uses special form (Section 2.1.6.1).

### 3.6 Atlantic Basin National Tropical Cyclone Watch Warning Product (TCV)

National TCV provides VTEC strings for tropical storm, hurricane, and storm surge watches/warnings for US states/territories in the Atlantic basin. Includes UGC for coastal/inland zones for wind, storm surge, or both. ETN uses special form (Section 2.1.6.1).

### 3.7 Atlantic Basin and WFO Honolulu WFO Hurricane Local Watch/Warning Product (TCV)

Segmented WFO TCV contains tropical cyclone wind and storm surge watches/warnings for coastal/inland zones (Atlantic basin WFOs only). Can include TR, HU, SS phenomenon codes. Uses all relevant VTEC action codes except EXT, EXB, EXP, ROU.

- **3.7.1 ETNs**: Atlantic basin ETNs are determined by NHC storm number. Central Pacific basin ETNs are determined by CPHC storm number.
- **3.7.2 Event Beginning and Ending Times**: All Storm Surge, Hurricane, and Tropical Storm Watches/Warnings in TCV products become effective immediately upon issuance and are valid until further notice (`000000T0000Z`).

### 3.8 Pacific Basin (except WFO Honolulu) WFO Hurricane Local Statement (HLS)

Segmented WFO HLS contains tropical cyclone wind watches, warnings, and statements for coastal/inland zones. Can include TR, HU, TY phenomenon codes. Uses all relevant VTEC action codes except EXT, EXB, EXP, ROU.

- **3.8.1 ETNs**: Eastern Pacific basin ETNs are determined by NHC storm number. Western Pacific basin ETNs are determined by JTWC storm number.
- **3.8.2 Event Beginning and Ending Times**: All Typhoon, Hurricane, and Tropical Storm Watches, Warnings, and Statements in HLS products become effective immediately upon issuance and are valid until further notice (`000000T0000Z`).

---

## 4. Hydrologic VTEC (H-VTEC) Format

H-VTEC appears only with P-VTEC strings having FL, FA, FF, or HY phenomenon codes. For FLW and FLS at specific river points, H-VTEC specifies flood severity, immediate cause, and timing of beginning, crest, and end, and relation to record floods. For FFA, FLW, FFW, FFS, and FLS (under Flood Statement identifier), H-VTEC has immediate cause but default zeros/Os for other elements.

### Generic Structure of H-VTEC Elements (Figure 4):

`/nwsli.s.ic.yymmddThhnnZB.yymmddThhnnZc.yymmddThhnnZE.fr/`

- **nwsli**: NWS Location Identifier
- **s**: Flood Severity
- **ic**: Immediate Cause
- **yymmddThhnnZB**: Flood Beginning Date/Time Group (UTC)
- **yymmddThhnnZc**: Flood Crest Date/Time Group (UTC)
- **yymmddThhnnZE**: Flood Ending Date/Time Group (UTC)
- **fr**: Flood Record Status

### 4.1 H-VTEC Element Definitions/Explanations

#### 4.1.1 nwsli (NWS Location Identifier)

Five alphanumeric characters for the specific location. Coded as five zeros (`00000`) for flood and flash flood products.

#### 4.1.2 s (Flood Severity) - See Appendix B for codes

Identifies severity of river/stream flooding where point-specific warnings are issued. Coded as zero (`0`) for Flood/Flash Flood Watches, Flood Warnings, and Flash Flood Warnings (except unknown flood severity set to "U" for non-heavy precipitation flash floods). Coded as "N" for Flood Advisories (flood stage not expected).

#### 4.1.3 ic (Immediate Cause) - See Appendix B for codes

Identifies the immediate cause of the flood.

#### 4.1.4 yymmddThhnnZB.yymmddThhnnZc.yymmddThhnnZE (Flood Timing)

Identify actual (or forecast) beginning, crest, and ending times of flooding at the forecast point in UTC. Coded as zeros (`000000T0000Z`) for Flood/Flash Flood Watches, Flood Advisories, Flood Warnings, and Flash Flood Warnings.

- **4.1.4.1 H-VTEC Flood Beginning Time vs P-VTEC Event Beginning Time**: Generally same for FLW, except when flooding began before initial warning issuance, H-VTEC reflects actual start time (past) while P-VTEC reflects warning issuance time (present).
- **4.1.4.2 H-VTEC Flood Ending Time vs P-VTEC Event Ending Time**: H-VTEC reflects time point falls below flood stage, P-VTEC reflects when event is expected to end. Not always same (e.g., P-VTEC may be later to cover surrounding area). If flood warning cancelled early, H-VTEC reflects actual end time while P-VTEC retains previous forecast end time.

#### 4.1.5 fr (Flood Record Status) - See Appendix B for codes

Identifies how the flood compares to the flood of record. Coded as two Os (`OO`) for Flood/Flash Flood Watches, Flood Warnings, and Flood Advisories.

### 4.2 Example of a Full H-VTEC String (with associated UGC and P-VTEC Strings)

See Appendix C for examples.

---

## 5. Special H-VTEC Rules, Applications and Interpretations

### 5.1 Flood Statement and Flash Flood Statement Products issued as Follow-Ups to Warnings.

FLS provides follow-up info for Flood Warnings, FFS for Flash Flood Warnings. They share phenomenon, significance, event times, and ETN of original warning.

### 5.2 Flood Advisories Issued Under the Flood Statement Identifier

FLS identifier for Flood Advisories provides information on elevated river/stream flows or urban ponding, less urgent than a warning. Uses FA phenomenon code (or FL for Forecast Points), significance level Y. P-VTEC uses actual event beginning/ending times, but H-VTEC uses zeros (flood warning criteria not expected).

### 5.3 Non-Flood Segments Included in Flood Warning for Forecast Points Product

FLW/FLS may include segments for forecast points not expected to reach flood warning criteria, to provide complete river reach information. These segments use ROU action code with HY phenomenon code and S significance level. Other P-VTEC and H-VTEC elements use default values, except H-VTEC site identifier and immediate cause.

### 5.4 Multiple Hydrologic P-VTEC Strings in a Single Product Segment

Normally one hydrologic P-VTEC string per segment (no upgrade/downgrade for hydrologic products). When Flash Flood Watches are replaced by Flood Watches (or vice-versa), paired CAN/NEW, CAN/EXA, or CAN/EXB P-VTEC strings are used. A single H-VTEC string follows, populated only with the immediate cause (since it's a flood watch product).

---

## APPENDIX A - Listing of P-VTEC Elements

### 1. Generic P-VTEC Structure

`/k.aaa.cccc.pp.s.####.yymmddThhnnZB-yymmddThhnnZE/`

### 2. Fixed identifier (k)

- **O**: Operational Product
- **T**: Test Product
- **E**: Experimental Product
- **X**: Experimental VTEC in an Operational Product

### 3. Actions (aaa)

- **NEW**: New Event
- **CON**: Event Continued
- **EXT**: Event Extended (Time)
- **EXA**: Event Extended (Area)
- **EXB**: Event Extended (Both Time and Area)
- **CAN**: Event Cancelled
- **UPG**: Event Upgraded
- **EXP**: Event Expired
- **COR**: Corrected
- **ROU**: Routine

### 4. Office ID (cccc)

Standard four-letter identifier of the NWS office.

### 5. Phenomenon (pp) - See Section 5.1 and 5.2 for detailed lists

- **5.1 Phenomenon (pp) codes grouped by hazard type**: Lists codes by Winter, Marine and Coastal, Non-Precipitation, Tropical, Water Resources, and Severe Storms.
- **5.2 Phenomenon (pp) codes in alphabetical order**: Alphabetical list of all codes.

### 6. Significance (s)

- **W**: Warning
- **A**: Watch
- **Y**: Advisory
- **S**: Statement
- **F**: Forecast
- **O**: Outlook
- **N**: Synopsis

### 7. Event Tracking Number - ETN (####)

A four-digit number assigned sequentially each year for each unique event phenomenon and significance per WFO. Special rules for convective watch redefining products and tropical cyclone watches/warnings.

### 8. Event Beginning and Ending Date/Time Groups

`yy` (Year), `mm` (Month), `dd` (Date), `T` (Fixed Time Indicator), `hh` (Hour in UTC), `nn` (Minute in UTC), `ZB` (Fixed UTC Beginning Date/Time Indicator), `ZE` (Fixed UTC Ending Date/Time Indicator).

---

## APPENDIX B - Listing of H-VTEC Elements

### Generic H-VTEC Structure

`/nwsli.s.ic.yymmddThhnnZB.yymmddThhnnZc.yymmddThhnnZE.fr/`

### Site Identifier (nwsli)

Five character NWS Site Identifier. Coded as five zeros (`00000`) for flood products.

### Flood Severity (s)

- **N**: None (for advisories)
- **0**: For Flood/Flash Flood Watches, Flood Warnings, and Flash Flood Warnings (no specific location observations/forecasts)
- **1**: Minor
- **2**: Moderate
- **3**: Major
- **U**: Unknown

### Immediate Cause (ic)

- **ER**: Excessive Rainfall
- **SM**: Snowmelt
- **RS**: Rain and Snowmelt
- **DM**: Dam or Levee Failure
- **GO**: Glacier-Dammed Lake Outburst
- **IJ**: Ice Jam
- **IC**: Rain and/or Snowmelt and/or Ice Jam
- **FS**: Upstream Flooding plus Storm Surge
- **FT**: Upstream Flooding plus Tidal Effects
- **ET**: Elevated Upstream Flow plus Tidal Effects
- **WT**: Wind and/or Tidal Effects
- **DR**: Upstream Dam or Reservoir Release
- **MC**: Other Multiple Causes
- **OT**: Other Effects
- **UU**: Unknown

### Flood Timing (yymmddThhnnZB.yymmddThhnnZc.yymmddThhnnZE)

`yy` (Year), `mm` (Month), `dd` (Day), `T` (Fixed Time Indicator), `hh` (Hour), `nn` (Minute), `ZB` (Beginning Time), `Zc` (Crest Time), `ZE` (Ending Time).

### Flood Record Status (fr)

- **OO**: Not applicable (for Flood Watches, Flash Flood Warnings, Flood Warnings, Flood Advisories, non-flood ROU segments).
- **NO**: A record flood is not expected.
- **NR**: Near record or record flood expected.
- **UU**: Flood without a period of record to compare.

---

## APPENDIX C - Examples and Interpretations

Provides detailed examples of P-VTEC and H-VTEC coding, illustrating various scenarios like single events, multiple events in a segment, changes in P-VTEC elements (phenomenon, significance, area, time), changes in H-VTEC elements (flood severity), corrections, national center products, and full event sequences for wind and flooding hazards.

**Example Keywords explained**:

- **Scenario**: Brief description of why the product is issued.
- **Issuing Office**: Name and four-character identifier of the issuing office.
- **Current time**: Time (UTC) of product issuance.
- **Immediate Cause**: Primary cause of flooding (for flood events).
- **Event (Product)**: VTEC event(s) and product class.
- **Product valid for**: Area (county, zone, gauge) for which product is valid.
- **Product expiration time**: UTC time when product expires.
- **Event Tracking Number**: ETN(s) assigned to the event(s).
- **Expected (or actual) Event Beginning, Crest, and Ending times...**: Dates/times included in P-VTEC and H-VTEC strings. Italicized if time has already occurred.
- **segment x of y within...**: UGC and VTEC string(s) for the product segment.
- **(UGC)**: The UGC string.
- **(P-VTEC)**: The P-VTEC string (numbered if multiple).
- **(H-VTEC)**: The H-VTEC string (for flood products).
- **Explanation**: Detailed description of VTEC coding.
