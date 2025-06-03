# cities.parquet has 18052 records
                          geom         name   pop_2010
0   POINT (-73.98143 40.76149)     New York  8175133.0
1  POINT (-118.24368 34.05223)  Los Angeles  3792621.0
2   POINT (-87.65005 41.85003)      Chicago  2695598.0
3   POINT (-73.94956 40.65009)     Brooklyn  2565635.0
4   POINT (-73.79745 40.75016)       Queens  2272771.0

# climdiv.parquet has 344 records
                                                     geom         lon        lat
iemid
WAC009  MULTIPOLYGON (((-117.04089 47.57309, -117.944 ... -118.003254  48.358277
FLC004  MULTIPOLYGON (((-81.80447 28.36182, -81.79089 ...  -81.535208  27.685818
KSC001  MULTIPOLYGON (((-101.98523 40.00328, -99.62537... -100.832495  39.566862
NEC005  MULTIPOLYGON (((-99.24169 41.74173, -98.29095 ...  -99.260241  41.213220
LAC009  MULTIPOLYGON (((-90.96357 30.34653, -90.85827 ...  -90.332299  29.692398

# conus.parquet has 1 records
                                                geom
0  MULTIPOLYGON (((-124.17566 40.81159, -124.1668...

# cwa.parquet has 123 records
                                                  geom  ...  region
wfo                                                     ...
ABR  MULTIPOLYGON (((-96.57259 46.02191, -96.2659 4...  ...      CR
AFC  MULTIPOLYGON (((179.64765 52.02626, 179.70442 ...  ...      PR
AFG  MULTIPOLYGON (((-166.93103 65.14315, -166.9569...  ...      PR
AJK  MULTIPOLYGON (((-132.07774 56.70303, -131.9020...  ...      PR
APX  MULTIPOLYGON (((-84.75324 45.78315, -84.72662 ...  ...      CR

# cwsu.parquet has 21 records
             name  ...        lat
cwsu               ...
ZAB   ALBUQUERQUE  ...  33.771912
ZAU       CHICAGO  ...  41.952254
ZBW       BOSTON   ...  43.479829
ZDC    WASHINGTON  ...  37.045634
ZDV        DENVER  ...  40.282091

# fema_regions.parquet has 10 records
                                  states                                               geom
region
1               [ME, NH, VT, MA, CT, RI]  MULTIPOLYGON (((-69.20438 47.45239, -69.22442 ...
3               [MD, PA, WV, DC, DE, VA]  MULTIPOLYGON (((-75.2985 37.963, -75.17281 38....
2                       [NY, NJ, PR, VI]  MULTIPOLYGON (((-67.87463 17.99977, -67.95356 ...
4       [NC, SC, GA, FL, AL, MS, TN, KY]  MULTIPOLYGON (((-80.35567 25.15823, -80.24945 ...
5               [IL, IN, OH, MI, WI, MN]  MULTIPOLYGON (((-86.98625 45.29866, -87.06606 ...
# iowawfo.parquet has 1 records
                                                geom
0  POLYGON ((-98.31889 42.88854, -98.46484 42.943...


# rfc.parquet has 13 records
               rfc_name basin_id  ...         lon        lat
rfc                               ...                       
ACR              Alaska    AKRFC  ... -152.144554  64.000383
KRF      Missouri Basin    MBRFC  ... -102.873613  43.746883
STR      Colorado Basin    CBRFC  ... -110.932460  37.259007
TUA  Arkansas-Red Basin    ABRFC  ...  -99.413631  36.285545
RSA   California-Nevada    CNRFC  ... -118.804034  38.242424

[5 rows x 5 columns]


# sfstns.parquet has 4407 records
                              name              geometry
sid                                                     
01M          BELMONT_TISHOMINGO_CO   POINT (-88.2 34.49)
04V          SAGUACHE_MUNI_AIRPORT  POINT (-106.17 38.1)
04W  HINCKLEY_FIELD_OF_DREAMS_ARPT   POINT (-92.9 46.02)
05F                     GATESVILLE   POINT (-97.8 31.42)
05U                         EUREKA  POINT (-116.01 39.6)


# ugcs_county.parquet has 3284 records
        cwa  ...        lat
ugc          ...           
UTC015  SLC  ...  38.996824
FMC002  GUM  ...   7.370092
FMC350  GUM  ...   8.561172
ASC020  PPG  ... -14.221924
CAC075  MTR  ...  37.755778

[5 rows x 4 columns]


# ugcs_firewx.parquet has 3552 records
        cwa  ...        lat
ugc          ...           
TXZ351  BRO  ...  26.966164
FLZ159  MLB  ...  27.396545
ARZ203  LZK  ...  36.183376
CAZ351  LOX  ...  34.516386
ARZ341  LZK  ...  34.419679

[5 rows x 4 columns]


# ugcs_zone.parquet has 4722 records
        cwa  ...        lat
ugc          ...           
TXZ451  BRO  ...  26.900696
AMZ088  NH2  ...  20.500000
AKZ328  AJK  ...  55.501211
PZZ575  MTR  ...  36.903465
NCZ076  RAH  ...  35.475027

[5 rows x 4 columns]


# us_states.parquet has 56 records
                                                         geom  ...        lat
state_abbr                                                     ...           
KY          MULTIPOLYGON (((-82.67075 37.13927, -82.72683 ...  ...  37.526672
LA          MULTIPOLYGON (((-89.39561 29.15126, -89.42897 ...  ...  31.072289
ME          MULTIPOLYGON (((-69.00669 44.28041, -69.04583 ...  ...  45.380957
MD          MULTIPOLYGON (((-76.21093 39.00784, -76.24268 ...  ...  39.050152
MA          MULTIPOLYGON (((-71.28619 41.7628, -71.3407 41...  ...  42.256607

[5 rows x 3 columns]


