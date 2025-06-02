# WFO SEVERE WEATHER PRODUCTS SPECIFICATION\*\*

## Table of Contents

1.  Introduction
2.  Severe Thunderstorm Warning (SVR)
    - 2.1 Mission Connection
    - 2.2 Issuance Guidelines
        - 2.2.1 Creation Software
        - 2.2.2 Issuance Criteria
        - 2.2.3 Issuance Time
        - 2.2.4 Valid Time
        - 2.2.5 Product Expiration Time
    - 2.3 Technical Description
        - 2.3.1 UGC Type
        - 2.3.2 MND Broadcast Line
        - 2.3.3 MND Header
        - 2.3.4 Content
            - 2.3.4.1 Thunderstorm Damage Threat Categorizations
        - 2.3.5 Format
    - 2.4 Updates, Amendments and Corrections
3.  Tornado Warning (TOR)
    - 3.1 Mission Connection
    - 3.2 Issuance Guidelines
        - 3.2.1 Creation Software
        - 3.2.2 Issuance Criteria
        - 3.2.3 Issuance Time
        - 3.2.4 Valid Time
        - 3.2.5 Product Expiration Time
    - 3.3 Technical Description
        - 3.3.1 UGC Type
        - 3.3.2 MND Broadcast Line
        - 3.3.3 MND Header
        - 3.3.4 Content
            - 3.3.4.1 Tornado Damage Threat Categorizations
        - 3.3.5 Format
    - 3.4 Updates, Amendments and Corrections
4.  Severe Weather Statement (SVS)
    - 4.1 Mission Connection
    - 4.2 Issuance Guidelines
        - 4.2.1 Creation Software
        - 4.2.2 Issuance Criteria
        - 4.2.3 Issuance Time
        - 4.2.4 Valid Time
        - 4.2.5 Product Expiration Time
    - 4.3 Technical Description
        - 4.3.1 UGC Type
        - 4.3.2 MND Broadcast Line
        - 4.3.3 MND Header
        - 4.3.4 Content
            - 4.3.4.1 Tornado and Thunderstorm Damage Threat Categorizations
        - 4.3.5 Format
            - 4.3.5.1 Event Tracking Number
    - 4.4 Updates, Amendments and Corrections
5.  Watch County Notification Message (WCN)
    _ 5.1 Mission Connection
    _ 5.2 Issuance Guidelines
    _ 5.2.1 Creation Software
    _ 5.2.2 Issuance Criteria
    _ 5.2.3 Issuance Time
    _ 5.2.4 Valid Time
    _ 5.2.5 Product Expiration Time
    _ 5.3 Technical Description
    _ 5.3.1 MND Broadcast Line
    _ 5.3.2 MND Header
    _ 5.3.3 Content
    _ 5.3.4 Format
    _ 5.3.4.1 Event Tracking Number
    _ 5.4 Updates, Amendments and Corrections
    APPENDIX A - Examples

---

## 1. Introduction

This procedural instruction describes the severe convective weather products issued by the National Oceanic and Atmospheric Administration’s (NOAA’s) National Weather Service (NWS) Weather Forecast Offices (WFOs). It provides guidelines associated with these products, specifies detailed content as needed, and outlines the format for each product type.

## 2. Severe Thunderstorm Warning (product category SVR)

### 2.1 Mission Connection

Severe Thunderstorm Warnings (SVRs) are issued to protect lives and property. WFO forecasters issue SVRs to provide the public, media, and emergency managers with advance notice of the combination of damaging wind gusts, large hail, and possible tornado development.

### 2.2 Issuance Guidelines

#### 2.2.1 Creation Software

WFOs will use WarnGen to issue SVRs.

#### 2.2.2 Issuance Criteria

WFOs should issue SVRs when there is radar or satellite indication and/or reliable reports of wind gusts equal to or in excess of 50 knots (58 miles per hour (mph)) and/or hail size of one inch (U.S. quarter-size) in diameter or larger. WFOs should issue SVRs for a convective cell or squall with little or no lightning that otherwise meets or exceeds the hail and/or wind warning criterion. A SVR should also be issued for potential tornado development in thunderstorms that also are forecasted to meet or exceed the minimum damaging wind gust and/or large hail criterion.

#### 2.2.3 Issuance Time

SVRs are non-scheduled, event-driven products.

#### 2.2.4 Valid Time

Valid times should be within 30 to 60 minutes of issuance. For thunderstorms that are expected to remain severe beyond the valid time of the original warning, WFOs should issue a new warning.

#### 2.2.5 Product Expiration Time

The product expiration time is the end of warning valid time.

### 2.3 Technical Description

SVRs will follow the Impact-Based Warning (IBW) format and content described in this section.

#### 2.3.1 Universal Geographic Code (UGC) Type

County (Zone for Alaska and parts of Pacific Region).

#### 2.3.2 Mass News Disseminator (MND) Broadcast Line

For states that require Emergency Alert System (EAS) activation, SVRs should include the broadcast line: “BULLETIN - EAS ACTIVATION REQUESTED”. If a state does not require EAS activation for SVRs, the broadcast line will read: “BULLETIN – IMMEDIATE BROADCAST REQUESTED”. The term “BULLETIN” is used when information is sufficiently urgent to warrant breaking into a normal broadcast.

#### 2.3.3 MND Header

The SVR MND header is “Severe Thunderstorm Warning”.

#### 2.3.4 Content

The following guidelines apply to the issuance of SVRs by WFOs:

**a. Writing Style:**

1.  SVRs will be in Letter Case with the exception of section headers, coded tag lines, and a special phrase for a Destructive storm(s) designed to be in Uppercase.
2.  SVRs will follow a standard bullet style format, with the third bullet providing sub-category information that distinguishes the hazard, source of information, and potential impacts.
3.  Locations used to identify the threatened areas should be larger towns and other familiar landmarks.
4.  Names of states and counties (or parts of counties) should be spelled out.
5.  Concise call-to-action (CTA) statements should be included.
6.  The WFO designated on-duty shift leader/supervisor may discontinue CTA statements in warnings during widespread severe weather outbreaks.
7.  Mileage markers may be used as reference points when a storm is occurring or forecast to move over a major highway but limited to five reference points or less.
8.  Named stadiums, arenas, or venues can be included in the locations section, as long as the residing city name is included as a separate location entry.

**b. Inclusion of Reports of Severe Events or Damage:**

1.  Recent credible reports of severe hail, wind gusts, and/or damage due to hail or high winds that are received and validated in a timely manner should be included.

**c. Pathcasts:**

1.  In general, warnings may contain ‘pathcasts’ (specific forecasts of location and arrival time) provided the forecaster has very high confidence in the movement (direction and speed) of the hazardous weather.
2.  Any ‘pathcast’ issued should use terms of uncertainty appropriate to the state of the science (e.g. ‘the severe thunderstorm will be near [location] around [time]’).
3.  Warnings that contain ‘pathcast’ information should be followed by frequent (approximately every 15 minutes) Severe Weather Statements (SVSs). This ensures that users receive the most recent information concerning the location and movement of the hazardous weather.

**d. Number and Divisions of Counties/Parishes:**

1.  WFOs should limit the number of counties/parishes in a SVR to 12 or less.
2.  If separating a county/parish into divisions, WFOs should use no more than a nine part division (i.e., northeast, east central, etc.) in coordination with state and local emergency managers and other partners.

**e. Severe Thunderstorm Moves Over Water:**

1.  If a severe thunderstorm moves over coastal waters, a Special Marine Warning (SMW) will be issued (see NWS Instruction (NWSI) 10-313 for details on SMWs and issuance criteria).

**f. Combining Warnings:**

1.  WFOs should keep Severe Thunderstorm and Flash Flood Warnings separate and consider utilizing CTA statements to indicate heavy rainfall in Severe Thunderstorm Warnings.

**g. Tornado Watch Information:**

1.  When a Tornado Watch is in effect for the warned area, WFOs should add this selection in the “PRECAUTIONARY/PREPAREDNESS ACTIONS” section, along with the additional pertinent CTA statements.
2.  The format for this information may either read as a generic statement (e.g., “A tornado watch remains in effect for the warned area.”), or the more explicit statement (e.g., “A tornado watch remains in effect until 10 PM EDT for Southeastern Alabama.”).
3.  This consideration is only valid for SVRs and their updates, through the SVS.

#### 2.3.4.1 Thunderstorm Damage Threat Categorizations

Considerable and Destructive warning categories will invoke the “THUNDERSTORM DAMAGE THREAT” coded tag line at the bottom of the warning and will note the category name. SVRs will include one of the three following impact-based categorizations based on the known or perceived damage threat.

- **a. Base (default; no associated coded tag line).** This categorization does not invoke the “THUNDERSTORM DAMAGE THREAT” coded tag, nor does the term “base” appear in the warning. This terminology refers to the default or uncategorized threshold for a warning. Minimum trigger wind/hail criteria for this level is the same as minimum severe wind (50 knots/58 mph) and/or hail size of one inch (U.S. quarter-size) in diameter.
- **b. Considerable.** The trigger for a Considerable warning is wind/hail criteria of at least 70 mph winds and/or hail size of one and three-quarter inches (golf ball-size) in diameter.
- **c. Destructive.** The trigger for a Destructive warning is wind/hail criteria of at least 80 mph winds and/or hail size of two and three-quarter inches (baseball-size) in diameter.

#### 2.3.5 Format

The SVR format will contain this information in the following order, through the IBW format (see Figure 1 below):

- **First Bullet** – Type of warning; and warning location(s);
- **Second Bullet** – Expiration time of warning;
- **Third Bullet** – Time; notation of “severe thunderstorm(s)” and the physical distance (in miles) from the closest location; storm motion. If edits of more than 10 mph or more than 45 degrees are required for the storm motion, the forecaster should adjust the track in WarnGen, rather than manually edit the text, in order to keep in agreement with TIME...MOT...LOC line.
    - \* Special insertion of a phrase that denotes the specific city/location or cities/locations, for instances when the “Destructive” Thunderstorm Damage Threat categorization is invoked. For a single storm, this line will read: `“THIS IS A DESTRUCTIVE STORM FOR [IMPACTED LOCATION(S)].”` For a line or cluster of storms, this line will read: `“THESE ARE DESTRUCTIVE STORMS FOR [IMPACTED LOCATION(S)].”`
    - The specifics on the inserted city/location names are as follows:
        - Manually added by the forecaster in all Uppercase text.
        - Limited to three specific locations, prioritizing the locations that are nearest to or will be most impacted by the destructive wind/hail threats.
        - Generalized to a locally-recognizable area if the threatened area is much larger than one, two, or even three cities/locations.
            - For largely rural areas or areas with many smaller localities, a combination of location names could be used (e.g., `“...MEDICINE LODGE AND RURAL AREAS OF BARBER COUNTY.”`) in all Uppercase text.
            - For all or portions of metropolitan areas expected to be impacted, use locally-recognizable names (e.g., `“...MUCH OF THE NORTHERN COLUMBUS METRO AREA, INCLUDING DUBLIN AND WORTHINGTON.”` or `“DUBLIN, WORTHINGTON, AND MUCH OF THE NORTHERN COLUMBUS METRO AREA.”`).
- **HAZARD (IBW Sub-Section 1).** Basis for warning (including recent credible reports if available); forecast or observed thunderstorm wind gusts and maximum hail sizes.
- **SOURCE (IBW Sub-Section 2).** Select one of these accepted source types (radar, trained weather spotters, law enforcement, emergency management, broadcast media, or public).
    - If a qualifying report of severe weather occurs from the warned storm within the time span of the valid area and time warning, it should be added in a separate sentence in this section, after the source type (e.g., “At 4:55 PM CDT, tennis ball size hail was reported 3 miles northeast of Emporia.”).
- **IMPACT (IBW Sub-Section 3).** This section contains predetermined statements that are based on the selected wind speed and/or hail size attribute. Default and designated alternative impact statements are as follows in Table 1. WFOs may make adjustments to the default statements based on local and situational considerations.

**Table 1: Impact Statements for Severe Thunderstorm Warnings**
| Severe Thunderstorm Attribute | Impact Statement(s) \[Use all numbered statements in order] |
| :----------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Wind - 60 mph** | 1) Expect damage to roofs, siding, and trees. <br> \* 1) Tree and power line damage is likely. <br> \* 2) Expect damage to some roofs, siding, carports, and fences. (this alternative option should include both statements) |
| **Wind - 70 mph** | 1) Expect considerable tree damage. <br> 2) Damage is likely to mobile homes, roofs, and outbuildings. <br> \* 1) Expect considerable tree and power line damage. <br> \* 2) Damage is likely to mobile homes, roofs, screen enclosures, carports, and outbuildings. |
| **Wind - 80 mph** | 1) Flying debris will be dangerous to those caught without shelter. <br> 2) Mobile homes will be heavily damaged. <br> 3) Expect considerable damage to roofs, windows, and vehicles. <br> 4) Extensive tree damage and power outages are likely. <br> \* (Alternative options are similar with "likely") |
| **Wind - 90 mph** | 1) You are in a life-threatening situation. <br> 2) Flying debris may be deadly to those caught without shelter. <br> 3) Mobile homes will be heavily damaged or destroyed. <br> 4) Homes and businesses will have substantial roof and window damage. <br> 5) Expect extensive tree damage and power outages. <br> \* (Alternative options are similar) |
| **Wind - 100 mph** | 1) You are in a life-threatening situation. <br> 2) Flying debris may be deadly to those caught without shelter. <br> 3) Mobile homes will be destroyed. <br> 4) Expect considerable damage to homes and businesses. <br> 5) Expect extensive tree damage and power outages. <br> \* (Alternative options are similar with "likely" and "widespread power outages") |
| **Hail - Quarter-Size (1.00") up to Ping Pong Ball-Size (1.50")** | 1) Damage to vehicles is expected. <br> \* 1) Damage to vehicles is likely. |
| **Hail - Golf Ball-Size (1.75") to Tennis Ball-Size (2.50")** | 1) People and animals outdoors will be injured. <br> 2) Expect damage to roofs, siding, windows, and vehicles. <br> \* 1) People and animals outdoors will likely be injured. <br> \* 2) Expect damage to roofs, siding, screen enclosures, windows, and vehicles. |
| **Hail - Baseball-Size (2.75 Inches) or greater** | 1) People and animals outdoors will be severely injured. <br> 2) Expect shattered windows, extensive damage to roofs, siding, and vehicles. <br> \* 1) Severe injuries are likely with hail this size. <br> \* 2) Expect shattered windows, extensive damage to roofs, siding, screen enclosures, and vehicles. |
_\* Note: Alternative impact statements may be utilized per Regional discretion._

- **Fourth Bullet** – Locations to be impacted during the warning (see Figure 1);
- **PRECAUTIONARY/PREPAREDNESS ACTIONS** – One or two short, concise, action-oriented CTA statements should be included. If CTAs are included under the PRECAUTIONARY/PREPAREDNESS ACTIONS, then two ampersands (&&) are required as a dissemination marker after the last CTA (see NWSI 10-1701, Section 5.5 for details on CTAs and markers). Credible reports of hail size and wind gusts, received in a timely manner, should be entered as part of the basis statement (first IBW sub-section “HAZARD”, under the third bullet), instead of the precautionary/preparedness actions section. If a Tornado Watch is in effect for the warned area, that information should be denoted in this section.
- **LAT...LON** – The warning area polygon as described by a series of latitude/longitude coordinates in decimal degrees with precision to hundredths (two (2) decimal places). The polygon will contain as few as three and as many as twenty vertices.
- **Partial County Alerting (PCA)** – For a partitioned county and a given warning, if a WFO invokes PCA for NOAA Weather Radio All Hazards (NWR) and the Emergency Alert System (EAS), a Partition Tag line will be located in the block below the double ampersand (&&) sign, immediately after the LAT...LON line and before the TIME...MOT...LOC line or IBW Tags. Each element of the Partition Tag Line will use a six digit code corresponding to the six digit Specific Area Message Encoder (SAME) location code, following the mandatory NWS and Federal Communications Commission (FCC) PSSCCC nomenclature, where P=partition number, SS=state and CCC=county. For non-partitioned counties, there is no Partition Tag line.
- **TIME...MOT...LOC** – The tracking information gives the location and movement of the event being tracked. Examples of such events could include the leading edge of a gust front or the leading edge of a hail core. The format (see Figure 1) includes the time of the observed event in Coordinated Universal Time (UTC), followed by a three digit direction of movement in degrees (direction the event is moving from), followed by speed of movement in knots, and finally the location of the event as a single latitude/longitude coordinate, or in the case of a line, two or more latitude/longitude coordinates.
- **IBW Coded Tag Lines** – This section details the required and optional IBW-coded tag lines according to each hazard type. These outputs are linked to options made within the WarnGen product generation application and are not editable in the warning text. All tag lines and information wording will be in Uppercase. The specifications for IBW-coded tag choices are as follows:
    - `TORNADO...POSSIBLE`
      (Optional; only one choice for this tag `[POSSIBLE]`. Select only if the severe thunderstorm is suspected to have the potential to produce a tornado but forecaster confidence does not warrant a Tornado Warning at the issuance time of the SVR). If this option is chosen, there must also be at least one of the other SVR criterion (wind and/or hail) selected.
    - `THUNDERSTORM DAMAGE THREAT...CONSIDERABLE/DESTRUCTIVE`
      (Will only appear for the selection of either of these two options `[CONSIDERABLE; DESTRUCTIVE]`, based on set minimum thresholds of either wind, hail, or both and will reflect the highest tier of damage threat. If the `DESTRUCTIVE` tag is invoked, then the `CONSIDERABLE` tag will not be used, as it is a lower tier category. When the `DESTRUCTIVE` tag for wind is used, it will place the phrase: `“This is an EXTREMELY DANGEROUS SITUATION.”` within the default CTA in the PRECAUTIONARY/PREPAREDNESS ACTIONS section.).
    - `HAIL THREAT...RADAR INDICATED/OBSERVED`
      (Required; based on selection from the “HAZARD” IBW sub-section). Can be a different selection from the Wind Threat coded tag selection. Can also be "Radar Indicated" despite including a validated report of severe hail within the warned area, if there is radar-based indication that larger hail is possible.
    - `MAX HAIL SIZE...X.XX IN`
      (Required; X.XX IN = value of maximum expected/reported hail size, in inches, from above in the “HAZARD” warning basis section; can be `0.00 IN` if no hail is expected or a lower value of hail size than the minimum SVR criteria, e.g., `<.75 IN`, if the minimum SVR wind criterion is met.).
    - `WIND THREAT...RADAR INDICATED/OBSERVED`
      (Required; based on selection from the “HAZARD” IBW sub-section). Can be a different selection from the Wind Threat coded tag. Can also be “Radar Indicated" despite including a validated severe wind speed report within the warned area, if there is radar-based indication that higher wind speeds are possible.
    - `MAX WIND GUST...XX MPH; XXX MPH for 100 MPH`
      (Required; XX MPH = value of maximum wind speed, in mph, from above in the “HAZARD” warning basis section, to the nearest 10 mph; can be `00 mph` if no thunderstorm wind gusts are expected or it can be a lower value than the minimum SVR thunderstorm wind gust criteria, e.g. `<50 MPH`, if the minimum SVR hail size criterion is met. A third digit would be added in the event of a 100 mph selection.).
    - _Note: IBW Coded Tag Order._ The `“TORNADO...POSSIBLE”` tag will appear at the top of the listing, in all cases, if selected. Otherwise, the hail-related tags will be first, then wind-related tags. This section also pertains to the updates to a SVR, under the SVS.

**Figure 1. Severe Thunderstorm Warning Format (Schematic)**

```
[WMO Header: WUaa5i cccc ddhhmm]
[AWIPS ID: SVRCCC]
[VTEC Line: STC001-002-ddhhmm- /k.aaa.cccc.pp.s.####.yymmddThhnnZB-yymmddThhnnZE/]

BULLETIN - EAS ACTIVATION (or IMMEDIATE BROADCAST) REQUESTED
Severe Thunderstorm Warning (...CORRECTED as required)
National Weather Service City State
time am/pm time_zone day mon dd yyyy

The National Weather Service in City has issued a

* Severe Thunderstorm Warning for...
  Portion County one in section State...(List warned counties)
  Portion County two in section State...(Number of counties will
  match number of counties in UGC Line)

* Until hhmm AM/PM time_zone (Expiration time of warning)

* At hhmm am/pm time_zone, warning basis, forward speed and
  direction.

  THIS IS A DESTRUCTIVE STORM/THESE ARE DESTRUCTIVE STORMS FOR
  [IMPACTED LOCATION/S]. (Upon invoking of the “Destructive”
  thunderstorm damage threat IBW tag only; use up to three
  city/location names).

  HAZARD...Warning basis elements (wind speed and/or hail size).
  SOURCE...(Choose one) Radar indicated, Trained weather spotters,
  Law enforcement, Emergency management, Broadcast media, or Public.
  IMPACT...Statements will populate based on the selected severe
  hazards in Table 1.

* Locations impacted include...
  Location #1, Location #2, Location #n. (n = variable number of
  locations).

PRECAUTIONARY/PREPAREDNESS ACTIONS...
(Call-to-Action statements).
(Tornado watch information, if valid for the warned area).

&&

LAT...LON (Required list of latitude/longitude coordinate pairs
outlining the forecaster-drawn warning area)
[Optional: PCA Partition Tag Line(s) if applicable, format PSSCCC]
TIME...MOT...LOC hhnnZ xxxDEG xxKT xxxx (lat/lon couplet(s))

TORNADO...POSSIBLE (will only appear if selected)
THUNDERSTORM DAMAGE THREAT...CONSIDERABLE/DESTRUCTIVE (will only appear if selected)
HAIL THREAT...RADAR INDICATED/OBSERVED
MAX HAIL SIZE...X.XX IN (X.XX = value of maximum expected hail size,
in diameter, from the “HAZARD” warning basis section)
WIND THREAT...RADAR INDICATED/OBSERVED
MAX WIND GUST...XX MPH (XX = value of maximum expected wind speed
from the “HAZARD” warning basis section to the nearest 10 mph. XXX
MPH for 100 mph selection)

$$
FORECASTER NAME/NUMBER (OPTIONAL)
```

### 2.4 Updates, Amendments and Corrections

Updates and amendments are not applicable. WFOs will correct SVRs for significant grammatical errors, format or dissemination code errors. Corrected warnings will have the same time in the MND Header and the same Event Tracking Number (ETN) in the Valid Time Event Code (VTEC) line as the original warning. WFOs should issue SVSs to inform users of erroneous counties removed from original warnings (either in the Federal Information Processing Standards (FIPS)/Zone UGC code or in the body of the warning).

## 3. Tornado Warning (product category TOR)

### 3.1 Mission Connection

Tornado Warnings (TOR) are issued to protect lives and property. WFO forecasters issue TORs to provide the public, media, and emergency managers with advance notice of tornadoes.

### 3.2 Issuance Guidelines

#### 3.2.1 Creation Software

WFOs will use WarnGen to issue TORs.

#### 3.2.2 Issuance Criteria

WFOs should issue TORs when there is radar indication and/or reliable reports of a tornado or developing tornado.

#### 3.2.3 Issuance Time

TORs are non-scheduled, event-driven products.

#### 3.2.4 Valid Time

Valid times should be 15 to 45 minutes from issuance. For a tornado expected to continue beyond the valid time of the original warning, WFOs should issue a new warning.

#### 3.2.5 Product Expiration Time

The product expiration time is the end of warning valid time.

### 3.3 Technical Description

TORs will follow the IBW format and content described in this section.

#### 3.3.1 UGC Type

County (Zone for Alaska Region and parts of Pacific Region).

#### 3.3.2 MND Broadcast Line

TORs will include the broadcast line “BULLETIN - EAS ACTIVATION REQUESTED”. The term “BULLETIN” is used when information is sufficiently urgent to warrant breaking into a normal broadcast.

#### 3.3.3 MND Header

The TOR MND header is “Tornado Warning”.

#### 3.3.4 Content

The following guidelines apply to the issuance of TORs by WFOs:

**a. Writing Style:**

1.  TORs will be in Letter Case with the exception of section headers, coded tag lines, the headline for a Tornado Emergency, special phrases for a Particularly Dangerous Situation, and special CTA statements designed to be in Uppercase.
2.  TORs will follow a standard bullet style format, with the third bullet providing sub-category information that distinguishes the hazard, source of information, and potential impacts.
3.  Locations used to identify the threatened areas should be larger towns and other familiar landmarks.
4.  Names of states and counties (or parts of counties) should be spelled out.
5.  Concise CTA statements should be included.
6.  The WFO designated on-duty shift leader/supervisor may discontinue CTA statements in warnings during widespread severe weather outbreaks.
7.  Mileage markers may be used as reference points when a storm is occurring or forecast to move over a major highway but limited to five reference points or less.
8.  Named stadiums, arenas, or venues can be included in the locations section, as long the residing city name is included as a separate location entry.

**b. Inclusion of Tornado or Tornado Damage Reports (3rd bullet):**

1.  Recent credible reports of a tornado, developing tornado, and/or recent credible reports of damage from a tornado that are received and validated in a timely manner should be included.

**c. Pathcasts:**

1.  In general, warnings may contain ‘pathcasts’ (specific forecasts of location and arrival time) provided the forecaster has very high confidence in the movement (direction and speed) of the hazardous weather.
2.  Any ‘pathcast’ issued should use terms of uncertainty appropriate to the state of the science (e.g., ‘the severe thunderstorm will be near [location] around [time]’).
3.  Warnings that contain ‘pathcast’ information should be followed by frequent (approximately every 15 minutes) SVSs. This ensures that users receive the most recent information concerning the location and movement of the hazardous weather.

**d. Number and Divisions of Counties/Parishes:**

1.  WFOs should limit the number of counties/parishes in a TOR to 12 or less.
2.  If separating a county/parish into divisions, WFOs should use no more than a nine part division (i.e., northeast, east central, etc.) in coordination with state and local emergency managers and other partners.

**e. Tornado Moves Over Water:**

1.  If a tornado moves over coastal waters, a SMW will be issued (see NWSI 10-313 for details on SMWs and issuance criteria).

**f. Combining Warnings:**

1.  WFOs should keep Tornado and Flash Flood Warnings separate. If these warnings have spatial and/or temporal overlap, WFOs should update the Tornado Warning area (polygon) to represent the forward movement and progression of that threat, while minimizing the warned area coincident with the Flash Flood Warning area, as appropriate. In these situations with simultaneous threats, CTAs should be chosen carefully in each warning to ensure they do not contradict.

#### 3.3.4.1 Tornado Damage Threat Categorizations

Considerable and Catastrophic warning categories will invoke the “TORNADO DAMAGE THREAT” coded tag line at the bottom of the warning and will note the category name. TORs will include one of the three following impact-based categorizations based on the known or perceived damage threat.

- **a. Base (default; no associated coded tag line).** This categorization does not invoke the “TORNADO DAMAGE THREAT” coded tag, nor does the term “base” appear in the warning. This terminology refers to the default or uncategorized threshold for a warning. However, a source of “OBSERVED” may be chosen for this level, without having to choose one of the two higher threat categorizations.
- **b. Considerable.** In situations when a tornado is occurring, whether from high confidence in evidential features in radar data and/or visual confirmation through reliable sources, WFOs have the option to express that the threat is considerable. Unlike the "catastrophic" categorization, a “considerable” categorization should be used in situations when there is lower confidence in the breadth or expanse of damage to interests and infrastructure out ahead of the tornado.
    1.  After the “third bullet” basis section, `“This is a PARTICULARLY DANGEROUS SITUATION. TAKE COVER NOW!”` line will appear. No changes will be made to the headline structure.
- **c. Catastrophic.** In exceedingly rare situations, when a severe threat to human life and catastrophic damage from a tornado is imminent or ongoing, WFOs have the option to invoke the “catastrophic” threat categorization with concurrence of the designated on-duty shift leader/supervisor. Given the gravity of the product, it should never be a single forecaster’s choice, but rather a team decision with input from all relevant office staff.
    1.  The headline addition of `“...TORNADO EMERGENCY FOR [IMPACTED LOCATION(S)]...”` will appear when this categorization is invoked.
    2.  The additional headline will be on a separate line directly following the date/time line in the MND Header and before the first line that begins “The National Weather Service in [WFO location] has issued a”. This headline will be preceded and followed by a three dot ellipsis.
    3.  `“TORNADO EMERGENCY for [IMPACTED LOCATIONS]”` is duplicated without ellipses in the last line of the third bullet, e.g., the basis statement of the warning. The “IMPACTED LOCATIONS” should be cities, towns, or well-known landmarks, and may include “AND SURROUNDING AREAS”. The term “RURAL AREAS” for a certain county or counties should only be used in addition to at least one named location (e.g. city, town, or well-known landmark).
    4.  Use of the "Catastrophic" damage threat categorization and thereby the “TORNADO EMERGENCY” terminology is appropriate for the tornadic situation if all of the following criteria are met:
        - a. Severe threat to human life is imminent or ongoing.
        - b. Catastrophic damage is imminent or ongoing.
        - c. Visual (1) or Radar (2):
            - (1) Reliable sources visually confirm tornado.
            - (2) Radar imagery (e.g., debris ball signature) strongly suggests the existence of a damaging tornado.

#### 3.3.5 Format

The TOR format will contain this information in the following order, through the IBW format (see Figure 2 below):

- **First Bullet** - Type of warning; warning location(s);
- **Second Bullet** - Expiration time of warning;
- **Third Bullet** - Time, basis for warning, storm motion. If edits of more than 10 mph or more than 45 degrees are required, the forecaster should adjust the track in WarnGen, rather than manually edit the text, in order to keep in agreement with TIME...MOT...LOC line.
- **HAZARD (IBW Sub-Section 1)**...Basis for warning (including recent credible reports, if available). Tornado will be mentioned first. When the tornado damage threat category is "Base" and the observed or maximum expected hail meets or exceeds SVR criteria, then the hail size will be included.
- **SOURCE (IBW Sub-Section 2)**...Select one of these accepted source types (radar, trained weather spotters, law enforcement, emergency management, broadcast media, or public). If a qualifying report of severe weather occurs from the warned storm within the time span of the valid area and time warning, it should be added in a separate sentence in this section, after the source type (e.g. “At 3:18 PM EDT, a tornado was reported 6 miles southwest of Meridian.”).
- **IMPACT (IBW Sub-Section 3)**...This section contains predetermined statements that are based on the selected attribute. Default and designated alternative impact statements are as follows in Table 2. WFOs may make adjustments to the default statements based on local and situational considerations.

**Table 2: Impact Statements for Tornado Warnings**
| Tornado Impact Attribute | Impact Statement(s) \[Use all numbered statements in order] |
| :----------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Landspout / Weak Tornado** | 1) Expect damage to mobile homes, roofs, and vehicles. <br> \* 1) Expect damage to mobile homes, roofs, screen enclosures, carports, vehicles and trees along the path of the tornado. |
| **"Base" (default)** | 1) Flying debris will be dangerous to those caught without shelter. <br> 2) Mobile homes will be damaged or destroyed. <br> 3) Damage to roofs, windows and vehicles will occur. <br> 4) Tree damage is likely. |
| **CONSIDERABLE** | 1) You are in a life-threatening situation. <br> 2) Flying debris may be deadly to those caught without shelter. <br> 3) Mobile homes will be destroyed. <br> 4) Considerable damage to homes, businesses, and vehicles is likely and complete destruction is possible. |
| **CATASTROPHIC** | 1) You are in a life-threatening situation. <br> 2) Flying debris may be deadly to those caught without shelter. <br> 3) Mobile homes will be destroyed. <br> 4) Considerable damage to homes, businesses, and vehicles is likely and complete destruction is possible. |
_\* Note: Alternative impact statements may be utilized per Regional discretion for Landspout / Weak Tornado only. The other statements are standard nationwide._

- **Fourth Bullet** – Locations to be impacted during the warning (see Figure 2);
- **PRECAUTIONARY/PREPAREDNESS ACTIONS** – One or two short, concise, action-oriented CTA statements should be included (unless designated on-duty shift leader/supervisor has discontinued call-to-action statements), starting with this Uppercase text phrase, `“TAKE COVER NOW!”`. If CTAs are included under the PRECAUTIONARY/PREPAREDNESS ACTIONS, then two ampersands (&&) are required as a dissemination marker after the last CTA (see NWSI 10-1701, Section 5.5 for details on CTAs and markers). Credible reports of tornadoes and associated damage should go in the basis statement (first IBW sub-section “HAZARD”, under the third bullet) instead of the precautionary/preparedness actions.
- **LAT...LON** – The warning area polygon as described by a series of latitude/longitude coordinates in decimal degrees with precision to hundredths (two (2) decimal places). The polygon will contain as few as three and as many as twenty vertices.
- **Partial County Alerting (PCA)** – For a partitioned county and a given warning, if a WFO invokes PCA for NWR and EAS, a Partition Tag line will be located in the block below the double ampersand (&&) sign, immediately after the LAT...LON line and before the TIME...MOT...LOC line or IBW Tags. Each element of the Partition Tag Line will use a six digit code corresponding to the six digit SAME location code, following the mandatory NWS and FCC PSSCCC nomenclature, where P=partition number, SS=state and CCC=county. For non-partitioned counties, there is no Partition Tag line.
- **TIME...MOT...LOC** – The tracking information gives the location and movement of the event being tracked. Examples of such events could include the low-level mesocyclone, or a report of the tornado location. The format includes the time of the observed event in UTC, followed by a three digit direction of movement in degrees (direction the event is moving from), followed by speed of movement in knots, and finally the location of the event as a single latitude/longitude coordinate.
- **IBW-Coded Tag Lines** – This section details the required and optional IBW-coded tag lines according to each hazard type. These outputs are linked to choices made within the WarnGen product generation application and are not editable in the warning text. All tag lines and information wording will be in Uppercase.
    - `TORNADO...RADAR INDICATED/OBSERVED`
      (Required first line, based on selection from the “HAZARD” IBW sub-section).
    - `TORNADO DAMAGE THREAT...CONSIDERABLE/CATASTROPHIC` (Will only appear for the selection of either of these two options (CONSIDERABLE; CATASTROPHIC)). The selection of `CONSIDERABLE` can be associated with either `RADAR INDICATED` or `OBSERVED` in the above tag and “Damaging tornado” will be placed in the HAZARD section, as the warning basis. The selection of `CATASTROPHIC` will assign `OBSERVED` in the above tag and “Deadly tornado” will be placed in the HAZARD section, as the warning basis. With either the tags, `CONSIDERABLE` or `CATASTROPHIC`, the phrase: `“This is a PARTICULARLY DANGEROUS SITUATION. TAKE COVER NOW!”` will also be placed in the third bullet, above the “HAZARD” section.
    - `MAX HAIL SIZE...X.XX INCH`
      (Required; X.XX INCH = value of maximum expected/reported hail size, in inches, from above in the “HAZARD” warning basis section; can be `0.00 IN` if no hail is expected or a lower value of hail size than the minimum SVR criteria, e.g., `<.75 IN.`.).

**Figure 2. Tornado Warning Format (Schematic)**

```
[WMO Header: WFaa5i cccc ddhhmm]
[AWIPS ID: TORCCC]
[VTEC Line: STC001-002-ddhhmm- /k.aaa.cccc.pp.s.####.yymmddThhnnZB-yymmddThhnnZE/]

BULLETIN - EAS ACTIVATION REQUESTED
Tornado Warning (... CORRECTED as required)
National Weather Service City State
time am/pm time_zone day mon dd yyyy

...TORNADO EMERGENCY FOR (CITY, CITIES, PORTION OF
COUNTY/COUNTIES)... (if applicable; IBW tornado damage threat tag
“Catastrophic” must be invoked/selected)

The National Weather Service in City has issued a

* Tornado Warning for...
  Portion County one in section State...(List warned counties)
  Portion County two in section State...(Number of Counties will
  match number of counties in UGC Line)

* Until hhmm AM/PM time_zone (Expiration time of warning)

* At hhmm am/pm time_zone, warning basis, forward speed and
  direction.

  TORNADO EMERGENCY for (same location/s as first headline). This is a
  PARTICULARLY DANGEROUS SITUATION. TAKE COVER NOW! (for the
  “Catastrophic” tornado damage threat IBW tag only)

  This is a PARTICULARLY DANGEROUS SITUATION. TAKE COVER NOW! (for the
  “Considerable” tornado damage threat IBW tag only)

  HAZARD...Warning basis statement (Tornado and; Damaging Tornado
  and; largest expected hail size - if chosen).
  SOURCE...(Choose one) Radar indicated, Trained weather spotters,
  Law enforcement, Emergency management, Broadcast media, or Public.
  IMPACT...Statements will populate based on the selected severe
  hazards in Table 2.

* Locations impacted include...
  Location #1, Location #2, Location #n. (n = variable number of
  locations).

PRECAUTIONARY/PREPAREDNESS ACTIONS...
(Call-to-Action statements, starting with "TAKE COVER NOW!").

&&

LAT...LON (Required list of latitude/longitude coordinate pairs
outlining the forecaster-drawn warning area)
[Optional: PCA Partition Tag Line(s) if applicable, format PSSCCC]
TIME...MOT...LOC hhnnZ xxxDEG xxKT xxxx (lat/lon couplet(s))

TORNADO...RADAR INDICATED; OBSERVED
TORNADO DAMAGE THREAT...CONSIDERABLE; CATASTROPHIC (will only appear if selected)
MAX HAIL SIZE...X.XX IN (X.XX = value of maximum expected hail size,
in diameter, from the “HAZARD” warning basis section)

$$
FORECASTER NAME/NUMBER (OPTIONAL)
```

### 3.4 Updates, Amendments and Corrections

Updates and amendments are not applicable. WFOs will correct TORs for significant grammatical errors, format or dissemination code errors. Corrected warnings will have the same time in the MND Header and the same ETN in the VTEC line as the original warning. WFOs should issue SVSs to inform users of erroneous counties removed from original warnings (either in the FIPS/Zone UGC code or in the body of the warning).

## 4. Severe Weather Statement (product category SVS)

### 4.1 Mission Connection

Severe Weather Statements (SVSs) provide the public and emergency managers with updated information for specific Severe Thunderstorm (SVR) and Tornado (TOR) Warnings. Updated information includes reports of observed severe weather. They also inform the public, media, and emergency managers when all or portions of a warning have been cancelled or have expired.

### 4.2 Issuance Guidelines

#### 4.2.1 Creation Software

WFOs will use WarnGen to issue SVSs.

#### 4.2.2 Issuance Criteria

The following guidelines apply to the issuance of SVSs by WFOs:

- **a. Cancellations** – WFOs should issue a SVS to provide notice a SVR or TOR has been cancelled for all or portions of the warning polygon.
- **b. Updates** – WFOs should issue SVSs at least once during the valid time of a SVR or TOR. During significant severe thunderstorm and tornado events, WFOs should issue more frequent SVS updates to keep the public informed of the progression of dangerous storms. This includes substantive changes to storm intensity and/or potential impacts (e.g., increase in hail size from quarter-sized to golf ball-sized; decrease in estimated wind gusts from 80 mph to 70 mph, radar-indicated tornado to a tornado confirmed by a visual report from a credible source), if the reports/observations are received within the valid time of the warning.
- **c. Corrections** – WFOs should issue a SVS to notify users of erroneous counties included in the original SVR or TOR (either in the FIPS/Zone UGC code or in the body of the warning) have been removed.
- **d. Expirations** – WFOs may issue a SVS to provide notice that a SVR or TOR has expired.

#### 4.2.3 Issuance Time

SVSs are non-scheduled, event-driven products.

#### 4.2.4 Valid Time

The valid time will be from the time of issuance to the warning expiration or cancellation time.

#### 4.2.5 Product Expiration Time

The product expiration time is no more than 15 minutes after the warning expiration or cancellation time.

### 4.3 Technical Description

SVSs will follow the IBW format and content described in this section.

#### 4.3.1 UGC Type

County (Zone for Alaska Region and parts of Pacific Region).

#### 4.3.2 MND Broadcast Line

None.

#### 4.3.3 MND Header

The SVS MND header is “Severe Weather Statement”.

#### 4.3.4 Content

The following Guidelines apply to the issuance of SVSs by WFOs.

- **a. Purpose:**
    1.  WFOs should issue SVSs to address the status of severe weather warnings.
    2.  WFOs will not use SVSs to expand in area or extend the valid time of TORs and SVRs.
    3.  If the threat of severe weather clears a significant portion of the warned area of a SVR or TOR during the valid period, such as a complete removal of a county or counties, forecasters should update the warning to reflect the changes.
- **b. Writing Style:**
    1.  SVSs will be in Letter Case with the exception of section headers, coded tag lines, the headline for a Tornado Emergency, special phrases for a Particularly Dangerous Situation or a Destructive storm(s), and special CTA statements designed to be in Uppercase.
    2.  The SVS will be in the IBW format for the section following the storm characteristics information (e.g., impact(s), timing, location, movement).
    3.  Locations used to identify the threatened areas should be larger towns and other familiar landmarks.
    4.  Names of states and counties (or parts of counties) should be spelled out.
    5.  Concise CTA statements should be included.
    6.  The WFO designated on-duty shift leader/supervisor may discontinue CTA statements in warnings during widespread severe weather outbreaks.
    7.  Mileage markers may be used as reference points when a storm is occurring or forecast to move over a major highway but limited to five reference points or less.
    8.  Named stadiums, arenas, or venues can be included in the locations section, as long the residing city name is included as a separate location entry.
- **c. Reports of Severe Events or Damage:**
    1.  Recent credible reports of a tornado, developing tornado, severe hail, or damaging wind that are received and validated in a timely manner should be included.
- **d. Pathcasts:**
    1.  In general, the SVS may contain 'pathcasts' (specific forecasts of location and arrival time) provided the forecaster has very high confidence in the direction and speed of the movement of the hazardous weather.
    2.  Any 'pathcast' issued should use terms of uncertainty appropriate to the state of the science (e.g., 'the tornadic storm will be near [location] around [time]').
    3.  In addition, SVSs with ‘pathcast' information should be frequently updated (approximately every 15 minutes). This ensures that users receive the most recent information concerning the location and movement of the hazardous weather.

#### 4.3.4.1 Tornado and Thunderstorm Damage Threat Categorizations

See Sections 2.3.4.1 (SVR) and 3.3.4.1 (TOR) for details on the IBW damage threat categorizations for Tornado and Severe Thunderstorm Warnings which are all applicable in continuation SVS updates.

#### 4.3.5 Format

(See Figure 3)

**Figure 3. Severe Weather Statement (SVS) Format (Schematic)**

```
[WMO Header: WWUS5i cccc ddhhmm]
[AWIPS ID: SVSccc]

Severe Weather Statement
National Weather Service City State
time am/pm time_zone day mon dd yyyy

[Segment for Cancellation - VTEC: /k.CAN.../]
STC001-ddhhmm-
/k.CAN.cccc.pp.s.####.yymmddThhnnZB-yymmddThhnnZE/
County A
time am/pm time_zone day mon dd yyyy

...SEVERE THUNDERSTORM or TORNADO WARNING HAS BEEN CANCELLED FOR
PORTION COUNTY A...

LAT...LON (Required list of latitude/longitude points outlining the
warning area - modified to remove those areas no longer threatened)
TIME...MOT...LOC hhnnZ xxxDEG xxKT xxxx (lat/lon coordinate(s))
$$

[Segment for Continuation/Update - VTEC: /k.CON.../]
STC003-ddhhmm-
/k.CON.cccc.pp.s.####.yymmddThhnnZB-yymmddThhnnZE/
County B
time am/pm time_zone day mon dd yyyy

...TORNADO EMERGENCY FOR (CITY/CITIES, PORTION/S OF COUNTY B)... (if
applicable; IBW tornado damage threat tag “Catastrophic” must be
invoked/selected)

...SEVERE THUNDERSTORM or TORNADO WARNING REMAINS IN EFFECT UNTIL
hhmm am/pm time_zone FOR COUNTY B...

At hhmm am/pm time_zone, warning basis, forward speed and direction.

[TORNADO EMERGENCY / PDS / DESTRUCTIVE STORM PHRASES AS APPLICABLE - see SVR/TOR specs]
  TORNADO EMERGENCY for (same location/s as first headline). This is a
  PARTICULARLY DANGEROUS SITUATION. TAKE COVER NOW! (for the
  “Catastrophic” tornado damage threat IBW tag only)

  This is a PARTICULARLY DANGEROUS SITUATION. TAKE COVER NOW! (for the
  “Considerable” tornado damage threat IBW tag only)

  THIS IS A DESTRUCTIVE STORM/THESE ARE DESTRUCTIVE STORMS for
  [IMPACTED LOCATION/S]. (upon invoking of the “Destructive”
  thunderstorm damage threat IBW tag only; use up to three
  city/location names)

HAZARD...Severe thunderstorm-based hazard(s) (hail and/or wind) or
tornado.
SOURCE...(Choose one) Radar indicated, Trained weather spotters, Law
enforcement, Emergency management, Broadcast media, or Public.
IMPACT...Statements will populate based on the selected severe
hazards in Table 1 (for SVR) or Table 2 (for TOR).

Locations impacted include...
Location #1, Location #2, Location #n. (n = variable number of
locations).

PRECAUTIONARY/PREPAREDNESS ACTIONS...
(Call-to-Action statements).
(Tornado watch information for Severe Thunderstorm Warnings only, if
valid for the warned area).

&&

LAT...LON (Required list of latitude/longitude points outlining the
warning area - modified to remove those areas no longer threatened)
TIME...MOT...LOC hhnnZ xxxDEG xxKT xxxx (lat/lon couplet(s))

[IBW Coded Tag Lines - as per SVR or TOR specifications]
(for a Tornado Warning)
TORNADO...RADAR INDICATED; OBSERVED
TORNADO DAMAGE THREAT...CONSIDERABLE; CATASTROPHIC
MAX HAIL SIZE...X.XX IN (X.XX = value of maximum expected hail size,
in diameter, from the “HAZARD” warning basis section)

(for a Severe Thunderstorm Warning)
TORNADO...POSSIBLE (will only appear if selected)
THUNDERSTORM DAMAGE THREAT...CONSIDERABLE/DESTRUCTIVE
HAIL THREAT...RADAR INDICATED/OBSERVED
MAX HAIL SIZE...X.XX IN (X.XX = value of maximum expected hail size,
in diameter, from the “HAZARD” warning basis section)
WIND THREAT...RADAR INDICATED/OBSERVED
MAX WIND GUST...XX MPH (XX = value of maximum expected wind speed
from the “HAZARD” warning basis section to the nearest 10 mph. XXX
MPH for 100 mph selection)

$$
FORECASTER NAME/NUMBER (OPTIONAL)
```

#### 4.3.5.1 Event Tracking Number (ETN)

The VTEC ETN (####) in the SVS will match the corresponding active SVR or TOR for updates and cancellations (See Figure 3).

### 4.4 Updates, Amendments and Corrections

Updates and amendments to the corresponding warning polygon should be provided as necessary through subsequent SVSs. WFOs will correct statements for format and grammatical errors as required.

## 5. Watch County Notification Message (product category WCN)

### 5.1 Mission Connection

WFOs will issue Watch County Notification Messages (WCN) to provide NOAA/NWS’ Storm Prediction Center (SPC), emergency managers, the media, and the public with a list of counties, parishes, independent cities, and marine zones in a convective watch area within their geographic area of responsibility.

### 5.2 Issuance Guidelines

#### 5.2.1 Creation Software

WFOs should use the Graphical Hazards Generation Editor (GHG) software to create WCNs.

#### 5.2.2 Issuance Criteria

Affected contiguous United States (CONUS) WFOs will issue initial WCNs after SPC issues the initial Watch Outline Update Message (WOU). WFOs in tropical areas outside the CONUS (OCONUS) will issue WCNs without a WOU from SPC and based on the potential of damaging winds, severe hail, and/or tornadoes. WFOs will issue updated WCNs to cancel, extend the valid time, or extend in area portions of one or more convective watches in their geographic area of responsibility.

#### 5.2.3 Issuance Time

WCNs are non-scheduled, event-driven products.

#### 5.2.4 Valid Time

WCNs are valid until the watch expiration time.

#### 5.2.5 Product Expiration Time

The expiration time is the same as the convective watch end time found in the initial WOU. WFOs may extend the convective watch expiration time in a WCN update after collaboration with SPC and the other WFOs in the watch area. Timely collaboration on a watch extended in time is particularly important so other WFOs in the watch area have the opportunity to cancel the watch from their counties.

### 5.3 Technical Description

WCNs will follow the format and content described in this section.

#### 5.3.1 UGC Type

County.

#### 5.3.2 MND Header

The WCN MND header is “WATCH COUNTY NOTIFICATION FOR WATCH nnnn”, where "nnnn" is the watch number. The watch number will be for the watch with the earliest issuance time if more than one watch is in effect for a WFO’s geographical area of responsibility.

#### 5.3.3 Content

WFOs and SPC are partners in the convective watch process. In the spirit of partnership, WFOs and SPC work toward a consensus convective watch area and duration before, during, and at the end of convective watches. This partnership is defined as collaboration. OCONUS WFOs are not required to collaborate with SPC.

WOUs will include all counties or parishes, independent cities and adjacent coastal water marine zones in a watch area (including nearshore zones out to 20 nautical miles and outer zones from 20-60 nautical miles). All Great Lakes marine zones within the United States will be included in convective watches. The initial WOU automatically generates the initial Watch County Notification Messages (WCN) for the affected WFOs. As a result of a collaboration call with those WFOs for which their CWA is included within a proposed convective watch, the counties or parishes, independent cities and marine zones listed in the initial WOU will match those listed in the initial WCNs issued by the affected WFOs.

- **a. Active Watches** – WFOs will issue updated WCNs to continue, cancel or extend in time or area portions of one or more active convective watches in their geographic area of responsibility.
- **b. New Watches** – WFOs will also issue updated WCNs to include new watches issued within their geographic area of responsibility while existing watches remain in effect.
- **c. Watch Extensions** – CONUS WFOs will collaborate with SPC and affected WFOs on counties, parishes, independent cities or marine zones added to the initial watch area, or extensions to the expiration time of the initial convective watch area.
- **d. Watch Replacements** – CONUS WFOs will collaborate with SPC and adjacent WFOs when counties, parishes, independent cities or marine zones are transferred from an existing convective watch to a new convective watch (e.g., watch replacement).
- **e. Watch Editing Consistency** – WFOs should ensure modifications to the convective watch area are consistent with modifications made by adjacent WFOs.
- **f. WCN Issuance Times** – WCNs should be issued by H+55 so that changes will be reflected in the WOU issued by SPC after the top of the hour.
- **g. Watch Cancellation/Expiration** – The final WCN for a particular convective watch will cancel or allow expiration of all remaining counties, parishes, independent cities and/or marine zones in the watch for their geographic area of responsibility.

#### 5.3.4 Format

(See Figure 4)

**Figure 4. Watch County Notification (WCN) Message Format (Schematic)**

```
[WMO Header: WWUS6i cccc ddhhmm]
[AWIPS ID: WCNCCC]

WATCH COUNTY NOTIFICATION FOR WATCH nnnn (or nnnn/nnnn if more than
one watch is in effect)
NATIONAL WEATHER SERVICE CITY STATE
time am/pm time_zone day mon dd yyyy

[VTEC Line: STC001-003-ddhhmm- /k.aaa.cccc.pp.s.####.yymmddThhnnZB-yymmddThhnnZE/]
(#### is ETN, matching SPC watch number)

[Segment Text - Varies based on action: Cancellation, Replacement, New, Extension, Continuation, Expiration]
Example Segments:
THE NATIONAL WEATHER SERVICE HAS CANCELLED SEVERE THUNDERSTORM (OR TORNADO WATCH) nnnn FOR THE FOLLOWING AREAS (If Cancellation Segment)

THE NATIONAL WEATHER SERVICE HAS ISSUED SEVERE THUNDERSTORM (OR TORNADO) WATCH nnnn UNTIL time am/pm time_zone WHICH REPLACES A PORTION OF SEVERE THUNDERSTORM (OR TORNADO) WATCH nnnn. THE NEW WATCH IS VALID FOR THE FOLLOWING AREAS (If Replacement Segment)

THE NATIONAL WEATHER SERVICE HAS ISSUED SEVERE THUNDERSTORM (OR TORNADO) WATCH nnnn IN EFFECT UNTIL time am/pm time_zone FOR THE FOLLOWING AREAS (If New Segment)

THE NATIONAL WEATHER SERVICE HAS EXTENDED SEVERE THUNDERSTORM (OR TORNADO) WATCH nnnn TO INCLUDE THE FOLLOWING AREAS UNTIL time am/pm time_zone (If Extension in Area Segment)

SEVERE THUNDERSTORM (OR TORNADO) WATCH NUMBER nnnn...PREVIOUSLY IN EFFECT UNTIL time am/pm time_zone...IS NOW IN EFFECT UNTIL time am/pm time_zone FOR THE FOLLOWING AREAS (If Extension in Time Segment)

SEVERE THUNDERSTORM (OR TORNADO) WATCH nnnn REMAINS VALID UNTIL time am/pm time_zone FOR THE FOLLOWING AREAS (If Continuation Segment)

THE NATIONAL WEATHER SERVICE WILL ALLOW SEVERE THUNDERSTORM (OR TORNADO) WATCH nnnn TO EXPIRE AT time am/pm time_zone FOR THE FOLLOWING AREAS (If Expiration Segment - issued prior to watch end time)

THE NATIONAL WEATHER SERVICE HAS ALLOWED SEVERE THUNDERSTORM (OR TORNADO) WATCH nnnn TO EXPIRE FOR THE FOLLOWING AREAS. (If Expiration Segment - issued after the watch end time)

SEVERE THUNDERSTORM (OR TORNADO) WATCH nnnn WILL BE ALLOWED TO EXPIRE (OR HAS EXPIRED). THE NEW WATCH IS VALID FOR THE FOLLOWING AREAS (If Replacement for Expired Segment)


IN STATE 1 THIS WATCH INCLUDES (or CANCELS or ALLOWS TO EXPIRE) n COUNTIES
LIST OF COUNTIES IN STATE 1 (OR PORTION OF STATE 1)

IN STATE 1 THIS WATCH INCLUDES (or CANCELS or ALLOWS TO EXPIRE) n INDEPENDENT CITIES
LIST OF INDEPENDENT CITIES IN STATE 1

THIS WATCH INCLUDES (or THIS CANCELS or ALLOWS TO EXPIRE) THE
FOLLOWING ADJACENT COASTAL WATERS
LIST OF MARINE ZONES

OTHER CITIES IN STATES 1 (OPTIONAL)

$$ (END OF SEGMENT)
```

#### 5.3.4.1 Event Tracking Number (ETN)

The VTEC ETN (####) will match the SPC watch number designated in the WOU, except for WCNs issued by WFOs in Pacific Region and Puerto Rico.

### 5.4 Updates, Amendments and Corrections

WFOs will update WCNs when counties, parishes, independent cities, or marine zones are cancelled or added from the watch or the watch valid time is extended. WFOs will correct WCNs for format and grammatical errors.

---

## APPENDIX A - Examples

This appendix provides the public with examples for each of the IBW categories for each of the WFO products. The examples illustrate various scenarios, including:

- **Severe Thunderstorm Warning (SVR):**
    - IBW Tag "Base" (with SPC Tornado Watch information included)
    - IBW Tag "Base" (Wind threshold only)
    - IBW Tag "Base" (Hail threshold only)
    - IBW Tag: “Tornado...Possible”
    - IBW Tag: “Tornado...Possible” with Wind threshold (only)
    - IBW Tag: “Considerable”
    - IBW Tag: “Considerable” (Wind threshold only)
    - IBW Tag: “Considerable” (Hail threshold only)
    - IBW Tag: “Destructive”
    - IBW Tag: “Destructive” (Wind threshold only)
    - IBW Tag: “Destructive” (Hail threshold only)
- **Tornado Warning (TOR):**
    - IBW Tag: “Base” (Radar indicated; no visual confirmation)
    - IBW Tag: “Base” (Visual confirmation)
    - IBW Tag: “Considerable” (Radar indicated; no visual confirmation)
    - IBW Tag: “Considerable” (Visual confirmation)
    - IBW Tag: “Catastrophic” TOR (Tornado Emergency - Radar indicated; no visual confirmation)
    - IBW Tag: “Catastrophic” TOR (Tornado Emergency - Visual confirmation)
- **Severe Weather Statement (SVS):**
    - IBW Tag: “Base” SVR
    - IBW Tag: “Base” SVR with partial cancellation
    - IBW Tag: “Base” SVR with inclusion of qualifying severe weather report
    - IBW Tag: “Considerable” SVR
    - IBW Tag: “Destructive” SVR
    - IBW Tag: “Base” TOR
    - IBW Tag: “Base” TOR with partial cancellation
    - TOR Expiration Statement
    - IBW Tag: “Considerable” TOR (Radar indicated; no visual and Visual confirmation)
    - IBW Tag: “Catastrophic” TOR (Tornado Emergency - Radar indicated; no visual and Visual confirmation)
- **Watch County Notification Message (WCN):**
    - Initial Issuance
    - Clearing Counties - One Watch in Effect
    - Watch Cancellation
    - Second Watch Issued While First Watch Remains in Effect
    - New Watch Issued Which Replaces an Old Watch and Partial Expiration of a Second Old Watch
    - Extending a Watch's Expiration Time for Selected Counties
    - Extension in Area
    - Partial Cancellation, Extension in Expiration Area and Time
