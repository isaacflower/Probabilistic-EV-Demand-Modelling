import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import datetime as dt

def clean_electric_nation_data(CC_transaction_data, GF_transaction_data, install_data):
    # Drop unneccesary columns
    install_data = install_data.drop(columns=['CarInstallDate', 'DCSProvider', 'Charger'])

    # Re-label PIVTypes
    PIVType_rename = {'Electric only (BEV)': 'BEV', 'Plug in Hybrid Electric Vehicle (PHEV)': 'PHEV', 'plug in Hybrid Electric Vehicle (PHEV)': 'PHEV', 'Range extender (REX)': 'REX'}
    install_data['PIVType'].replace(PIVType_rename, inplace=True)

    # Label Transactions with provider
    CC_transaction_data['Provider'] = 'CrowdCharge'
    GF_transaction_data['Provider'] = 'GreenFlux'

    # Combine transaction Data
    transaction_data = pd.concat([CC_transaction_data, GF_transaction_data])

    # Drop Unneccesary columns
    dropped_columns = [
        'CarKW',
        'CarKWh',
        'ParticipantCarkW',
        'ParticipantCarkWh',
        'Part_of_Managed_Group',
        'Weekday_or_Weekend',
        'Max_Current_Drawn_for_T',
        't_inactive_start',
        't_inactive_end',
        'Used_a_Timer',
        'Began_in_weekday_evening_peak',
        'Hot_Unplug',
        'T1_Managed',
        'T2_Managed',
        'Restricton T1',
        'Restriction T2',
        'PartOfManagedGroup',
        'WeekdayOrWeekend',
        'MaxAmpsDrawnForT',
        'tInactiveStart',
        'tInactiveEnd',
        'UsedATimer',
        'BeganInWeekdayEveningPeak',
        'HotUnplug',
        'Managed',
        'PercentageTimeInTransactionManaged',
        'ActiveCharging_Start',
        'ActiveChargingStart'
    ]

    transaction_data = transaction_data.drop(columns=dropped_columns)

    # Rename Columns
    transaction_data = transaction_data.rename(columns={'PluggedInTime':'SessionDurationM'})

    # Combine transaction and install Data
    session_df = pd.merge(transaction_data, install_data, on = 'ParticipantID')

    # Filter Abnormal consumption
    session_df= session_df[(session_df.ConsumedkWh > 0) & (session_df.ConsumedkWh <= 102.5)]

    # Only keep sessions in which the consumed energy is less than or equal to 2.5% higher than the nominal battery capacity
    session_df = session_df[session_df.ConsumedkWh < 1.025 * session_df.CarkWh]

    # Due to incomplete data on duration and end times, we must approximate Charging Duration and End Charge Time using ConsumedkWh
    # Assumes charging occurs at max charge rate for whole duration. This will almost always under estimate charging time due to rate decreases at high SoC.
    session_df['ApproxChargingDurationH'] = session_df.ConsumedkWh/session_df.CarkW 
    session_df = session_df.dropna(subset = ['ApproxChargingDurationH'])
    session_df['ApproxChargingDurationM'] = round(session_df.ApproxChargingDurationH * 60).astype('Int64')
    session_df['ApproxEndCharge'] = session_df.AdjustedStartTime + pd.to_timedelta(session_df.ApproxChargingDurationM, unit='minute')

    # Remove Session with missing Trial values
    session_df = session_df.dropna(subset = ['Trial'])

    # Remove sessions from trial 3 as the charging behaviour has been influenced
    session_df = session_df[session_df.Trial != 3]

    # Remove very short sessions that are less than 1 minute
    session_df = session_df[session_df.ApproxChargingDurationM >= 1]

    # Remove session durations that are longer than a week (10,080 seconds)
    session_df = session_df[session_df.SessionDurationM <= 10080]

    # Remove sessions with anomolous start and end times (i.e. before or after the trial window)

    # Remove Starttime that preceeds 2017
    session_df = session_df[session_df.AdjustedStartTime >= dt.datetime(2017,1,1,0,0,)]

    # Remove Starttime that exceeds 2018
    session_df = session_df[session_df.AdjustedStartTime <= dt.datetime(2019,1,1,0,0,)]

    # Set max charging duration to be session duration
    session_df['ApproxChargingDurationM'] = session_df[['ApproxChargingDurationM', 'SessionDurationM']].min(axis=1).astype('Int64')

    # Sort by AdjustedStartTime
    session_df = session_df.sort_values(by=['AdjustedStartTime'], ascending=True)

    session_df = session_df.reset_index(drop=True)

    return session_df, install_data

def split_sessions(session_df):
    # Separate split sessions from the rest of the sessions
    splits = session_df[session_df.ApproxEndCharge.dt.date > session_df.AdjustedStartTime.dt.date].copy()
    session_df_dropped = session_df[~ session_df.TransactionID.isin(splits.TransactionID.unique())].copy()

    # Spitth sessions and duplicate info
    split_df = pd.merge(pd.DataFrame({
        'TransactionID': list(splits.TransactionID) + list(splits.TransactionID),
        'AdjustedStartTime': list(splits.AdjustedStartTime) + list(splits.ApproxEndCharge.dt.floor(freq='1D')),
        'ApproxEndCharge': list(splits.AdjustedStartTime.dt.ceil(freq='1D') - dt.timedelta(seconds=1)) + list(splits.ApproxEndCharge)}),
        splits.drop(['AdjustedStartTime', 'ApproxEndCharge'], axis=1), on = 'TransactionID')
    
    # Adjust charging durations and consumedkWh accordingly
    split_df['ApproxChargingDurationM'] = round((split_df.ApproxEndCharge - split_df.AdjustedStartTime).dt.seconds/60).astype('Int64')
    split_df['ApproxChargingDurationH'] = ((split_df.ApproxEndCharge - split_df.AdjustedStartTime).dt.seconds/(60*60))
    split_df['ConsumedkWh'] = split_df.ApproxChargingDurationH * split_df.CarkW

    # Rejoin the split sessions with the remains sessions
    session_df_split = pd.concat([session_df_dropped, split_df])

    # Drop unneccesary columns
    dropped_columns = [
        'StartTime',
        'StopTime',
        'AdjustedStopTime',
        'SessionDurationM',
        'EndCharge',
        'ChargingDuration'
    ]

    session_df_split = session_df_split.drop(columns=dropped_columns)

    session_df_split = session_df_split.reset_index(drop=True)

    return session_df_split