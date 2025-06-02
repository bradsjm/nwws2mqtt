This document outlines the specifications and procedures for various tropical cyclone products issued by Weather Forecast Offices (WFOs) under the National Weather Service (NWS) Instruction 10-601, effective April 25, 2023. This instruction supersedes the July 14, 2022 version.

### 1. Weather Forecast Office (WFO) Tropical Cyclone Products

WFOs issue tropical cyclone products to inform media, local decision makers, and the public about current and anticipated tropical cyclone conditions in their County Warning Area (CWA). They also determine the issuance of inland tropical cyclone wind watches and warnings. Coastal Atlantic basin WFOs and WFO San Juan, Puerto Rico, collaborate with the National Hurricane Center (NHC) for storm surge watches and warnings. All WFOs must ensure product consistency with tropical cyclone forecast centers and surrounding offices.

#### 1.1 WFO Tropical Cyclone Local Watch/Warning Product (WFO TCV)

The TCV is issued by WFOs with tropical cyclone wind watch/warning responsibility, except WFO Guam and WSO Pago Pago. It is a segmented Valid Time Event Code (VTEC) product, with each segment covering a discrete forecast zone.

- **Content**: Includes land-based tropical cyclone wind and storm surge (for Atlantic basin WFOs only) watches/warnings, meteorological information, hazards (wind, storm surge, flooding rain, tornadoes), and potential threats/impacts. It's generated from local gridded forecast information and national guidance, not intended for manual editing.
- **Purpose**: Designed for parsing by the weather enterprise and paired with the WFO HLS for a complete, localized tropical forecast. Useful for decision makers by providing detailed, zone-level information on hazard timing, threats, and impacts.
- **Mission Connection**: Primary WFO product for disseminating land-based tropical cyclone watches and warnings. Conveys information from NHC/CPHC and WFOs. Coastal TCVs must align with NHC/CPHC Tropical Cyclone Public Advisory (TCP) coastal watch/warning hazards.
- **Issuance Guidelines**:
    - **Software**: Advanced Weather Interactive Processing System (AWIPS) Graphical Forecast Editor (GFE).
    - **Criteria**: Issued after NHC/CPHC TCP for consistent VTEC Event Tracking Number (ETN).
        - **Coastal WFOs (with significant tidal influences)**: Caribou ME, Portland ME, Boston/Norton MA, New York City NY, Philadelphia PA, Baltimore MD/Washington DC, Wakefield VA, Newport/Morehead City NC, Wilmington NC, Charleston SC, Honolulu HI, Brownsville TX, Corpus Christi TX, Houston/Galveston TX, Lake Charles LA, New Orleans LA, Mobile AL, Tallahassee FL, Tampa Bay FL, Miami FL, Key West FL, Melbourne FL, Jacksonville FL, San Juan PR, Los Angeles CA, San Diego CA.
        - **Inland WFOs (when hurricane/tropical storm force winds may impact CWA)**: Albany NY, Binghamton NY, Blacksburg VA, Burlington VT, Columbia SC, Greenville/Spartanburg SC, Raleigh/Durham NC, State College PA, Atlanta GA, Austin/San Antonio TX, Birmingham AL, Fort Worth TX, Huntsville AL, Jackson MS, Little Rock AR, Memphis TN, Morristown TN, Nashville TN, Shreveport LA.
        - Inland WFOs not listed above will use Non-Precipitation Warning (NPW) products for hurricane/tropical storm force winds.
    - **Times**:
        - **Initial Issuances**: Coastal WFOs issue TCVs as closely as possible to the first NHC/CPHC tropical storm/hurricane watch/warning. Abbreviated TCVs are allowed for timely notifications, followed by a full TCV. Inland WFOs issue TCVs in coordination with neighbors when NHC/CPHC forecasts tropical storm/hurricane force winds within 48 hours (watches) to 36 hours (warnings).
        - **Subsequent updates**: Within 30 minutes of regular/intermediate tropical cyclone forecast center advisories, or for other significant operational changes (e.g., rainfall, tornado info). TCV wind/storm surge changes must align with NHC/CPHC public advisories.
        - **Final**: Cease when all local tropical cyclone watches/warnings expire for the CWA.
    - **Valid Time**: Valid from issuance until subsequent TCV or watch/warning expiration. Issued at least every 6 hours during an event.
    - **Event Beginning/Ending Time**: VTEC includes start time; ending time is not explicitly provided due to forecast uncertainties.
    - **Product Expiration Time**: Generally 6 hours post-issuance, coinciding with next update or event end. Set to 8 hours for potential delays.
- **Technical Description**:
    - **UGC Type**: Zone (Z) form.
    - **MND Header**: "(Name or Number) Local Watch/Warning Statement/Advisory Number ##". "##" is sequential advisory number. Coded string (BBCCYYYY) appended to "Issuing Office City State" line.
    - **Content Structure**: One or more formatted segments per UGC zone, containing: UGC/VTEC encoding, watch/warning headlines, plain language locations, and hazard sections (Meteorological forecast, Threat, Potential Impacts, Sources of additional information).
    - **VTEC Phenomena Codes**: TROPICAL STORM (TR), HURRICANE (HU), STORM SURGE (SS\*).
    - **VTEC Significance Codes**: Warning (W), Watch (A). \*WFOs Los Angeles, San Diego, and Honolulu do not issue storm surge watches/warnings.
    - **ETN**: Unique value for each tropical cyclone, derived from the basin's storm number in the tropical cyclone forecast center's TCP.
    - **Mandatory Subsections**: HEADLINE(s), LOCATIONS AFFECTED, WIND, FLOODING RAIN, TORNADO, FOR MORE INFORMATION. STORM SURGE is mandatory for surge-prone zones.
- **Relationship to other products**:
    - **Short Term Forecast (NOW)**: Complements TCV by providing more specific information for the next 6 hours.
    - **Zone Forecast Product (ZFP)**: Will highlight tropical cyclone watches and warnings from the TCV.
    - **WFO-issued Advisory/Watch/Warning Products**: Tables 1A, 1B, 2A, 2B define issuance actions. (Refer to original document for detailed tables).

#### 1.2 Hurricane Local Statement (HLS)

The HLS is a discussion-based preparedness product providing a succinct message on land-based local impacts from a tropical cyclone. All WFOs with tropical cyclone wind watch/warning responsibility (except WFO Guam and WSO Pago Pago) issue this standard HLS, which is non-segmented and lacks VTEC. Marine hazards are in the Marine Weather Message (MWW).

- **Mission Connection**: Provides critical information for life/property protection and minimizing economic/environmental losses from tropical cyclones. It’s a common source for diverse users (media, decision makers, public).
- **Issuance Guidelines**:
    - **Software**: AWIPS GFE.
    - **Criteria**: Issued after TCP and WFO TCV when watches/warnings are active. Can be issued stand-alone to dispel rumors if no watches/warnings are in effect.
    - **Times**:
        - **Initial**: Closely follow WFO TCV issuance.
        - **Subsequent**: Closely follow WFO TCV issuance for each advisory.
        - **Final**: Soon after all tropical cyclone watches/warnings are canceled via WFO TCV. PNS can relay post-storm info.
    - **Valid Time**: Valid from issuance until subsequent HLS. Issued at least every 6 hours.
    - **Product Expiration Time**: Generally 6 hours post-issuance, coinciding with next update or event end. Set to 8 hours for potential delays.
- **Technical Description**:
    - **UGC Type**: Zone (Z) form.
    - **MND Header**: "(System Type) (Name or Number) Local Statement Advisory Number ##". "##" is sequential advisory number. Coded string (BBCCYYYY) appended to "Issuing Office City State" line.
    - **Content**: Focus on most severe hazards and threatened areas. Uses latest advisory for tropical cyclone position. Organized into sections: Affected Area, Headline/Primary Message, New Information, Situation Overview, Precautionary/Preparedness Actions, Next Update.
    - **Mandatory Sections**: NEW INFORMATION, SITUATION OVERVIEW, POTENTIAL IMPACTS, PRECAUTIONARY / PREPAREDNESS ACTIONS, NEXT UPDATE.
- **Relationship to other products**:
    - **Short Term Forecast (NOW)**: Complements HLS by providing specific conditions for the next 6 hours.
    - **Public Information Statement (PNS)**: Encouraged before first HLS for routine preparedness info.
    - **Special Weather Statement (SPS)**: May provide preliminary info for systems not yet issuing advisories.
    - **Hazardous Weather Outlook (HWO)**: May address peripheral weather concerns until first tropical cyclone advisory.

#### 1.3 Tropical Cyclone Local Statement (HLS) – South Pacific and western North Pacific

This HLS product, issued by WFO Guam and WSO Pago Pago, is discussion-centric and provides information on land-based local impacts. It serves as a common source for diverse users (media, decision makers, public) and supports local authorities with generalized and specific tropical cyclone information.

- **Format**: Consists of an Overview Block and UGC/VTEC formatted segments (for Guam/Northern Marianas only; WSO Pago Pago HLS does not include VTEC).
    - **Overview Block**: Provides generalized tropical cyclone information for the entire CWA.
    - **UGC/VTEC Formatted Segments**: Expands on Overview Block with detailed information for specific zones.
- **Mission Connection**: Primary WFO/WSO product in these basins for life/property protection and minimizing losses.
- **Issuance Guidelines**:
    - **Software**: AWIPS GFE.
    - **Criteria**: For WFO Guam, a TCP precedes HLS issuance. No TCP for WSO Pago Pago CWA. HLSs should not be issued for systems not formally recognized by tropical cyclone centers.
    - **Times**:
        - **Initial**: As soon as possible following first tropical storm/hurricane/typhoon watch/warning. WFO Guam issues within one hour of TCP. Abbreviated HLS allowed for timely alerts for new zones.
        - **Subsequent**: Within 30 minutes of regular/intermediate tropical cyclone forecast center advisories, or for operationally significant changes.
        - **Final**: Routine HLSs may cease when threat ends or watches/warnings expire. WFO Guam can continue issuing HLS for sub-warning criteria impacts.
    - **Valid Time**: Valid from issuance until subsequent HLS. Issued at least every 6 hours.
    - **Event Beginning/Ending Time**: VTEC includes start time; ending time not explicitly provided. WFO Guam for Micronesia and WSO Pago Pago products do not include VTEC.
    - **Product Expiration Time**: Generally 6 hours post-issuance, coinciding with next update or event end.
- **Technical Description**:
    - **UGC Type**: Zone (Z) form.
    - **MND Header**: "(System Type) (Name or Number) Local Statement".
    - **Content**: Focus on most severe hazards and threatened areas. Uses latest advisory for tropical cyclone position. Wording can be added about where additional storm information can be found (supporting TCP for WFO Guam, PNSs, NOWs).
    - **Mandatory Sections in Overview Block**: NEW INFORMATION, AREAS AFFECTED, WATCHES / WARNINGS, STORM INFORMATION, SITUATION OVERVIEW, PRECAUTIONARY / PREPAREDNESS ACTIONS, NEXT UPDATE.
    - **Optional Sections in Segments**: PROBABILITY TROPICAL STORM / HURRICANE CONDITIONS, WINDS, STORM SURGE AND STORM TIDE, INLAND FLOODING, TORNADOES, OTHER.
    - **VTEC Phenomena Codes (WFO Guam HLS)**: TROPICAL STORM (TR), TYPHOON (TY).
    - **VTEC Significance Codes**: Warning (W), Watch (A), Statement (S).
- **Relationship to other products**:
    - **Short Term Forecast (NOW)**: Complements HLS for critical storm information.
    - **Zone Forecast Product (ZFP)**: Will highlight tropical cyclone watches and warnings.
    - **Public Information Statement (PNS)**: Encouraged before first HLS for routine preparedness info.
    - **Special Weather Statement (SPS)**: May provide preliminary info for systems not yet issuing advisories.
    - **Hazardous Weather Outlook (HWO)**: May address peripheral weather concerns until first tropical cyclone advisory.

#### 1.4 Non-precipitation Weather Products (NPW)

Inland WFOs that do not issue TCV or HLS will issue NPW for high wind watches/warnings if hurricane, tropical storm, subtropical storm, or post-tropical cyclone winds are forecast for their CWA.

- **Mission Connection**: Provide advance notice of hazardous weather events.
- **Issuance Guidelines**:
    - **Software**: AWIPS GFE.
    - **Criteria**:
        - **Watch**: When tropical storm/hurricane force winds possible within 48 hours.
        - **Warning**: When tropical storm/hurricane force winds expected within 36 hours.

#### 1.5 Extreme Wind Warning (EWW)

Short-duration warnings issued by WFOs for immediate threats to lives and property. Atlantic basin, WFO Guam, and WFO Honolulu forecasters issue EWWs for extreme sustained winds of a major hurricane/typhoon (Category 3 or higher), usually associated with the eyewall. WFOs in Southern California and WSO Pago Pago do not issue EWWs.

- **Mission Connection**: Inform public to take immediate shelter in interior of well-built structure due to onset of extreme tropical cyclone winds.
- **Issuance Guidelines**:
    - **Software**: AWIPS WarnGen.
    - **Criteria**: Both conditions must be met:
        - Tropical cyclone is Category 3 or greater on Saffir-Simpson Hurricane Wind Scale (NHC, JTWC, CPHC).
        - Sustained surface winds of 100 knots (115 mph) or greater are occurring or expected on land in CWA within one hour (for WFO Guam, limited to Guam and Northern Marianas).
    - **Issuance Time**: Non-scheduled, event-driven.
    - **Valid Time**: Up to three hours. Forecasters use judgment based on area size and cyclone speed.
- **Technical Description**:
    - **UGC Type**: County.
    - **MND Broadcast Line**: "BULLETIN – EAS ACTIVATION REQUESTED."
    - **MND Header**: "EXTREME WIND WARNING".
- **Updates and Amendments**: New EWW issued if criteria met beyond original warning time. WFOs (except Guam) issue SVSs during EWW validity for wind observations/damage reports.
- **Cancellations and Expirations**: WFOs (except Guam) issue SVSs for public notification.
- **Corrections**: For significant grammatical/content errors. Original ETN and time retained.

#### 1.6 Post Tropical Cyclone Report (PSH)

Primary WFO product for reporting and documenting local tropical cyclone impacts and observations. WSO Pago Pago is exempt.

- **Mission Connection**: Provides NHC, CPHC, NWS HQ, media, public, and emergency management with a record of peak tropical cyclone conditions. Used for post-event reports, news articles, and historical records. Standardized CSV format for observations.
- **Issuance Guidelines**:
    - **Creation Software**: AWIPS, spreadsheet, word processing, NWS Content Management System (CMS).
    - **Criteria**: All WFOs that issued tropical cyclone watches/warnings and HLSs prepare PSH. WFO Guam coordinates with WSOs for information within their area.
    - **Issuance Times**: Preliminary reports within 5 days of last HLS. Complete report within 15 days of last HLS. Updates as needed, especially for fatalities. NHC coordinates fatality reporting with PSH, NWS Storm Data, and NHC Tropical Cyclone Report.
- **Technical Description**:
    - **MND Header**: "POST TROPICAL CYCLONE REPORT... (TROPICAL CYCLONE TYPE) (NAME)". Tropical cyclone type is peak intensity during impact.
    - **Content (PSH Suite)**: PSH text product alerts users to new/updated info via WFO "Tropical Event Summary" webpage (https://weather.gov/XXX/TropicalEventSummary).
        1.  **PSH Text Product**: Mixed-case text to alert users to new/updated info, points to webpage.
        2.  **Observational Data Summary**: Summary of extreme wind, pressure, rainfall, and water level (coastal WFOs only) point-based observations.
        3.  **Impacts Report**: Narrative summary of impacts from all tropical cyclone hazards (wind, storm surge, inland flooding, tornadoes, etc.) per county/parish/independent city/island, including deaths, injuries, damages, evacuations.
        4.  **Downloadable Observational Data**: CSV files for Wind and Pressure, Rainfall, Water Level (coastal WFOs only), and Tornado data.
- **Data Reporting**:
    - **Wind and Pressure**: Highest sustained wind speed, peak gust, date/times (UTC), anemometer height (meters). Lowest sea level pressure, date/time (UTC). All reliable sources.
    - **Rainfall**: Storm total amount (inches) and duration (dates). Significant amounts (3+ inches).
    - **Maximum Observed Water Levels**: Preferred reference level MHHW. Reports include datum and source.
    - **High Water Marks (HWMs)**: NWS identifies locations for partner agency surveys. USGS is primary source. Report max water level (feet above datum).
    - **Tornadoes**: Times (UTC) and locations, brief damage description. From Preliminary Local Storm Reports (LSRs).

### 2. Correction Procedures

#### 2.1 Non-VTEC Product Corrections

WFOs use a "CCA" (or "CCB" for second correction) appended to the WMO header. "CORRECTED FOR" is optional.

#### 2.2 VTEC Product Corrections

WFOs follow NWSI 10-1703 procedures. Refer to GFE correction job sheet: https://www.weather.gov/vtec/GHG_COR.

### 3. Procedures for Populating Wind Forecast Grids for Tropical Cyclone Events

Updates to this directive will incorporate better methods for populating NDFD wind forecasts.

#### 3.1 Wind Speed Values Within the 34-knot Wind Radii (0-120 hours)

Field offices use designated wind tool with latest NHC/CPHC/JTWC advisory wind radii. Do not exceed official wind radii. Outside official advisory periods, use climatology-persistence model output or coordinate. Do not exceed maximum sustained wind speed forecast from tropical cyclone forecast center. Apply local knowledge and mesoscale expertise for final forecasts.

#### 3.2 Wind Speed Values Outside the 34-knot Wind Radii (0-168 hours)

Use deterministic wind speed values.

#### 3.3 Wind Direction Values Inside or Outside the 34-knot Wind Radii (0-168 hours)

Use deterministic wind direction values.

#### 3.4 Wind Gust Values Inside or Outside the 34-knot Wind Radii

Required. Created via local GFE procedures. Methodology and values should be collaborated with neighboring WFOs.

#### 3.5 Caveat

Emphasize caution for all text and graphical products due to uncertainty in forecast track, size, and intensity: "Winds in and near tropical cyclones should be used with caution due to uncertainty in forecast track, size, and intensity."

### 4. Procedures for Tropical Cyclone Storm Surge Watch/Warning Collaboration with NHC

Updates to this directive will incorporate better methods for populating NDFD storm surge forecasts. Instructions intended for Atlantic basin coastal WFOs only.

#### 4.1 Collaboration Initiation

NHC informs affected WFOs when storm surge inundation values approach watch/warning criteria.

#### 4.2 Collaborative Process

NHC sends proposed storm surge grids via AWIPS GFE. WFOs edit as appropriate and send back. Second round of collaboration may occur. NHC makes final determination in case of disagreement.

#### 4.3 Finalization of Storm Surge Watches/Warnings

WFOs finalize storm surge hazards prior to advisory time, adding them to local WFO Hazards grid for use in WFO TCV product. Storm surge watches/warnings must begin and end at zone boundaries. If part of a zone is impacted by storm surge watch/warning, no other coastal flood hazard can be in effect for that zone simultaneously.

### APPENDIX B - Tropical Cyclone Assessment and Warning Product Identifiers

(Refer to original document for full tables)

- **Hurricane Local Statement (HLS)**: Includes WMO Headers and AWIPS Product Identifiers for Atlantic, Brownsville TX, San Juan PR (Spanish), Eastern Pacific, Central Pacific (Hawaiian Islands), Western North Pacific (Guam/Micronesia), and South Pacific (Pago Pago/American Samoa).
- **Tropical Cyclone Local Watch/Warning (TCV)**: Includes WMO Headers and AWIPS Product Identifiers for Atlantic, Brownsville TX, Eastern Pacific, Central Pacific (Hawaiian Islands).
- **Extreme Wind Warning (EWW)**: Includes WMO Headers and AWIPS Product Identifiers for Atlantic, Brownsville TX, Guam, Honolulu HI, San Juan PR.
