import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import re
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(layout="wide", page_title="UK FC Picking Velocity Map")

# --- 2. DATA SOURCES ---
SHEET_ID = "1uKo-jej2UlA-cdhgYFWS9CqQ5h0uqcxLi-BSp-V1V6o"
RAW_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=RAW"

st.sidebar.title("🏃 Picking Navigation")

@st.cache_data(ttl=10)
def load_picking_data():
    t = datetime.now().timestamp()
    df_raw = pd.read_csv(f"{RAW_URL}&t={t}")
    df_bp = pd.read_csv('master_blueprint.csv')
    df_raw.columns = df_raw.columns.str.strip().str.replace(' ', '_').str.lower()
    return df_bp, df_raw

try:
    df_blueprint, df_raw_data = load_picking_data()

    def sanitize(text):
        return re.sub(r'[^A-Z0-9]', '', str(text)).upper()

    # --- 3. FILTERS ---
    client_list = ["All Clients"] + sorted(df_raw_data['client_name'].dropna().unique().tolist())
    selected_client = st.sidebar.selectbox("Filter by Client", client_list)
    selected_level = st.sidebar.selectbox("Select Floor View", ["Level 1", "Level 2", "Level 3", "Level 4", "Level 5"])

    # --- 4. DATA PREP ---
    df_lvl_bp = df_blueprint[df_blueprint['level'].astype(str).str.contains(selected_level, case=False)].copy()
    df_lvl_bp['match_key'] = df_lvl_bp['bay_name'].apply(sanitize)
    valid_map_bays = set(df_lvl_bp['match_key'].unique())

    if selected_client != "All Clients":
        df_work = df_raw_data[df_raw_data['client_name'] == selected_client].copy()
    else:
        df_work = df_raw_data.copy()

    df_work['bay_key'] = df_work['bay'].apply(sanitize)
    df_mapped_only = df_work[df_work['bay_key'].isin(valid_map_bays)].copy()

    # --- 5. CALCULATIONS ---
    bay_counts = df_mapped_only['bay_key'].value_counts().to_dict()
    location_rank = df_mapped_only['location'].value_counts().reset_index()
    location_rank.columns = ['Location', 'Picks']

    # --- 6. GRID MAPPING ---
    if df_lvl_bp.empty:
        st.error(f"No coordinates found for {selected_level}")
    else:
        max_r, max_c = int(df_lvl_bp['grid_row'].max() + 1), int(df_lvl_bp['grid_col'].max() + 1)
        color_grid = np.full((max_r, max_c), np.nan)
        
        for _, row in df_lvl_bp.iterrows():
            r, c = int(row['grid_row']), int(row['grid_col'])
            m_key = row['match_key']
            # We assign 0 if no picks, which will map to our neutral color
            color_grid[r, c] = bay_counts.get(m_key, 0)

        # --- 7. VISUALIZATION ---
        st.title(f"Picking Velocity: {selected_level} ({selected_client})")
        
        # Scale Logic
        max_val = max(bay_counts.values()) if bay_counts else 0
        # Force vmax to be at least 1 to prevent color-stretching bugs
        vmax_limit = max(max_val, 1)

        fig, ax = plt.subplots(figsize=(25, 12), facecolor='none')
        ax.set_facecolor('none')
        
        # --- NEW COLOR PALETTE ---
        # First color (#e0e0e0) is for 0 picks (Light Gray)
        # Remaining colors create a "Heat" gradient for 1+ picks
        colors = ["#e0e0e0", "#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"]
        cmap = mcolors.LinearSegmentedColormap.from_list("custom_heat", colors, N=256)
        
        sns.heatmap(
            color_grid, 
            cmap=cmap, 
            cbar=True,
            linewidths=0.5, 
            linecolor='white', # White grid lines look cleaner for picking maps
            vmin=0, 
            vmax=vmax_limit, 
            mask=np.isnan(color_grid), 
            ax=ax
        )

        # Labels
        processed_labels = set()
        for _, row in df_lvl_bp.iterrows():
            r, c = int(row['grid_row']), int(row['grid_col'])
            clean_label = re.sub(r'\d+$', '', str(row['bay_name'])).rstrip('-').strip()
            if f"{clean_label}_{c}" not in processed_labels:
                ax.text(c + 0.5, r - 0.7, clean_label, ha='center', va='bottom', color='#888888', weight='bold', fontsize=10)
                processed_labels.add(f"{clean_label}_{c}")

        plt.axis('off')
        st.pyplot(fig, use_container_width=True)

        # --- 8. TOP LOCATIONS LIST ---
        st.markdown("---")
        st.subheader(f"🏆 Top 15 Picked Locations ({selected_client})")
        st.dataframe(location_rank.head(15), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error: {e}")
