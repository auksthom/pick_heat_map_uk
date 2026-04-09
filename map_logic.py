import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import re
from datetime import datetime
import numpy as np

# --- 1. SETTINGS & UI ---
st.set_page_config(layout="wide", page_title="Multi-Level Warehouse Heatmap")

st.sidebar.title("🏢 Site Navigation")
level_options = ["Level 1", "Level 2", "Level 3", "Level 4", "Level 5"]
level_to_prefix = {"Level 1": "T1", "Level 2": "T2", "Level 3": "T3", "Level 4": "T4", "Level 5": "T5"}

selected_level = st.sidebar.selectbox("Select Floor", level_options)
prefix = level_to_prefix[selected_level]

# --- 2. DATA SOURCES ---
SHEET_ID = "189xHc5ijA8Dd40agyp98Qo-p4P6xRzBNLilCOhyERQc"
STOCK_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=stock_report"
CAPS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=warehouse_capacity"

# --- 3. OPTIMIZED DATA LOADING ---
def get_time_slot():
    now = datetime.now()
    return f"Morning_{now.strftime('%Y-%m-%d')}" if 8 <= now.hour < 20 else f"Night_{now.strftime('%Y-%m-%d')}"

@st.cache_data(ttl=None)
def load_all_data(slot):
    t = datetime.now().timestamp()
    df_s = pd.read_csv(f"{STOCK_URL}&t={t}")
    df_c = pd.read_csv(f"{CAPS_URL}&t={t}")
    # Load your new master blueprint
    df_b = pd.read_csv('master_blueprint.csv')
    return df_b, df_s, df_c

try:
    current_slot = get_time_slot()
    df_blueprint, df_stock, df_caps = load_all_data(current_slot)

    # --- 4. CLEANING & FILTERING ---
    df_stock.columns = df_stock.columns.str.strip().str.replace(' ', '_').str.lower()
    df_caps.columns = df_caps.columns.str.strip().str.replace(' ', '_').str.lower()

    # Filter Sheets data to match the selected floor prefix (T1, T2, etc.)
    df_stock_filtered = df_stock[df_stock['bay_name'].str.startswith(prefix, na=False)].copy()
    df_caps_filtered = df_caps[df_caps['bay_name'].str.startswith(prefix, na=False)].copy()

    def create_key(text):
        return re.sub(r'[^a-zA-Z0-9]', '', str(text)).upper()

    df_stock_filtered['match_key'] = df_stock_filtered['bay_name'].apply(create_key)
    df_caps_filtered['match_key'] = df_caps_filtered['bay_name'].apply(create_key)

    # Calculate Utilization
    df_merge = pd.merge(df_caps_filtered, df_stock_filtered, on='match_key', how='left')
    df_merge['util'] = (pd.to_numeric(df_merge['used_m3'], errors='coerce').fillna(0) / 
                        pd.to_numeric(df_merge['capacity_m3'], errors='coerce').replace(0, 0.1)) * 100
    util_dict = df_merge.set_index('match_key')['util'].to_dict()

    # --- 5. SEARCH LOGIC ---
    st.title(f"Warehouse Heatmap: {selected_level}")
    search_query = st.sidebar.text_input(f"🔍 Search Bay (e.g., {prefix}-E-1)")
    search_key = create_key(search_query) if search_query else None

    # --- 6. BUILDING THE GRID FOR THE SELECTED LEVEL ---
    # Filter blueprint for the current level
    df_lvl_blueprint = df_blueprint[df_blueprint['level'] == selected_level]
    
    if df_lvl_blueprint.empty:
        st.warning(f"No blueprint data found for {selected_level}. Check your CSV.")
    else:
        # Create empty grid based on max coordinates in blueprint
        max_r, max_c = int(df_lvl_blueprint['grid_row'].max() + 1), int(df_lvl_blueprint['grid_col'].max() + 1)
        color_grid = np.full((max_r, max_c), np.nan)
        
        label_positions = []
        processed_labels = set()
        found_coords = None

        for _, row in df_lvl_blueprint.iterrows():
            r, c = int(row['grid_row']), int(row['grid_col'])
            m_key = row['match_key']
            raw_name = row['bay_name']
            
            # Apply color from util dict
            color_grid[r, c] = util_dict.get(m_key, 0)
            
            # Search highlight
            if search_key and m_key == search_key:
                found_coords = (r, c)

            # Labeling logic (Headers like T1-E)
            clean_label = re.sub(r'\d+$', '', raw_name).rstrip('-').strip()
            label_id = f"{clean_label}_{c}"
            if label_id not in processed_labels:
                label_positions.append((r, c, clean_label))
                processed_labels.add(label_id)

        # --- 7. VISUALIZATION ---
        plt.rcParams['figure.facecolor'] = '#121212'
        fig, ax = plt.subplots(figsize=(25, 12))
        ax.set_facecolor('#121212')
        
        cmap = mcolors.LinearSegmentedColormap.from_list("", ["#2ecc71", "#f1c40f", "#e74c3c"])
        sns.heatmap(color_grid, cmap=cmap, cbar=False, linewidths=1.5, 
                    linecolor='#121212', vmin=0, vmax=100, mask=np.isnan(color_grid), ax=ax)

        if found_coords:
            ax.add_patch(plt.Rectangle((found_coords[1], found_coords[0]), 1, 1, fill=False, edgecolor='#00ffff', lw=8))

        for r, c, name in label_positions:
            ax.text(c + 0.5, r - 0.7, name, ha='center', color='white', weight='bold', fontsize=10)

        plt.axis('off')
        st.pyplot(fig, use_container_width=True)
        st.success(f"Floor sync complete for {current_slot}")

except Exception as e:
    st.error(f"Error loading map: {e}")