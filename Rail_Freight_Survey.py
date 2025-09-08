import streamlit as st
from firebase_config import initialize_firebase
import base64
import uuid
from datetime import datetime
import pandas as pd




# Initialize Firebase
db = None
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    def init_firestore():
        global db
        if db is not None:
            return db
        if not firebase_admin._apps:
            # Replace escaped newlines if needed:
            sa = dict(st.secrets["firebase_credentials"])
            if "\\n" in sa.get("private_key", ""):
                sa["private_key"] = sa["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(sa)
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        return db
except Exception:
    # Allow app to run without firebase installed
    pass

# ---- THEME + GLOBAL CSS ----
def inject_css(
    *,
    card_bg="rgba(255,255,255,0.92)",
    card_radius="12px",
    card_pad="10px 12px",
    gap_below="10px",
    option_gap="6px",
    label_gap="6px",
    font_color="#000",
):
    st.markdown(f"""
    <style>
    :root {{
      --card-bg: {card_bg};
      --card-radius: {card_radius};
      --card-pad: {card_pad};
      --gap-below: {gap_below};
      --option-gap: {option_gap};
      --label-gap: {label_gap};
      --font-color: {font_color};
    }}

    /* Generic card */
    .card {{
      background: var(--card-bg);
      padding: var(--card-pad);
      border-radius: var(--card-radius);
      margin: 6px 0 var(--gap-below) 0;
      color: var(--font-color);
    }}

    /* Question label pill */
    .q-label {{
      background: var(--card-bg);
      padding: 6px 8px;
      border-radius: 8px;
      margin: 6px 0 6px 0;
      color: var(--font-color);
      font-weight: 800;
    }}

    /* QA container (label + widget in one box if you want) */
    .qa-card {{
      background: var(--card-bg);
      padding: var(--card-pad);
      border-radius: var(--card-radius);
      margin: 6px 0 var(--gap-below) 0;
    }}
    .qa-title {{
      color: var(--font-color);
      font-weight: 800;
      margin: 0 0 var(--label-gap) 0;
    }}

    /* Streamlit widgets inside */
    div[role="radiogroup"] {{
      display: flex; flex-wrap: wrap;
      gap: var(--option-gap);
      margin-top: 0;   /* no extra gap above options */
    }}
    div[role="radiogroup"] > label {{
      margin: 0 !important;
      padding: 2px 6px;
    }}

    /* Sliders look like cards and keep spacing tight */
    div[data-testid="stSlider"] {{
      background: var(--card-bg);
      padding: 6px;
      border-radius: 8px;
      margin: 6px 0 var(--gap-below) 0;
    }}

    /* Number inputs (importance matrix) */
    div[data-testid="stNumberInput"] label {{ margin-bottom: 2px; }}
    div[data-testid="stNumberInput"] > div {{ margin-top: 0; }}

    /* Matrix blocks */
    .matrix-label, .matrix-hint, .matrix-row {{
      background: var(--card-bg);
      border-radius: 8px;
      padding: 6px 8px;
      margin: 6px 0;
      color: var(--font-color);
    }}
    .matrix-label b {{ font-weight: 800; }}
    .matrix-hint i {{ opacity: .9; }}

    /* Markdown paragraph default tightening */
    div[data-testid="stMarkdownContainer"] p {{ margin: .25rem 0; }}

    /* Tables */
    table {{ margin-bottom: 8px; }}
    th, td {{ padding: 6px 8px !important; color: var(--font-color); }}
    </style>
    """, unsafe_allow_html=True)

st.set_page_config(page_title="CH Intermodal Freight Survey", layout="centered")

inject_css(card_bg="rgba(255,255,255,0.92)", option_gap="6px", label_gap="6px")

survey_schema = [
    {
        "section": "Section 1: Company Profile",
        "items": [
            {"id":"company_profile","label":"Company Profile (select all that apply)","type":"multiselect",
             "options":["Manufacturer","Retailer/Wholesaler","Freight Forwarder (3PL/4PL)","Intermodal Operator (Rail, Terminal)","Other"]},
            {"id":"industry_sector","label":"Industry Sector","type":"multiselect",
             "options":["Automotive","Chemicals","Consumer Goods","Industrial Equipment","Dangerous goods","Perishable goods","Food & Beverage","Other"]},
            {"id":"annual_teu","label":"Annual Freight Volume (TEU per year)","type":"radio",
             "options":["< 100","100 – 500","500 – 1,000","> 1,000"]},
            {"id":"cost_per_teu","label":"Transport Cost per TEU (CHF per TEU)","type":"radio",
             "options":["< 500","500 – 1,000","1,000 – 2,000","> 2,000"]},
            {"id":"shipment_types","label":"Primary shipment types","type":"multiselect",
             "options":["Full Trailer Load (FTL)","Containers","Semitrailers","Bulk Freight"]},
            {"id":"distance_ch","label":"Typical transport distance within Switzerland","type":"radio",
             "options":["< 100 km","100–200 km","200–300 km","> 400 km"]},
            {"id":"rail_freq","label":"How frequently do you use rail freight? (1=Never, 5=Always)","type":"likert5"},
            {"id":"mode_decider","label":"Who makes transport mode decisions?","type":"multiselect",
             "options":["Logistics / Supply Chain Manager","CEO / Senior Executive","Operations Manager","Procurement / Purchasing","Other"]},
        ],
    },
    {
        "section": "Section 2: Current Transport Mode & Segmentation",
        "items": [
            {"id":"existing_mode","label":"Existing transport mode","type":"multiselect",
             "options":["Road","Rail","Water","Multimodal","Other"]},
            {"id":"reasons_current","label":"Reasons for current mode (select all that apply)","type":"multiselect",
             "options":["Cost efficiency","Transit time / Speed","Reliability (on-time)","Flexibility","Accessibility (terminal/first-last mile)","Sustainability (CO₂)","Risk avoidance","Regulatory compliance","Technological integration (tracking, digital booking)"]},
            {"id":"use_intermodal_12m","label":"Used intermodal rail in last 12 months?","type":"radio","options":["Yes","No"]},
            {"id":"intermodal_frequency","label":"If yes, how often do you use intermodal?","type":"radio","options":["Occasionally (1–5/yr)","Regularly (6+/yr)","Always"]},
            {"id":"nonuser_reasons","label":"If NOT using intermodal, why?","type":"multiselect",
             "options":["Cost is too high","Rail schedules not flexible","Transit time too long","Terminal access inconvenient","Need last-mile road","Complicated booking","Lack of tracking","Delays","Damage/loss","Other"]},
            {"id":"stop_using_reasons","label":"If no longer using intermodal, reasons","type":"multiselect",
             "options":["High costs","Limited rail network coverage","Long transit time","Inflexible schedules","Damage/loss concerns","Complex coordination with rail operators","Other"]},
            {"id":"user_reasons","label":"If using intermodal, key reasons","type":"multiselect",
             "options":["Cost savings","Appropriate transport time","Customised service","Environmental benefits","Improved reliability","Other"]},
        ],
    },
    {
        "section": "Section 3: Mode Choice Factors & Preferences",
        "items": [
            {"id":"factor_importance","label":"Rate importance (1–5) for each factor","type":"matrix_likert5",
             "rows":["Cost","Transport Time","Service Frequency","Punctuality (On-Time)","Terminal Accessibility","CO₂ Emissions / Sustainability","Flexibility (Schedule)","Cargo Security & Damage Risk","Digital Tracking","Booking Convenience"]},
            {"id":"improvements","label":"What improvements would increase intermodal usage?","type":"multiselect",
             "options":["Lower costs","Faster transport times","More frequent rail schedules","Better reliability","Improved terminal access","Digital tracking solutions","Easy booking","Improved transparency","Other"]},
        ],
    },
    {
        "section": "Section 4: Psychological / Behavioral Factors",
        "items": [
            {"id":"trust_overall","label":"Trust in intermodal rail vs trucking (1–5)","type":"likert5"},
            {"id":"on_time_perf","label":"For users: rail meets scheduled delivery times (1–5)","type":"likert5"},
            {"id":"delay_severity_single","label":"How serious are delays? (1–5)","type":"likert5"},
            {"id":"flexibility_vs_truck","label":"Flexibility vs truck (1–5)","type":"likert5"},
            {"id":"service_frequency_fit","label":"Adequacy of service frequency (1–5)","type":"likert5"},
            {"id":"delay_severity_table","label":"Delay severity by duration","type":"matrix_ordinal",
             "rows":["1 Day","2 Days","3 Days","4 Days","5+ Days"],
             "cols":["Not Serious at All","Slightly Serious","Moderately Serious","Highly Serious","Very Serious"]},
            {"id":"cost_perception","label":"Cost of rail vs road (1=Much More Expensive, 5=Much Cheaper)","type":"likert5"},
            {"id":"risk_damage","label":"Risk of damage/theft/loss (1–5)","type":"likert5"},
            {"id":"industry_influence","label":"Influence of industry trends/competitors (1–5)","type":"likert5"},
            {"id":"sustainability_importance","label":"Importance of sustainability (1–5)","type":"likert5"},
            {"id":"low_carbon_priority","label":"Priority for low-carbon modes (1–5)","type":"likert5"},
            {"id":"pay_premium_co2","label":"Willingness to pay CO₂ premium (1–5)","type":"likert5"},
            {"id":"stick_current_mode","label":"Likelihood to keep current mode (1–5)","type":"likert5"},
            {"id":"time_pressure","label":"Decisions under time pressure (1–5)","type":"likert5"},
            {"id":"pressure_to_use_rail","label":"Felt pressure to use intermodal rail (1–5)","type":"likert5"},
            {"id":"extra_comm_time","label":"Extra communication time vs other modes (1–5)","type":"likert5"},
            {"id":"branch_specific_need","label":"Need for branch-specific services (1–5)","type":"likert5"},
            {"id":"finance_complexity","label":"Financial process complexity (1–5)","type":"likert5"},
            {"id":"transparency","label":"Process transparency (1–5)","type":"likert5"},
            {"id":"admin_complexity","label":"Administrative process complexity (1–5)","type":"likert5"},
            {"id":"portfolio_fit","label":"Service portfolio fit (1–5)","type":"likert5"},
            {"id":"terminal_access","label":"Terminal accessibility (1–5)","type":"likert5"},
            {"id":"meets_requirements","label":"Meets logistics requirements (1–5)","type":"likert5"},
            {"id":"booking_convenience","label":"Booking convenience in CH (1–5)","type":"likert5"},
            {"id":"digital_tracking_importance","label":"Importance of digital tracking (1–5)","type":"likert5"},
            {"id":"comfort_new_solutions","label":"Comfort with trying intermodal rail (1–5)","type":"likert5"},
            {"id":"concerns","label":"Top concerns about intermodal rail","type":"multiselect",
             "options":["Unreliable schedules","Poor customer service","Lack of flexibility","Terminal access issues","Higher cost","Other"]},
            {"id":"psych_open","label":"Other psychological/behavioral factors","type":"textarea"},
        ],
    },
    {
        "section": "Section 5: Environmental Impact",
        "items": [
            {"id":"co2_importance","label":"Importance of CO₂ reduction (1–5)","type":"likert5"},
            {"id":"sustainable_energy","label":"Importance of sustainable/alternative energy (1–5)","type":"likert5"},
        ],
    },
    {
        "section": "Section 6: Policy & Regulatory",
        "items": [
            {"id":"policy_encouragement","label":"Policies that would encourage rail (select all)","type":"multiselect",
             "options":["Subsidies for rail transport","Carbon tax on road transport","Investment in rail infrastructure","Digital freight platforms for easier booking","More flexible rail schedules","Priority access for time-sensitive freight","Branch-specific intermodal services","Other"]},
            {"id":"aware_regulations","label":"Aware of Swiss transport regulations impacting mode choice?","type":"radio","options":["Yes","No"]},
            {"id":"pilot_test","label":"Open to pilot-testing new intermodal solutions?","type":"radio","options":["Yes","No"]},
            {"id":"govt_influence","label":"Influence of government campaigns (1–5)","type":"likert5"},
            {"id":"policy_suggestions","label":"Policy suggestions (open text)","type":"textarea"},
        ],
    },
]

def card(title=None, body_html=""):
    st.markdown(
        f"""
        <div class="card">
            {f"<h3 style='margin:0 0 8px 0;'>{title}</h3>" if title else ""}
            <div>{body_html}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def display_question_label(text):
    st.markdown(f'<div class="q-label">{text}</div>', unsafe_allow_html=True)

def display_multiple_choice(question, options, key):
    # One-box layout: label + radio inside the same card
    st.markdown(f'<div class="qa-card"><div class="qa-title">{question}</div>', unsafe_allow_html=True)
    val = st.radio(label="", options=options, key=key, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
    return val

def likert5(key, label):
    st.markdown(f'<div class="qa-card"><div class="qa-title">{label}</div>', unsafe_allow_html=True)
    val = st.slider("", 1, 5, 3, key=key, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
    return val

def matrix_likert5(prefix, rows):
    # Label outside so it reads like a section
    display_question_label("Please rate each item (1–5)")
    vals = {}
    for r in rows:
        st.markdown(f'<div class="qa-card"><div class="qa-title">{r}</div>', unsafe_allow_html=True)
        vals[r] = st.slider("", 1, 5, 3, key=f"{prefix}:{r}", label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)
    return vals

def matrix_ordinal(prefix, label, rows, cols):
    st.markdown(f'<div class="matrix-label"><b>{label}</b></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="matrix-hint"><i>Please select one option per row</i></div>', unsafe_allow_html=True)

    vals = {}
    for r in rows:
        st.markdown(f'<div class="matrix-row"><b>{r}</b></div>', unsafe_allow_html=True)
        vals[r] = st.radio("", cols, horizontal=True, key=f"{prefix}:{r}", label_visibility="collapsed")
    return vals

def display_multiselect(question, options, key):
    st.markdown(f'<div class="qa-card"><div class="qa-title">{question}</div>', unsafe_allow_html=True)
    val = st.multiselect("", options, key=key, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
    return val

def display_text(question, key):
    st.markdown(f'<div class="qa-card"><div class="qa-title">{question}</div>', unsafe_allow_html=True)
    val = st.text_input("", key=key, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
    return val

def display_textarea(question, key):
    st.markdown(f'<div class="qa-card"><div class="qa-title">{question}</div>', unsafe_allow_html=True)
    val = st.text_area("", key=key, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
    return val


def answers_to_row(answers: dict, schema: list) -> dict:
    """
    Convert nested answers to a flat row (one dict) where
    keys = question labels (and matrix sublabels) and values = user selections.
    """
    row = {}

    for section in schema:
        for item in section["items"]:
            qid   = item["id"]
            label = item["label"]
            typ   = item["type"]
            val   = answers.get(qid, None)

            if typ in ("text", "textarea", "radio"):
                row[label] = val if val is not None else ""

            elif typ == "multiselect":
                row[label] = ", ".join(val) if val else ""

            elif typ == "likert5":
                row[label] = int(val) if val is not None else None

            elif typ == "matrix_likert5":
                # val is a dict: {row_label: rating}
                for r_label, r_val in (val or {}).items():
                    row[f"{label} | {r_label}"] = int(r_val) if r_val is not None else None

            elif typ == "matrix_ordinal":
                # val is a dict: {row_label: selected_option_text}
                for r_label, r_val in (val or {}).items():
                    row[f"{label} | {r_label}"] = r_val if r_val is not None else ""

            else:
                # fallback
                row[label] = val if val is not None else ""

    return row



def save_to_firebase(row: dict):
    try:
        client = init_firestore()
        doc_ref = client.collection("ch_intermodal_survey_rows").document()  # new collection name
        doc_ref.set(row)  # flat fields
        return True, doc_ref.id
    except Exception as e:
        return False, str(e)



# Function to set a background image
def set_background(image_path):
    with open(image_path, "rb") as f:
        img_data = f.read()
    b64_encoded = base64.b64encode(img_data).decode()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{b64_encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# Function to display the header with a logo
def display_header():


    st.markdown(
        """
        <div style="text-align: center; padding: 2px;">
            <img src="https://logowik.com/content/uploads/images/eth-zurich1144.jpg" width="100">
            <h1 style="color: white;">Survey: Swiss Intermodal Freight</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

# Function to encode local image to Base64
def get_image_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# Function to display the footer with developer details
def display_footer():


    st.markdown(
        f"""
        <div style="text-align: center; padding: 10px; background-color: rgba(255, 255, 255); border-radius: 10px; margin-top: 20px;">
            <p style="color: black;">© 2025 ETH Zurich. All rights reserved.</p>
        </div>
        """,
        unsafe_allow_html=True
    )




def main():


    # Optional background image (local)
    set_background("project-mobility.jpg")  # Background image


    display_header()

    

    # CSS tune-up
    st.markdown(
        """
        <style>
        .stRadio > div { background: rgba(255,255,255,0.92); padding: 8px; border-radius: 6px; }
        div[data-testid="stSlider"] { background: rgba(255,255,255,0.92); padding: 6px; border-radius: 6px; }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Intro card (optional)

    if st.session_state.get("page_idx", 0) != -1:

        card(
            "About this survey",
            "This pilot study explores short-distance intermodal rail adoption in Switzerland. "
            "Your responses will inform a discrete choice model and an optimization study. "
            "It takes ~8–10 minutes. Thank you!"
        )

    # Init session state
    if "page_idx" not in st.session_state:
        st.session_state.page_idx = 0
    if "answers" not in st.session_state:
        st.session_state.answers = {}

    ######## INSERT SUCCESS PAGE ######
    # Display the success page if that's the current page
    if st.session_state.page_idx == -1:
        st.markdown(
            """
            <div style="padding: 20px; background-color: rgba(255, 255, 255, 0.9); 
                        border-radius: 10px; margin: 50px auto; max-width: 600px; text-align: center;">
                <h2 style="color: green;">Thank You!</h2>
                <p style="font-size: 18px;color: green;">Your survey has been submitted successfully.</p>
                <p style="color: green;">Your responses will help improve our research.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    # Render current page
    pages = survey_schema
    section = pages[st.session_state.page_idx]

    card(title=section["section"])

    # Collect inputs
    for item in section["items"]:
        t = item["type"]
        key = item["id"]
        label = item["label"]
        if t == "radio":
            st.session_state.answers[key] = display_multiple_choice(label, item["options"], key)
        elif t == "multiselect":
            st.session_state.answers[key] = display_multiselect(label, item["options"], key)
        elif t == "text":
            st.session_state.answers[key] = display_text(label, key)
        elif t == "textarea":
            st.session_state.answers[key] = display_textarea(label, key)
        elif t == "likert5":
            st.session_state.answers[key] = likert5(key, label)
        elif t == "matrix_likert5":
            st.session_state.answers[key] = matrix_likert5(key, item["rows"])
        elif t == "matrix_ordinal":
            st.session_state.answers[key] = matrix_ordinal(key, label, item["rows"], item["cols"])
        else:
            st.info(f"Unknown field type: {t}")

    # Navigation buttons (always the same 3 columns)
    nav1, nav2, nav3 = st.columns(3)

    # Previous (left)
    with nav1:
        if st.session_state.page_idx > 0 and st.button("Previous"):
            st.session_state.page_idx -= 1
            st.rerun()

    # Next / Submit (right)
    with nav3:
        is_last = st.session_state.page_idx == len(pages) - 1
        if not is_last:
            if st.button("Next"):
                st.session_state.page_idx += 1
                st.rerun()
        else:
            if st.button("Submit"):
                flat_row = answers_to_row(st.session_state.answers, survey_schema)
                # add metadata columns (also stored as fields)
                flat_row["submitted_at_utc"] = datetime.utcnow().isoformat() + "Z"
                flat_row["schema_version"] = "v1"
                flat_row["app_version"] = "2025-09-05"

                ok, info = save_to_firebase(flat_row)   # <-- now saving the flat row
                if ok:
                    st.session_state.answers = {}
                    st.session_state.page_idx += 1
                    st.session_state.page_idx = -1  # This critical line was missing
                    # st.session_state.page = "Page 1"  # Reset to first page after submission
                    st.rerun()
                else:
                    st.error(f"Could not save to Firestore: {info}")

                
                    
                

        # Submit button (only on the last page) - placed in the same column as the Next button would be
        

    
    display_footer()


if __name__ == "__main__":
    main()