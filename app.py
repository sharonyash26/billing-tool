import streamlit as st
import pandas as pd
import string
import io

st.title("Billing Tool - Finance Output")

# =========================================
# Helper functions
# =========================================

def parse_client_ids(value):
    """
    Scenario C helper:
    Example cell value: 3001,3002,3003,3004,3005
    """
    if pd.isna(value):
        return []
    return [x.strip() for x in str(value).split(",") if x.strip()]


# =========================================
# Upload manager file
# =========================================

uploaded_file = st.file_uploader("Upload your input CSV", type=["csv"])

if uploaded_file is not None:
    # Load uploaded manager CSV
    df = pd.read_csv(uploaded_file, encoding="cp1252")

    st.write("Preview of uploaded data:")
    st.dataframe(df.head())

    # =========================================
    # Validate required columns
    # =========================================
    required_columns = [
        "Account Name",
        "Product",
        "Contract Amount",
        "OpportunityID",
        "Scenario",
        "Start Month",
        "Start Year",
        "Implementation Fee",
        "Monthly Amount",
        "Delivery Month",
        "Delivery Year",
        "Property Count",
        "AviClientId"
    ]

    missing_cols = [col for col in required_columns if col not in df.columns]

    if missing_cols:
        st.error(f"Missing required columns in uploaded file: {missing_cols}")
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
        property_count = int(row["Property Count"]) if pd.notnull(row["Property Count"]) else 0

        start_month = int(row["Start Month"]) if pd.notnull(row["Start Month"]) else None
        start_year = int(row["Start Year"]) if pd.notnull(row["Start Year"]) else None
        delivery_month = int(row["Delivery Month"]) if pd.notnull(row["Delivery Month"]) else None
        delivery_year = int(row["Delivery Year"]) if pd.notnull(row["Delivery Year"]) else None

        # Primary AviClientId for Scenario A/B
        avi_client_id = row["AviClientId"] if pd.notnull(row["AviClientId"]) else None

        # Optional Scenario C support
        client_ids = []
        if "ClientID List" in df.columns:
            client_ids = parse_client_ids(row["ClientID List"])

        # Warn if Scenario C property count and client ID list don't match
        if scenario == "C" and len(client_ids) > 0 and property_count != len(client_ids):
            st.warning(
                f"ClientID count does not match Property Count for Account Name: {account_name}"
            )

        # =========================================
        # SCENARIO A
        # =========================================
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
                    "Scenario": "A",
                    "Billing Queue": start_month,
                    "Contract Amount": contract_amount,
                    "Split Type": "One time Implementation",
                    "Split Amount": implementation_fee,
                    "Balance after Split": contract_amount - implementation_fee,
                    "Onboarding": "Implementation",
                    "Amount": implementation_fee,
                    "Frequency": "One-Time",
                    "OpportunityID": opportunity_id,
                    "Status": "Ready to Bill"
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
                    "Scenario": "A",
                    "Billing Queue": delivery_month,
                    "Contract Amount": None,
                    "Split Type": "Ongoing",
                    "Split Amount": monthly_amount,
                    "Balance after Split": contract_amount - implementation_fee - monthly_amount,
                    "Onboarding": "Onboarded",
                    "Amount": monthly_amount,
                    "Frequency": "Monthly",
                    "OpportunityID": opportunity_id,
                    "Status": "Forecast"
                })

        # =========================================
        # SCENARIO B
        # =========================================
        elif scenario == "B":
            half_amount = contract_amount * 0.5

            # Signature row
            output_rows.append({
                "Account Name": account_name,
                "AviClientId": avi_client_id,
                "Month": start_month,
                "Year": start_year,
                "Product": product,
                "Description": "50% due upon signature",
                "Scenario": "B",
                "Billing Queue": start_month,
                "Contract Amount": contract_amount,
                "Split Type": "50% Due Upon Signature",
                "Split Amount": half_amount,
                "Balance after Split": contract_amount - half_amount,
                "Onboarding": "Implementation",
                "Amount": half_amount,
                "Frequency": "One-Time",
                "OpportunityID": opportunity_id,
                "Status": "Ready to Bill"
            })

            # Completion row
            output_rows.append({
                "Account Name": account_name,
                "AviClientId": avi_client_id,
                "Month": delivery_month,
                "Year": delivery_year,
                "Product": product,
                "Description": "50% due upon completion",
                "Scenario": "B",
                "Billing Queue": delivery_month,
                "Contract Amount": None,
                "Split Type": "Final Delivery",
                "Split Amount": half_amount,
                "Balance after Split": 0,
                "Onboarding": "",
                "Amount": half_amount,
                "Frequency": "One-Time",
                "OpportunityID": opportunity_id,
                "Status": "Forecast"
            })

        # =========================================
        # SCENARIO C
        # =========================================
        elif scenario == "C":
            # Implementation fee row
            if implementation_fee > 0:
                # If Scenario C has a ClientID List, use the first client ID
                impl_client_id = client_ids[0] if len(client_ids) > 0 else avi_client_id

                output_rows.append({
                    "Account Name": account_name,
                    "AviClientId": impl_client_id,
                    "Month": start_month,
                    "Year": start_year,
                    "Product": product,
                    "Description": "Implementation fee",
                    "Scenario": "C",
                    "Billing Queue": start_month,
                    "Contract Amount": contract_amount,
                    "Split Type": "One time Implementation",
                    "Split Amount": implementation_fee,
                    "Balance after Split": contract_amount - implementation_fee,
                    "Onboarding": "",
                    "Amount": implementation_fee,
                    "Frequency": "One-Time",
                    "OpportunityID": opportunity_id,
                    "Status": "Ready to Bill"
                })

            remaining = contract_amount - implementation_fee

            if property_count > 0:
                per_property_amount = remaining / property_count
                letters = list(string.ascii_uppercase)

                for i in range(property_count):
                    current_client_id = client_ids[i] if i < len(client_ids) else None

                    if i < len(letters):
                        property_label = letters[i]
                    else:
                        property_label = f"{i+1}"

                    output_rows.append({
                        "Account Name": account_name,
                        "AviClientId": current_client_id,
                        "Month": delivery_month,
                        "Year": delivery_year,
                        "Product": product,
                        "Description": f"{product} - Property {property_label}",
                        "Scenario": "C",
                        "Billing Queue": delivery_month,
                        "Contract Amount": None,
                        "Split Type": "Split Invoice",
                        "Split Amount": per_property_amount,
                        "Balance after Split": per_property_amount,
                        "Onboarding": "",
                        "Amount": per_property_amount,
                        "Frequency": "One-Time",
                        "OpportunityID": opportunity_id,
                        "Status": "Forecast"
                    })

    # =========================================
    # Engine output
    # =========================================
    final_output = pd.DataFrame(output_rows)

    # Fix AviClientId so it does not show decimals like 379.0
    final_output["AviClientId"] = pd.to_numeric(
        final_output["AviClientId"], errors="coerce"
    ).astype("Int64")

    # Warn if IDs missing
    if final_output["AviClientId"].isnull().any():
        st.warning("Some rows are missing AviClientId")
        missing_rows = final_output[final_output["AviClientId"].isnull()][
            ["Account Name", "Product", "Scenario", "OpportunityID"]
        ]
        st.write("Rows missing AviClientId:")
        st.dataframe(missing_rows)

    st.write("Engine Output Preview:")
    st.dataframe(final_output)

    # =========================================
    # Finance output
    # =========================================
    finance_output = pd.DataFrame()

    finance_output["AviClientId"] = final_output["AviClientId"]
    finance_output["Month"] = final_output["Month"]
    finance_output["Year"] = final_output["Year"]
    finance_output["ClientName"] = final_output["Account Name"]
    finance_output["Product"] = final_output["Product"]
    finance_output["Category"] = final_output["Product"]
    finance_output["Description"] = final_output["Description"].fillna("")
    finance_output["Value"] = final_output["Amount"]
    finance_output["SiteName"] = None
    finance_output["City"] = None
    finance_output["State"] = None
    finance_output["Zip"] = None
    finance_output["Comment"] = "Generated from Billing Tool"

    st.write("Finance Output Preview:")
    st.dataframe(finance_output)

    # =========================================
    # Download Engine Output as Excel
    # =========================================
    engine_output_file = io.BytesIO()
    final_output.to_excel(engine_output_file, index=False, engine="openpyxl")

    st.download_button(
        label="Download Engine Output (Excel)",
        data=engine_output_file.getvalue(),
        file_name="Engine_Output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # =========================================
    # Download as Excel
    # =========================================
    output = io.BytesIO()
    finance_output.to_excel(output, index=False, engine="openpyxl")

    st.download_button(
        label="Download Final Billing File (Excel)",
        data=output.getvalue(),
        file_name="Final_Billing_Output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )