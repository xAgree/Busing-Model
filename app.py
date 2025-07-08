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

# Timedelta objects
Arrival_Rollover = pd.Timedelta(minutes=Arrival_TimeFrame)
Departure_Rollover = pd.Timedelta(minutes=Departure_TimeFrame)
Domestic_Rollover = pd.Timedelta(minutes=Domestic_TimeFrame)

# --- Streamlit App ---
st.title("Bus Requirement Calculator")

uploaded_schedule = st.file_uploader("Upload Linked Schedule Excel File", type=["xlsx"])
uploaded_pax_db = st.file_uploader("Upload Passenger DB Excel File", type=["xlsx"])

include_domestic = st.checkbox("Include Domestic Bus Operations", value=False)

if uploaded_schedule and uploaded_pax_db:
    # Read files
    df = pd.read_excel(uploaded_schedule, header=1)
    PDB = pd.read_excel(uploaded_pax_db)

    df_Arrival = df[["Flight No.", "Gate Start Time", "Gate End Time", "Stand", "Terminal", "Seats"]]
    df_Departure = df[["Flight No..1", "Gate Start Time.1", "Gate End Time.1", "Stand.1", "Terminal.1", "Seats.1"]]
    df_Departure = df_Departure.rename(columns={
        "Flight No..1": "Flight No.", "Gate Start Time.1": "Gate Start Time", 
        "Gate End Time.1": "Gate End Time", "Stand.1": "Stand", 
        "Terminal.1": "Terminal", "Seats.1": "Seats"
    })

    def insert_zeros(flight_no):
        if isinstance(flight_no, str):
            if len(flight_no) == 3:
                return flight_no[:2] + "00" + flight_no[2:]
            elif len(flight_no) == 4:
                return flight_no[:2] + "0" + flight_no[2:]
        return flight_no

    df_Arrival["Flight No."] = df_Arrival["Flight No."].apply(insert_zeros)
    df_Departure["Flight No."] = df_Departure["Flight No."].apply(insert_zeros)

    # Filter Remote and International
    df_Arrival = df_Arrival[df_Arrival["Stand"].str.contains("Remote", na=False)]
    df_Arrival = df_Arrival[df_Arrival["Terminal"].str.contains("International", na=False)]
    df_Arrival = df_Arrival[df_Arrival["Seats"] != 0]

    df_Departure = df_Departure[df_Departure["Stand"].str.contains("Remote", na=False)]
    df_Departure = df_Departure[df_Departure["Terminal"].str.contains("International", na=False)]
    df_Departure = df_Departure[df_Departure["Seats"] != 0]

    # Transit and Pax merge
    df_Departure["Transit Time"] = df_Arrival["Transit Time"] = 21.7

    df_Arrival = df_Arrival.merge(PDB[["Row Labels", "Total Pax"]], 
                              left_on="Flight No.", right_on="Row Labels", 
                              how="left")
    df_Arrival = df_Arrival.drop(columns="Row Labels")
    df_Arrival = df_Arrival.rename(columns={"Total Pax": "PAX"})

    df_Departure = df_Departure.merge(PDB[["Row Labels", "Total Pax"]], 
                              left_on="Flight No.", right_on="Row Labels", 
                              how="left")
    df_Departure = df_Departure.drop(columns="Row Labels")
    df_Departure = df_Departure.rename(columns={"Total Pax": "PAX"})

    # Setup arrival dataframe
    A = df_Arrival.copy()
    A['Trips_Needed'] = np.ceil(A['PAX'] / BUS_CAPACITY)
    A['Gate Start Time'] = pd.to_datetime(A['Gate Start Time'], errors='coerce')
    A['Gate End Time'] = pd.to_datetime(A['Gate End Time'], errors='coerce')
    A['Transit Time'] = pd.to_numeric(A['Transit Time'])
    A['max_trips'] = Arrival_TimeFrame // A['Transit Time']
    A['buses_needed_per_flight'] = np.ceil(A['Trips_Needed'] / A['max_trips'])

    start_time = A["Gate Start Time"].min().floor("D")
    end_time = A["Gate End Time"].max().replace(hour=23, minute=55)
    time_index = pd.date_range(start=start_time, end=end_time, freq="5min")
    A_bus_counts = pd.Series(0, index=time_index)

    for _, row in A.iterrows():
        start = row["Gate Start Time"]
        delta = Arrival_Rollover
        if row["Trips_Needed"] % 2 == 1:
            A_bus_counts.loc[start:start+delta] += row["buses_needed_per_flight"] - 1
            A_bus_counts.loc[start:start+(delta/2)] += 1
        else:
            A_bus_counts.loc[start:start+delta] += row["buses_needed_per_flight"]

    # Setup departure dataframe
    D = df_Departure.copy()
    D['Trips_Needed'] = np.ceil(D['PAX'] / BUS_CAPACITY)
    D['Gate Start Time'] = pd.to_datetime(D['Gate Start Time'], errors='coerce')
    D['Gate End Time'] = pd.to_datetime(D['Gate End Time'], errors='coerce')
    D['Transit Time'] = pd.to_numeric(D['Transit Time'])
    D['max_trips'] = Departure_TimeFrame // D['Transit Time']
    D['buses_needed_per_flight'] = np.ceil(D['Trips_Needed'] / D['max_trips'])
    D_bus_counts = pd.Series(0, index=time_index)

    for _, row in D.iterrows():
        start = row["Gate End Time"]
        delta = Departure_Rollover
        if row["Trips_Needed"] % 2 == 1:
            D_bus_counts.loc[start:start+delta] += row["buses_needed_per_flight"] - 1
            D_bus_counts.loc[start:start+(delta/2)] += 1
        else:
            D_bus_counts.loc[start:start+delta] += row["buses_needed_per_flight"]

    # Optional: domestic
    Do_bus_counts = pd.Series(0, index=time_index)
    if include_domestic:
        try:
            df_Domestic = pd.read_excel(uploaded_schedule, sheet_name="Dom Bus Operations")
            df_Domestic['Trips_Needed'] = np.ceil(df_Domestic['PAX'] / BUS_CAPACITY)
            df_Domestic['Gate Start Time'] = pd.to_datetime(df_Domestic['Gate Start Time'])
            df_Domestic['Transit Time'] = pd.to_numeric(df_Domestic['Transit Time'])
            df_Domestic['max_trips'] = Domestic_TimeFrame // df_Domestic['Transit Time']
            df_Domestic['buses_needed_per_flight'] = np.ceil(df_Domestic['Trips_Needed'] / df_Domestic['max_trips'])
            for _, row in df_Domestic.iterrows():
                start = row["Gate Start Time"]
                delta = Domestic_Rollover
                if row["Trips_Needed"] % 2 == 1:
                    Do_bus_counts.loc[start:start+delta] += row["buses_needed_per_flight"] - 1
                    Do_bus_counts.loc[start:start+(delta/2)] += 1
                else:
                    Do_bus_counts.loc[start:start+delta] += row["buses_needed_per_flight"]
        except Exception as e:
            st.warning(f"Could not load Domestic: {e}")

    # Combine
    df_result = pd.DataFrame({
        "Departure": D_bus_counts,
        "Arrival": A_bus_counts,
        "Domestic": Do_bus_counts
    })
    df_result["Total_Buses_Required"] = df_result.sum(axis=1)

    # Output
    peak = int(df_result["Total_Buses_Required"].max())
    st.success(f"✅ **Peak buses required:** {peak}")

    # Plot
    st.subheader("Bus Requirement Timeline")
    fig, ax = plt.subplots(figsize=(14, 6))
    df_result[["Departure", "Arrival", "Domestic"]].plot(
        kind="bar", stacked=True, ax=ax,
        color=["#1f77b4", "#ff7f0e", "#089404"], width=1
    )
    ax.set_xlabel("Time")
    ax.set_ylabel("Bus Count")
    ax.set_title("Buses in Use Over Time")
    ax.legend(loc="upper right")
    ax.xaxis.set_major_locator(plt.MaxNLocator(10))
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)

    

# Export DataFrame to Excel in memory
excel_buffer = BytesIO()
df_result.to_excel(excel_buffer, index=True, engine='openpyxl')
excel_buffer.seek(0)

# Create download button
st.download_button(
    label="📥 Download Time Series Excel",
    data=excel_buffer,
    file_name="Time_Series.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

