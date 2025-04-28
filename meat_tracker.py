import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

# --- GOOGLE DRIVE SETUP (Service Account Auth) ---
def init_drive():
    scope = ['https://www.googleapis.com/auth/drive']
    creds_dict = st.secrets["google"]["service_account"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    
    gauth = GoogleAuth()
    gauth.credentials = credentials
    return GoogleDrive(gauth)

drive = init_drive()

# --- USERNAME SETUP ---
username = st.sidebar.text_input("Enter your username to access your data")

# --- LOAD AND SAVE FUNCTIONS ---
def load_data(username):
    filename = f"{username}.csv"
    file_list = drive.ListFile({'q': f"title='{filename}' and trashed=false"}).GetList()
    if file_list:
        file = file_list[0]
        file.GetContentFile(filename)
        df = pd.read_csv(filename, parse_dates=['date'])

        df['date'] = pd.to_datetime(df['date']).dt.normalize()

        # Upgrade old data format
        if 'count' not in df.columns:
            df['count'] = 1

        return df, file
    else:
        return pd.DataFrame(columns=['date', 'count']), None

def save_data(df, username, existing_file):
    filename = f"{username}.csv"
    df.to_csv(filename, index=False)
    if existing_file:
        existing_file.SetContentFile(filename)
        existing_file.Upload()
    else:
        new_file = drive.CreateFile({'title': filename})
        new_file.SetContentFile(filename)
        new_file.Upload()

# --- MAIN APP ---
st.title("Meat-Eating Tracker")
st.sidebar.header("Tracker Settings")

if username:
    df, existing_file = load_data(username)

    # Sidebar input for logging
    selected_date = st.sidebar.date_input("Select the date")
    meat_events = st.sidebar.number_input("How many meat-eating events on this day?", min_value=0, step=1)

    if st.sidebar.button("Save"):
        selected_date = pd.to_datetime(selected_date).normalize()
        df = df[df['date'] != selected_date]  # Remove previous entry for this date

        # Add new entry for the selected date
        if meat_events > 0:
            new_row = pd.DataFrame({'date': [selected_date], 'count': [meat_events]})
            df = pd.concat([df, new_row], ignore_index=True)
        elif meat_events == 0:
            # Explicitly log a 0 for no meat-eating events, so it will appear as 0 in the chart
            new_row = pd.DataFrame({'date': [selected_date], 'count': [0]})
            df = pd.concat([df, new_row], ignore_index=True)
        
        save_data(df, username, existing_file)
        st.sidebar.success(f"Saved {meat_events} event(s) for {selected_date.date()}!")
        st.rerun()

    if not df.empty:
        df['date'] = pd.to_datetime(df['date']).dt.normalize()
        df_grouped = df.groupby('date')['count'].sum()

        start_date = pd.to_datetime('2025-02-10')
        all_dates = pd.date_range(start=start_date, end=datetime.today(), freq='D')

        # Reindex to fill missing days with NaN (unlogged days)
        df_grouped = df_grouped.reindex(all_dates)

        # Set unlogged days (NaN) to 1 for grey bar representation
        df_grouped_filled = df_grouped.fillna(1)

        # --- Track Active and Archived Achievements ---
        active_achievements = []
        archived_achievements = []

        # --- Current and Longest streaks ---
        today = pd.Timestamp(datetime.today().date())

        longest_streak = 0
        streak = 0
        for val in df_grouped.values:
            if val == 0:
                streak += 1
                longest_streak = max(longest_streak, streak)
            else:
                streak = 0

        col1, col2 = st.columns(2)
        with col1:
            st.metric("🥗 Days without meat", f"{streak} days")
        with col2:
            st.metric("🏆 Longest streak", f"{longest_streak} days")

        # --- Achievements ---
        # Streak milestones based on longest streak ever
        if longest_streak >= 10 and "10-day streak" not in active_achievements:
            active_achievements.append("10-day streak")
        if longest_streak >= 20 and "20-day streak" not in active_achievements:
            active_achievements.append("20-day streak")
        if longest_streak >= 30 and "30-day streak" not in active_achievements:
            active_achievements.append("30-day streak")
        
        # Full meat-free weeks (Monday to Sunday)
        full_weeks = 0
        df_zero_filled = df_grouped.fillna(999)  # Use 999 to catch unlogged days
        
        first_meat_free_week = False  # Flag to track if the first meat-free week is completed
        
        for i in range(len(df_zero_filled) - 6):
            week = df_zero_filled.iloc[i:i+7]
            week_dates = week.index
        
            if week_dates[0].weekday() == 0 and week_dates[-1].weekday() == 6:
                if all(week == 0):  # This means it's a full meat-free week
                    full_weeks += 1
                    if full_weeks == 1:
                        first_meat_free_week = True  # Set the flag when the first meat-free week is completed
        
        if full_weeks > 0 and "1-week streak" not in active_achievements:
            active_achievements.append("1-week streak")
        
        # --- Negative Achievement for Logging Meat After Meat-Free Week ---
        if first_meat_free_week and df_grouped[df_grouped > 0].index.min() > df_zero_filled.index[6]:  # After the first full meat-free week
            st.markdown("""
            <div style='background-color:#f8d7da;padding:20px;border-radius:10px;border-left:5px solid red;'>
                <strong>🚨 Oops! You logged meat after your first meat-free week!</strong><br>
                <strong>Don't worry, it's a small setback. Keep going!</strong>
            </div>
            """, unsafe_allow_html=True)
            archived_achievements = active_achievements.copy()  # Move all active achievements to archived
            active_achievements.clear()  # Clear active achievements

        # --- Display Active Achievements ---
        if active_achievements:
            st.markdown("### Active Achievements")
            for achievement in active_achievements:
                st.markdown(f"🎉 {achievement}")

        # --- Display Archived Achievements ---
        if archived_achievements:
            st.markdown("### Archived Achievements")
            for achievement in archived_achievements:
                st.markdown(f"❌ {achievement}")

        # --- Plotting (Bar Chart) --- 
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot all days with grey bars (1 for unlogged)
        ax.bar(df_grouped_filled.index, df_grouped_filled.values, color='grey', alpha=0.6, label="Unlogged Day")
        
        # Plotting the meat-eating events (green bars) on top of the grey bars
        ax.bar(df_grouped.index[df_grouped > 0], df_grouped[df_grouped > 0], color='green', label="Logged Meat Eating")
        
        # Set labels for x and y axis
        ax.set_xlabel("Time")
        ax.set_ylabel("Meat-Eating Events")
        ax.tick_params(axis='y')
        
        # Define weekly ticks (every 7 days, i.e., Mondays)
        weekly_ticks = pd.date_range(start=df_grouped_filled.index[0], end=df_grouped_filled.index[-1], freq='W-MON')
        
        # Set the positions for the ticks and labels
        ax.set_xticks(df_grouped_filled.index)  # Set tick positions for each day
        
        # Set the tick labels only for the weekly ticks (e.g., Mondays)
        ax.set_xticks(weekly_ticks)  # Position the weekly ticks on the x-axis
        ax.set_xticklabels(weekly_ticks.strftime('%Y-%m-%d'), rotation=45, ha='right')  # Only label the weekly ticks
        
        # Minor ticks: Display small lines without labels
        ax.tick_params(axis='x', which='minor', length=4, width=1, color='black')
        
        # Major ticks: Make them a bit longer for the weekly labels
        ax.tick_params(axis='x', which='major', length=7, width=2, color='black')
        
        # Display legend and tight layout
        ax.legend()
        
        # --- Y-Axis as Whole Numbers ---
        ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
        
        # Tight layout for the plot
        plt.tight_layout()
        
        # Show the plot
        st.pyplot(fig)
        
        # --- Download Button ---
        df_download = df_grouped.reset_index()
        df_download.columns = ['date', 'count']
        df_download['date'] = df_download['date'].dt.strftime('%Y-%d-%m')  # European format
        st.download_button(
            label="📥 Download your data as CSV",
            data=df_download.to_csv(index=False).encode('utf-8'),
            file_name=f"{username}_meat_tracker_log.csv",
            mime='text/csv'
        )


else:
    st.warning("Please enter your username in the sidebar to continue.")
