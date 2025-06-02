This document outlines the specifications for various weather products issued by the National Weather Service (NWS) and the Storm Prediction Center (SPC). It supersedes NWSI 10-517, dated October 9, 2017.

## 1. Short Term Forecast (NOW)

- **Mission Connection:** Provides detailed weather information within 6 hours of issuance.
- **Issuance Guidelines:**
    - **Software:** Primarily Graphical Hazards Generation Editor (GHG). WarnGen may be used for low-impact non-convective events.
    - **Criteria:** Discusses evolution of precipitation, winter weather, sea breezes, marine weather, fog, winds, and temperatures. **Must not** contain information about "sub-severe" thunderstorms meeting SPS criteria. Consistent with graphical short-term forecasts if both are issued.
    - **Time:** Non-scheduled, event-driven.
    - **Valid Time:** From issuance until expiration.
    - **Expiration Time:** Not more than 6 hours after issuance.
- **Technical Description:**
    - **UGC Type:** Zone (Z) code for GHG, County (C) for WarnGen.
    - **MND Header:** "Short Term Forecast."
    - **Content:** Non-technical, future tense, concise, focusing on precipitation location, movement, intensity, amounts, and duration. General mentions of thunderstorm coverage and movement are allowed, but no specific wind/hail values or potential impacts. Can be segmented by zone groupings in GHG.
- **Updates:** Not updated or amended, only corrected for format/grammatical errors.

---

## 2. Special Weather Statement (SPS)

- **Mission Connection:** Provides information on ongoing or imminent weather hazards requiring heightened awareness/action, typically within 6 hours, but can be for major events beyond 6 hours.
- **Issuance Guidelines:**
    - **Software:** GHG or WarnGen.
    - **Criteria:**
        - **Developing Hazardous Convective Weather:** To heighten awareness of ongoing/imminent hazardous convective weather within 1-2 hours.
        - **Sub-Severe Thunderstorms:** For strong thunderstorms approaching or expected to approach severe criteria (NWSI 10-511 Section 2.2.2). General criteria include:
            1.  Sustained winds/gusts of 40-57 mph (lower values at forecaster's discretion).
            2.  Hail less than 1 inch in diameter.
            3.  Frequent to continuous lightning.
            4.  Landspouts not anticipated to threaten lives/property.
            5.  Funnel clouds not expected to become tornado threats.
            6.  Waterspouts exclusively over inland water bodies, not expected to reach/threaten shoreline.
        - **Other Short-term Hazards:** For high-impact events supplementing other hazardous weather products (e.g., "black ice," heavy snow bands below warning criteria, lake-effect snow affecting visibility, heavy rainfall not causing flooding, near-advisory level heat/wind chills, local blowing dust).
        - **Major Events Forecast Beyond 6 Hours:** To heighten awareness of major events forecast beyond 6 hours.
    - **Time:** Non-scheduled, event-driven.
    - **Valid Time:** From issuance until expiration or update.
    - **Expiration Time:** Not more than 6 hours after issuance, except for events forecast beyond 12 hours, where it's not more than 12 hours.
- **Technical Description:**
    - **UGC Type:** Zone (Z) code for GHG, County (C) for WarnGen. Public Zones for zone-based SPSs.
    - **MND Header:** "Special Weather Statement."
    - **Content:** Consistent with other hazardous weather products, concise, non-technical.
    - **Format:**
        - **Generic Format:** Used for non-convective situations (Sections 3.2.2 a, c, and d). May include lat/lon polygon for sub-CWA specificity.
        - **Impact-Based Format for Sub-Severe Thunderstorms:** Specific order:
            - **Basis Statement:** Time, "strong thunderstorm(s)," distance from closest location, storm motion.
            - **HAZARD:** Basis for issuance, forecast/observed wind gusts, max hail sizes.
            - **SOURCE:** Accepted types (radar, spotters, law enforcement, etc.). Include qualifying sub-severe weather reports.
            - **IMPACT:** Predetermined statements based on wind speed/hail size (see Table 1 in document).
            - **Locations Impacted Section:** Inclusion of affected locations.
            - **PRECAUTIONARY/PREPAREDNESS ACTIONS:** One or two short, action-oriented CTA statements. Includes "&&" dissemination marker. Tornado/Severe Thunderstorm Watch info optional if valid.
            - **LAT...LON:** Warning area polygon coordinates (2 decimal places).
            - **TIME...MOT...LOC:** Tracking info (time UTC, 3-digit direction, speed in knots, lat/lon coordinate(s)).
            - **Impact-Based Coded Tag Lines:** Required and optional tags in uppercase (LANDSPOUT, WATERSPOUT, MAX HAIL SIZE, MAX WIND GUST). Hail tag first, then wind. Landspout/waterspout first if invoked.
- **Updates:** Updated as needed, corrected for format/grammatical errors.

---

## 3. Hazardous Weather Outlook (HWO)

- **Mission Connection:** Provides a single source of information on expected hazardous weather for the seven-day forecast period to the public, media, and emergency managers.
- **Issuance Guidelines:**
    - **Software:** GHG.
    - **Criteria:** Varies by WFO/region. Can be routine daily, event-driven, or not issued. Decision made in coordination with users and regional office. Updated whenever necessary to depict latest hazards.
    - **Time:** Typically 5-7 AM local time, or 4-7 AM with Regional concurrence.
    - **Valid Time:** From issuance until next scheduled issuance/update, unless event-driven.
    - **Expiration Time:** 24 hours from routine issuance time (including updates), unless event-driven.
- **Technical Description:**
    - **UGC Type:** Zone (Z) code.
    - **MND Header:** "Hazardous Weather Outlook."
    - **Content:** Concise, non-technical terms for specific weather hazards for the first and second forecast periods, with brief discussion for Day Two through Seven. Includes general time, location, possible impact, and uncertainty. Does not duplicate specific short-fuse warnings/advisories but may refer to other long-fuse products.
        - **Headlines:** Optional (mandatory for tropical cyclones). Updated if headlines change.
        - **Geographic Locations:** Short description of covered area, can be segmented.
        - **Days of Week:** May include actual days (e.g., "Today").
        - **Content Guidelines By Weather Hazard:**
            - **Convective Weather:** Large hail, damaging winds, tornadoes. Includes SPC Categorical Convective Outlook info (Day 1, 2, 3 Risks). May mention strong convection and SPC Day 4-8 potential.
            - **Winter Weather:** Wind chill, freezing fog, snow, freezing rain, sleet. Mentions hazards in Day 3-7 if >=30% chance of meeting warning/advisory criteria. Mentions active watches/warnings/advisories for Days 1-2.
            - **Non Precipitation:** Strong winds, excessive heat, extreme cold, blowing dust/sand, freezing temps (growing season), dense fog. Mentions active watches/warnings/advisories for Days 1-2. Mentions hazards in Day 3-7 if >=30% chance of meeting warning/advisory criteria.
            - **Fire Weather:** Extremely dry conditions, strong gusty winds, dry thunderstorms. Mentions active Fire Weather Watches/Red Flag Warnings for Days 1-2. May include SPC Fire Weather Outlook (Day 1, 2).
            - **Flooding:** Inland flooding, small stream flood, life-threatening flood-prone areas.
            - **Marine:** High winds, high seas, high surf, coastal flooding, waterspout potential. Rip currents (NWSI 10-310). May omit hazards not directly affecting coastline/lakeshore.
            - **Tropical:** Headlines Day 1 Tropical Cyclone Watches/Warnings (NHC, CPHC, JTWC). Urges users to consult Hurricane Local Statements for detailed info. Consistent with NHC/WPC guidance for Days 2-7. Uses specific statement for potential impact in Days 2-5. No reference beyond official product time frame (currently 5 days).
        - **"Nil" Statement:** For routine HWO with no expected hazards (Day 1 and/or Days 2-7 sections). "No hazardous weather is expected at this time" or "The probability for widespread hazardous weather is low." No "nil" statements for specific hazard types.
        - **Spotter Instructions:** May include instructions for spotters/emergency managers (can be omitted if no hazardous weather expected).
        - **Grids and Graphics:** Supplemental info may be produced with Regional concurrence, consistent with text.
- **Updates:** Updated if forecast changes. Higher priority on updating relevant watch, warning, and advisory products. Corrected for format/grammatical errors.

---

## 4. Preliminary Local Storm Report (LSR)

- **Mission Connection:** Provides reported observations of hazardous weather events to SPC, RFCs, adjacent WFOs, public, media, and emergency managers. Primary basis for monthly _Storm Data_ publication.
- **Issuance Guidelines:**
    - **Software:** AWIPS LSR generation software (other software with Regional concurrence).
    - **Criteria:** For severe weather (tornadoes, waterspouts, large hail, thunderstorm/marine wind gusts, flash floods) and other events in Appendix B. Issued for events meeting/exceeding warning criteria. Hail reports >= 0.75 inches. May issue for events not exceeding warning criteria. As close to real-time as possible. Used to "summarize" reports during/at end of event. Events reported >7 days after occurrence included in monthly _Storm Data_.
    - **Time:** Non-scheduled, event-driven.
    - **Valid Time:** Upon issuance.
    - **Expiration Time:** Not applicable.
- **Technical Description:**
    - **UGC Type:** Not applicable.
    - **MND Header:** "PRELIMINARY LOCAL STORM REPORT."
    - **Content:** National standard format. Denotes measured (M), estimated (E), or unknown (U) origin for magnitude. All data fields at prescribed column. Includes: phenomenon type, date/time, event location (state, county, direction, distance from known site, lat/lon), source, damage, deaths, injuries, and remarks (plain English, full sentences). Delimiter "&&" for narrative summary.
    - **Preliminary Nature:** Final verified reports in monthly _Storm Data_. Refer to NDS directives for warning criteria.
- **Updates:** Not applicable for updates/amendments. New LSR issued for new/updated reports. Corrected for format/grammatical errors.

---

## 5. Mesoscale Discussion (MD)

- **Mission Connection:** Conveys location and meteorological reasoning for short-term hazardous weather concerns to CONUS WFOs, public, media, and specialized users.
- **Issuance Guidelines:**
    - **Software:** N-AWIPS graphics creation tool (NMAP) and SPC web-based product generation software.
    - **Criteria:** Depends on weather hazard type (see Section 6.3.3 for details).
    - **Time:** Non-scheduled, event-driven.
    - **Valid Time:** From issuance until next update time.
- **Technical Description:**
    - **UGC Type:** Zone (Z) code.
    - **MND Header:** "MESOSCALE DISCUSSION nnnn" (nnnn is a 4-digit number, reset to 0001 on Jan 1 at 0000 UTC).
    - **Content:** Alerts to short-term weather hazards. Types by weather hazard:
        - **Severe Potential:** Discusses convective trends and severe thunderstorm potential.
            - **Watch likely:** Issued 1-2 hours before Severe Thunderstorm/Tornado Watch issuance.
            - **Watch possible:** Organized severe convection possible, but Watch need unclear in 1-2 hours.
            - **Watch unlikely:** Isolated strong to severe convection ongoing/expected, but not meeting Watch criteria for coverage/duration in 1-2 hours. Also for potential convective watch monitoring when development is potentially severe but insufficient coverage/duration.
            - **Watch needed soon:** Organized severe convection may develop rapidly, Watch issued in 15-30 minutes.
            - **Probability of watch issuance:** Probability values (5, 20, 40, 60, 80, 95%).
        - **Watch Update:** Issued at least every 2-3 hours for active convective watches. Focuses on mesoscale/storm-scale features. Also issued 1-2 hours before expiration, detailing expected SPC actions. Begins "THE SEVERE WEATHER THREAT FOR (SEVERE THUNDERSTORM/TORNADO) WATCH nnnn CONTINUES."
        - **Heavy Snow:** For snowfall >=1 inch/hour for >=2 hours (<4000 ft MSL) or >=2 inches/hour for >=2 hours (>4000 ft MSL). May address precipitation trends and rare events.
        - **Freezing Rain:** For accumulations >=0.05 inch/hour for >=3 hours. May address precipitation type change.
        - **Blizzard:** For mesoscale blizzard conditions persisting >=3 hours.
        - **Snow Squall:** For snow squalls expected to last >=1 hour with visibility reductions of <=0.5 SM.
        - **Convective Outlook Upgrade:** Issued when upgrading Day 1 convective outlook risk to "moderate" or "high." Issued prior to 1300, 1630, 2000, or 0100 UTC outlook times, describing area to be upgraded. Refers to ensuing outlook discussion.
        - **Update to 0100 UTC Convective Outlook:** Issued when thunderstorms/severe thunderstorms develop after 0600 UTC in areas not adequately covered by 0100 UTC outlook and expected to continue for >=2 hours. Discusses convective threats not in 0100 UTC Day 1 Outlook.
- **Updates:** Issued as needed. No updates. Corrected for format/grammatical errors.
