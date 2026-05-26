import streamlit as st
import pandas as pd
import datetime
import io
import plotly.express as px
from sqlalchemy import text

# ==========================================
# 1. PAGE CONFIGURATION & PREMIUM V2 THEME
# ==========================================
st.set_page_config(page_title="Ayushman Arogya Mandir Portal", page_icon="⚕️", layout="wide")

# ADVANCED CSS FOR PREMIUM LOOK
st.markdown("""
    <style>
    /* Import Premium Font */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }
    
    /* Soft Modern Background */
    .stApp { 
        background: linear-gradient(135deg, #f0fdf4 0%, #e0f2fe 100%); 
    }
    
    /* Main Headers */
    h1 { color: #0f172a; font-weight: 700; letter-spacing: -1px; text-shadow: 1px 1px 2px rgba(0,0,0,0.05); }
    h2, h3 { color: #1e293b; font-weight: 600; }
    h4 { color: #15803d; font-weight: 600; }
    
    /* Gradient Animated Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
        color: white; 
        border-radius: 30px; 
        font-size: 16px; 
        font-weight: 600; 
        padding: 12px 24px; 
        border: none; 
        width: 100%;
        box-shadow: 0 4px 15px rgba(22, 163, 74, 0.3);
        transition: all 0.3s ease;
    }
    .stButton>button:hover { 
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(22, 163, 74, 0.4);
    }
    
    /* Download Button Specific */
    .stDownloadButton>button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);
    }
    
    /* Beautiful 3D Metric Cards */
    .metric-container {
        display: flex; justify-content: space-between; gap: 25px; margin-top: 15px; margin-bottom: 30px;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        border-top: 5px solid #16a34a; 
        padding: 25px; 
        border-radius: 15px; 
        flex: 1;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        text-align: center;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
    }
    .metric-card p { margin: 0; font-size: 1rem; color: #64748b; font-weight: 500; }
    .metric-card h2 { margin: 10px 0 0 0; font-size: 2.8rem; color: #0f172a; font-weight: 700; }
    
    /* Alert Card Styling */
    .metric-card.alert { border-top-color: #ef4444; }
    .metric-card.alert h2 { color: #ef4444; }
    
    /* Professional Tabs */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 8px; 
        background-color: rgba(255,255,255,0.5); 
        padding: 5px; 
        border-radius: 12px; 
    }
    .stTabs [data-baseweb="tab"] { 
        border-radius: 8px; 
        padding: 12px 24px; 
        background-color: transparent; 
        border: none;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #16a34a !important; 
        color: white !important; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        box-shadow: 4px 0 15px rgba(0,0,0,0.03);
    }
    .sidebar-header { 
        text-align: center; padding: 20px 0; border-bottom: 2px dashed #e2e8f0; margin-bottom: 25px;
    }
    .sidebar-header h2 { font-size: 1.4rem; margin: 15px 0 5px 0; color: #15803d; font-weight: 700;}
    .sidebar-header p { font-size: 0.85rem; color: #64748b; margin:0; font-weight: 500;}
    
    /* Custom Containers */
    .form-container {
        background: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.03);
    }
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
        
        res = s.execute(text("SELECT COUNT(*) FROM medicines")).fetchone()
        if res[0] == 0:
            defaults = ["Tab Paracetamol 500mg", "Tab Amoxicillin 500mg", "ORS Packets", "Tab IFA", "Tab Albendazole 400mg", "Tab Zinc 20mg"]
            for med in defaults:
                s.execute(text("INSERT INTO medicines (name) VALUES (:name) ON CONFLICT DO NOTHING"), {"name": med})
        s.commit()

try:
    init_db()
except Exception as e:
    st.error("Database Connection Error! Check Streamlit Secrets.")
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
# 3. SIDEBAR NAVIGATION
# ==========================================
if 'page' not in st.session_state: st.session_state.page = "Dashboard"
def nav_to(page_name): st.session_state.page = page_name

with st.sidebar:
    st.markdown("""
        <div class="sidebar-header">
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/1/13/National_Health_Mission_Logo.svg/300px-National_Health_Mission_Logo.svg.png" width="120" style="border-radius: 10px;">
            <h2>Ayushman Arogya Mandir</h2>
            <p>🌟 Rural Health Care Portal</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.write("### 📌 Navigation Menu")
    PAGES = {"🏠 Dashboard": "Dashboard", "👥 Master Data": "Master Data", "📦 Stock Inventory": "Stock Inventory", "🩺 Smart OPD (AI)": "Smart OPD (AI)", "📊 Analytics & Export": "Reports & Analytics"}
    
    for label, page_name in PAGES.items():
        if st.button(label, key=f"nav_{page_name}"): 
            nav_to(page_name)
            st.rerun()
            
    st.markdown("<br><br><br><p style='text-align:center; color:#94a3b8; font-size:12px;'>Secure Portal V2.0<br>Connected to Cloud DB</p>", unsafe_allow_html=True)

# ==========================================
# 4. PAGE: DASHBOARD
# ==========================================
if st.session_state.page == "Dashboard":
    st.markdown("<h1>👋 Welcome back, CHO!</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#64748b; font-size:16px;'>Overview for today: <b>{datetime.date.today().strftime('%A, %B %d, %Y')}</b></p>", unsafe_allow_html=True)
    
    today_opd = run_query("SELECT COUNT(*) as c FROM opd_visits WHERE visit_date=:d", {"d": str(datetime.date.today())}).iloc[0]['c']
    stock_df = get_all_balances()
    low_stock = len(stock_df[stock_df['current_balance'] < 100]) if not stock_df.empty else 0
    total_reg = run_query("SELECT COUNT(*) as c FROM patients").iloc[0]['c']
    
    st.markdown(f"""
        <div class="metric-container">
            <div class="metric-card">
                <p>🩺 Today's OPD</p>
                <h2>{today_opd}</h2>
            </div>
            <div class="metric-card">
                <p>👥 Total Citizens</p>
                <h2>{total_reg}</h2>
            </div>
            <div class="metric-card alert">
                <p>⚠️ Low Stock Items</p>
                <h2>{low_stock}</h2>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### ⚡ Quick Launch")
    q1, q2, q3 = st.columns(3)
    with q1:
        if st.button("📝 Register New Patient"): nav_to("Smart OPD (AI)"); st.rerun()
    with q2:
        if st.button("📥 Update Stock Entry"): nav_to("Stock Inventory"); st.rerun()
    with q3:
        if st.button("📈 Download Report"): nav_to("Reports & Analytics"); st.rerun()

# ==========================================
# 5. PAGE: MASTER DATA
# ==========================================
elif st.session_state.page == "Master Data":
    st.markdown("<h1>🗂️ Master Data Hub</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["👨‍👩‍👧‍👦 Citizen Registry", "💊 Medicine Database"])
    
    with tab1:
        st.markdown("<div class='form-container'>", unsafe_allow_html=True)
        st.info("Upload Village Survey / Jan Aadhaar Excel (.xlsx)")
        uploaded_excel = st.file_uploader("Select File", type=['xlsx'])
        if uploaded_excel:
            df = pd.read_excel(uploaded_excel, engine='openpyxl')
            if st.button("Import Data to Cloud"):
                for _, row in df.iterrows():
                    execute_query("INSERT INTO patients (name, age, gender, village, family_id, phone) VALUES (:name, :age, :gender, :village, :fid, :phone)", 
                                  {"name": str(row.get('Name','')), "age": int(row.get('Age',0)), "gender": str(row.get('Gender','')), "village": str(row.get('Village','')), "fid": str(row.get('FamilyID','')), "phone": str(row.get('Phone',''))})
                st.success("Citizen Data Imported Successfully!")
        st.markdown("<br><b>Recent Registrations:</b>", unsafe_allow_html=True)
        st.dataframe(run_query("SELECT * FROM patients ORDER BY id DESC LIMIT 50"), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with tab2:
        st.markdown("<div class='form-container'>", unsafe_allow_html=True)
        col1, col2 = st.columns([1, 2])
        with col1:
            new_med = st.text_input("Enter New Medicine Name")
            if st.button("➕ Add to Database") and new_med:
                execute_query("INSERT INTO medicines (name) VALUES (:name) ON CONFLICT DO NOTHING", {"name": new_med})
                st.success(f"{new_med} added.")
        with col2:
            st.dataframe(run_query("SELECT * FROM medicines ORDER BY name"), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 6. PAGE: STOCK INVENTORY
# ==========================================
elif st.session_state.page == "Stock Inventory":
    st.markdown("<h1>📦 Smart Stock Inventory</h1>", unsafe_allow_html=True)
    med_list = run_query("SELECT name FROM medicines ORDER BY name")['name'].tolist()
    
    tab1, tab2, tab3 = st.tabs(["✍️ Manual Entry", "📂 Excel Supply Upload", "📋 View Live Register"])
    
    with tab1:
        st.markdown("<div class='form-container'>", unsafe_allow_html=True)
        with st.form("stock_entry"):
            st.write("#### Add New Transaction")
            c1, c2 = st.columns(2)
            with c1:
                col_my = st.text_input("1. Month & Year", value=datetime.date.today().strftime("%B %Y"))
                col_med = st.selectbox("2. Medicine Name", med_list)
                col_vn = st.text_input("3. Voucher Number")
                col_pg = st.text_input("8. Physical Page No.")
            with c2:
                col_recv = st.number_input("4. Quantity Received (IN)", min_value=0, value=0)
                col_iss = st.number_input("5. Quantity Issued (OUT)", min_value=0, value=0)
                col_rem = st.text_input("7. Remarks (Batch/Expiry)")
            
            if st.form_submit_button("💾 Save to Cloud Register"):
                new_bal = get_med_balance(col_med) + col_recv - col_iss
                execute_query('''INSERT INTO stock (month_year, medicine_name, voucher_no, qty_received, qty_issued, balance, remark, page_no)
                                 VALUES (:my, :med, :vn, :rec, :iss, :bal, :rem, :pg)''', 
                              {"my": col_my, "med": col_med, "vn": col_vn, "rec": col_recv, "iss": col_iss, "bal": new_bal, "rem": col_rem, "pg": col_pg})
                st.success(f"Transaction Saved! Updated balance for {col_med}: {new_bal}")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown("<div class='form-container'>", unsafe_allow_html=True)
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
                if st.button("✅ Confirm & Save All"):
                    for _, row in edited_df.iterrows():
                        execute_query("INSERT INTO medicines (name) VALUES (:name) ON CONFLICT DO NOTHING", {"name": row['medicine_name']})
                        new_bal = get_med_balance(row['medicine_name']) + int(row['qty_received']) - int(row['qty_issued'])
                        execute_query('''INSERT INTO stock (month_year, medicine_name, voucher_no, qty_received, qty_issued, balance, remark, page_no)
                                         VALUES (:my, :med, :vn, :rec, :iss, :bal, :rem, :pg)''', 
                                      {"my": row['month_year'], "med": row['medicine_name'], "vn": row['voucher_no'], "rec": row['qty_received'], "iss": row['qty_issued'], "bal": new_bal, "rem": row['remark'], "pg": row['page_no']})
                    st.success("Stock updated from Excel!")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab3:
        st.dataframe(run_query("SELECT month_year, medicine_name, voucher_no, qty_received, qty_issued, balance, remark FROM stock ORDER BY id DESC LIMIT 100"), use_container_width=True)

# ==========================================
# 7. PAGE: SMART OPD (AI)
# ==========================================
elif st.session_state.page == "Smart OPD (AI)":
    st.markdown("<h1>🩺 AI Clinical Support & OPD</h1>", unsafe_allow_html=True)
    
    patients = run_query("SELECT * FROM patients")
    if patients.empty:
        st.warning("Please add patient data in Master Data first.")
    else:
        pat_dict = {f"{r['name']} (Age: {r['age']} | ID: {r['family_id']})": (r['id'], r['age']) for _, r in patients.iterrows()}
        c1, c2 = st.columns([1.2, 1])
        
        with c1:
            st.markdown("<div class='form-container'>", unsafe_allow_html=True)
            st.markdown("#### 👤 Patient Assessment")
            selected_pat = st.selectbox("Select Patient", list(pat_dict.keys()))
            pat_id, pat_age = pat_dict[selected_pat]
            pat_weight = st.number_input("Weight (Kg) (Required for pediatric calculation)", value=60 if pat_age > 12 else (pat_age*2)+8)
            
            st.write("---")
            st.write("**Vitals Check**")
            vc1, vc2, vc3, vc4 = st.columns(4)
            with vc1: temp = st.number_input("Temp (°F)", value=98.6, step=0.1)
            with vc2: spo2 = st.number_input("SpO2 (%)", value=98, max_value=100)
            with vc3: hr = st.number_input("Pulse (bpm)", value=75)
            with vc4: bp = st.text_input("BP", value="120/80")
            
            st.write("---")
            st.write("**Signs & Symptoms**")
            common_symptoms = ["Fever", "Cough", "Sore Throat", "Runny Nose", "Diarrhea", "Vomiting", "Abdominal Pain", "Headache", "Body Ache", "Burning Micturition"]
            selected_symp = st.multiselect("Select Primary Symptoms", common_symptoms)
            other_symp = st.text_input("Additional Clinical Notes")
            
            analyze_btn = st.button("🔍 Generate AI Protocol")
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown("<div class='form-container'>", unsafe_allow_html=True)
            st.markdown("#### 🧠 AI Decision Support")
            if analyze_btn:
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

                st.markdown(f"**Predicted Pattern:** <span style='color:#16a34a; font-size:18px; font-weight:bold;'>{best_match}</span>", unsafe_allow_html=True)
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
                        st.info(txt)
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
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 8. PAGE: REPORTS & ANALYTICS
# ==========================================
elif st.session_state.page == "Reports & Analytics":
    st.markdown("<h1>📊 Analytics & Cloud Export</h1>", unsafe_allow_html=True)
    
    opd_df = run_query("SELECT visit_date, COUNT(id) as patients FROM opd_visits GROUP BY visit_date")
    if not opd_df.empty: 
        st.markdown("<div class='form-container'>", unsafe_allow_html=True)
        fig = px.bar(opd_df, x='visit_date', y='patients', title="Daily OPD Footfall", color_discrete_sequence=['#16a34a'])
        fig.update_layout(plot_bgcolor='white', paper_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div><br>", unsafe_allow_html=True)
    
    st.markdown("<div class='form-container'>", unsafe_allow_html=True)
    st.subheader("Current Stock Balances")
    full_stock = get_all_balances()
    st.dataframe(full_stock, use_container_width=True)
    st.markdown("</div><br>", unsafe_allow_html=True)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        run_query("SELECT p.name, o.* FROM opd_visits o JOIN patients p ON o.patient_id = p.id").to_excel(writer, index=False, sheet_name='OPD_Register')
        run_query("SELECT * FROM stock").to_excel(writer, index=False, sheet_name='Stock_Ledger')
        full_stock.to_excel(writer, index=False, sheet_name='Current_Balances')
        
    st.download_button(label="📥 Download Complete Report (Excel)", data=output.getvalue(),
                       file_name=f"SHC_Report_{datetime.date.today().strftime('%b_%Y')}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
