import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import time

# 1. Page Configuration
st.set_page_config(
    page_title="QualiFuel Dashboard",
    page_icon="website icon.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ThingSpeak Credentials
TS_CHANNEL_ID = "3296519"
TS_READ_API_KEY = "1RE5E2KSMRQA9C3U"
# To clear history, you need your User API Key from ThingSpeak Account Settings
TS_USER_API_KEY = "JSLLJNE9I9K4I0UQ" 

# Initialize Session State for the Fuel Station edits
if 'station_data' not in st.session_state:
    st.session_state.station_data = {}

@st.cache_data(ttl=10)
def fetch_live_data():
    url = f"https://api.thingspeak.com/channels/{TS_CHANNEL_ID}/feeds.json?api_key={TS_READ_API_KEY}&results=1000"
    try:
        response = requests.get(url)
        data = response.json()
        feeds = data.get('feeds', [])
        if not feeds:
            return pd.DataFrame()
        
        df = pd.DataFrame(feeds)
        df = df.rename(columns={
            "created_at": "Timestamp",
            "field1": "Fuel Type",
            "field2": "Confidence (%)",
            "field3": "Ethanol %",
            "field4": "Water %",
            "field5": "Kerosene %",
            "field6": "Temperature (°C)",
            "field7": "Speed of Sound (m/s)",
            "field8": "Impedance Slope"
        })
        
       # Convert Timestamp to Datetime object
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
        
        numeric_cols = ["Confidence (%)", "Ethanol %", "Water %", "Kerosene %", 
                        "Temperature (°C)", "Speed of Sound (m/s)", "Impedance Slope"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
        
        def get_adulterant(row):
            if row["Ethanol %"] > 0: return "Ethanol"
            if row["Water %"] > 0: return "Water"
            if row["Kerosene %"] > 0: return "Kerosene"
            return "None"
        
        df["Adulterant"] = df.apply(get_adulterant, axis=1)
        
        # Helper to calculate Week of Month (1-4)
        df["Year"] = df["Timestamp"].dt.year
        df["Month"] = df["Timestamp"].dt.month_name()
        df["Week"] = df["Timestamp"].apply(lambda d: (d.day-1)//7 + 1)
        df["Week"] = df["Week"].apply(lambda w: f"Week {min(w, 4)}") # Cap at Week 4
        
        return df.iloc[::-1] 
    except:
        return pd.DataFrame()

df_live = fetch_live_data()

# 2. CSS Styling
st.markdown("""
    <style>
    div[data-testid="stMetric"] { background-color: var(--background-color); border: 1px solid #E0E0E0; padding: 20px; border-radius: 15px; text-align: center; }
    .detection-card { background-color: #3D6355 !important; color: white !important; padding: 1.8rem; border-radius: 25px; text-align: center; margin-bottom: 20px; }
    .accuracy-card { background-color: #3D6355 !important; color: white !important; padding: 1.5rem; border-radius: 25px; display: flex; align-items: center; justify-content: center; gap: 20px; }
    .circle-progress {
        background: radial-gradient(closest-side, #3D6355 79%, transparent 80% 100%),
                    conic-gradient(#C4D7B2 var(--percentage), #FFFFFF 0);
        border-radius: 50%; width: 100px; height: 100px; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold; color: white !important;
    }
    .stButton>button { border-radius: 20px; border: 1px solid #3D6355; color: #3D6355; }
    </style>
    """, unsafe_allow_html=True)

# 3. Header
st.markdown("""
    <div style='text-align: center;'>
        <p style='font-size: 3rem; font-weight: 700; margin-bottom: 0px;'>
            QualiFuel Dashboard
        </p>
    </div>
""", unsafe_allow_html=True)

st.markdown('<hr style="border: none; border-top: 1px solid rgba(128, 128, 128, 0.3); margin: 10px 0;">', unsafe_allow_html=True)

# 4. Global Logic
if not df_live.empty:
    latest = df_live.iloc[0]
    total_samples = len(df_live)
    pure_count = len(df_live[df_live['Adulterant'] == 'None'])
    adul_count = total_samples - pure_count
    avg_acc = int(df_live["Confidence (%)"].mean())
else:
    latest, total_samples, pure_count, adul_count, avg_acc = None, 0, 0, 0, 0

# Metrics Styling
st.markdown("""
    <style>
    div[data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.05); 
        border: 1px solid #3D6355 !important;
        padding: 1.5rem !important;
        border-radius: 20px !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
    }
    div[data-testid="stMetricLabel"] > div {
        color: var(--text-color) !important;
        font-weight: 800 !important;
        font-size: 1.4rem !important;
        text-align: center !important;
    }
    div[data-testid="stMetricValue"] > div {
        color: var(--text-color) !important;
        font-weight: 700 !important;
        font-size: 3.2rem !important;
        text-align: center !important;
    }
    [data-testid="metric-container"] {
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
    }
    </style>
""", unsafe_allow_html=True)

m_left, col1, col2, col3, m_right = st.columns([1, 3, 3, 3, 1])
with col1: st.metric("Total Sample", total_samples)
with col2: st.metric("Pure Fuel", pure_count)
with col3: st.metric("Adulterated Fuel", adul_count)

st.markdown("<br>", unsafe_allow_html=True)

# 5. Middle Row
row2_left_margin, left_col, right_col, row2_right_margin = st.columns([0.2, 3, 7, 0.5], gap="large")

with left_col:
    ts_text = latest['Timestamp'].strftime('%Y-%m-%d %H:%M:%S') if latest is not None else "No Data Detected"
    fuel_text = latest['Fuel Type'] if latest is not None else "_______"
    adul_text = latest['Adulterant'] if latest is not None else "_______"
    conf_text = f"{latest['Confidence (%)']}%" if latest is not None else "_______"
    e_val = f"{latest['Ethanol %']}%" if latest is not None else "0%"
    w_val = f"{latest['Water %']}%" if latest is not None else "0%"
    k_val = f"{latest['Kerosene %']}%" if latest is not None else "0%"

    st.markdown(f"""
        <div class="detection-card">
        <p style="color:white; font-size: 2.2rem; font-weight: bold; margin-top: 0; margin-bottom: 5px;">
            Latest Detection
        </p>
        <p style="color:white; opacity: 0.8; font-size: 1.1rem;">{ts_text}</p>
        <hr style="border-top: 1px solid rgba(255,255,255,0.3); width: 80%; margin: 15px auto;">
        <div style="text-align: center; line-height: 1.5; font-size: 1.2rem;">
            <p style="margin:0;"><b>Fuel Type:</b> {fuel_text}</p>
            <p style="margin:0;"><b>Confidence:</b> {conf_text}</p>
            <p style="margin:0;"><b>Ethanol:</b> {e_val}</p>
            <p style="margin:0;"><b>Water:</b> {w_val}</p>
            <p style="margin:0;"><b>Kerosene:</b> {k_val}</p>
        </div>
    </div>
        <div class="accuracy-card">
            <div class="circle-progress" style="--percentage: {avg_acc}%">{avg_acc}%</div>
            <div style="color:white; font-size: 22px; font-weight: bold; width: 45%; text-align: left; display: flex; align-items: center; justify-content: center;">
                Classification<br>Accuracy
            </div>
        </div>
    """, unsafe_allow_html=True)

with right_col:
    chart_title_col, filter_col1, filter_col2 = st.columns([4, 2, 2])
    with chart_title_col:
        st.subheader("Adulterants Distribution Chart", anchor = False)
    
    if not df_live.empty:
        # Month and Year Filters
        available_years = sorted(df_live["Year"].unique(), reverse=True)
        available_months = ["January", "February", "March", "April", "May", "June", 
                            "July", "August", "September", "October", "November", "December"]
        
        with filter_col1:
            current_month_name = df_live["Month"].iloc[0]
            sel_month = st.selectbox("Month", available_months, index=available_months.index(current_month_name)) 
        with filter_col2:
            sel_year = st.selectbox("Year", available_years)

        # Filter Data based on selection
        filtered_df = df_live[(df_live["Year"] == sel_year) & (df_live["Month"] == sel_month)]

        # Prepare Weekly Data
        weeks = ["Week 1", "Week 2", "Week 3", "Week 4"]
        categories = ['Water', 'Ethanol', 'Kerosene', 'None']
        colors = ['#C4D7B2', '#79947C', '#3D5C50', '#203A30']

        fig = go.Figure()

        for cat, color in zip(categories, colors):
            cat_values = []
            for w in weeks:
                count = len(filtered_df[(filtered_df["Week"] == w) & (filtered_df["Adulterant"] == cat)])
                cat_values.append(count)
            
            fig.add_trace(go.Bar(
                name=cat,
                x=weeks,
                y=cat_values,
                marker_color=color
            ))

        fig.update_layout(
            barmode='group',
            height=450,
            margin=dict(t=10, b=10, l=10, r=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            yaxis=dict(gridcolor='rgba(128, 128, 128, 0.2)')
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for chart.")

st.write("---")

# 6. Data History with Clear Button Logic
title_col, button_area = st.columns([8, 2])
with title_col: st.subheader("Data History", anchor=False)

with button_area:
    check_col, action_col = st.columns([1, 1]) 
    
    with check_col:
        # We add a 'key' here so we can control this widget programmatically
        confirm_clear = st.checkbox(
            "Delete", 
            help="Confirm permanent deletion.",
            key="wipe_gate" 
        )
    
    with action_col:
        if st.button("Clear History", type="secondary", disabled=not confirm_clear):
            try:
                res = requests.delete(
                    f"https://api.thingspeak.com/channels/{TS_CHANNEL_ID}/feeds.json", 
                    params={'api_key': TS_USER_API_KEY},
                    timeout=5
                )
                
                if res.status_code == 200:
                    # 1. Reset the checkbox state globally
                    st.session_state.wipe_gate = True
                    
                    # 2. Show success message
                    st.success("Cleared!")
                    
                    # 3. Rerun to refresh the table and show the unchecked box
                    st.rerun()
                else:
                    st.error(f"Error: {res.status_code}")
            except:
                st.error("Failed")

if not df_live.empty:
    df_history = df_live.copy()
    # Format timestamp for display in table
    df_history["Timestamp_Display"] = df_history["Timestamp"].dt.strftime('%Y-%m-%d %H:%M:%S')

    display_cols = ["Timestamp_Display", "Fuel Type", "Confidence (%)", "Ethanol %", "Water %", "Kerosene %", "Temperature (°C)", "Speed of Sound (m/s)", "Impedance Slope"]
    
    edited_df = st.data_editor(
        df_history[display_cols],
        use_container_width=True,
        hide_index=True,
        key="data_editor"
    )

# 7. Auto-Refresh Logic
time.sleep(10)
st.rerun()
