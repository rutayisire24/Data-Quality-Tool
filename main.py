import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
from scipy import stats

st.title("Dataset Quality Checker")
st.write(
    "This application will allow you to upload your dataset and run a quality check on it."
)
st.markdown("---")


def identify_missing_values(data):
    missing_flags = data.isnull()
    summary = missing_flags.sum()
    violations = data[missing_flags.any(axis=1)]
    return data, summary, violations


# Uploading the dataset
st.subheader("Upload your files here : ")

upload_data = st.file_uploader("Choose a CSV file", type=["CSV"])
if upload_data is not None:
    read_data = pd.read_csv(upload_data, encoding="latin-1", on_bad_lines="skip")


# Looking at your dataset
st.write("Dataset Overview : ")
try:
    st.dataframe(read_data.head(5))
except:
    st.error("KINDLY UPLOAD YOUR CSV FILE !!!")
    st.stop()

# Column selection for quality checks
st.subheader("Select Columns for Quality Checks:")
selected_columns = st.multiselect("Choose columns", read_data.columns.tolist())
if not selected_columns:
    st.warning(
        "No columns selected. Please select at least one column to proceed with quality checks."
    )
    st.stop()
else:
    # Continue with your data quality checks on the selected columns
    original_data = read_data
    read_data = read_data[selected_columns]

# Dataset Shape
st.write("Rows and Columns size : ")
st.write(read_data.shape)

# Dataset Summary
st.write("Descriptive Statistics of your dataset : ")
st.write(read_data.describe())
st.markdown("---")


# More Exploration
st.subheader(" Dataset Quality Checks:")

# Checking for Null Values :
if st.button("Missing Values Check"):
    data, summary, violations = identify_missing_values(read_data)
    st.write(f"Missing values summary:\n{summary}")

    if not violations.empty:
        csv = violations.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Flagged Records for Missing Values",
            data=csv,
            file_name="missing_values.csv",
            mime="text/csv",
        )

# Check for completeness ratio
if st.button("Check for Completeness Ratio", key=3):
    not_missing = read_data.notnull().sum().round(0)
    completeness = round(sum(not_missing) / len(read_data), 0)
    st.write("Completeness Ratio for the dataset : ", completeness)
    if completeness >= 0.80:
        st.success("Looks Good !")
    else:
        st.error(
            "Poor Data Quality due to low completeness ratio : less than 80 perecent !"
        )
        st.text(
            "Completeness is defined as the ratio of non-missing values to total records in dataset."
        )


# Function to flag outliers using IQR
def flag_outliers_iqr(group):
    q1 = group["Value"].quantile(0.25)
    q3 = group["Value"].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    group["possible_outlier"] = [
        "possible" if (x < lower_bound or x > upper_bound) else "no"
        for x in group["Value"]
    ]
    return group


# Adjusted Outlier Check for Facility Level using IQR
if st.button("Check for Outliers by Facility", key="facility_outliers_iqr"):
    # Convert selected data to long format for outlier analysis
    long_df = pd.melt(
        read_data,
        id_vars=["organisationunitname"],
        var_name="Metric",
        value_name="Value",
    )

    # Apply the outlier detection and flagging, grouped by facility and Metric
    flagged_df = long_df.groupby(
        ["organisationunitname", "Metric"], as_index=False
    ).apply(flag_outliers_iqr)

    # Filter to obtain only the rows flagged as possible outliers
    outliers_df = flagged_df[flagged_df["possible_outlier"] == "possible"]

    outliers_df = pd.pivot_table(
        outliers_df, index="organisationunitname", columns="Metric", values="Value"
    )
    final_outliers = pd.merge(outliers_df, read_data, how="left")

    if not outliers_df.empty:
        st.warning(
            "Found outliers in your dataset, grouped by facility. Here are some of them:"
        )
        st.dataframe(outliers_df.head())  # Show a preview of outliers

        # Optionally, provide a download button for the outlier data
        csv = outliers_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Flagged Outliers by Facility as CSV",
            data=csv,
            file_name="flagged_outliers_by_facility.csv",
            mime="text/csv",
        )
    else:
        st.success(
            "No significant outliers found in the selected columns by facility using IQR."
        )
st.markdown("---")

st.subheader("> Thank you for using the dataset quality checker.")
