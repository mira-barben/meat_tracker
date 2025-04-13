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
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.normalize()  
    return df

# Save the data to a CSV
def save_data(df):
    df.to_csv('meat_eating_log.csv', index=False)

# Function to update meat-eating log
def add_meat_day(date, df):
    # Add new meat day entry (allowing for multiple entries per day)
    date = pd.to_datetime(date).normalize()  
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
#st.subheader("Timeseries")
if not df.empty:
    # Ensure the 'date' column is datetime and set it as the index
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    # Resample by day and count the meat-eating events
    df_resampled = df.resample('D').size()

    # Set start date of logger
    start_date = pd.to_datetime('2025-02-10')  
    all_dates = pd.date_range(start=start_date, end=datetime.today(), freq='D')
    df_resampled = df_resampled.reindex(all_dates, fill_value=0)  # Fill missing dates with 0

    # Calculate streaks
    today = pd.Timestamp(datetime.today().date())

    # Helper: get days with meat
    meat_days = df_resampled[df_resampled > 0]

    # --- Current streak ---
    if df_resampled.index[-1] == today and df_resampled[today] > 0:
        current_streak = 0
    else:
        streak = 0
        for date in reversed(df_resampled.index):
            if date > today:
                continue
            if df_resampled[date] == 0:
                streak += 1
            else:
                break
        current_streak = streak

    # --- Longest streak ---
    longest_streak = 0
    streak = 0
    for val in df_resampled.values:
        if val == 0:
            streak += 1
            longest_streak = max(longest_streak, streak)
        else:
            streak = 0

    # Display achievements next to the chart
    col1, col2 = st.columns(2)

    with col1:
        st.metric("🥗 Days without meat", f"{current_streak} days")

    with col2:
        st.metric("🏆 Longest streak", f"{longest_streak} days")


    plt.figure(figsize=(10, 6))
    plt.plot(df_resampled.index, df_resampled.values, marker='o', color='green', label='Meat-eating events')
    plt.yticks(range(0, int(df_resampled.max()) + 1))

    # Axis formatting
    plt.xlabel("Time")
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


