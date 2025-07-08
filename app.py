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
df_Departure = df_Departure.rename(columns={"Flight No..1" : "Flight No.", "Gate Start Time.1" : "Gate Start Time", "Gate End Time.1" : "Gate End Time", "Stand.1" : "Stand", "Terminal.1" : "Terminal", "Seats.1" : "Seats"})

def insert_zeros(flight_no):
    if isinstance(flight_no, str):
        if len(flight_no) == 3:
            return flight_no[:2] + "00" + flight_no[2:]
        elif len(flight_no) == 4:
            return flight_no[:2] + "0" + flight_no[2:]
    return flight_no

df_Arrival["Flight No."] = df_Arrival["Flight No."].apply(insert_zeros)
df_Departure["Flight No."] = df_Departure["Flight No."].apply(insert_zeros)

df_Arrival = df_Arrival[df_Arrival["Stand"].str.contains("Remote", na=False)]
df_Arrival = df_Arrival[df_Arrival["Terminal"].str.contains("International", na=False)]
df_Arrival = df_Arrival[df_Arrival["Seats"] != 0]
df_Departure = df_Departure[df_Departure["Stand"].str.contains("Remote", na=False)]
df_Departure = df_Departure[df_Departure["Terminal"].str.contains("International", na=False)]
df_Departure = df_Departure[df_Departure["Seats"] != 0]

df_Departure["Transit Time"] = 21.7
df_Arrival["Transit Time"] = 21.7

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

# Arrival
Arrival = df_Arrival
Arrival['Trips_Needed'] = np.ceil(Arrival['PAX'] / BUS_CAPACITY)
Arrival['Gate Start Time'] = pd.to_datetime(Arrival['Gate Start Time'], format='%d/%m/%Y %H:%M')
Arrival['Gate End Time'] = pd.to_datetime(Arrival['Gate End Time'], format='%d/%m/%Y %H:%M')
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

# Departure
Departure = df_Departure
Departure['Trips_Needed'] = np.ceil(Departure['PAX'] / BUS_CAPACITY)
Departure['Gate Start Time'] = pd.to_datetime(Departure['Gate Start Time'], format='%d/%m/%Y %H:%M')
Departure['Gate End Time'] = pd.to_datetime(Departure['Gate End Time'], format='%d/%m/%Y %H:%M')
Departure['Transit Time'] = pd.to_numeric(Departure['Transit Time'])

max_trips_D = Departure_TimeFrame // Departure['Transit Time']
Departure['buses_needed_per_flight'] = np.ceil(Departure['Trips_Needed'] / max_trips_D)

D_bus_counts = pd.Series(0, index=time_index)
for _, row in Departure.iterrows():
    start = row["Gate End Time"]
    delta = Departure_Rollover
    if row["Trips_Needed"] % 2 == 1:
        D_bus_counts.loc[start:start+delta] += row["buses_needed_per_flight"] - 1
        D_bus_counts.loc[start:start+(delta/2)] += 1
    else:
        D_bus_counts.loc[start:start+delta] += row["buses_needed_per_flight"]

# Domestic (optional)
Do_bus_counts = pd.Series(0, index=time_index)
if 'df_Domestic' in locals():
    Domestic = df_Domestic
    Domestic = pd.read_excel(file, sheet_name="Dom Bus Operations")
    Do_missing = [col for col in ["Transit Time", "PAX", "Gate Start Time", "Gate End Time"] if col not in Domestic.columns]
    if Do_missing:
        print(f"Missing columns in Domestic: {', '.join(Do_missing)}")

    Domestic['Trips_Needed'] = np.ceil(Domestic['PAX'] / BUS_CAPACITY)
    Domestic['Gate Start Time'] = pd.to_datetime(Domestic['Gate Start Time'], format='%d/%m/%Y %H:%M')
    Domestic['Gate End Time'] = pd.to_datetime(Domestic['Gate End Time'], format='%d/%m/%Y %H:%M')
    Domestic['Transit Time'] = pd.to_numeric(Domestic['Transit Time'])

    max_trips_Dom = Domestic_TimeFrame // Domestic['Transit Time']
    Domestic['buses_needed_per_flight'] = np.ceil(Domestic['Trips_Needed'] / max_trips_Dom)

    for _, row in Domestic.iterrows():
        start = row["Gate Start Time"]
        delta = Domestic_Rollover
        if row["Trips_Needed"] % 2 == 1:
            Do_bus_counts.loc[start:start+delta] += row["buses_needed_per_flight"] - 1
            Do_bus_counts.loc[start:start+(delta/2)] += 1
        else:
            Do_bus_counts.loc[start:start+delta] += row["buses_needed_per_flight"]

# Combine all operations
df = pd.DataFrame({
    "Departure": D_bus_counts,
    "Arrival": A_bus_counts,
    "Domestic": Do_bus_counts
})
df["Total_Buses_Required"] = df.sum(axis=1)

# Final Result: Print or export the total number of required buses
total_buses_needed = int(df["Total_Buses_Required"].max())
print(f"\nTotal buses required at peak time: {total_buses_needed}")

df.to_excel("Time_Series.xlsx", index=False)

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

