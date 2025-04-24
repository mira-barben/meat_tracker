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

    selected_date = st.sidebar.date_input("Select the date")
    meat_events = st.sidebar.number_input("How many meat-eating events on this day?", min_value=0, step=1)

    if st.sidebar.button("Save"):
        selected_date = pd.to_datetime(selected_date).normalize()
        df = df[df['date'] != selected_date]  # Remove previous entry for this date
        new_row = pd.DataFrame({'date': [selected_date], 'count': [meat_events]})
        df = pd.concat([df, new_row], ignore_index=True)
        save_data(df, username, existing_file)
        st.sidebar.success(f"Saved {meat_events} event(s) for {selected_date.date()}!")
        st.rerun()

    if not df.empty:
        df['date'] = pd.to_datetime(df['date']).dt.normalize()
        df_grouped = df.groupby('date')['count'].sum()

        start_date = pd.to_datetime('2025-02-10')
        today = pd.Timestamp(datetime.today().date())
        all_dates = pd.date_range(start=start_date, end=today, freq='D')

        df_grouped = df_grouped.reindex(all_dates, fill_value=0)

        # --- "Days without meat" Calculation ---
        days_without_meat = 0
        for date in reversed(df_grouped.index):
            if df_grouped.loc[date] == 0:
                days_without_meat += 1  # Count consecutive days with no meat
            else:
                break  # Stop counting as soon as we hit a day with meat

        # --- Longest Streak Calculation ---
        longest_streak = 0
        streak = 0
        for date in df_grouped.index:
            if df_grouped.loc[date] == 0:
                streak += 1  # Increment streak if no meat on this day
            else:
                longest_streak = max(longest_streak, streak)
                streak = 0  # Reset streak when meat is eaten
        longest_streak = max(longest_streak, streak)  # In case the streak ends on the last day

        # --- Display Results ---
        col1, col2 = st.columns(2)
        with col1:
            st.metric("🥗 Days without meat", f"{days_without_meat} days")
        with col2:
            st.metric("🏆 Longest streak", f"{longest_streak} days")

        # --- Visualization ---
        df_all = pd.DataFrame(index=all_dates)
        df_all.index.name = 'date'
        df_all['actual_count'] = 0

        df_all['actual_count'] = df.set_index('date')['count']
        df_all['logged'] = df_all.index.isin(df['date'])

        def compute_visual(row):
            if row['logged']:
                if row['actual_count'] == 0:
                    return pd.NA, 'none'  # hide bar if no meat
                else:
                    return row['actual_count'], 'green'
            else:
                return 1, 'lightgray'

        df_all[['plot_count', 'color']] = df_all.apply(compute_visual, axis=1, result_type='expand')

        import matplotlib.patches as mpatches
        plt.figure(figsize=(12, 6))
        mask = df_all['color'] != 'none'
        plt.bar(df_all.index[mask], df_all.loc[mask, 'plot_count'], color=df_all.loc[mask, 'color'])

        plt.xticks(
            ticks=pd.date_range(start=start_date, end=today, freq='7D'),
            labels=[d.strftime('%d.%m') for d in pd.date_range(start=start_date, end=today, freq='7D')],
            rotation=45
        )

        plt.xlabel("Date")
        plt.ylabel("Meat-Eating Events")
        plt.title("Meat Consumption Timeseries")

        legend_patches = [
            mpatches.Patch(color='green', label='Logged (meat eaten)'),
            mpatches.Patch(color='lightgray', label='Not logged')
        ]
        plt.legend(handles=legend_patches)
        plt.tight_layout()
        st.pyplot(plt)

        # --- Download Button ---
        df_download = df_grouped.reset_index()
        df_download.columns = ['date', 'count']
        df_download['date'] = df_download['date'].dt.strftime('%Y-%d-%m')
        st.download_button(
            label="📥 Download your data as CSV",
            data=df_download.to_csv(index=False).encode('utf-8'),
            file_name=f"{username}_meat_tracker_log.csv",
            mime='text/csv'
        )
else:
    st.warning("Please enter your username in the sidebar to continue.")

