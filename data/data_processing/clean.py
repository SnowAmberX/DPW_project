import pandas as pd
import numpy as np

#compact.csv
df = pd.read_csv('compact.csv')

columns_to_keep = ['country', 'date', 'new_cases', 'new_cases_smoothed',
       'population', 'total_vaccinations', 'people_vaccinated',
       'new_deaths', 'new_deaths_smoothed', 'stringency_index']

df_clean = df[columns_to_keep].copy()

df_clean = df_clean.dropna(subset=['new_cases', 'new_cases_smoothed', 'new_deaths', 'new_deaths_smoothed'], how='any')

numeric_columns = ['total_vaccinations']

df_clean.fillna(0, inplace=True)

df_clean.to_csv('cleaned_compact.csv', index=False)

#vaccinations_us.csv
df = pd.read_csv('vaccinations_us.csv')

columns_to_keep = ['state', 'date', 'total_vaccinations', 
       'people_vaccinated', 'people_fully_vaccinated']

df_clean = df[columns_to_keep].copy()
numeric_columns = ['total_vaccinations']

for col in numeric_columns:
    if col in df_clean.columns:
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
        df_clean[col] = df_clean.groupby('state')[col].ffill()
for col in numeric_columns:
    if col in df_clean.columns:
        s = df_clean[col].copy()
        dif = s.diff()
        dif_corrected = dif.clip(lower=0)
        s_corrected = dif_corrected.cumsum() + s.iloc[0]
        if pd.notna(s.iloc[0]):
            s_corrected.iloc[0] = s.iloc[0]
        
        df_clean[col] = s_corrected
df_clean.to_csv('cleaned_vaccinations_us.csv', index=False)


#vaccinations_global.csv
df = pd.read_csv('vaccinations_global.csv')
columns_to_keep =  ['country', 'date', 'daily_vaccinations_smoothed', 'daily_people_vaccinated_smoothed',
       'daily_people_vaccinated_smoothed_per_hundred',
       'daily_vaccinations_smoothed_per_million',
       'total_vaccinations_interpolated', 'people_vaccinated_interpolated',
       'people_fully_vaccinated_interpolated', 'total_boosters_interpolated',
       'total_vaccinations_no_boosters_interpolated',
       'rolling_vaccinations_6m', 'rolling_vaccinations_6m_per_hundred',
       'rolling_vaccinations_9m', 'rolling_vaccinations_9m_per_hundred',
       'rolling_vaccinations_12m', 'rolling_vaccinations_12m_per_hundred']

df_clean = df[columns_to_keep].copy()
df_clean = df_clean.dropna(how='any')
df_clean.to_csv('cleaned_vaccinations_global.csv', index=False)

#vaccinations_manufacturer.csv
df = pd.read_csv('vaccinations_manufacturer.csv')
column_names = ['total_vaccinations']
for col in column_names:
    if col in df.columns:
        s = df[col].copy()
        dif = s.diff()
        dif_corrected = dif.clip(lower=0)
        s_corrected = dif_corrected.cumsum() + s.iloc[0]
        if pd.notna(s.iloc[0]):
            s_corrected.iloc[0] = s.iloc[0]
        df[col] = s_corrected
df.to_csv('cleaned_vaccinations_manufacturer.csv', index=False)


#vaccinations_age.csv
df = pd.read_csv('vaccinations_age.csv')

df_clean = df.dropna(how='any')
df_clean.to_csv('cleaned_vaccinations_age.csv', index=False)

#cases_deaths.csv
df = pd.read_csv('cases_deaths.csv')
columns_to_keep = ['country', 'date', 'new_cases', 'total_cases', 'new_deaths',
       'total_deaths', 'weekly_cases', 'weekly_deaths',
       'biweekly_cases',
       'biweekly_deaths', 'new_cases_per_million',
       'new_deaths_per_million', 'total_cases_per_million',
       'total_deaths_per_million', 'weekly_cases_per_million',
       'weekly_deaths_per_million', 'biweekly_cases_per_million',
       'biweekly_deaths_per_million', 'total_deaths_per_100k',
       'new_deaths_per_100k', 'new_cases_7_day_avg_right',
       'new_deaths_7_day_avg_right', 'new_cases_per_million_7_day_avg_right',
       'new_deaths_per_million_7_day_avg_right',
       'new_deaths_per_100k_7_day_avg_right', 'cfr', 'cfr_100_cases',
       'days_since_100_total_cases',
       'days_since_5_total_deaths', 'days_since_1_total_cases_per_million',
       'days_since_0_1_total_deaths_per_million']
df_clean = df[columns_to_keep].copy()
numeric_columns = ['total_cases', 
       'total_deaths', 'total_cases_per_million',
       'total_deaths_per_million', 'total_deaths_per_100k']

for col in numeric_columns:
    if col in df_clean.columns:
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
        df_clean[col] = df_clean.groupby('country')[col].ffill()
df_clean = df_clean.fillna(0)
for col in numeric_columns:
    if col in df_clean.columns:
        s = df_clean[col].copy()
        dif = s.diff()
        dif_corrected = dif.clip(lower=0)
        s_corrected = dif_corrected.cumsum() + s.iloc[0]
        if pd.notna(s.iloc[0]):
            s_corrected.iloc[0] = s.iloc[0]
        df_clean[col] = s_corrected

df_clean.to_csv('cleaned_cases_deaths.csv', index=False)


#merge into one single table
compact_df = pd.read_csv('cleaned_compact.csv')
cases_df = pd.read_csv('cleaned_cases_deaths.csv')
vacin_df = pd.read_csv('cleaned_vaccinations_global.csv')
df = compact_df.copy()
cols_to_use = ['country', 'date'] + [col for col in vacin_df.columns if col not in ['country', 'date']]
df = pd.merge(df, vacin_df[cols_to_use], on=['country', 'date'], how='left', suffixes=('', '_global'))

cols_to_use = ['country', 'date'] + [col for col in cases_df.columns if col not in ['country', 'date']]
df = pd.merge(df, cases_df[cols_to_use], on=['country', 'date'], how='left', suffixes=('', '_cases'))

df.to_csv('merged.csv', index=False)
