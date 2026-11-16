VARIABLES = [
 dict(id="lst",name="Land Surface Temperature",category="Temperature",unit="°C",source="MODIS Terra MOD11A2 v6.1",spatial="1 km",temporal="8-day",coverage="2000–present",base=28,trend=.35,amp=9,noise=1.6),
 dict(id="pr",name="Precipitation",category="Hydrology",unit="mm/month",source="GPM IMERG",spatial="0.1°",temporal="30-min–monthly",coverage="1998–present",base=110,trend=-8,amp=95,noise=40),
 dict(id="sm",name="Soil Wetness",category="Land",unit="fraction",source="MERRA-2 M2TMNXLND",spatial="0.5°×0.625°",temporal="Monthly",coverage="1980–present",base=.45,trend=-.012,amp=.12,noise=.05),
 dict(id="ro",name="Runoff",category="Hydrology",unit="1e-5 kg m-2 s-1",source="MERRA-2 M2TMNXLND",spatial="0.5°×0.625°",temporal="Monthly",coverage="1980–present",base=2.2,trend=.1,amp=1.8,noise=.8),
 dict(id="o3",name="Tropospheric Ozone",category="Atmosphere",unit="DU",source="OMI/MLS L3",spatial="1°",temporal="Monthly",coverage="2004–present",base=32,trend=.5,amp=4,noise=1.5),
 dict(id="ndvi",name="Vegetation Index (NDVI)",category="Vegetation",unit="index",source="MODIS MOD13",spatial="1 km",temporal="16-day",coverage="2000–present",base=.55,trend=.012,amp=.15,noise=.04),
 dict(id="sst",name="Sea Surface Temperature",category="Ocean",unit="°C",source="MODIS Aqua",spatial="4 km",temporal="Monthly",coverage="2002–present",base=27,trend=.2,amp=1.5,noise=.4),
 dict(id="et",name="Evapotranspiration",category="Land",unit="mm/month",source="GLDAS Noah",spatial="0.25°",temporal="3-hourly–monthly",coverage="2000–present",base=65,trend=.4,amp=30,noise=9),
]
REGIONS = [
 dict(id="subarnarekha",name="Subarnarekha Basin",lat=22.8,lon=86.2),
 dict(id="delhi",name="Delhi NCR",lat=28.6,lon=77.2),
 dict(id="sahel",name="Sahel",lat=14.0,lon=0.0),
 dict(id="amazon",name="Amazon",lat=-3.0,lon=-60.0),
 dict(id="plains",name="Great Plains",lat=40.0,lon=-98.0),
]
def get(vid):
    return next((v for v in VARIABLES if v["id"] == vid), None)
