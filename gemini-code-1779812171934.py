import streamlit as st
import pandas as pd
import datetime
import io
import plotly.express as px
from sqlalchemy import text
import time

# ==========================================
# AYUSHMAN AROGY A MANDIR PORTAL - v2.7 (OPTIMIZED)
# Neon + Streamlit ke liye fast caching + Weight-based Dosage
# ==========================================

st.set_page_config(
    page_title="Ayushman Arogya Mandir",
    page_icon="⚕️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    * {font-family: 'Poppins', sans-serif;}
    .stApp {background: linear-gradient(135deg, #f0fdf4 0%, #e0f2fe 100%);}
    h1 {color: #0f172a; font-weight: 700; letter-spacing: -1px;}
    .metric-card {background: rgba(255,255,255,0.95); border-radius: 16px; padding: 24px; 
                  box-shadow: 0 10px 25px rgba(0,0,0,0.08); border-top: 6px solid #16a34a; text-align:center;}
    .stButton>button {background: linear-gradient(135deg, #16a34a, #15803d); border-radius: 12px; 
                      font-weight: 600; box-shadow: 0 6px 15px rgba(22,163,74,0.3);}
    .stButton>button:hover {transform: translateY(-4px); box-shadow: 0 12px 20px rgba(22,163,74,0.4);}
    .form-container {background: white; padding: 28px; border-radius: 16px; box-shadow: 0 8px 25px rgba(0,0,0,0.06);}
</style>
""", unsafe_allow_html=True)

# ====================== WEIGHT-BASED DOSAGE (IMPROVED) ======================
def get_weight_based_dosage(med_name: str, age_years: float, weight_kg: float) -> str:
    if weight_kg <= 0 or weight_kg > 150:
        weight_kg = max(5.0, age_years * 2 + 8)
        note = " (Weight estimated — measure accurately!)"
    else:
        note = ""

    med_l = med_name.lower().strip()
    is_child = (age_years < 12) and (weight_kg < 40)

    if not is_child:
        if "paracetamol" in med_l:
            return f"500–1000 mg every 4–6 hrs (max 4g/day){note}"
        elif "amoxycillin" in med_l or "amoxicillin" in med_l:
            return f"500 mg TDS or 875 mg BD × 5–7 days{note}"
        elif "zinc" in med_l:
            return "20–40 mg elemental zinc daily"
        elif "ors" in med_l:
            return "1 sachet after each loose stool (or 75 ml/kg rehydration)"
        elif "cetirizine" in med_l or "levocetirizine" in med_l:
            return "10 mg once daily (evening)"
        else:
            return f"Standard adult dose{note}"

    # Pediatric
    if "paracetamol" in med_l:
        dose_mg = round(weight_kg * 15)
        max_daily = min(round(weight_kg * 60), 4000)
        return f"{dose_mg} mg per dose (15 mg/kg) every 4–6 hrs (max 4 doses). Max daily ~{max_daily} mg.{note}"

    elif "amoxycillin" in med_l or "amoxicillin" in med_l:
        daily = round(weight_kg * 40)
        per_dose = round(daily / 3)
        ml = round(per_dose / 50, 1)
        return f"~{per_dose} mg TDS ({40} mg/kg/day). ~{ml} ml of 250mg/5ml syrup TDS × 5 days.{note}"

    elif "zinc" in med_l:
        return "20 mg daily × 10–14 days (diarrhea)" if age_years >= 0.5 else "10 mg daily × 10–14 days."

    elif "ors" in med_l:
        rehyd = round(weight_kg * 75)
        return f"After each loose stool. Some dehydration: ~{rehyd} ml over 4 hrs."

    elif "cetirizine" in med_l or "levocetirizine" in med_l:
        if age_years < 2: return "2.5 mg once daily"
        elif age_years < 6: return "5 mg once daily"
        else: return "5–10 mg once daily"

    else:
        return f"Standard pediatric dose for {weight_kg} kg, {age_years} yr.{note}"

# ====================== DATABASE + CACHING (OPTIMIZED FOR SPEED) ======================
@st.cache_resource(ttl=7200)
def get_connection():
    try:
        return st.connection("postgresql", type="sql")
    except Exception:
        st.error("🚨 Database connection failed. Check Neon Secrets.")
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
            visit_date DATE, vitals TEXT, symptoms TEXT, diagnosis TEXT, treatment TEXT, dispensed_meds TEXT)'''))

        borunda_medicines = [
            "Adrenaline Injection IP 1mg/ml (IM/IV use)", "Albendazole Oral suspension IP 400 mg/10ml",
            "Albendazole Tablets IP 400 mg", "Amlodipine Tablets IP 5 mg", "Amoxycillin Cap IP 250mg",
            "Amoxycillin Capsules IP 500 Mg", "Amoxycillin Oral Suspension IP (Dry syrup) 125 mg/5ml",
            "Antacid Tablets Formula contains Magnesium Trisilicate 250 mg, Dried Aluminium Hydroxide Gel 120 mg, Peppermint Oil",
            "Antacid Syrup Each 5 Ml Contains Phenylephrine Hydrochloride 2.5mg, Chlorpheniramine Maleate 1 Mg, And Paracetamol 125 Mg",
            "Calcium and Vitamin D3 Suspension", "Cerumolytic Drops (Wax dissolving ear drops)",
            "Cetirizine syrup IP 5mg/5 ml", "Chloroquine Phosphate Tab. IP 250mg",
            "Ciprofloxacin Eye Drops IP 0.3% w/v", "Ciprofloxacin Tablet IP 500 mg Film Coated",
            "Clotrimazole mouth paint (Clotrimazole 1% w/w)", "Co-trimoxazole Tablets IP",
            "Co-trimoxazole oral suspension IP", "Compound Sodium Lactate Inj. IP",
            "Dextrose Inj IP 25% w/v", "Dextrose Inj IP 5%", "Diclofenac Gastro Resistant Tablet IP 50 mg",
            "Diclofenac Sodium Inj IP 25 mg/ ml (IM/IV Use)", "Diclofenac Gel",
            "Dicyclomine Inj IP 10 mg /ml", "Dicyclomine and Paracetamol Tablets",
            "Domperidone Suspension IP 5mg/5ml", "Domperidone Tab IP 10 mg",
            "Face Mask, Disposable", "Ferrous Sulphate With Folic Acid Tab",
            "Ferrous Sulphate with Folic Acid Tab IP (Paediatric)", "Fluconazole Tablets IP 150mg",
            "Folic Acid Tab IP 5 mg", "Framycetin Sulphate Cream 1% 30gm Pack",
            "Furosemide Injection IP 10mg/ml", "Gloves Size 6.5 Inches",
            "Hydrocortisone Sodium Succinate Injection IP 100 mg", "Hydrogen Peroxide Solution IP 6 Percent",
            "Hyoscine Butyl bromide Tablets IP 10mg", "Ibuprofen Tab IP 200 mg",
            "Isosorbide dinitrate Tab IP 5 mg", "Lactulose solution", "Levocetirizine Tablet 5mg",
            "Metronidazole Tablets IP 200 mg", "Metronidazole Tablets IP 400 mg",
            "Norfloxacin Tab IP 400mg Film Coated", "Ondansetron Inj IP 2mg /ml",
            "Ondansetron Oral Suspension/Solution/ Syrup 2mg/5ml", "Ondansetron Orally Disintegrating Tablets IP 4mg",
            "ORS Powder IP", "Paracetamol Drops Pediatric", "Paracetamol Tab IP 500 mg",
            "Pethidine Inj IP", "Povidone Iodine Ointment 5% 15 gm", "Povidone Iodine solution IP 5 %",
            "Primaquine Tab IP 2.5 mg", "Primaquine Tab IP 7.5 mg", "Ranitidine HCL Injection IP 50mg/2ml",
            "Salbutamol Tab IP 2 mg", "Salbutamol Syrup IP 2mg/5ml", "Sodium Chloride Inj IP 500 ml",
            "Sterile Hypodermic Syringe with Needle", "Surgical Spirit IP (100 ml)",
            "Vitamin A Paediatric Oral Solution IP", "Vitamin B complex Tablet NFI",
            "Zinc Sulphate Dispersible Tablets IP Elemental Zinc 10 mg"
        ]
        for med in borunda_medicines:
            s.execute(text("INSERT INTO medicines (name) VALUES (:name) ON CONFLICT DO NOTHING"), {"name": med})
        s.commit()

init_db()

# ====================== CACHED FUNCTIONS (SPEED OPTIMIZED) ======================
@st.cache_data(ttl=600)
def get_all_medicines():
    return pd.read_sql(text("SELECT name FROM medicines ORDER BY name"), conn.engine)['name'].tolist()

@st.cache_data(ttl=300)
def get_all_balances():
    df = pd.read_sql(text("""
        SELECT medicine_name, SUM(qty_received) - SUM(qty_issued) as current_balance 
        FROM stock GROUP BY medicine_name HAVING SUM(qty_received) - SUM(qty_issued) >= 0
    """), conn.engine)
    return df if not df.empty else pd.DataFrame(columns=["medicine_name", "current_balance"])

@st.cache_data(ttl=300)
def get_dashboard_data():
    today = datetime.date.today()
    today_opd = pd.read_sql(text("SELECT COUNT(*) as c FROM opd_visits WHERE visit_date = :d"), 
                            conn.engine, params={"d": today}).iloc[0]['c']
    total_patients = pd.read_sql(text("SELECT COUNT(*) as c FROM patients"), conn.engine).iloc[0]['c']
    stock_df = get_all_balances()
    low_stock = len(stock_df[stock_df['current_balance'] < 50]) if not stock_df.empty else 0
    return today_opd, total_patients, low_stock

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
            <p style="color:#64748b; font-size:0.9rem;">CHC Borunda • Fast Portal v2.7</p>
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

# ====================== DASHBOARD (CACHED) ======================
if st.session_state.page == "Dashboard":
    st.markdown("<h1>👋 Namaste CHO Ji!</h1>", unsafe_allow_html=True)
    st.markdown(f"**Today:** {datetime.date.today().strftime('%A, %d %B %Y')} | CHC Borunda")

    today_opd, total_patients, low_stock = get_dashboard_data()

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("🩺 Today's OPD", today_opd)
    with col2: st.metric("👥 Total Citizens", total_patients)
    with col3: st.metric("⚠️ Low Stock Items", low_stock, delta_color="inverse")
    with col4: st.metric("💊 Total Medicines", len(get_all_medicines()))

    st.markdown("### ⚡ Quick Actions")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🩺 Start Smart OPD", use_container_width=True, type="primary"):
            st.session_state.page = "Smart OPD (AI)"; st.rerun()
    with c2:
        if st.button("📦 Update Stock", use_container_width=True):
            st.session_state.page = "Stock Inventory"; st.rerun()
    with c3:
        if st.button("📊 Download Report", use_container_width=True):
            st.session_state.page = "Reports"; st.rerun()

# ====================== MASTER DATA ======================
elif st.session_state.page == "Master Data":
    st.markdown("<h1>🗂️ Master Data Hub</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["👨‍👩‍👧‍👦 Citizen Registry", "💊 Medicine Database"])
    
    with tab1:
        st.subheader("Bulk Import Citizens from Excel")
        uploaded = st.file_uploader("Upload .xlsx", type=["xlsx"], key="pat_upload")
        if uploaded:
            df = pd.read_excel(uploaded, engine='openpyxl')
            st.dataframe(df.head(10), use_container_width=True)
            if st.button("🚀 Import All Citizens", type="primary"):
                with st.spinner("Importing..."):
                    success = 0
                    for _, row in df.iterrows():
                        try:
                            execute_query("""INSERT INTO patients (name, age, gender, village, family_id, phone)
                                             VALUES (:n, :a, :g, :v, :f, :p) ON CONFLICT (family_id) DO NOTHING""", {
                                "n": str(row.get('Name', '')), 
                                "a": int(row.get('Age', 0)) if pd.notna(row.get('Age')) else 0,
                                "g": str(row.get('Gender', '')), "v": str(row.get('Village', '')),
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
        st.subheader("💊 Medicine Database")
        st.info(f"**Total Medicines: {len(get_all_medicines())}** (All 66 CHC Borunda medicines loaded)")
        if st.button("🔄 Refresh All Medicines", type="primary"):
            init_db()
            st.cache_data.clear()
            st.success("✅ All medicines refreshed!")
            st.rerun()
        st.dataframe(pd.DataFrame(get_all_medicines(), columns=["Medicine Name"]), use_container_width=True)

# ====================== STOCK INVENTORY (FULL) ======================
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
                execute_query("""INSERT INTO stock (month_year, medicine_name, voucher_no, qty_received, qty_issued, balance, remark, page_no)
                                 VALUES (:my, :med, :vn, :rec, :iss, :bal, :rem, :pg)""", {
                    "my": month_year, "med": medicine, "vn": voucher or "Manual",
                    "rec": received, "iss": issued, "bal": new_bal,
                    "rem": remark or "Manual Entry", "pg": page_no or "1"
                })
                st.success(f"✅ Saved! New balance: **{new_bal}**")
                st.cache_data.clear()
                st.balloons()

    with tab2:
        st.info("Upload CHC Borunda / e-Aushadhi Supply Receipt")
        excel_file = st.file_uploader("Upload Excel", type=["xlsx"], key="stock_bulk")
        if excel_file:
            df_raw = pd.read_excel(excel_file, engine='openpyxl', header=3)
            df_raw.columns = [str(col).strip() for col in df_raw.columns]
            med_col = next((col for col in df_raw.columns if 'Item_Name' in col or 'Item Name' in col), None)
            qty_col = next((col for col in df_raw.columns if 'Issue_Qty' in col or 'Qty' in col), None)
            
            if med_col and qty_col:
                extracted = []
                for _, r in df_raw.iterrows():
                    med_name = str(r[med_col]).strip()
                    if med_name and med_name.lower() != 'nan' and 'GRAND TOTAL' not in med_name:
                        extracted.append({
                            "month_year": datetime.date.today().strftime("%B %Y"),
                            "medicine_name": med_name,
                            "voucher_no": "CHC-BULK",
                            "qty_received": int(r[qty_col]) if pd.notna(r[qty_col]) else 0,
                            "qty_issued": 0,
                            "remark": "Borunda Indent",
                            "page_no": "1"
                        })
                st.success(f"✅ {len(extracted)} medicines extracted!")
                edited = st.data_editor(pd.DataFrame(extracted), use_container_width=True, num_rows="dynamic")
                if st.button("✅ Save All to Stock"):
                    with st.spinner("Saving..."):
                        for _, row in edited.iterrows():
                            execute_query("INSERT INTO medicines (name) VALUES (:n) ON CONFLICT DO NOTHING", {"n": row['medicine_name']})
                            new_b = get_med_balance(row['medicine_name']) + int(row['qty_received'])
                            execute_query("""INSERT INTO stock (month_year, medicine_name, voucher_no, qty_received, qty_issued, balance, remark, page_no)
                                             VALUES (:my, :med, :vn, :rec, :iss, :bal, :rem, :pg)""", 
                                          {**row.to_dict(), "bal": new_b})
                        st.success("🎉 Stock updated!")
                        st.cache_data.clear()

    with tab3:
        st.dataframe(run_query("SELECT * FROM stock ORDER BY id DESC LIMIT 100"), use_container_width=True)

# ====================== SMART OPD (AI) + WEIGHT DOSAGE ======================
elif st.session_state.page == "Smart OPD (AI)":
    st.markdown("<h1>🩺 Smart OPD with AI + Weight-Based Dosage</h1>", unsafe_allow_html=True)
    
    patients = run_query("SELECT id, name, age, gender, family_id FROM patients ORDER BY name")
    if patients.empty:
        st.warning("No patients found. Add in Master Data first.")
    else:
        patient_options = [f"{r['name']} (Age: {r['age']}, ID: {r['family_id']})" for _, r in patients.iterrows()]
        pat_dict = {opt: (row['id'], row['age']) for opt, row in zip(patient_options, patients.to_dict('records'))}
        
        colA, colB = st.columns([1.3, 1])
        with colA:
            st.subheader("👤 Patient Assessment")
            selected = st.selectbox("Select Patient", patient_options)
            pat_id, pat_age = pat_dict[selected]
            
            default_weight = 60 if pat_age >= 12 else max(5, pat_age * 2 + 8)
            pat_weight = st.number_input("Weight (kg) - Required for pediatric dosage", value=default_weight, step=0.5)
            
            st.subheader("Vitals")
            v1, v2, v3, v4 = st.columns(4)
            with v1: temp = st.number_input("Temperature (°F)", value=98.6, step=0.1)
            with v2: spo2 = st.number_input("SpO2 (%)", value=98, max_value=100)
            with v3: pulse = st.number_input("Pulse (bpm)", value=78)
            with v4: bp = st.text_input("BP", "120/80")
            
            st.subheader("Symptoms")
            common_symptoms = ["Fever", "Cough", "Cold", "Runny Nose", "Sore Throat", "Bodyache", "Headache", "Diarrhea", "Vomiting", "Abdominal Pain"]
            selected_symp = st.multiselect("Select Symptoms", common_symptoms, default=["Fever"])
            notes = st.text_area("Additional Clinical Notes", height=100)
            
            if st.button("🔍 Run AI Diagnosis + Dosage", type="primary", use_container_width=True):
                symptom_text = " ".join(selected_symp).lower() + " " + notes.lower()
                
                diseases = {
                    "Viral Fever / Pyrexia": {"meds": ["Paracetamol Tab IP 500 mg"]},
                    "Upper Respiratory Tract Infection (URTI)": {"meds": ["Amoxycillin Capsules IP 500 Mg", "Cetirizine syrup IP 5mg/5 ml", "Paracetamol Tab IP 500 mg"]},
                    "Acute Gastroenteritis": {"meds": ["ORS Powder IP", "Zinc Sulphate Dispersible Tablets IP Elemental Zinc 10 mg"]},
                    "Allergic Rhinitis": {"meds": ["Cetirizine syrup IP 5mg/5 ml", "Levocetirizine Tablet 5mg"]}
                }
                
                best_disease = max(diseases, key=lambda x: (3 if "fever" in symptom_text else 0) + 
                                   (4 if "cough" in symptom_text or "sore" in symptom_text else 0) +
                                   (4 if "diarrhea" in symptom_text or "vomit" in symptom_text else 0))
                
                st.session_state.ai_diagnosis = best_disease
                st.session_state.ai_meds = diseases[best_disease]["meds"]
                st.session_state.ai_vitals = f"T:{temp}°F | SpO2:{spo2}% | HR:{pulse} | BP:{bp} | Wt:{pat_weight}kg"
                st.session_state.ai_symptoms = ", ".join(selected_symp)
                st.session_state.pat_age = pat_age
                st.session_state.pat_weight = pat_weight
                st.rerun()
        
        with colB:
            st.subheader("🧠 AI Recommendation + Dosage")
            if 'ai_diagnosis' in st.session_state:
                st.markdown(f"**Diagnosis:** <span style='color:#16a34a; font-size:1.4rem;'>{st.session_state.ai_diagnosis}</span>", unsafe_allow_html=True)
                
                current_stock = get_all_balances()
                stock_map = {m.lower(): bal for m, bal in zip(current_stock['medicine_name'], current_stock['current_balance'])}
                
                dispense_list = []
                for med in st.session_state.ai_meds:
                    avail = next((m for m in stock_map if med.lower() in m.lower() and stock_map[m] > 0), None)
                    if avail:
                        dosage_info = get_weight_based_dosage(avail, float(st.session_state.pat_age), float(st.session_state.pat_weight))
                        st.success(f"✅ **{avail}**")
                        st.markdown(f"**Dosage:** {dosage_info}")
                        dispense_list.append({"med": avail, "qty": 10})
                    else:
                        st.error(f"❌ {med} — Out of Stock")
                
                st.session_state.dispense_list = dispense_list
                
                if st.button("💾 Finalize & Log OPD Visit", type="primary"):
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
                    st.success("✅ Visit Logged Successfully!")
                    st.balloons()
                    for k in list(st.session_state.keys()):
                        if k.startswith("ai_") or k in ["dispense_list", "pat_age", "pat_weight"]:
                            if k in st.session_state: del st.session_state[k]
                    st.rerun()

# ====================== REPORTS ======================
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
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

st.sidebar.caption("🚀 v2.7 • Weight-Based Dosage + Strong Caching • Neon Optimized")
