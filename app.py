import streamlit as st
import pandas as pd
import string
import io

st.set_page_config(page_title="Billing Tool", layout="wide")
st.title("Billing Tool")

# =========================================
# Helper functions
# =========================================
def parse_client_ids(value):
    """
    Scenario C helper:
    Example cell value: 3001,3002,3003,3004,3005
    """
    if pd.isna(value) or str(value).strip() == "":
        return []
    return [x.strip() for x in str(value).split(",") if x.strip()]


def read_uploaded_file(uploaded_file):
    """
    Reads either CSV or Excel file based on extension.
    """
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file, encoding="cp1252")
    elif name.endswith(".xlsx"):
        return pd.read_excel(uploaded_file)
    else:
        raise ValueError("Unsupported file type. Please upload CSV or Excel.")


# =========================================
# STEP 1 - Upload Power BI export and generate template
# =========================================
st.header("Step 1 — Upload Power BI Export")

st.write(
    """
Upload the CSV exported from Power BI.  
This file should contain only the base columns:

- Account Name
- Product
- Contract Amount
- OpportunityID
- AviClientId
"""
)

base_file = st.file_uploader(
    "Upload Power BI export (CSV or Excel)",
    type=["csv", "xlsx"],
    key="base_upload"
)

if base_file is not None:
    try:
        base_df = read_uploaded_file(base_file)
        base_df = base_df.dropna(how="all")

        st.subheader("Base File Preview")
        st.dataframe(base_df)

        base_required_cols = [
            "Account Name",
            "Product",
            "Contract Amount",
            "OpportunityID",
            "AviClientId"
        ]

        base_missing = [c for c in base_required_cols if c not in base_df.columns]

        if base_missing:
            st.error(f"Missing required columns in Power BI export: {base_missing}")
        else:
            # Build fillable template
            template_df = base_df.copy()

            # Add manager-entry columns
            template_df["Scenario"] = ""
            template_df["Start Month"] = ""
            template_df["Start Year"] = ""
            template_df["Implementation Fee"] = ""
            template_df["Monthly Amount"] = ""
            template_df["Delivery Month"] = ""
            template_df["Delivery Year"] = ""
            template_df["Property Count"] = ""
            template_df["ClientID List"] = ""

            st.subheader("Template Preview")
            st.dataframe(template_df)

            # Download template as Excel
            template_file = io.BytesIO()
            template_df.to_excel(template_file, index=False, engine="openpyxl")

            st.download_button(
                label="Download Input Template (Fill This)",
                data=template_file.getvalue(),
                file_name="Billing_Input_Template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Could not process base upload: {e}")


# =========================================
# STEP 2 - Upload completed template and process billing logic
# =========================================
st.header("Step 2 — Upload Completed Template")

st.write(
    """
After filling the template, upload it here.

Required manager-entered columns:
- Scenario
- Start Month
- Start Year
- Implementation Fee
- Monthly Amount
- Delivery Month
- Delivery Year
- Property Count
- ClientID List (for Scenario C)
"""
)

completed_file = st.file_uploader(
    "Upload completed template (CSV or Excel)",
    type=["csv", "xlsx"],
    key="completed_upload"
)

if completed_file is not None:
    try:
        df = read_uploaded_file(completed_file)
        df = df.dropna(how="all")

        st.subheader("Completed Template Preview")
        st.dataframe(df.head())

        required_cols = [
            "Account Name",
            "Product",
            "Contract Amount",
            "OpportunityID",
            "AviClientId",
            "Scenario",
            "Start Month",
            "Start Year",
            "Implementation Fee",
            "Monthly Amount",
            "Delivery Month",
            "Delivery Year",
            "Property Count"
        ]

        missing = [c for c in required_cols if c not in df.columns]

        if missing:
            st.error(f"Missing required columns in completed template: {missing}")
            st.stop()

        output_rows = []

        # =========================================
        # BILLING ENGINE
        # =========================================
        for _, row in df.iterrows():
            scenario = str(row["Scenario"]).strip().upper()

            account_name = row["Account Name"]
            product = row["Product"]
            opportunity_id = row["OpportunityID"]

            contract_amount = row["Contract Amount"] if pd.notnull(row["Contract Amount"]) else 0
            implementation_fee = row["Implementation Fee"] if pd.notnull(row["Implementation Fee"]) else 0
            monthly_amount = row["Monthly Amount"] if pd.notnull(row["Monthly Amount"]) else 0
            property_count = int(row["Property Count"]) if pd.notnull(row["Property Count"]) and str(row["Property Count"]).strip() != "" else 0

            start_month = int(row["Start Month"]) if pd.notnull(row["Start Month"]) and str(row["Start Month"]).strip() != "" else None
            start_year = int(row["Start Year"]) if pd.notnull(row["Start Year"]) and str(row["Start Year"]).strip() != "" else None
            delivery_month = int(row["Delivery Month"]) if pd.notnull(row["Delivery Month"]) and str(row["Delivery Month"]).strip() != "" else None
            delivery_year = int(row["Delivery Year"]) if pd.notnull(row["Delivery Year"]) and str(row["Delivery Year"]).strip() != "" else None

            avi_client_id = row["AviClientId"] if pd.notnull(row["AviClientId"]) and str(row["AviClientId"]).strip() != "" else None

            client_ids = []
            if "ClientID List" in df.columns:
                client_ids = parse_client_ids(row["ClientID List"])

            # Validation warning for Scenario C
            if scenario == "C" and len(client_ids) > 0 and property_count != len(client_ids):
                st.warning(
                    f"ClientID count does not match Property Count for {account_name}"
                )

            # ========== SCENARIO A ==========
            if scenario == "A":
                # Implementation fee row
                if implementation_fee > 0:
                    output_rows.append({
                        "Account Name": account_name,
                        "AviClientId": avi_client_id,
                        "Month": start_month,
                        "Year": start_year,
                        "Product": product,
                        "Description": "Implementation fee",
                        "Amount": implementation_fee,
                        "Scenario": "A"
                    })

                # Ongoing monthly row (single row for now)
                if monthly_amount > 0:
                    output_rows.append({
                        "Account Name": account_name,
                        "AviClientId": avi_client_id,
                        "Month": delivery_month,
                        "Year": delivery_year,
                        "Product": product,
                        "Description": "",
                        "Amount": monthly_amount,
                        "Scenario": "A"
                    })

            # ========== SCENARIO B ==========
            elif scenario == "B":
                half = contract_amount * 0.5

                output_rows.append({
                    "Account Name": account_name,
                    "AviClientId": avi_client_id,
                    "Month": start_month,
                    "Year": start_year,
                    "Product": product,
                    "Description": "50% due upon signature",
                    "Amount": half,
                    "Scenario": "B"
                })

                output_rows.append({
                    "Account Name": account_name,
                    "AviClientId": avi_client_id,
                    "Month": delivery_month,
                    "Year": delivery_year,
                    "Product": product,
                    "Description": "50% due upon completion",
                    "Amount": half,
                    "Scenario": "B"
                })

            # ========== SCENARIO C ==========
            elif scenario == "C":
                # Implementation fee row
                if implementation_fee > 0:
                    first_id = client_ids[0] if client_ids else avi_client_id

                    output_rows.append({
                        "Account Name": account_name,
                        "AviClientId": first_id,
                        "Month": start_month,
                        "Year": start_year,
                        "Product": product,
                        "Description": "Implementation fee",
                        "Amount": implementation_fee,
                        "Scenario": "C"
                    })

                remaining = contract_amount - implementation_fee

                if property_count > 0:
                    each = remaining / property_count
                    letters = list(string.ascii_uppercase)

                    for i in range(property_count):
                        cid = client_ids[i] if i < len(client_ids) else None
                        label = letters[i] if i < 26 else str(i + 1)

                        output_rows.append({
                            "Account Name": account_name,
                            "AviClientId": cid,
                            "Month": delivery_month,
                            "Year": delivery_year,
                            "Product": product,
                            "Description": f"{product} - Property {label}",
                            "Amount": each,
                            "Scenario": "C"
                        })

        # =========================================
        # ENGINE OUTPUT
        # =========================================
        engine_df = pd.DataFrame(output_rows)

        if not engine_df.empty:
            engine_df["AviClientId"] = pd.to_numeric(
                engine_df["AviClientId"], errors="coerce"
            ).astype("Int64")

        st.subheader("Engine Output Preview")
        st.dataframe(engine_df)

        # Download Engine Output
        engine_excel = io.BytesIO()
        engine_df.to_excel(engine_excel, index=False, engine="openpyxl")

        st.download_button(
            "Download Engine Output (Excel)",
            data=engine_excel.getvalue(),
            file_name="Engine_Output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # =========================================
        # FINANCE OUTPUT
        # =========================================
        finance_df = pd.DataFrame()

        finance_df["AviClientId"] = engine_df["AviClientId"]
        finance_df["Month"] = engine_df["Month"]
        finance_df["Year"] = engine_df["Year"]
        finance_df["ClientName"] = engine_df["Account Name"]
        finance_df["Product"] = engine_df["Product"]
        finance_df["Category"] = engine_df["Product"]
        finance_df["Description"] = engine_df["Description"].fillna("")
        finance_df["Value"] = engine_df["Amount"]

        finance_df["SiteName"] = ""
        finance_df["City"] = ""
        finance_df["State"] = ""
        finance_df["Zip"] = ""
        finance_df["Comment"] = "Generated from Billing Tool"

        st.subheader("Finance Output Preview")
        st.dataframe(finance_df)

        # Download Finance Output
        finance_excel = io.BytesIO()
        finance_df.to_excel(finance_excel, index=False, engine="openpyxl")

        st.download_button(
            "Download Final Billing File (Excel)",
            data=finance_excel.getvalue(),
            file_name="Final_Billing_Output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Could not process completed template: {e}")
