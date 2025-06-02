This document, "NATIONAL WEATHER SERVICE INSTRUCTION 10-601," dated April 25, 2023, outlines the specifications and procedures for Weather Forecast Office (WFO) Tropical Cyclone Products. It supersedes the previous instruction dated July 14, 2022.

## Weather Forecast Office (WFO) Tropical Cyclone Products

WFOs issue tropical cyclone products to inform media, local decision makers, and the public about current and anticipated tropical cyclone conditions within their County Warning Area (CWA). They are also responsible for issuing tropical cyclone wind watches and warnings for inland portions of their CWA. Coastal Atlantic basin WFOs, along with WFO San Juan, Puerto Rico, collaborate with the National Hurricane Center (NHC) for storm surge watches and warnings. All products must be consistent with the latest guidance from the respective tropical cyclone forecast center and surrounding offices.

### 1.1 WFO Tropical Cyclone Local Watch/Warning Product (WFO TCV)

TCVs are issued by WFOs with tropical cyclone wind watch/warning responsibility, with the exception of WFO Guam and WSO Pago Pago.

**Product Details:**

- **Format:** Segmented Valid Time Event Code (VTEC) product, with each segment representing a discrete forecast zone.
- **Content:** Land-based tropical cyclone wind and storm surge (Atlantic basin WFOs only) watches/warnings, meteorological information, and hazards (wind, storm surge, flooding rain, tornadoes) with potential threats and impacts.
- **Generation:** Primarily generated from local gridded forecast information and national guidance; not intended for manual editing.
- **Purpose:** To provide a complete, localized tropical forecast, paired with the WFO HLS. Useful for decision makers due to detailed information on hazard timing, threats, and impacts at a zone level. Designed for parsing by the weather enterprise.
- **Mission Connection:** Primary WFO product for disseminating land-based tropical cyclone watches and warnings within their CWA, providing critical information for life and property protection. It conveys watches and warnings from NHC/CPHC and also disseminates WFO-issued watches and warnings for land zones. Coastal watch/warning information must align with the NHC/CPHC Tropical Cyclone Public Advisory (TCP).
- **Creation Software:** Advanced Weather Interactive Processing System (AWIPS) Graphical Forecast Editor (GFE).
- **Issuance Criteria:** Cannot be issued before the national center issues a TCP due to VTEC Event Tracking Number (ETN) derivation from national products.
- **Offices Issuing TCVs:**
    - **Coastal WFOs:** Caribou, ME; Portland, ME; Boston/Norton, MA; New York City, NY; Philadelphia, PA; Baltimore, MD/Washington, DC; Wakefield, VA; Newport/Morehead City, NC; Wilmington, NC; Charleston, SC; Brownsville, TX; Corpus Christi, TX; Houston/Galveston, TX; Lake Charles, LA; New Orleans, LA; Mobile, AL; Tallahassee, FL; Tampa Bay, FL; Miami, FL; Key West, FL; Melbourne, FL; Jacksonville, FL; San Juan, PR; Los Angeles, CA; San Diego, CA; Honolulu, HI.
    - **Inland WFOs:** Albany, NY; Binghamton, NY; Blacksburg, VA; Burlington, VT; Columbia, SC; Greenville/Spartanburg, SC; Raleigh/Durham, NC; State College, PA; Atlanta, GA; Austin/San Antonio, TX; Birmingham, AL; Fort Worth, TX; Huntsville, AL; Jackson, MS; Little Rock, AR; Memphis, TN; Morristown, TN; Nashville, TN; Shreveport, LA.
    - Inland WFOs not listed above will use Non-Precipitation Warning (NPW) products instead of TCVs.
- **Issuance Times:**
    - **Initial Issuances (Coastal WFOs):** As close as possible to the first issuance of a tropical storm/hurricane watch/warning by NHC/CPHC. Abbreviated TCVs may be issued for timely notifications.
    - **Initial Issuances (Inland WFOs):** In coordination with neighboring WFOs, when tropical storm/hurricane force winds are forecast within 48 hours (watches) to 36 hours (warnings) by NHC/CPHC.
    - **Subsequent Updates:** Within 30 minutes of a regularly scheduled or intermediate advisory from the tropical cyclone forecast center with watch/warning changes for the WFO's CWA. May also be updated for other significant changes (e.g., rainfall, tornado information). No dissemination prior to official NHC/CPHC advisory release unless coordinated.
    - **Final:** Cease when local tropical cyclone watches/warnings are no longer in effect.
- **Valid Time:** At issuance until subsequent TCV or watches/warnings expire. Issued at least once every 6 hours during an event.
- **Event Beginning/Ending Time:** VTEC contains a start time. No explicit ending time provided due to forecast uncertainties.
- **Product Expiration Time:** Generally 6 hours after issuance, coinciding with next update or event end. Set to 8 hours to allow for possible issues.
- **Technical Description:**
    - **UGC Type:** Zone (Z) form.
    - **MND Header:** "(Name or Number) Local Watch/Warning Statement/Advisory Number ##." "##" is the sequential advisory number. Coded string (BBCCYYYY) appended to "Issuing Office City State" line.
    - **Content:** One or more formatted segments per UGC zone, containing VTEC encoding, headlines, affected locations, and hazard sections (meteorological forecast, threat, potential impacts, additional information sources).
    - **Format:** Mandatory headlines and section headers per UGC/VTEC segment. VTEC phenomena codes: TR (Tropical Storm), HU (Hurricane), SS\* (Storm Surge). Significance codes: W (Warning), A (Watch).
    - **ETN:** Unique value per tropical cyclone, derived from the basin's storm number in the issuing office's TCP.
    - **Mandatory Segment Subsections:** LOCATIONS AFFECTED, WIND, STORM SURGE (for surge-prone zones), FLOODING RAIN, TORNADO, FOR MORE INFORMATION.
- **Relationship to other products:**
    - **Short Term Forecast (NOW):** NOW is a standalone product for conditions within 6 hours, complementing TCV.
    - **Zone Forecast Product (ZFP):** ZFPs will highlight tropical cyclone watches and warnings from TCV.
    - **Coastal Hazard Message (CFW):** Issued when tropical cyclone watches/warnings are in effect. CFW water levels (inundation) will be consistent with HLS and TCP.

### 1.2 Hurricane Local Statement (HLS)

The HLS is a discussion/preparedness product conveying succinct messages on land-based local impacts from tropical cyclones.

**Product Details:**

- **Scope:** Issued by all WFOs with tropical cyclone wind watch/warning responsibility, _except_ WFO Guam and WSO Pago Pago. This version does _not_ contain VTEC information and is not segmented.
- **Content:** Overview of the storm from a local perspective, succinct messages on local impacts, information for diverse users (media, decision makers, public). Ordered by greatest expected impact. Possible sections: wind, surge, flooding rain, tornadoes, other coastal hazards.
- **Creation Software:** AWIPS GFE.
- **Issuance Criteria:** Issued after the tropical cyclone forecast center TCP and WFO TCV when watches/warnings are active. Can be issued standalone to dispel rumors.
- **Issuance Times:**
    - **Initial Issuances:** Closely after WFO TCV issuance.
    - **Subsequent Updates:** Closely after WFO TCV issuance for each advisory.
    - **Final:** Soon after all tropical cyclone watches/warnings are canceled via WFO TCV. PNS may be used for post-storm information.
- **Valid Time:** At issuance until subsequent HLS or watches/warnings expire. Issued at least once every 6 hours during an event. Next update time indicated in product.
- **Product Expiration Time:** Generally 6 hours after issuance (or 8 hours to allow for delays), coinciding with next update or event end.
- **Technical Description:**
    - **UGC Type:** Zone (Z) form.
    - **MND Header:** "(System Type) (Name or Number) Local Statement Advisory Number ##." "##" is sequential advisory number. Coded string (BBCCYYYY) appended to "Issuing Office City State" line.
    - **Content Sections (Mandatory):** NEW INFORMATION, SITUATION OVERVIEW, POTENTIAL IMPACTS, PRECAUTIONARY/PREPAREDNESS ACTIONS, NEXT UPDATE.
    - **Potential Impacts Sections:** Wind, Surge, Flooding Rain, Tornadoes. Only sections with legitimate threats are included.
    - **Precautionary/Preparedness Actions:** Includes recommendations, announcements, evacuation information.
    - **Additional Sources of Information:** Links to readiness sites (ready.gov, getagameplan.org, redcross.org).
- **Relationship to other products:**
    - **Short Term Forecast (NOW):** NOW is a standalone product for conditions within 6 hours, complementing HLS.
    - **Public Information Statement (PNS):** Encouraged before the first HLS for routine preparedness information.
    - **Special Weather Statement (SPS):** Can provide preliminary information for systems not yet issuing advisories. For sub-severe convective storms outside tropical wind watch/warning zones, Impact-Based Warning (IBW) formatted SPS should be used.
    - **Hazardous Weather Outlook (HWO):** Can address peripheral weather until first tropical cyclone advisory or initial local watch/warning.

### 1.3 Tropical Cyclone Local Statement (HLS) – South Pacific and western North Pacific

This HLS is issued by WFO Guam and WSO Pago Pago.

**Product Details:**

- **Scope:** Discussion-centric preparedness product with land-based local impacts information. Common source for diverse users. Provides decision-making support with generalized and specific tropical cyclone information.
- **Format (Guam and Northern Marianas):** Two components:
    - **Overview Block:** Generalized tropical cyclone information relative to entire CWA.
    - **UGC/VTEC formatted segments:** Detailed information for specific zones within CWA. (WSO Pago Pago HLS does not include VTEC, nor does WFO Guam HLS for areas outside Guam/Northern Marianas).
- **Content:** Focus on most severe hazards, peak magnitude, timing, and duration. Tropical cyclone position information from latest advisory or estimates. Distance/bearing information relative to local landmarks.
- **Coordination:** WFO Guam and WSO Pago Pago coordinate with RSMC Nadi and each other for integrated forecasts for Samoas. Continuous coordination with JTWC, CPHC, and WSO Pago Pago for watch/warning events.
- **Creation Software:** AWIPS GFE.
- **Issuance Criteria:** Issued when CWA is subject to tropical cyclone watch/warning or evacuation orders. Can dispel rumors. Cannot be issued before formal advisories from tropical cyclone centers.
- **Issuance Times:**
    - **Initial Issuances:** As soon as possible after first tropical storm/hurricane/typhoon watch/warning from forecast center. WFO Guam issues within one hour of TCP. Abbreviated HLS may be issued to expedite time-sensitive information for new zones.
    - **Subsequent Updates:** Within 30 minutes of regular/intermediate advisory with changes in watches/warnings.
    - **Final:** Routine HLSs cease when tropical cyclone is no longer a threat or watches/warnings expire. WFO Guam can continue for sub-warning criteria impacts.
- **Valid Time:** At issuance until subsequent HLS or watches/warnings expire. Issued at least once every 6 hours. Next update time indicated.
- **Event Beginning/Ending Time:** VTEC contains a start time (when NEW hazard issued). WFO Guam (Micronesia) and WSO Pago Pago products do not include VTEC. No explicit ending time due to forecast uncertainties.
- **Product Expiration Time:** Generally 6 hours after issuance, coinciding with next update or event end.
- **Technical Description:**
    - **UGC Type:** Zone (Z) form.
    - **MND Header:** "(System Type) (Name or Number) Local Statement."
    - **Content Sections (Overview Block - Mandatory):** .NEW INFORMATION, .AREAS AFFECTED, .WATCHES/WARNINGS, .STORM INFORMATION, .SITUATION OVERVIEW, .PRECAUTIONARY/PREPAREDNESS ACTIONS, .NEXT UPDATE.
    - **Optional Sections in UGC/VTEC segments:** .PROBABILITY TROPICAL STORM/HURRICANE CONDITIONS, .WINDS, .STORM SURGE AND STORM TIDE, .INLAND FLOODING, .TORNADOES, .OTHER.
    - **VTEC Phenomena Codes (WFO Guam HLS):** TR (Tropical Storm), TY (Typhoon).
    - **VTEC Significance Codes (Pacific hurricane basin):** W (Warning), A (Watch), S (Statement). /S/ for rumors/storm-related issues in zones not under watch/warning.
- **Relationship to other products:**
    - **Short Term Forecast (NOW):** NOW is a standalone product for conditions within 6 hours, complementing HLS.
    - **Zone Forecast Product (ZFP):** ZFPs will highlight tropical cyclone watches and warnings.
    - **Public Information Statement (PNS):** Encouraged before the first HLS for routine preparedness.
    - **Special Weather Statement (SPS):** Can provide preliminary information for systems not yet issuing advisories. For sub-severe convective storms outside tropical wind watch/warning zones, IBW formatted SPS should be used.
    - **Hazardous Weather Outlook (HWO):** Can address peripheral weather until first tropical cyclone advisory or initial local watch/warning.

### 1.4 Non-precipitation Weather Products (NPW)

Inland WFOs that do not issue TCV or HLS will issue NPW for high wind watches and/or warnings if hurricane, tropical storm, subtropical storm, or post-tropical cyclone winds are forecast.

**Product Details:**

- **Mission Connection:** Long duration warnings for protection of lives and property, providing advance notice of hazardous events.
- **Creation Software:** AWIPS GFE.
- **Issuance Criteria:**
    - **Watch:** High Wind Watches for inland areas when tropical storm/hurricane force winds are possible within 48 hours.
    - **Warning:** High Wind Warnings for areas when tropical storm/hurricane force winds are expected within 36 hours.

### 1.5 Extreme Wind Warning (EWW)

**Product Details:**

- **Mission Connection:** Short duration warnings for immediate threats. Issued by Atlantic basin, WFO Guam, and WFO Honolulu forecasters to provide public with advance notice of extreme sustained winds of a major hurricane/typhoon (Category 3 or higher), usually associated with the eyewall. Informs public to seek immediate shelter in well-built structures. WFOs in Southern California and WSO Pago Pago do not issue EWWs.
- **Creation Software:** AWIPS WarnGen.
- **Issuance Criteria:** Issued for Atlantic and western and central North Pacific basin tropical cyclones when _both_ criteria are met:
    - Tropical cyclone is Category 3 or greater on Saffir-Simpson Hurricane Wind Scale (NHC, JTWC, CPHC).
    - Sustained surface winds of 100 knots (115 mph) or greater are occurring or expected on land in WFO's CWA within one hour. WFO Guam's EWWs are limited to Guam and Northern Marianas.
- **Issuance Time:** Non-scheduled, event-driven product.
- **Valid Time:** Up to a three-hour period. Forecasters use judgment based on area size and cyclone speed. If criteria still met after expiration, new EWW issued.
- **Product Expiration Time:** End of warning valid time.
- **Technical Description:**
    - **UGC Type:** County.
    - **MND Broadcast Line:** "BULLETIN – EAS ACTIVATION REQUESTED."
    - **MND Header:** "EXTREME WIND WARNING".
- **Updates and Amendments:** New EWWs issued if criteria met beyond original valid time. Except for WFO Guam, WFOs issue SVSs during EWW valid time with wind observations/damage reports.
- **Cancellations and Expirations:** Except for WFO Guam, WFOs issue SVSs to inform public of EWW cancellations/expirations.
- **Corrections:** WFOs correct EWWs for grammatical/content errors. Corrected warnings retain original MND Header time and VTEC ETN. Area/valid time errors cannot be changed in a COR.

### 1.6 Post Tropical Cyclone Report (PSH)

The PSH is the primary WFO product for reporting and documenting local tropical cyclone impacts and observations to the public. WSO Pago Pago is exempt from issuing the PSH.

**Product Details:**

- **Mission Connection:** Provides NHC, CPHC, NWS Headquarters, media, public, and emergency management with a record of peak tropical cyclone conditions. Data used for post-event reports, news articles, and historical records. Standardized CSV format for observations and PDF for summaries/impacts.
- **Creation Software:** AWIPS, spreadsheet, word processing, NWS Content Management System (CMS).
- **Issuance Criteria:** All WFOs that issued tropical cyclone watches/warnings and HLSs will prepare post-storm reports. WFO Guam coordinates with WSOs for information.
- **Issuance Times:** Preliminary reports within 5 days of last HLS. Complete report with full PSH suite information within 15 days of last HLS. Updates as needed, possibly for several months (especially for fatalities). NHC coordinates fatality reporting consistency. WFO Guam releases PSH as soon as practical after last advisory if HLS was issued.
- **Valid/Expiration Times:** Not applicable.
- **Technical Description:**
    - **UGC Type:** Not applicable.
    - **MND Header:** "POST TROPICAL CYCLONE REPORT... (TROPICAL CYCLONE TYPE) (NAME)." Type reflects peak intensity during impact.
    - **Content:** PSH suite signals new/updated information via WFO's "Tropical Event Summary" webpage (`https://weather.gov/XXX/TropicalEventSummary`).
    - **PSH Suite Components:**
        1.  **PSH Text Product:** Mixed-case text to alert users, points to "Tropical Event Summary" webpage.
        2.  **Observational Data Summary (PDF):** Summary of extreme wind, pressure, rainfall, and water level (coastal WFOs only) point-based observations.
        3.  **Impacts Report (PDF):** Narrative summary of impacts (wind, storm surge, inland flooding, tornadoes, etc.) in each affected county/parish/independent city/island, including deaths, injuries, dollar damages, evacuations, etc.
        4.  **Downloadable Observational Data (CSV):** Collection of observations in CSV format (Wind and Pressure, Rainfall, Water Level (coastal WFOs only), Tornadoes).
    - **Included Data in Initial/Updated Reports:**
        - **Wind and Pressure:** Highest sustained surface wind speed (knots, mph) and duration, peak gust (knots, mph) and date/time (UTC), anemometer height (meters). All land-based NOAA, DoD, FAA official sites and reliable land-based data. NOAA buoy/C-MAN stations in marine warning areas. Adjusted speeds if known. Lowest sea level pressure (mb) and date/time (UTC). Pressures < 1005 mb required, > 1005 mb as needed/requested.
        - **Rainfall:** Storm total amount (inches) and duration (dates). Data from all sources, significant totals (generally >= 3 inches).
        - **Maximum Observed Water Levels - Gage Data:** Preferred reference MHHW. NOAA tide stations use MHHW. USGS/other non-NOS tide gages report on MHHW if possible. NAVD88 or AGL acceptable. Reference datum and data source specified. NOS CO-OPS provides final report to NWS Regional offices.
        - **High Water Marks (HWMs):** NWS identifies locations for partner agencies to survey. USGS is primary source. AGL measurements typical, no conversion. Coordinate with NHC for consistency. Do not include debris-line HWMs. Report max water level (feet above datum). Identify location/date/time (UTC). Observations >= 1 foot required, < 1 foot as needed/requested. Unlikely in initial PSH, updated as available.
        - **Tornadoes:** Report times (UTC) and locations, damage description. From Preliminary Local Storm Reports (LSRs). Latitude/longitude with highest precision.

---

## 2. Correction Procedures

### 2.1 Non-VTEC Product Corrections

WFOs use a specific format for corrections (e.g., WTUS82 KILM 290301 CCA). Second correction uses "B" (CCB). "CORRECTED FOR" is optional.

### 2.2 VTEC Product Corrections

WFOs follow NWSI 10-1703 procedures. Refer to GFE correction job sheet.

---

## 3. Procedures for Populating Wind Forecast Grids for Tropical Cyclone Events

Updates planned for better integration into NDFD.

### 3.1 Wind Speed Values Within the 34-knot Wind Radii

- **0 to 120 hours:** Field offices use designated wind tool and latest NHC/CPHC/JTWC advisory wind radii. Do not exceed official radii. If radii unavailable, use climatology-persistence model output or coordinate. Not necessary once system is post-tropical or dissipated.
- **Storm Intensity:** Use full continuum of values, up to max sustained wind speed in forecast advisory. Do not exceed.
- **Local Knowledge:** Apply local knowledge/mesoscale expertise to explicit wind speed forecasts within stated constraints.
- **121 to 168 hours:** Use Radii Climatology and Persistence Model (RCL) wind tool, capping at 45 knots. If RCL points unavailable, collaborate for background closest to NHC/WPC points, capping at 45 knots.

### 3.2 Wind Speed Values Outside the 34 knot Wind Radii

- **0 to 168 hours:** Use deterministic wind speed values.

### 3.3 Wind Direction Values Inside or Outside the 34 knot Wind Radii

- **0 to 168 hours:** Use deterministic wind direction values.

### 3.4 Wind Gust Values Inside or Outside the 34 knot Wind Radii

Wind gust grids are required, created via local GFE. Methodology and values should be collaborated.

### 3.5 Caveat

Emphasize for all text/graphical products: "Winds in and near tropical cyclones should be used with caution due to uncertainty in forecast track, size, and intensity."

---

## 4. Procedures for Tropical Cyclone Storm Surge Watch/Warning Collaboration with NHC

Instructions for Atlantic basin coastal WFOs only. Updates planned for NDFD integration.

### 4.1 Collaboration Initiation

NHC informs affected WFOs when storm surge inundation values approach watch/warning criteria.

### 4.2 Collaborative Process

NHC sends proposed storm surge grids (Proposed SS grids) via AWIPS GFE. WFOs edit for local area and send back. Second round of collaboration if needed. NHC makes final determination for disagreements.

### 4.3 Finalization of Storm Surge Watches/Warnings

WFOs finalize surge hazards before advisory time. Added to local WFO Hazards grid and used in TCV product (AWIPS GFE text formatter). Storm surge watches/warnings must begin/end at zone boundaries. If part of a zone is impacted by surge watch/warning, no other coastal flood hazard can be in effect for that zone. Other coastal hazards are allowed.

---

## APPENDIX B - Tropical Cyclone Assessment and Warning Product Identifiers

This appendix lists WMO Headers and AWIPS Product Identifiers for various tropical cyclone products.

- **Hurricane Local Statement (HLS):**

    - Atlantic: WTUS/81-84/ KCCC** (HLSNNN**)
    - Brownsville, TX: WTUS84 KBRO (HLSBRO)
    - San Juan, PR: WTCA82 TJSJ (HLSSJU)
    - San Juan (Spanish): WTCA82 TJSJ (HLSSPN)
    - Eastern Pacific: WTUS86 KCCC** (HLSNNN**)
    - Central Pacific (All Hawaiian Islands): WTHW80 PHFO (HLSHFO)
    - Western North Pacific (Guam and Micronesia): WTPQ/81-85/ PGUM (HLSPQ/1-5/)
    - South Pacific (Pago Pago, American Samoa): WTZS/81-85/NSTU (HLSZS/1-5/)

- **Tropical Cyclone Local Watch/Warning (TCV):**

    - Atlantic: WTUS/81-84/ KCCC** (TCVNNN**)
    - Brownsville, TX: WTUS84 KBRO (TCVBRO)
    - Eastern Pacific: WTUS86 KCCC** (TCVNNN**)
    - Central Pacific (All Hawaiian Islands): WTHW80 PHFO (TCVHFO)

- **Extreme Wind Warning (EWW):**
    - Atlantic: WFUS/51-55/KCCC** (EWWNNN**)
    - Brownsville, TX: WFUS54 KBRO (EWWBRO)
    - Guam: WFPQ50 PGUM (EWWGUM)
    - Honolulu, HI: WFHW50 PHFO (EWWHFO)
    - San Juan, PR: WFCA52 TJSJ (EWWSJU)

_NOTE: "KCCC" and "NNN" represent the valid WFO 4-letter and 3-letter station identifiers, respectively._
