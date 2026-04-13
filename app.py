import streamlit as st
import pandas as pd
import plotly.express as px

# --- Dashboard Config & UI Setup ---
st.set_page_config(page_title="Kavach & Radio Diagnostic Tool", page_icon="🚂", layout="wide")
st.title("🚂 Kavach: Loco Radio vs TCAS Diagnostic Tool")
st.markdown("Upload your Datalogger CSV file to automatically analyze and generate a logical root-cause report.")

# --- Constants for Validation ---
REQUIRED_COLUMNS = ['Loco ID', 'ComFailCnt', 'Rad1 RSSI', 'Rad2 RSSI', 'RevPwr', 'RadRxPktCnt']

# ==========================================
# FILE UPLOAD SECTION
# ==========================================
st.markdown("### 📂 Step 1: Upload Data")
uploaded_file = st.file_uploader("Apni CSV file yahan upload karein (e.g., SHM_SHM_1.csv)", type=["csv"])

if uploaded_file is not None:
    try:
        # --- Load Data ---
        df = pd.read_csv(uploaded_file)
        
        # --- Validate Columns ---
        missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            st.error(f"❌ Uploaded CSV is missing required columns: **{', '.join(missing_cols)}**")
            st.stop()
            
        st.success("✅ File successfully load ho gayi hai!")
        st.markdown("---")

        # --- Clean Data for Robust Logic ---
        df['ComFailCnt_Clean'] = df['ComFailCnt'].astype(str).str.strip().str.lower()
        
        # --- Apply Diagnostic Logic ---
        is_max_count = df['ComFailCnt_Clean'] == 'max count'
        radio_rssi_faults = df[is_max_count & ((df['Rad1 RSSI'] >= 130) | (df['Rad2 RSSI'] >= 130))]
        tcas_toggles = df[is_max_count & ((df['Rad1 RSSI'].between(50, 80)) | (df['Rad2 RSSI'].between(50, 80)))]
        antenna_faults = df[df['RevPwr'] > 2.5]
        packet_zero_faults = df[df['RadRxPktCnt'] == 0]

        # --- KPI Metrics Row ---
        st.markdown("### 📊 Step 2: Overall Fleet Summary")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Logs Analyzed", f"{len(df):,}")
        col2.metric("📻 Radio Faults (HW)", len(radio_rssi_faults))
        col3.metric("🧠 TCAS Faults (SW)", len(tcas_toggles))
        col4.metric("📡 Antenna Leaks (HW)", len(antenna_faults))
        col5.metric("⚠️ Zero Rx Packets", len(packet_zero_faults))

        st.markdown("---")

        # ==========================================
        # TABS FOR REPORT & VISUALS
        # ==========================================
        tab1, tab2 = st.tabs(["📋 Step 3: Logical Report Generator", "📉 Visualizations & Data Explorer"])

        with tab1:
            st.markdown("### Select a Locomotive for Deep Analysis")
            unique_locos = sorted(df['Loco ID'].dropna().unique())
            selected_loco = st.selectbox("Loco ID:", ["-- Select Loco --"] + list(unique_locos))

            if selected_loco != "-- Select Loco --":
                l_radio = radio_rssi_faults[radio_rssi_faults['Loco ID'] == selected_loco]
                l_tcas = tcas_toggles[tcas_toggles['Loco ID'] == selected_loco]
                l_antenna = antenna_faults[antenna_faults['Loco ID'] == selected_loco]
                l_blind = packet_zero_faults[packet_zero_faults['Loco ID'] == selected_loco]
                
                # We will build a text string here so it can be downloaded
                download_text = f"=========================================\n"
                download_text += f" KAVACH DIAGNOSTIC REPORT \n"
                download_text += f" Locomotive ID: {selected_loco}\n"
                download_text += f"=========================================\n\n"

                st.write(f"## 📝 Diagnostic Report for Locomotive: **{selected_loco}**")
                
                # --- Hardware Logic Detection ---
                if len(l_antenna) > 0 or len(l_radio) > 0 or len(l_blind) > 0:
                    st.error("🚨 **CONCLUSION: HARDWARE ISSUE DETECTED**")
                    st.markdown("#### **Logical Breakdown:**")
                    
                    download_text += "CONCLUSION: HARDWARE ISSUE DETECTED\n\n"
                    
                    if len(l_antenna) > 0:
                        msg = f"- Antenna/Cable Fault: The Reverse Power (RevPwr) exceeded the critical 2.5 threshold {len(l_antenna)} times.\n  Logic: High reverse power indicates that the RF signal is reflecting back into the transmitter rather than broadcasting into the air. This is a classic physical symptom of a damaged RF cable, a loose connection, or a mis-tuned external antenna."
                        st.write("📡 **" + msg.replace("- Antenna", "Antenna"))
                        download_text += msg + "\n\n"
                    
                    if len(l_radio) > 0:
                        msg = f"- Radio Receiver Fault: The system logged a Communication Failure while the Radio Signal Strength (RSSI) was extremely high (>130) {len(l_radio)} times.\n  Logic: If the signal is 'too strong' yet data transfer fails, the radio receiver module is likely hardware-saturated, malfunctioning, or receiving localized jamming/interference."
                        st.write("📻 **" + msg.replace("- Radio", "Radio"))
                        download_text += msg + "\n\n"
                    
                    if len(l_blind) > 0:
                        msg = f"- Radio Blindness: The Rx Packet Count dropped to 0 for {len(l_blind)} logs.\n  Logic: The hardware physically stopped receiving any airwave data from the station."
                        st.write("⚠️ **" + msg.replace("- Radio", "Radio"))
                        download_text += msg + "\n\n"
                        
                # --- Software/TCAS Logic Detection ---
                elif len(l_tcas) > 0:
                    st.warning("⚠️ **CONCLUSION: SOFTWARE / TCAS CPU ISSUE DETECTED**")
                    st.markdown("#### **Logical Breakdown:**")
                    
                    download_text += "CONCLUSION: SOFTWARE / TCAS CPU ISSUE DETECTED\n\n"
                    
                    msg = f"- TCAS Processing Fault: The system recorded Communication Failures {len(l_tcas)} times despite the RSSI being in the healthy, perfect range (50-80).\n  Logic: The antenna and radio are successfully catching a good signal from the station, but the main TCAS unit/CPU is failing to process these packets. The maintenance team should check the TCAS logic unit, NMS syncing, or reboot the internal software state."
                    st.write("🧠 **" + msg.replace("- TCAS", "TCAS"))
                    download_text += msg + "\n\n"
                    
                # --- No Faults Logic ---
                else:
                    st.success("✅ **CONCLUSION: NO KNOWN ISSUES DETECTED**")
                    msg = "Based on the established logic (VSWR, RSSI, and Packet thresholds), this locomotive is operating normally within the uploaded timeframe."
                    st.write(msg)
                    
                    download_text += "CONCLUSION: NO KNOWN ISSUES DETECTED\n\n"
                    download_text += msg + "\n\n"

                # ==========================================
                # DOWNLOAD BUTTON
                # ==========================================
                st.markdown("---")
                st.download_button(
                    label="📥 Download Detailed Report (.txt)",
                    data=download_text,
                    file_name=f"Loco_{selected_loco}_Diagnostic_Report.txt",
                    mime="text/plain"
                )

        with tab2:
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                fault_counts = {
                    "Radio (HW)": len(radio_rssi_faults), 
                    "TCAS (SW)": len(tcas_toggles), 
                    "Antenna (HW)": len(antenna_faults),
                    "Zero Packets (HW)": len(packet_zero_faults)
                }
                df_faults = pd.DataFrame(list(fault_counts.items()), columns=['Type', 'Count'])
                
                if df_faults['Count'].sum() > 0:
                    fig_pie = px.pie(df_faults, names='Type', values='Count', hole=0.4, title="Fleet Fault Distribution")
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("👍 No faults detected across the fleet. Not enough data to generate pie chart.")

            with col_chart2:
                fig_line = px.scatter(df.reset_index(), x='index', y='RevPwr', color='RevPwr', color_continuous_scale='Reds', title="Reverse Power (VSWR) Timeline")
                fig_line.add_hline(y=2.5, line_dash="dash", line_color="red", annotation_text="Critical Threshold (2.5)")
                st.plotly_chart(fig_line, use_container_width=True)
                
            st.markdown("#### 📄 Raw Data Preview (First 100 Rows)")
            st.dataframe(df.head(100), use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ Error loading file: `{e}`. Kripya check karein ki file sahi CSV format mein hai.")

else:
    st.info("👆 Upar diye gaye 'Browse files' button par click karein aur apni CSV file upload karein.")
