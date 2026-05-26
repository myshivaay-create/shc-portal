import streamlit as st
import pandas as pd
import datetime
import io
import plotly.express as px
from sqlalchemy import text
import time

# ==========================================
# AYUSHMAN AROGY A MANDIR PORTAL - OPTIMIZED v2.1
# Best Performance + Premium UI + Production Ready
# ==========================================

st.set_page_config(
    page_title="Ayushman Arogya Mandir",
    page_icon="⚕️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== PREMIUM THEME ======================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    * {font-family: 'Poppins', sans-serif;}
    .stApp {background: linear-gradient(135deg, #f0fdf4 0%, #e0f2fe 100%);}
    h1 {color: #0f172a; font-weight: 700; letter-spacing: -1px;}
    .metric-card {background: rgba(255,255,255,0.95); border-radius: 16px; padding: 24px; 
                  box-shadow: 0 10px 25px rgba(0,0,0,0.08); border-top: 5px solid #16a34a;}
    .stButton>button {background: linear-gradient(135deg, #16a34a, #15803d); border-radius: 12px; 
                      font-weight: 600; box-shadow: 0 6px 15px rgba(22,163,74,0.25);}
    .stButton>button:hover {transform: translateY(-3px); box-shadow: 0 10px 20px rgba(22,163,74,0.35);}
    .form-container {background: white; padding: 28px; border-radius: 16px; 
                     box-shadow: 0 8px 25px rgba(0,0,0,0.06);}
</style>
""", unsafe_allow_html=True)

# ====================== DATABASE CONNECTION ======================
@st.cache_resource(ttl=3600)
def get_connection():
    try:
        return st.connection("postgresql", type="sql")
    except Exception:
        st.error("🚨 Database connection failed. Check your Neon Secrets.")
        st.stop()

conn = get_connection()

def init_db():
    with conn.session as s:
        s.execute(text('''CREATE TABLE IF NOT EXISTS medicines (id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS patients (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL, age INTEGER, gender TEXT,
            village TEXT, family_id TEXT UNIQUE, phone TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS stock (
            id SERIAL PRIMARY KEY, month_year TEXT, medicine_name TEXT,
            voucher_no TEXT, qty_received INTEGER DEFAULT 0, qty_issued INTEGER DEFAULT 0,
            balance INTEGER, remark TEXT, page_no TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS opd_visits (
            id SERIAL PRIMARY KEY, patient_id INTEGER REFERENCES patients(id),
            visit_date DATE, vitals TEXT, symptoms TEXT, diagnosis TEXT, treatment TEXT,
            dispensed_meds TEXT)'''))
        
        # Default medicines
        if s.execute(text("SELECT COUNT(*) FROM medicines")).fetchone()[0] == 0:
            defaults = ["Tab Paracetamol 500mg", "Tab Amoxicillin 500mg", "ORS Packets", "Tab IFA",
                        "Tab Albendazole 400mg", "Tab Zinc 20mg", "Tab Levofloxacin 500mg",
                        "Syrup Paracetamol", "Tab Cetirizine 10mg", "Tab Ranitidine 150mg"]
            for med in defaults:
                s.execute(text("INSERT INTO medicines (name) VALUES (:name) ON CONFLICT DO NOTHING"), {"name": med})
        s.commit()

init_db()

# ====================== CACHED QUERIES ======================
@st.cache_data(ttl=30)
def get_all_medicines():
    return pd.read_sql(text("SELECT name FROM medicines ORDER BY name"), conn.engine)['name'].tolist()

@st.cache_data(ttl=30)
def get_all_balances():
    df = pd.read_sql(text("""
        SELECT medicine_name, SUM(qty_received) - SUM(qty_issued) as current_balance 
        FROM stock GROUP BY medicine_name HAVING SUM(qty_received) - SUM(qty_issued) >= 0
    """), conn.engine)
    return df if not df.empty else pd.DataFrame(columns=["medicine_name", "current_balance"])

def get_med_balance(med_name: str) -> int:
    df = pd.read_sql(text("SELECT SUM(qty_received) - SUM(qty_issued) as bal FROM stock WHERE medicine_name = :med"), 
                     conn.engine, params={"med": med_name})
    bal = df.iloc[0]['bal'] if not df.empty and pd.notna(df.iloc[0]['bal']) else 0
    return max(0, int(bal))

def run_query(query: str, params: dict = None):
    if params is None: params = {}
    return pd.read_sql(text(query), conn.engine, params=params)

def execute_query(query: str, params: dict = None):
    if params is None: params = {}
    with conn.session as s:
        s.execute(text(query), params)
        s.commit()

# ====================== SIDEBAR ======================
if 'page' not in st.session_state:
    st.session_state.page = "Dashboard"

with st.sidebar:
    st.markdown("""
        <div style="text-align:center; padding:20px 0;">
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/1/13/National_Health_Mission_Logo.svg/300px-National_Health_Mission_Logo.svg.png" width="110">
            <h2 style="margin:8px 0 4px 0; color:#15803d;">Ayushman Arogya Mandir</h2>
            <p style="color:#64748b; font-size:0.9rem;">🌟 Sub-Center • Smart Health Portal</p>
        </div>
    """, unsafe_allow_html=True)
    
    PAGES = {
        "🏠 Dashboard": "Dashboard",
        "👥 Citizen Registry": "Master Data",
        "📦 Stock & Inventory": "Stock Inventory",
        "🩺 Smart OPD (AI)": "Smart OPD (AI)",
        "📊 Reports & Analytics": "Reports"
    }
    
    for label, page in PAGES.items():
        if st.button(label, use_container_width=True, key=f"nav_{page}"):
            st.session_state.page = page
            st.rerun()

# ====================== PAGE: DASHBOARD ======================
if st.session_state.page == "Dashboard":
    st.markdown("<h1>👋 Namaste, CHO Ji!</h1>", unsafe_allow_html=True)
    st.markdown(f"**Today:** {datetime.date.today().strftime('%A, %d %B %Y')}")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        today_opd = run_query("SELECT COUNT(*) as c FROM opd_visits WHERE visit_date = :d", 
                             {"d": datetime.date.today()}).iloc[0]['c']
        st.metric("🩺 Today's OPD", today_opd)
    with col2:
        total_patients = run_query("SELECT COUNT(*) as c FROM patients").iloc[0]['c']
        st.metric("👥 Total Citizens", total_patients)
    with col3:
        low_stock = len(get_all_balances()[get_all_balances()['current_balance'] < 50])
        st.metric("⚠️ Low Stock Items", low_stock, delta_color="inverse")
    with col4:
        st.metric("📦 Total Medicines", len(get_all_medicines()))
    
    st.markdown("### ⚡ Quick Actions")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🩺 Start Smart OPD", use_container_width=True, type="primary"):
            st.session_state.page = "Smart OPD (AI)"
            st.rerun()
    with c2:
        if st.button("📦 Update Stock", use_container_width=True):
            st.session_state.page = "Stock Inventory"
            st.rerun()
    with c3:
        if st.button("📊 View Full Report", use_container_width=True):
            st.session_state.page = "Reports"
            st.rerun()

# ====================== PAGE: MASTER DATA ======================
elif st.session_state.page == "Master Data":
    st.markdown("<h1>🗂️ Master Data Hub</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["👨‍👩‍👧‍👦 Citizen Registry", "💊 Medicine Database"])
    
    with tab1:
        st.subheader("Bulk Import from Excel")
        uploaded = st.file_uploader("Upload .xlsx file", type=["xlsx"], key="patient_upload")
        if uploaded:
            df = pd.read_excel(uploaded, engine='openpyxl')
            st.dataframe(df.head(10), use_container_width=True)
            if st.button("🚀 Import All Citizens", type="primary"):
                with st.spinner("Importing..."):
                    success = 0
                    for _, row in df.iterrows():
                        try:
                            execute_query("""
                                INSERT INTO patients (name, age, gender, village, family_id, phone)
                                VALUES (:n, :a, :g, :v, :f, :p)
                                ON CONFLICT (family_id) DO NOTHING
                            """, {
                                "n": str(row.get('Name', '')),
                                "a": int(row.get('Age', 0)) if pd.notna(row.get('Age')) else 0,
                                "g": str(row.get('Gender', '')),
                                "v": str(row.get('Village', '')),
                                "f": str(row.get('FamilyID', row.get('Family Id', ''))),
                                "p": str(row.get('Phone', ''))
                            })
                            success += 1
                        except: pass
                    st.success(f"✅ {success} citizens imported!")
                    st.cache_data.clear()
        st.subheader("Recent Citizens")
        st.dataframe(run_query("SELECT * FROM patients ORDER BY created_at DESC LIMIT 50"), use_container_width=True)
    
    with tab2:
        new_med = st.text_input("➕ Add New Medicine")
        if st.button("Add Medicine") and new_med.strip():
            execute_query("INSERT INTO medicines (name) VALUES (:name) ON CONFLICT DO NOTHING", {"name": new_med.strip()})
            st.success(f"✅ {new_med} added!")
            st.cache_data.clear()
        st.dataframe(run_query("SELECT name FROM medicines ORDER BY name"), use_container_width=True)

# ====================== PAGE: STOCK INVENTORY ======================
elif st.session_state.page == "Stock Inventory":
    st.markdown("<h1>📦 Smart Stock Register</h1>", unsafe_allow_html=True)
    med_list = get_all_medicines()
    tab1, tab2, tab3 = st.tabs(["✍️ Manual Entry", "📂 Excel Bulk Upload", "📋 Live Ledger"])
    
    with tab1:
        with st.form("stock_form"):
            c1, c2 = st.columns(2)
            with c1:
                month_year = st.text_input("Month & Year", value=datetime.date.today().strftime("%B %Y"))
                medicine = st.selectbox("Medicine", med_list)
                voucher = st.text_input("Voucher No.")
                page_no = st.text_input("Page No.")
            with c2:
                received = st.number_input("Quantity Received", min_value=0, value=0)
                issued = st.number_input("Quantity Issued", min_value=0, value=0)
                remark = st.text_input("Remarks / Batch / Expiry")
            
            if st.form_submit_button("💾 Save Transaction"):
                current_bal = get_med_balance(medicine)
                new_bal = current_bal + received - issued
                execute_query("""
                    INSERT INTO stock (month_year, medicine_name, voucher_no, qty_received, qty_issued, balance, remark, page_no)
                    VALUES (:my, :med, :vn, :rec, :iss, :bal, :rem, :pg)
                """, {
                    "my": month_year, "med": medicine, "vn": voucher or "Manual",
                    "rec": received, "iss": issued, "bal": new_bal,
                    "rem": remark or "Manual Entry", "pg": page_no or "1"
                })
                st.success(f"✅ Saved! New balance: **{new_bal}**")
                st.cache_data.clear()
                st.balloons()
    
    with tab2:
        st.info("Upload e-Aushadhi Supply Receipt")
        excel_file = st.file_uploader("Upload Excel", type=["xlsx"], key="stock_bulk")
        if excel_file:
            df_raw = pd.read_excel(excel_file, engine='openpyxl')
            df_raw.columns = [str(col).strip().title() for col in df_raw.columns]
            
            med_col = next((col for col in df_raw.columns if any(x in col.lower() for x in ['medicine','item','product'])), None)
            qty_col = next((col for col in df_raw.columns if any(x in col.lower() for x in ['qty','quantity','received'])), None)
            
            if med_col and qty_col:
                extracted = []
                for _, r in df_raw.iterrows():
                    med_name = str(r[med_col]).strip()
                    if med_name and med_name.lower() != 'nan':
                        extracted.append({
                            "month_year": datetime.date.today().strftime("%B %Y"),
                            "medicine_name": med_name,
                            "voucher_no": "BULK",
                            "qty_received": int(r[qty_col]) if pd.notna(r[qty_col]) else 0,
                            "qty_issued": 0,
                            "remark": "Bulk Import",
                            "page_no": "1"
                        })
                st.success(f"✅ {len(extracted)} items found!")
                edited = st.data_editor(pd.DataFrame(extracted), use_container_width=True, num_rows="dynamic")
                if st.button("✅ Save All to Stock"):
                    with st.spinner("Saving..."):
                        for _, row in edited.iterrows():
                            execute_query("INSERT INTO medicines (name) VALUES (:n) ON CONFLICT DO NOTHING", {"n": row['medicine_name']})
                            new_b = get_med_balance(row['medicine_name']) + int(row['qty_received'])
                            execute_query("""INSERT INTO stock (month_year, medicine_name, voucher_no, qty_received, qty_issued, balance, remark, page_no)
                                             VALUES (:my, :med, :vn, :rec, :iss, :bal, :rem, :pg)""", 
                                          {**row.to_dict(), "bal": new_b})
                        st.success("🎉 Bulk stock updated!")
                        st.cache_data.clear()
            else:
                st.error("Medicine/Quantity columns not detected")
    
    with tab3:
        st.dataframe(run_query("SELECT * FROM stock ORDER BY id DESC LIMIT 100"), use_container_width=True)

# ====================== PAGE: SMART OPD (AI) ======================
elif st.session_state.page == "Smart OPD (AI)":
    st.markdown("<h1>🩺 Smart OPD with AI Clinical Support</h1>", unsafe_allow_html=True)
    
    patients = run_query("SELECT id, name, age, gender, family_id FROM patients ORDER BY name")
    if patients.empty:
        st.warning("No patients yet. Add in Master Data first.")
    else:
        patient_options = [f"{r['name']} (Age: {r['age']}, ID: {r['family_id']})" for _, r in patients.iterrows()]
        pat_dict = {opt: (row['id'], row['age']) for opt, row in zip(patient_options, patients.to_dict('records'))}
        
        colA, colB = st.columns([1.3, 1])
        with colA:
            st.subheader("Patient Assessment")
            selected = st.selectbox("Select Patient", patient_options)
            pat_id, pat_age = pat_dict[selected]
            
            st.subheader("Vitals")
            v1, v2, v3, v4 = st.columns(4)
            with v1: temp = st.number_input("Temperature (°F)", value=98.6, step=0.1)
            with v2: spo2 = st.number_input("SpO2 (%)", value=98, max_value=100)
            with v3: pulse = st.number_input("Pulse (bpm)", value=78)
            with v4: bp = st.text_input("BP", "120/80")
            
            st.subheader("Symptoms")
            common = ["Fever", "Cough", "Cold", "Diarrhea", "Vomiting", "Headache", "Bodyache", "Sore Throat", "Burning Micturition", "Abdominal Pain"]
            symptoms = st.multiselect("Select Symptoms", common)
            notes = st.text_area("Additional Clinical Notes", height=80)
            
            if st.button("🔍 Run AI Protocol", type="primary", use_container_width=True):
                symptom_str = " ".join(symptoms).lower() + " " + notes.lower()
                diseases = {
                    "Upper Respiratory Tract Infection (URTI)": {"meds": ["Paracetamol", "Amoxicillin"]},
                    "Acute Gastroenteritis": {"meds": ["ORS", "Zinc", "Paracetamol"]},
                    "Viral Fever": {"meds": ["Paracetamol"]},
                    "Typhoid / Enteric Fever": {"meds": ["Levofloxacin"]},
                    "Allergic Rhinitis": {"meds": ["Cetirizine"]}
                }
                best_disease = max(diseases, key=lambda x: (3 if "fever" in symptom_str else 0) + 
                                   (3 if any(s in symptom_str for s in ["cough","sore"]) else 0) +
                                   (3 if any(s in symptom_str for s in ["diarrhea","vomit"]) else 0))
                
                st.session_state.ai_diagnosis = best_disease
                st.session_state.ai_meds = diseases[best_disease]["meds"]
                st.session_state.ai_vitals = f"T:{temp}°F | SpO2:{spo2}% | HR:{pulse} | BP:{bp}"
                st.session_state.ai_symptoms = ", ".join(symptoms) + (" | " + notes if notes else "")
                st.rerun()
        
        with colB:
            st.subheader("🧠 AI Recommendation")
            if 'ai_diagnosis' in st.session_state:
                st.markdown(f"**Diagnosis:** <span style='color:#16a34a; font-size:1.3rem;'>{st.session_state.ai_diagnosis}</span>", unsafe_allow_html=True)
                
                current_stock = get_all_balances()
                stock_map = {m.lower(): bal for m, bal in zip(current_stock['medicine_name'], current_stock['current_balance'])}
                
                dispense = []
                for med in st.session_state.ai_meds:
                    avail = next((m for m in stock_map if med.lower() in m.lower() and stock_map[m] > 0), None)
                    if avail:
                        qty = 10 if "paracetamol" in med.lower() else 15
                        st.success(f"✅ {avail} → Dispense {qty}")
                        dispense.append({"med": avail, "qty": qty})
                    else:
                        st.error(f"❌ {med} — Out of Stock")
                
                st.session_state.dispense_list = dispense
                auto_deduct = st.checkbox("Auto-deduct from stock", value=True)
                
                if st.button("💾 Finalize OPD Visit", type="primary"):
                    execute_query("""
                        INSERT INTO opd_visits (patient_id, visit_date, vitals, symptoms, diagnosis, treatment, dispensed_meds)
                        VALUES (:pid, :vd, :vit, :sym, :diag, :tx, :disp)
                    """, {
                        "pid": pat_id, "vd": datetime.date.today(),
                        "vit": st.session_state.ai_vitals,
                        "sym": st.session_state.ai_symptoms,
                        "diag": st.session_state.ai_diagnosis,
                        "tx": ", ".join(st.session_state.ai_meds),
                        "disp": str(st.session_state.dispense_list)
                    })
                    
                    if auto_deduct:
                        for item in st.session_state.dispense_list:
                            newb = get_med_balance(item['med']) - item['qty']
                            execute_query("""
                                INSERT INTO stock (month_year, medicine_name, voucher_no, qty_received, qty_issued, balance, remark, page_no)
                                VALUES (:my, :med, :vn, 0, :iss, :bal, 'OPD Auto', 'OPD')
                            """, {"my": datetime.date.today().strftime("%B %Y"), "med": item['med'], "vn": "OPD-AI", "iss": item['qty'], "bal": newb})
                    
                    for k in list(st.session_state.keys()):
                        if k.startswith("ai_") or k == "dispense_list":
                            del st.session_state[k]
                    st.success("✅ Visit logged successfully!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()

# ====================== PAGE: REPORTS ======================
elif st.session_state.page == "Reports":
    st.markdown("<h1>📊 Analytics & Export</h1>", unsafe_allow_html=True)
    opd_trend = run_query("SELECT visit_date, COUNT(*) as footfall FROM opd_visits GROUP BY visit_date ORDER BY visit_date")
    if not opd_trend.empty:
        fig = px.bar(opd_trend, x='visit_date', y='footfall', title="Daily OPD Footfall", color_discrete_sequence=['#16a34a'])
        st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Current Stock Status")
    st.dataframe(get_all_balances(), use_container_width=True)
    
    if st.button("📥 Download Complete Excel Report"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            run_query("SELECT p.name as patient_name, o.* FROM opd_visits o JOIN patients p ON o.patient_id = p.id").to_excel(writer, sheet_name="OPD_Register", index=False)
            run_query("SELECT * FROM stock ORDER BY id DESC").to_excel(writer, sheet_name="Stock_Ledger", index=False)
            get_all_balances().to_excel(writer, sheet_name="Current_Stock", index=False)
            run_query("SELECT * FROM patients").to_excel(writer, sheet_name="Citizen_Registry", index=False)
        
        st.download_button(
            label="✅ Download Full Report",
            data=output.getvalue(),
            file_name=f"Ayushman_Report_{datetime.date.today().strftime('%d_%b_%Y')}.xlsx",
            mime="application/vnd.openxml
