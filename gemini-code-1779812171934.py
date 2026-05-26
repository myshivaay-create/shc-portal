import streamlit as st
import pandas as pd
import datetime
import io
import plotly.express as px
from sqlalchemy import text

# ==========================================
# 1. PAGE CONFIGURATION & PREMIUM THEME
# ==========================================
st.set_page_config(page_title="SHC Assistant Portal", page_icon="⚕️", layout="wide")

st.markdown("""
    <style>
    /* NHM / Ayushman Arogya Mandir Professional Theme */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp { background-color: #f8fafc; }
    
    h1, h2, h3 { color: #0f172a; font-weight: 700; }
    h4 { color: #16a34a; font-weight: 600; }
    
    /* Professional Buttons */
    .stButton>button {
        background-color: #16a34a; color: white; border-radius: 6px; 
        font-size: 15px; font-weight: 600; padding: 10px 20px; border: none; width: 100%;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .stButton>button:hover { 
        background-color: #15803d; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.15); 
        transform: translateY(-1px);
    }
    
    /* Premium Metric Cards */
    .metric-container {
        display: flex; justify-content: space-between; gap: 20px; margin-bottom: 25px;
    }
    .metric-card {
        background-color: white; border-left: 5px solid #16a34a; 
        padding: 20px; border-radius: 10px; flex: 1;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    }
    .metric-card p { margin: 0; font-size: 0.9rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;}
    .metric-card h2 { margin: 5px 0 0 0; font-size: 2.2rem; color: #0f172a; }
    .metric-card.alert { border-left-color: #ef4444; }
    .metric-card.alert h2 { color: #ef4444; }
    
    /* Layout Adjustments */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        border-radius: 6px 6px 0 0; padding: 10px 20px; background-color: #e2e8f0; 
    }
    .stTabs [aria-selected="true"] { background-color: #16a34a; color: white; }
    
    .sidebar-header { text-align: center; padding-bottom: 20px; border-bottom: 1px solid #e2e8f0; margin-bottom: 20px;}
    .sidebar-header h2 { font-size: 1.2rem; margin: 10px 0 5px 0; color: #16a34a;}
    .sidebar-header p { font-size: 0.8rem; color: #64748b; margin:0;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CLOUD DATABASE CONNECTION
# ==========================================
conn = st.connection("postgresql", type="sql")

def init_db():
    with conn.session as s:
        s.execute(text('''CREATE TABLE IF NOT EXISTS medicines (id SERIAL PRIMARY KEY, name TEXT UNIQUE)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS patients (
            id SERIAL PRIMARY KEY, name TEXT, age INTEGER, gender TEXT, village TEXT, family_id TEXT, phone TEXT
        )'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS stock (
            id SERIAL PRIMARY KEY, month_year TEXT, medicine_name TEXT, voucher_no TEXT,
            qty_received INTEGER, qty_issued INTEGER, balance INTEGER, remark TEXT, page_no TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS opd_visits (
            id SERIAL PRIMARY KEY, patient_id INTEGER, visit_date DATE,
            vitals TEXT, symptoms TEXT, diagnosis TEXT, treatment TEXT
        )'''))
        
        # Default essential meds
        res = s.execute(text("SELECT COUNT(*) FROM medicines")).fetchone()
        if res[0] == 0:
            defaults = ["Tab Paracetamol 500mg", "Tab Amoxicillin 500mg", "ORS Packets", "Tab IFA", "Tab Albendazole 400mg", "Tab Zinc 20mg"]
            for med in defaults:
                s.execute(text("INSERT INTO medicines (name) VALUES (:name) ON CONFLICT DO NOTHING"), {"name": med})
        s.commit()

try:
    init_db()
except Exception as e:
    st.info("ℹ️ System is in setup mode. Please configure database credentials in Streamlit Secrets.")
    st.stop()

def run_query(query, params=None):
    if params is None: params = {}
    return pd.read_sql(text(query), conn.engine, params=params)

def execute_query(query, params=None):
    if params is None: params = {}
    with conn.session as s:
        s.execute(text(query), params)
        s.commit()

def get_all_balances():
    return run_query("SELECT medicine_name, SUM(qty_received) - SUM(qty_issued) as current_balance FROM stock GROUP BY medicine_name")

def get_med_balance(med_name):
    df = run_query("SELECT SUM(qty_received) - SUM(qty_issued) as bal FROM stock WHERE medicine_name=:med", {"med": med_name})
    return int(df.iloc[0]['bal']) if pd.notna(df.iloc[0]['bal']) else 0

# ==========================================
# 3. SIDEBAR NAVIGATION (Professional UI)
# ==========================================
if 'page' not in st.session_state: st.session_state.page = "Dashboard"
def nav_to(page_name): st.session_state.page = page_name

with st.sidebar:
    st.markdown("""
        <div class="sidebar-header">
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/1/13/National_Health_Mission_Logo.svg/300px-National_Health_Mission_Logo.svg.png" width="100">
            <h2>Ayushman Arogya Mandir</h2>
            <p>Sub-Health Center • Jodhpur Zone</p>
        </div>
    """, unsafe_allow_html=True)
    
    PAGES = ["Dashboard", "Master Data", "Stock Inventory", "Smart OPD (AI)", "Reports & Analytics"]
    for p in PAGES:
        if st.button(p, key=f"nav_{p}"): nav_to(p); st.rerun()

# ==========================================
# 4. PAGE: DASHBOARD
# ==========================================
if st.session_state.page == "Dashboard":
    st.markdown("<h1>System Dashboard</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#64748b; font-weight:600;'>Operating Date: {datetime.date.today().strftime('%B %d, %Y')}</p>", unsafe_allow_html=True)
    
    today_opd = run_query("SELECT COUNT(*) as c FROM opd_visits WHERE visit_date=:d", {"d": str(datetime.date.today())}).iloc[0]['c']
    stock_df = get_all_balances()
    low_stock = len(stock_df[stock_df['current_balance'] < 100]) if not stock_df.empty else 0
    total_reg = run_query("SELECT COUNT(*) as c FROM patients").iloc[0]['c']
    
    st.markdown(f"""
        <div class="metric-container">
            <div class="metric-card">
                <p>Today's OPD Footfall</p>
                <h2>{today_opd}</h2>
            </div>
            <div class="metric-card">
                <p>Registered Citizens</p>
                <h2>{total_reg}</h2>
            </div>
            <div class="metric-card alert">
                <p>Low Stock Alerts</p>
                <h2>{low_stock}</h2>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.write("---")
    st.markdown("<h3>Quick Actions</h3>", unsafe_allow_html=True)
    q1, q2, q3 = st.columns(3)
    with q1:
        if st.button("🩺 Start Smart OPD"): nav_to("Smart OPD (AI)"); st.rerun()
    with q2:
        if st.button("📦 Receive Supply"): nav_to("Stock Inventory"); st.rerun()
    with q3:
        if st.button("📊 View Reports"): nav_to("Reports & Analytics"); st.rerun()

# ==========================================
# 5. PAGE: MASTER DATA
# ==========================================
elif st.session_state.page == "Master Data":
    st.markdown("<h1>Master Data Management</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["👥 Family & Citizen Register", "💊 Medicine Master"])
    
    with tab1:
        st.info("Upload standard Village Survey / Jan Aadhaar Excel (.xlsx)")
        uploaded_excel = st.file_uploader("Select File", type=['xlsx'])
        if uploaded_excel:
            df = pd.read_excel(uploaded_excel, engine='openpyxl')
            if st.button("Import Data"):
                for _, row in df.iterrows():
                    execute_query("INSERT INTO patients (name, age, gender, village, family_id, phone) VALUES (:name, :age, :gender, :village, :fid, :phone)", 
                                  {"name": str(row.get('Name','')), "age": int(row.get('Age',0)), "gender": str(row.get('Gender','')), "village": str(row.get('Village','')), "fid": str(row.get('FamilyID','')), "phone": str(row.get('Phone',''))})
                st.success("Citizen Data Imported Successfully!")
        st.dataframe(run_query("SELECT * FROM patients ORDER BY id DESC LIMIT 50"), use_container_width=True)
        
    with tab2:
        col1, col2 = st.columns([1, 2])
        with col1:
            new_med = st.text_input("Enter New Medicine Name")
            if st.button("Add to Master") and new_med:
                execute_query("INSERT INTO medicines (name) VALUES (:name) ON CONFLICT DO NOTHING", {"name": new_med})
                st.success(f"{new_med} added.")
        with col2:
            st.dataframe(run_query("SELECT * FROM medicines ORDER BY name"), use_container_width=True)

# ==========================================
# 6. PAGE: STOCK INVENTORY
# ==========================================
elif st.session_state.page == "Stock Inventory":
    st.markdown("<h1>Stock Inventory Register</h1>", unsafe_allow_html=True)
    med_list = run_query("SELECT name FROM medicines ORDER BY name")['name'].tolist()
    
    tab1, tab2, tab3 = st.tabs(["📝 Manual Entry", "📁 Bulk Upload (Excel)", "🔍 View Register"])
    
    with tab1:
        with st.form("stock_entry"):
            c1, c2 = st.columns(2)
            with c1:
                col_my = st.text_input("1. Month & Year", value=datetime.date.today().strftime("%B %Y"))
                col_med = st.selectbox("2. Medicine Name", med_list)
                col_vn = st.text_input("3. Voucher Number")
                col_pg = st.text_input("8. Physical Page No.")
            with c2:
                col_recv = st.number_input("4. Quantity Received", min_value=0, value=0)
                col_iss = st.number_input("5. Quantity Issued", min_value=0, value=0)
                col_rem = st.text_input("7. Remarks (Batch/Expiry)")
            
            if st.form_submit_button("Save Entry"):
                new_bal = get_med_balance(col_med) + col_recv - col_iss
                execute_query('''INSERT INTO stock (month_year, medicine_name, voucher_no, qty_received, qty_issued, balance, remark, page_no)
                                 VALUES (:my, :med, :vn, :rec, :iss, :bal, :rem, :pg)''', 
                              {"my": col_my, "med": col_med, "vn": col_vn, "rec": col_recv, "iss": col_iss, "bal": new_bal, "rem": col_rem, "pg": col_pg})
                st.success(f"Entry saved. Updated balance for {col_med}: {new_bal}")

    with tab2:
        st.info("Upload CHC e-Aushadhi Supply Receipt (.xlsx)")
        excel_file = st.file_uploader("Select Excel Receipt", type=['xlsx'])
        if excel_file:
            df_upload = pd.read_excel(excel_file, engine='openpyxl')
            extracted = []
            for _, row in df_upload.iterrows():
                med_name = row.get('Medicine Name', row.get('Item Name', ''))
                qty = row.get('Quantity', row.get('Qty', row.get('Received', 0)))
                if pd.notna(med_name) and str(med_name).strip() != '':
                    extracted.append({"month_year": datetime.date.today().strftime("%B %Y"), "medicine_name": str(med_name), "voucher_no": "UPLOAD", "qty_received": int(qty) if pd.notna(qty) else 0, "qty_issued": 0, "remark": "Bulk Entry", "page_no": "1"})
            
            if extracted:
                edited_df = st.data_editor(pd.DataFrame(extracted), num_rows="dynamic", use_container_width=True)
                if st.button("Confirm & Save All"):
                    for _, row in edited_df.iterrows():
                        execute_query("INSERT INTO medicines (name) VALUES (:name) ON CONFLICT DO NOTHING", {"name": row['medicine_name']})
                        new_bal = get_med_balance(row['medicine_name']) + int(row['qty_received']) - int(row['qty_issued'])
                        execute_query('''INSERT INTO stock (month_year, medicine_name, voucher_no, qty_received, qty_issued, balance, remark, page_no)
                                         VALUES (:my, :med, :vn, :rec, :iss, :bal, :rem, :pg)''', 
                                      {"my": row['month_year'], "med": row['medicine_name'], "vn": row['voucher_no'], "rec": row['qty_received'], "iss": row['qty_issued'], "bal": new_bal, "rem": row['remark'], "pg": row['page_no']})
                    st.success("Stock updated from Excel!")

    with tab3:
        st.dataframe(run_query("SELECT month_year, medicine_name, voucher_no, qty_received, qty_issued, balance, remark FROM stock ORDER BY id DESC LIMIT 100"), use_container_width=True)

# ==========================================
# 7. PAGE: SMART OPD (AI)
# ==========================================
elif st.session_state.page == "Smart OPD (AI)":
    st.markdown("<h1>🧠 Clinical AI Support & OPD</h1>", unsafe_allow_html=True)
    
    patients = run_query("SELECT * FROM patients")
    if patients.empty:
        st.warning("Ensure patient data exists in Master Data.")
    else:
        pat_dict = {f"{r['name']} (Age: {r['age']} | ID: {r['family_id']})": (r['id'], r['age']) for _, r in patients.iterrows()}
        c1, c2 = st.columns([1.2, 1])
        
        with c1:
            st.markdown("#### 1. Patient Assessment")
            with st.container(border=True):
                selected_pat = st.selectbox("Select Patient", list(pat_dict.keys()))
                pat_id, pat_age = pat_dict[selected_pat]
                pat_weight = st.number_input("Weight (Kg) (Required for pediatric calculation)", value=60 if pat_age > 12 else (pat_age*2)+8)
                
                st.write("**Vitals**")
                vc1, vc2, vc3, vc4 = st.columns(4)
                with vc1: temp = st.number_input("Temp (°F)", value=98.6, step=0.1)
                with vc2: spo2 = st.number_input("SpO2 (%)", value=98, max_value=100)
                with vc3: hr = st.number_input("Pulse (bpm)", value=75)
                with vc4: bp = st.text_input("BP", value="120/80")
                
                st.write("**Symptoms**")
                common_symptoms = ["Fever", "Cough", "Sore Throat", "Runny Nose", "Diarrhea", "Vomiting", "Abdominal Pain", "Headache", "Body Ache", "Burning Micturition"]
                selected_symp = st.multiselect("Select Primary Symptoms", common_symptoms)
                other_symp = st.text_input("Clinical Notes")
                
                analyze_btn = st.button("🔍 Generate AI Protocol")

        with c2:
            st.markdown("#### 2. AI Decision Support")
            if analyze_btn:
                with st.container(border=True):
                    diseases = {
                        "Upper Respiratory Tract Infection (URTI)": {"sym": ["Cough", "Sore Throat", "Runny Nose", "Fever"], "meds": ["Amoxicillin", "Paracetamol"]},
                        "Acute Gastroenteritis": {"sym": ["Diarrhea", "Vomiting", "Abdominal Pain", "Fever"], "meds": ["ORS", "Zinc", "Paracetamol"]},
                        "Viral Pyrexia": {"sym": ["Fever", "Body Ache", "Headache"], "meds": ["Paracetamol"]}
                    }
                    
                    best_match = "Symptomatic Care (Undifferentiated)"
                    best_score = 0
                    plan_meds = ["Paracetamol"] 
                    
                    for d_name, d_data in diseases.items():
                        score = sum(1 for s in selected_symp if s in d_data["sym"])
                        if score > best_score:
                            best_score = score; best_match = d_name; plan_meds = d_data["meds"]

                    st.markdown(f"**Predicted Pattern:** <span style='color:#16a34a;'>{best_match}</span>", unsafe_allow_html=True)
                    st.write("---")
                    
                    current_stock = get_all_balances()
                    stock_dict = dict(zip(current_stock['medicine_name'].str.lower(), current_stock['current_balance']))
                    
                    final_treatment_text = ""
                    dispense_list = []
                    
                    for med_base in plan_meds:
                        dose = "1 OD"
                        if "Paracetamol" in med_base: dose = "500mg SOS" if pat_age > 12 else f"{int(pat_weight * 15)}mg SOS"
                        elif "Amoxicillin" in med_base: dose = "500mg TDS x 5 Days" if pat_age > 12 else "Syrup TDS x 5 Days"
                        elif "Zinc" in med_base: dose = "20mg OD x 14 Days"
                        elif "ORS" in med_base: dose = "After loose stool"
                            
                        available_med = None
                        for stock_name, qty in stock_dict.items():
                            if med_base.lower() in stock_name and qty > 0:
                                available_med = stock_name.title(); break
                        
                        if available_med:
                            txt = f"💊 {available_med} - {dose}"
                            st.write(txt)
                            final_treatment_text += txt + "\n"
                            dispense_list.append({"med": available_med, "qty": 5 if "Amoxicillin" not in med_base else 15})
                        else: st.error(f"❌ {med_base} - OUT OF STOCK")
                    
                    st.session_state.temp_diagnosis = best_match
                    st.session_state.temp_treatment = final_treatment_text
                    st.session_state.temp_symp = ", ".join(selected_symp) + " | " + other_symp
                    st.session_state.temp_vitals = f"T:{temp}, SpO2:{spo2}, HR:{hr}, BP:{bp}"
                    st.session_state.dispense_list = dispense_list
            
            if 'temp_diagnosis' in st.session_state:
                st.write("")
                auto_deduct = st.checkbox("Auto-deduct dispensed quantity from Stock", value=True)
                if st.button("💾 Finalize & Log Visit"):
                    execute_query('''INSERT INTO opd_visits (patient_id, visit_date, vitals, symptoms, diagnosis, treatment)
                                     VALUES (:pid, :vd, :vit, :sym, :diag, :tx)''', 
                                  {"pid": pat_id, "vd": str(datetime.date.today()), "vit": st.session_state.temp_vitals, "sym": st.session_state.temp_symp, "diag": st.session_state.temp_diagnosis, "tx": st.session_state.temp_treatment})
                    
                    if auto_deduct:
                        my_str = datetime.date.today().strftime("%B %Y")
                        for item in st.session_state.dispense_list:
                            new_bal = get_med_balance(item['med']) - item['qty']
                            execute_query('''INSERT INTO stock (month_year, medicine_name, voucher_no, qty_received, qty_issued, balance, remark, page_no)
                                             VALUES (:my, :med, :vn, :rec, :iss, :bal, :rem, :pg)''', 
                                          {"my": my_str, "med": item['med'], "vn": "OPD-AUTO", "rec": 0, "iss": item['qty'], "bal": new_bal, "rem": "OPD Dispense", "pg": "OPD"})
                    
                    for key in ['temp_diagnosis', 'temp_treatment', 'temp_symp', 'temp_vitals', 'dispense_list']: del st.session_state[key]
                    st.success("Visit Logged Successfully!")

# ==========================================
# 8. PAGE: REPORTS & ANALYTICS
# ==========================================
elif st.session_state.page == "Reports & Analytics":
    st.markdown("<h1>📊 Analytics & Export</h1>", unsafe_allow_html=True)
    
    opd_df = run_query("SELECT visit_date, COUNT(id) as patients FROM opd_visits GROUP BY visit_date")
    if not opd_df.empty: 
        fig = px.bar(opd_df, x='visit_date', y='patients', title="Daily OPD Footfall", color_discrete_sequence=['#16a34a'])
        st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Current Stock Balances")
    full_stock = get_all_balances()
    st.dataframe(full_stock, use_container_width=True)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        run_query("SELECT p.name, o.* FROM opd_visits o JOIN patients p ON o.patient_id = p.id").to_excel(writer, index=False, sheet_name='OPD_Register')
        run_query("SELECT * FROM stock").to_excel(writer, index=False, sheet_name='Stock_Ledger')
        full_stock.to_excel(writer, index=False, sheet_name='Current_Balances')
        
    st.download_button(label="📥 Download Complete Report (Excel)", data=output.getvalue(),
                       file_name=f"SHC_Report_{datetime.date.today().strftime('%b_%Y')}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")