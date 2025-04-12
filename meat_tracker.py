import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Create or load the dataset
def load_data():
    try:
        # Try loading existing data
        df = pd.read_csv('meat_eating_log.csv')
    except FileNotFoundError:
        # Create an empty DataFrame if the file doesn't exist
        df = pd.DataFrame(columns=['date'])
    
    # Ensure the 'date' column is of datetime type and strip any time information
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.normalize()  # Stripping time part
    return df

# Save the data to a CSV
def save_data(df):
    df.to_csv('meat_eating_log.csv', index=False)

# Function to update meat-eating log
def add_meat_day(date, df):
    # Add new meat day entry (allowing for multiple entries per day)
    # Make sure the date has no time part
    date = pd.to_datetime(date).normalize()  # Normalize to ensure no time component
    new_row = pd.DataFrame({'date': [date]})
    df = pd.concat([df, new_row], ignore_index=True)
    return df

# Streamlit UI
st.title("Meat-Eating Tracker")
st.sidebar.header("Tracker Settings")

# Load existing data
df = load_data()

# Sidebar to add a new meat day
meat_day_input = st.sidebar.date_input("Select the date you ate meat")
meat_events_input = st.sidebar.number_input("How many times did you eat meat on this day?", min_value=1, step=1)

if st.sidebar.button("Log"):
    # Add the meat-eating events for that day
    for _ in range(meat_events_input):
        df = add_meat_day(meat_day_input, df)
    save_data(df)
    st.sidebar.success(f"{meat_events_input} meat-eating events added for {meat_day_input}!")

# Display the data
st.subheader("Timeseries")
if not df.empty:
    # Ensure the 'date' column is datetime and set it as the index
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    # Resample by day and count the meat-eating events
    df_resampled = df.resample('D').size()

    # Ensure we have data starting from March 2025 (or earliest date)
    start_date = pd.to_datetime('2025-03-01')  # Start date can be changed as required
    all_dates = pd.date_range(start=start_date, end=datetime.today(), freq='D')
    df_resampled = df_resampled.reindex(all_dates, fill_value=0)  # Fill missing dates with 0

    plt.figure(figsize=(10, 6))
    plt.plot(df_resampled.index, df_resampled.values, marker='o', color='blue', label='Meat-eating events')

    # Make sure the Y-axis has whole numbers
    plt.yticks(range(0, int(df_resampled.max()) + 1))

    # Ensure dates on the x-axis are formatted properly (without time)
    plt.xlabel("Date")
    plt.ylabel("Number of Meat-Eating Events")
    plt.xticks(rotation=45)
    plt.tight_layout()

    st.pyplot(plt)

# Add a reset button in the sidebar to clear data
if st.sidebar.button("Reset Data"):
    # Clear the meat_eating_log.csv file by overwriting it with an empty DataFrame
    df = pd.DataFrame(columns=['date'])
    save_data(df)
    st.sidebar.success("Data has been reset!")

