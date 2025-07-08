# app.py

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO

# Constants
BUS_CAPACITY = 60
Arrival_TimeFrame = 45
Departure_TimeFrame = 45
Domestic_TimeFrame = 15

Arrival_Rollover = pd.Timedelta(minutes=Arrival_TimeFrame)
Departure_Rollover = pd.Timedelta(minutes=Departure_TimeFrame)
Domestic_Rollover = pd.Timedelta(minutes=Domestic_TimeFrame)

# --- Streamlit App ---
st.title("Bus Requirement Calculator")

uploaded_schedule = st.file_uploader("Upload Linked Schedule Excel File", type=["xlsx"])
uploaded_pax_db = st.file_uploader("Upload Passenger DB Excel File", type=["xlsx"])

include_domestic = st.checkbox("Include Domestic Bus Operations", value=False)

def insert_zeros(flight_no):
    if isinstance(flight_no, str):
        if len(flight_no) == 3:
            return flight_no[:2] + "00" + flight_no[2:]
        elif len(flight_no) == 4:
            return flight_no[:2] + "0" + flight_no[2:]
    return flight_no

if uploaded_schedule and uploaded_pax_db:
    try:
        # Read data
        df = pd.read_excel(uploaded_schedule, header=1)
        PDB = pd.read_excel(uploaded_pax_db)

        df_Arrival = df[["Flight No.", "Gate Start Time", "Gate End Time", "Stand", "Terminal", "Seats"]]
        df_Departure = df[["Flight No..1", "Gate Start Time.1", "Gate End Time.1", "Stand.1", "Terminal.1", "Seats.1"]]
        df_Departure = df_Departure.rename(columns={
            "Flight No..1": "Flight No.",
            "Gate Start Time.1": "Gate Start Time",
            "Gate End Time.1": "Gate End Time",
            "Stand.1": "Stand",
            "Terminal.1": "Terminal",
            "Seats.1": "Seats"
        })

        df_Arrival["Flight No."] = df_Arrival["Flight No."].apply(insert_zeros)
        df_Departure["Flight No."] = df_Departure["Flight No."].apply(insert_zeros)

        df_Arrival = df_Arrival[df_Arrival["Stand"].str.contains("Remote", na=False)]
        df_Arrival = df_Arrival[df_Arrival["Terminal"].str.contains("International", na=False)]
        df_Arrival = df_Arrival[df_Arrival["Seats"] != 0]
        df_Departure = df_Departure[df_Departure["Stand"].str.contains("Remote", na=False)]
        df_Departure = df_Departure[df_Departure["Terminal"].str.contains("International", na=False)]
        df_Departure = df_Departure[df_Departure["Seats"] != 0]

        df_Arrival["Transit Time"] = 21.7
        df_Departure["Transit Time"] = 21.7

        df_Arrival = df_Arrival.merge(PDB[["Row Labels", "Total Pax"]],
                                      left_on="Flight No.", right_on="Row Labels", how="left")
        df_Arrival.drop(columns="Row Labels", inplace=True)
        df_Arrival.rename(columns={"Total Pax": "PAX"}, inplace=True)

        df_Departure = df_Departure.merge(PDB[["Row Labels", "Total Pax"]],
                                          left_on="Flight No.", right_on="Row Labels", how="left")
        df_Departure.drop(columns="Row Labels", inplace=True)
        df_Departure.rename(columns={"Total Pax": "PAX"}, inplace=True)

        # ARRIVAL
        Arrival = df_Arrival.copy()
        Arrival['Trips_Needed'] = np.ceil(Arrival['PAX'] / BUS_CAPACITY)
        Arrival['Gate Start Time'] = pd.to_datetime(Arrival['Gate Start Time'], errors='coerce')
        Arrival['Gate End Time'] = pd.to_datetime(Arrival['Gate End Time'], errors='coerce')
        Arrival['Transit Time'] = pd.to_numeric(Arrival['Transit Time'])

        max_trips_A = Arrival_TimeFrame // Arrival['Transit Time']
        Arrival['buses_needed_per_flight'] = np.ceil(Arrival['Trips_Needed'] / max_trips_A)

        start_time = Arrival["Gate Start Time"].min().floor("D")
        end_time = Arrival["Gate End Time"].max().replace(hour=23, minute=55)
        time_index = pd.date_range(start=start_time, end=end_time, freq="5min")
        A_bus_counts = pd.Series(0, index=time_index)

        for _, row in Arrival.iterrows():
            start = row["Gate Start Time"]
            delta = Arrival_Rollover
            if row["Trips_Needed"] % 2 == 1:
                A_bus_counts.loc[start:start+delta] += row["buses_needed_per_flight"] - 1
                A_bus_counts.loc[start:start+(delta/2)] += 1
            else:
                A_bus_counts.loc[start:start+delta] += row["buses_needed_per_flight"]

        # DEPARTURE
        Departure = df_Departure.copy()
        Departure['Trips_Needed'] = np.ceil(Departure['PAX'] / BUS_CAPACITY)
        Departure['Gate Start Time'] = pd.to_datetime(Departure['Gate Start Time'], errors='coerce')
        Departure['Gate End Time'] = pd.to_datetime(Departure['Gate End Time'], errors='coerce')
        Departure['Transit Time'] = pd.to_numeric(Departure['Transit Time'])

        max_trips_D = Departure_TimeFrame // Departure['Transit Time']
        Departure['buses_needed_per_flight'] = np.ceil(Departure['Trips_Needed'] / max_trips_D)

        D_bus_counts = pd.Series(0, index=time_index)
        for _, row in Departure.iterrows():
            start = row["Gate End Time"]
            delta = Departure_Rollover
            if row["Trips_Needed"] % 2 == 1:
                D_bus_

