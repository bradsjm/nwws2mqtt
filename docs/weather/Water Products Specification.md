This document, "NATIONAL WEATHER SERVICE INSTRUCTION 10-922," issued on August 3, 2021, by the Department of Commerce, National Oceanic & Atmospheric Administration, National Weather Service, outlines the specifications for Weather Forecast Office Water Resources Products.

**General Product Standards:**

- All products follow NWS-supported dissemination standards, including World Meteorological Organization (WMO) headers, AWIPS identifiers, Universal Geographic Codes (UGC), Mass News Dissemination (MND) header blocks, and specific content formats (NWSI 10-1701, 10-1702, 10-1703).
- The term "county" also encompasses "borough," "parish," and "independent city."
- Event Tracking Numbers (ETN) for non-adjacent areas should be different for products with the same AWIPS identifier, though manually changing system-generated ETNs is discouraged.
- Terminology for expressing event frequency should use "X percent annual chance event" instead of "T-year event." Events with less than 0.2% annual chance should not be cited.

**Multi-tiered "Ready, Set, Go" Concept:**

NWS products utilize a three-tiered concept to convey hazard severity, timing, and forecaster confidence for water resources products:

- **Hydrologic Outlook ("Ready"):** Indicates the possibility of a hazardous flooding event developing, providing long lead time for preparation.
- **Flood Watch ("Set"):** Issued when the expectation of a flood event has increased but its occurrence, location, and/or timing remain uncertain. Provides sufficient lead time for mitigation.
- **Flash Flood Warnings, Flood Warnings, and Advisories ("Go"):** Issued regardless of timeframe when an event is occurring, imminent, or has a very high probability of occurrence.

**Specific Product Types and Their Issuance Guidelines:**

**1. Hydrologic Outlook (ESF)**
_ **Purpose:** Provides long lead time information on potential flooding or other water resources events, enabling preparation, mitigation, and reservoir planning.
_ **Issuance Criteria:** Issued on an as-needed basis for the WFO's hydrologic service area (HSA) when flooding is possible 24+ hours out (or 12+ hours if certainty is low), or to indicate no longer a possibility of flooding. Also for long-term forecasts like water supply.
_ **Issuance Time:** Non-scheduled, event-driven for flood events; scheduled for long-term forecasts.
_ **Valid/Expiration Time:** Valid until cancelled or updated; expires 12-24 hours (or several days) for flood events, up to 30 days for long-term forecasts.
_ **Content:** Non-segmented, non-bulleted. Includes headline, area, timing, relevant factors, outlook definition, and closing statement. Formatted with WMO heading, AWIPS identifier, UGC type, MND product type line.
_ **Updates:** New product issuance.

**2. Flood Watch (FFA)**
_ **VTEC Code:** FA (flood watch) or FF (flash flood watch); Significance Code: A.
_ **Purpose:** Informs the public of potential flooding, typically 6-48 hours before the event.
_ **Issuance Criteria:** Issued when 50-80% chance of flooding within 48 hours (or beyond if best way to convey), or debris flows from burn scars/landslide-prone areas. Also for dam/levee failure threat (not imminent), changes to effective time, increased area, or updates/cancellations.
_ **Issuance Time:** Non-scheduled, event-driven.
_ **Valid/Expiration Time:** Valid from start to end of potential flooding; expires 6-8 hours after issuance (up to 12-24 for longer events), or 30 minutes after watch expiration/cancellation.
_ **Content:** Segmented, bulleted format (except cancellations/expirations). Optional general overview. Required segmented watch information section with UGC, P-VTEC, H-VTEC, zones/cities, date/time stamp. Includes "WHAT," "WHERE," "WHEN," "IMPACTS," "ADDITIONAL DETAILS" bullets, and optional Call-to-Action (CTA).
_ **Updates:** New product issuance with appropriate VTEC action codes. Corrections for text/format errors are allowed in segments, but not for VTEC-linked elements or areas covered.
_ **Replacement:** To replace with a warning, issue the warning first, then cancel the watch.

**3. Flood Watch for Forecast Points (FFA) - Optional Product**
_ **VTEC Code:** FL; Significance Code: A.
_ **Purpose:** Informs the public of potential flooding at specific forecast points on rivers/streams, typically 6-48 hours before the event.
_ **Issuance Criteria:** Similar to general Flood Watch, but for specific locations, when 50-80% chance of flooding within 48 hours (or beyond). Also for dam/levee failure threat (not imminent), changes to effective time, updates/cancellations, or increased area (by issuing a new watch).
_ **Issuance Time:** Non-scheduled, event-driven.
_ **Valid/Expiration Time:** Valid from start to end of potential flooding; expires 6-8 hours after issuance (up to 12-24 for longer events), or 30 minutes after watch expiration/cancellation.
_ **Content:** Segmented, bullet format. Optional general overview/synopsis. Required segmented watch information section with UGC, P-VTEC, H-VTEC, date/time stamp. Includes "WHAT," "WHERE" (river/stream/point name), "WHEN," "ADDITIONAL DETAILS" (with sub-bullets for current stage/flow, flood stage/flow, forecast, impacts), and optional CTA.
_ **Updates:** New product issuance with appropriate VTEC action codes. Corrections for text/format errors allowed, but not for VTEC-linked elements.
_ **Replacement:** To replace with a warning, issue the warning first, then cancel the watch.

**4. Flash Flood Warning (FFW)**
_ **VTEC Code:** FF; Significance Code: W.
_ **Purpose:** Issued when flash flooding is imminent or likely, requiring immediate action to protect life and property (e.g., dangerous small stream/urban flooding, dam/levee failures).
_ **Issuance Criteria:** Flash flooding is reported, dam/levee failure is imminent/occurring, sudden natural stream obstruction failure is imminent/occurring, radar/rain gage indicates flash flooding likely, hydrologic model indicates flash flooding on small streams, or previous warning needs time extension. New FFW for adjacent areas as warnings cannot be extended in area.
_ **Issuance Time:** Non-scheduled, event-driven.
_ **Valid/Expiration Time:** Valid from issuance until expected end of flooding (or product cancellation). Extensions usually 6 hours or less, up to 12-24 hours for prolonged heavy rain. Expiration time matches valid time.
_ **Content:** Bulleted, Impact-Based Warning (IBW) format. Includes UGC, P-VTEC, H-VTEC, date/time stamp. Headlines for immediate cause (ER, IC, MC, UU, DM, DR, GO, IJ, RS, SM), event ending time. "HAZARD," "SOURCE," "IMPACT" details. Optional "FLASH FLOOD EMERGENCY" phrase for severe threats. Includes Call-to-Action (CTA) and latitude/longitude polygon coordinates. IBW tags like "RADAR INDICATED," "OBSERVED," "FLASH FLOOD DAMAGE THREAT" (Base, CONSIDERABLE, CATASTROPHIC), "EXPECTED RAINFALL RATE," "DAM or LEVEE FAILURE."
_ **Updates:** Flash Flood Statement (FFS) for updates/cancellations. New FFW for new areas or time extensions. Corrections for text/format errors.
_ **WEA Issuance:** Only for FFW with CONSIDERABLE or CATASTROPHIC damage threat tags.

**5. Flash Flood Statement (FFS)**
_ **VTEC Code:** FF; Significance Code: W.
_ **Purpose:** Provides supplemental information on active flash flood warning products, including updated observations and impact information.
_ **Issuance Criteria:** Announce cancellation/expiration of FFW, or provide additional information for continuing FFW. Issued when flooding has ended for warned area.
_ **Issuance Time:** Non-scheduled, event-driven.
_ **Valid/Expiration Time:** FFW remains valid until expires/cancelled. FFS expiration matches FFW expiration; 10 minutes after FFW expiration/cancellation.
_ **Content:** Segmented, non-bulleted format. Includes UGC, P-VTEC, H-VTEC, counties/cities, date/time stamp. Headlines for cancellation, expiration, or continuation. "HAZARD," "SOURCE," "IMPACT" details for continuations. Call-to-Action (CTA). Latitude/longitude polygon coordinates. IBW tags (same as FFW).
_ **Updates:** Additional FFS for updates. Corrections for text/format errors.
_ **WEA Issuance:** Only for FFS showing an increase in damage threat.

**6. Flood Warning For Forecast Points (FLW)**
_ **VTEC Code:** FL; Significance Code: W.
_ **Purpose:** Issued for high flow, overflow, or inundation at specific forecast points, threatening life/property, not covered by other warnings.
_ **Issuance Criteria:** RFC guidance indicates >80% likelihood, reports indicate flooding occurring, or forecast flooding increases to higher category. Special criteria for category increases (CON/EXT action codes).
_ **Issuance Time:** Non-scheduled, event-driven.
_ **Valid/Expiration Time:** Valid from forecast start until end of flooding (or cancellation). Expiration typically 12-24 hours after issuance (can be 6 hours for rapid changes).
_ **Content:** Segmented, bulleted format. Optional general overview/synopsis (required for category increases). Each forecast point has its own segment with UGC, P-VTEC, H-VTEC, date/time stamp. Includes "WHAT," "WHERE" (river/stream/point name), "WHEN," "ADDITIONAL DETAILS" (with sub-bullets for current stage/flow, flood stage/flow, recent activity, forecast, impacts, history), and optional CTA.
_ **Updates:** Flood Statement (FLS) for updates. Corrections for text/format errors are allowed, but not for VTEC-linked elements or changes to observed/forecast data.
_ **ROU Segments:** May include "ROU" segments for forecast points below flood warning criteria if beneficial for a complete overview.

**7. Flood Statement - Follow-up to Flood Warning For Forecast Points (FLS)**
_ **VTEC Code:** FL; Significance Code: W.
_ **Purpose:** Provides supplemental information on previously issued flood warnings for forecast points, including updated observations and forecasts.
_ **Issuance Criteria:** Information update/supplement needed for existing warning, or cancellation/expiration of warning.
_ **Issuance Time:** Non-scheduled, event-driven.
_ **Valid/Expiration Time:** Flood warning remains valid as per its initial issuance. FLS expiration typically 12-24 hours after issuance, or 30 minutes after warning expiration/cancellation.
_ **Content:** Segmented, non-bulleted format. Optional general overview/synopsis. Includes UGC, P-VTEC, H-VTEC, date/time stamp. Headlines for cancellation, expiration, or continuation. Details on current/future hydrometeorological conditions and impacts. \* **Updates:** Additional FLS for updates. Corrections for text/format errors are allowed, but not for VTEC-linked elements.

**8. Flood Warning (FLW)**
_ **VTEC Code:** FA; Significance Code: W.
_ **Purpose:** Issued for high flow, overflow, or inundation in a geographical area not covered by flash flood warnings or flood warnings for forecast points.
_ **Issuance Criteria:** Flood monitoring/forecasting indicates >80% likelihood over an area not quantifiable by forecast points, widespread reported flooding not quantifiable by forecast points, previous warning needs time extension, or flooding is imminent/occurring in areas not under a valid warning.
_ **Issuance Time:** Non-scheduled, event-driven.
_ **Valid/Expiration Time:** Valid from issuance until expected end of flooding (or cancellation). Expiration typically 6-24 hours after issuance.
_ **Content:** Segmented, bulleted format. Optional general overview/synopsis. Includes UGC, P-VTEC, H-VTEC, counties/cities, date/time stamp. Headlines for immediate cause (ER, IC, MC, UU, DM, DR, GO, IJ, RS, SM), event ending time. "WHERE" (geographic area), "WHEN," "IMPACTS," "ADDITIONAL DETAILS" bullets. Optional CTA. Latitude/longitude polygon coordinates. \* **Updates:** Flood Statement (FLS) for updates. Corrections for text/format errors are allowed, but not for VTEC-linked elements or areas covered. New FLW for new areas or time extensions.

**9. Flood Statement - Follow-up to a Flood Warning (FLS)**
_ **VTEC Code:** FA; Significance Code: W.
_ **Purpose:** Provides supplemental information on previously issued flood warnings, such as updated observations and impact information.
_ **Issuance Criteria:** Information update/supplement needed for existing warning, or cancellation/expiration of warning.
_ **Issuance Time:** Non-scheduled, event-driven.
_ **Valid/Expiration Time:** Flood warning remains valid as per its initial issuance. FLS expiration typically 6-24 hours after issuance, or 10 minutes after warning expiration/cancellation.
_ **Content:** Segmented, non-bulleted format. Optional general overview/synopsis. Includes UGC, P-VTEC, H-VTEC, counties/cities, date/time stamp. Headlines for cancellation, expiration, or continuation. Brief post-event synopsis (for CAN/EXP) or current hydrometeorological situation/impacts (for CON). Optional CTA. Latitude/longitude polygon coordinates. \* **Updates:** Additional FLS for updates. Corrections for text/format errors.

**10. Flood Statement - Flood Advisory (FLS)**
_ **VTEC Code:** FA; Significance Code: Y.
_ **Purpose:** Provides information on elevated river/stream flow or ponding of water in a geographic area, less urgent than a warning.
_ **Issuance Criteria:** Elevated streamflow/ponding is occurring or >80% likely and warrants public notification (not above flood stage). Advisory needed for new areas not under an existing advisory. Updated hydrometeorological information needed.
_ **Issuance Time:** Non-scheduled, event-driven.
_ **Valid/Expiration Time:** Valid until hydrologic conditions end or product cancelled/updated. Expiration time matches valid time (6-24 hours after issuance) or 10 minutes after advisory expiration/cancellation.
_ **Content:** Segmented, bulleted format (except CAN/EXP/CON). Optional general overview/synopsis. Includes UGC, P-VTEC, H-VTEC, counties/cities, date/time stamp. Headlines for new issuance, extension, or continuation. "WHAT" (type of flooding, hydrologic condition), "WHERE" (geographic area), "WHEN," "IMPACTS," "ADDITIONAL DETAILS" bullets. Optional CTA. Latitude/longitude polygon coordinates.
_ **Updates:** New product issuance for new advisories. Follow-up FLS for extensions. Corrections for text/format errors.
_ **Replacement:** To replace with a warning, issue the warning first, then cancel the advisory.

**11. Flood Statement - Flood Advisory for Forecast Points (FLS)**
_ **VTEC Code:** FL; Significance Code: Y.
_ **Purpose:** Provides information on elevated river/stream flows at specific locations, less urgent than a warning. (Optional product for some WFOs).
_ **Issuance Criteria:** Elevated streamflow >80% likely (not above flood stage). New advisory for additional forecast points. Updated hydrometeorological information.
_ **Issuance Time:** Non-scheduled, event-driven.
_ **Valid/Expiration Time:** Valid until elevated streamflow is no longer concern or product cancelled/updated. Expiration matches valid time (6-24 hours) or 30 minutes after advisory expiration/cancellation.
_ **Content:** Segmented, bullet format. Optional general overview/synopsis. Includes UGC, P-VTEC, H-VTEC, NWSLI, date/time stamp. Headlines for new issuance, extension, or continuation. "WHAT" (elevated streamflow), "WHERE" (river/stream/point name), "WHEN," "ADDITIONAL DETAILS" (current stage/flow, flood stage/flow, forecast, impacts), and optional CTA.
_ **Updates:** Follow-up FLS for updates. Corrections for text/format errors.
_ **Replacement:** To replace with a warning, issue the warning first, then cancel the advisory.

**12. Hydrologic Statement (RVS)**
_ **Purpose:** Provides hydrologic forecasts and related information in an easily readable format for users without sophisticated decoding capabilities.
_ **Issuance Criteria:** River forecasts prepared for HSA or significant hydrologic conditions.
_ **Issuance Time:** Scheduled or event-driven.
_ **Valid Time:** From release until next update or specified.
_ **Content:** Non-segmented, non-bulleted. Headline, narrative information, and/or observations/forecasts of river stages, lake levels, ice conditions.
_ **Updates:** New product issuance.

**13. Hydrologic Summary (RVA)**
_ **Purpose:** Provides hydrologic observations and related information, including river stages, lake levels, precipitation, and ice conditions.
_ **Issuance Criteria:** After data on rivers/reservoirs in HSA are collected and quality controlled.
_ **Issuance Time:** Scheduled.
_ **Valid Time:** From release until next update or specified.
_ **Content:** Non-segmented, non-bulleted. Optional headline, tabular data.
_ **Updates:** New product issuance.

**14. River and Lake Forecast Product (RVD)**
_ **Purpose:** Provides hydrologic forecasts and observations in Standard Hydrometeorological Exchange Format (SHEF) for computer applications.
_ **Issuance Criteria:** Daily for daily forecast points in HSA; more frequent updates if needed.
_ **Issuance Time:** Routine schedule; can be daily or weekly.
_ **Valid Time:** From release until updated.
_ **Content:** Table of observed/forecast SHEF A.b A data, vertically aligned. Includes NWSLI, station name, flood stage, current stage/elevation, 24-hour change, one-day forecast, additional data (6-hourly/daily up to 7 days). Grouped by river basin. Optional narrative.
_ **Updates:** New product issuance.

**15. Hydrometeorological Data Products (RRx)**
_ **Purpose:** Contains precipitation and other hydrometeorological data from various networks (NWS Cooperative Network, flood warning systems, ASOS, partner agencies).
_ **Issuance Criteria:** To disseminate hydrometeorological data.
_ **Issuance Time:** Scheduled.
_ **Valid Time:** Not applicable (observed data report).
_ **Content:** SHEF format. WMO header, MND header block, headline statement (if WFO product).
_ **Updates:** New product issuance.

**16. Hydrometeorological Data Summary Products (HYx)**
_ **Purpose:** Provides daily, weekly, and monthly summaries of quality-controlled hydrometeorological observations.
_ **Issuance Criteria:** When daily, weekly, or monthly data compiled/reviewed.
_ **Issuance Time:** Scheduled.
_ **Valid Time:** Not applicable (observed data report).
_ **Content:** WMO header, MND header block, optional headline.
_ **Updates:** New product issuance.

**17. Hydrometeorological Coordination Message (HCM)**
_ **Purpose:** Internal communication between WFOs, RFCs, and NCEP for forecast/support-oriented information. Not publicly distributed.
_ **Issuance Criteria:** As needed for internal coordination.
_ **Issuance Time:** Non-scheduled, event-driven.
_ **Content:** Topics include contingency planning, QPF/hydrologic forecast verification, gage/radar data problems.

**18. Web-Based Products**
_ **Purpose:** Water resources forecast information and observed data from products, plus additional WFO output, made available graphically and through databases via the Internet (AHPS).
_ **Standards:** Conforms to NWS, NOAA, DOC policies (NWSI 10-932). Displays and features described in "Water Resources Information on the Web: A Manual for Users."
