# Packages

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd
import seaborn as sns
import folium

# For geocoding
from geopy.geocoders import Nominatim

import requests
from requests import get

# LSOA Spatial Data
lsoa_geo = gpd.read_file('../data/spatial_data/lsoa_data/Lower_Layer_Super_Output_Areas__December_2011__Boundaries_Full_Clipped__BFC__EW_V3.shp')

# LSOA Lookup Table
lsoa_lookup = pd.read_csv('../data/spatial_data/lsoa_data/LSOA_(2011)_to_LSOA_(2021)_to_Local_Authority_District_(2022)_Lookup_for_England_and_Wales_(Version_2).csv')

# Vehicle Registration
v_lsoa = pd.read_csv('../data/vehicle_data/df_VEH0125.csv')

v_lsoa = v_lsoa[v_lsoa['BodyType'] == 'Cars']
v_lsoa = v_lsoa[v_lsoa['Keepership'] == 'Private']
v_lsoa = v_lsoa[v_lsoa['LicenceStatus'] == 'Licensed']
v_lsoa = v_lsoa.replace('[c]', np.nan)
v_lsoa = v_lsoa.replace('[x]', np.nan)

cols_v = v_lsoa.columns.drop(['LSOA11CD', 'LSOA11NM', 'BodyType', 'Keepership', 'LicenceStatus'])
v_lsoa[cols_v] = v_lsoa[cols_v].apply(pd.to_numeric).astype('Int64')

v_lsoa_geo = pd.merge(lsoa_geo.loc[:, ['LSOA11CD', 'geometry']], v_lsoa, on='LSOA11CD', how='outer') # Merge Registration and Geo Data

v_bnes_lsoa = v_lsoa_geo[v_lsoa_geo['LSOA11CD'].isin(lsoa_lookup[lsoa_lookup['LAD22NM'] == 'Bath and North East Somerset'].LSOA11CD)] # Filter for BNES

v_bnes_lsoa = v_bnes_lsoa.to_crs('EPSG:4326') # Change CRS

v_bnes_lsoa.to_csv('../data/processed_data/v_bnes_lsoa.csv')

# EV Registration
ev_lsoa = pd.read_csv('../data/vehicle_data/df_VEH0145.csv')

ev_lsoa = ev_lsoa[ev_lsoa['Keepership'] == 'Private']
ev_lsoa = ev_lsoa.replace('[c]', np.nan)

cols_ev = ev_lsoa.columns.drop(['LSOA11CD', 'LSOA11NM', 'Fuel', 'Keepership'])
ev_lsoa[cols_ev] = ev_lsoa[cols_ev].apply(pd.to_numeric) # Convert cols to numeric

ev_lsoa_geo = pd.merge(lsoa_geo.loc[:, ['LSOA11CD', 'geometry']], ev_lsoa, on='LSOA11CD', how='outer') # Merge Registration and Geo Data

ev_bnes_lsoa = ev_lsoa_geo[ev_lsoa_geo['LSOA11CD'].isin(lsoa_lookup[lsoa_lookup['LAD22NM'] == 'Bath and North East Somerset'].LSOA11CD)] # Filter for BNES

ev_bnes_lsoa = ev_bnes_lsoa.to_crs('EPSG:4326') # Change CRS

bev_bnes_lsoa = ev_bnes_lsoa[(ev_bnes_lsoa.Fuel == 'Battery electric') | (ev_bnes_lsoa.Fuel.isnull())]
bev_bnes_lsoa.loc[bev_bnes_lsoa['Fuel'].isnull(), 'Fuel'] = 'Battery electric'
bev_bnes_lsoa.to_csv('../data/processed_data/bev_bnes_lsoa.csv')

phev_bnes_lsoa = ev_bnes_lsoa[(ev_bnes_lsoa.Fuel == 'Plug-in hybrid electric (petrol)') | (ev_bnes_lsoa.Fuel == 'Plug-in hybrid electric (diesel)') | (ev_bnes_lsoa.Fuel.isnull())]
phev_bnes_lsoa.loc[phev_bnes_lsoa['Fuel'].isnull(), 'Fuel'] = 'Plug-in hybrid electric'
phev_bnes_lsoa.to_csv('../data/processed_data/phev_bnes_lsoa.csv')

rex_bnes_lsoa = ev_bnes_lsoa[(ev_bnes_lsoa.Fuel == 'Range extended electric') | (ev_bnes_lsoa.Fuel.isnull())]
rex_bnes_lsoa.loc[rex_bnes_lsoa['Fuel'].isnull(),'Fuel'] = 'Range extended electric'
rex_bnes_lsoa.to_csv('../data/processed_data/rex_bnes_lsoa.csv')

tot_bnes_lsoa = ev_bnes_lsoa[(ev_bnes_lsoa.Fuel == 'Total') | (ev_bnes_lsoa.Fuel.isnull())]
tot_bnes_lsoa.loc[tot_bnes_lsoa['Fuel'].isnull(),'Fuel'] = 'Total'
tot_bnes_lsoa.to_csv('../data/processed_data/tot_bnes_lsoa.csv')

# Households
house_lsoa = pd.read_csv('../data/demographic_data/census_2021/LSOA_households.csv')

house_lsoa = house_lsoa.rename(columns={'Lower layer Super Output Areas Code':'LSOA21CD'}) # Rename Column Title to match style

house_lsoa = pd.merge(house_lsoa, lsoa_lookup.loc[:, ['LSOA11CD', 'LSOA21CD']], on = 'LSOA21CD', how='outer') # Add LSOA11CD to dataframe using lsoa_lookup

house_lsoa_geo = pd.merge(lsoa_geo.loc[:, ['LSOA11CD', 'geometry']], house_lsoa, on='LSOA11CD', how='outer') # Merge with Household counts with Geo Data

house_bnes_lsoa = house_lsoa_geo[house_lsoa_geo['LSOA11CD'].isin(lsoa_lookup[lsoa_lookup['LAD22NM'] == 'Bath and North East Somerset'].LSOA11CD)] # Filter for BNES

house_bnes_lsoa.to_csv('../data/processed_data/house_bnes_lsoa.csv')

# # FUNCTIONS

# def merge_with_geo_data(data, geo_data, key):
#     return pd.merge(geo_data.loc[:, [key, 'geometry']], data, on=key, how='outer')