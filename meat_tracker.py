import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# --- USERNAME SETUP ---
username = st.sidebar.text_input("Enter your username to access your data")

# --- LOAD AND SAVE FUNCTIONS ---
def load_data(username):
    filename = f"data_{username}.csv"
    try:
        df = pd.read_csv(filename)
    except FileNotFoundError:
        df = pd.DataFrame(columns=['date'])
    
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.normalize()
    return df

def save_data(df, username):
    filename = f"data_{username}.csv"
    df.to_csv(filename, index=False)

def add_meat_day(date, df):
    date = pd.to_datetime(date).normalize()
    new_row = pd.DataFrame({'date': [date]})
    df = pd.concat([df, new_row], ignore_index=True)
    return df

# --- MAIN APP ---
st.title("Meat-Eating Tracker")
st.sidebar.header("Tracker Settings")

if username:
    # Load user data
    df = load_data(username)

    # Sidebar input for logging
    meat_day_input = st.sidebar.date_input("Select the date you ate meat")
    meat_events_input = st.sidebar.number_input("How many times did you eat meat on this day?", min_value=1, step=1)

    if st.sidebar.button("Log"):
        for _ in range(meat_events_input):
            df = add_meat_day(meat_day_input, df)
        save_data(df, username)
        st.sidebar.success(f"{meat_events_input} meat-eating events added for {meat_day_input}!")

    # --- Display Data ---
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df_resampled = df.resample('D').size()

        start_date = pd.to_datetime('2025-02-10')  
        all_dates = pd.date_range(start=start_date, end=datetime.today(), freq='D')
        df_resampled = df_resampled.reindex(all_dates, fill_value=0)

        today = pd.Timestamp(datetime.today().date())

        # Current streak
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

        # Longest streak
        longest_streak = 0
        streak = 0
        for val in df_resampled.values:
            if val == 0:
                streak += 1
                longest_streak = max(longest_streak, streak)
            else:
                streak = 0

        col1, col2 = st.columns(2)
        with col1:
            st.metric("🥗 Days without meat", f"{current_streak} days")
        with col2:
            st.metric("🏆 Longest streak", f"{longest_streak} days")

        # Plotting
        plt.figure(figsize=(10, 6))
        plt.plot(df_resampled.index, df_resampled.values, marker='o', color='green', label='Meat-eating events')
        plt.yticks(range(0, int(df_resampled.max()) + 1))
        plt.xlabel("Time")
        plt.ylabel("Number of Meat-Eating Events")
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(plt)

        # Download Button
        st.download_button(
            label="📥 Download your data as CSV",
            data=df.reset_index().to_csv(index=False).encode('utf-8'),
            file_name=f"{username}_meat_log.csv",
            mime='text/csv'
        )

    # Reset button
    if st.sidebar.button("Reset Data"):
        df = pd.DataFrame(columns=['date'])
        save_data(df, username)
        st.sidebar.success("Your data has been reset!")
else:
    st.warning("Please enter your username in the sidebar to continue.")
