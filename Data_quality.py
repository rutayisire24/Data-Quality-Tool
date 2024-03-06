import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
from scipy import stats

st.title("Dataset Quality Checker")
st.write("This application will allow you to upload your dataset and run a quality check on it.")
st.markdown("---")


# Uploading the dataset
st.subheader("Upload your files here : ")

upload_data = st.file_uploader("Choose a CSV file", type = ['CSV'])
if upload_data is not None:
    read_data = pd.read_csv(upload_data, encoding='latin-1',on_bad_lines='skip')


# Looking at your dataset
st.write("Dataset Overview : ")
try:
    number_of_rows = st.slider("No of rows:",5,10)
    head = st.radio("View from Top or Bottom",('Head','Tail'))
    if head=='Head':
        st.dataframe(read_data.head(number_of_rows))
    else:
        st.dataframe(read_data.tail(number_of_rows))
except:
    st.error("KINDLY UPLOAD YOUR CSV FILE !!!")
    st.stop()

# Column selection for quality checks
st.subheader("Select Columns for Quality Checks:")
selected_columns = st.multiselect("Choose columns", read_data.columns.tolist())
if not selected_columns:
    st.warning("No columns selected. Please select at least one column to proceed with quality checks.")
    st.stop()
else:
    # Continue with your data quality checks on the selected columns
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

#Checking for Null Values : 
if st.button('Check for Missing Values',key=1): 

    null_values = (read_data.isnull().sum()/len(read_data)*100).round(0)
    missing = null_values.sum()
    st.write(null_values)
    if missing >=10:
        st.error("Poor Data Quality : more than 10 percent of missing values !")
    else:
        st.success("Looks Good !")

    st.text("Ideally 0-10 perecent is the maximum missing values allowed,")
    st.text("However, this depends from case to case")
    

#Check for completeness ratio
if st.button("Check for Completeness Ratio",key=3):
    not_missing = (read_data.notnull().sum().round(2))
    completeness = round(sum(not_missing)/len(read_data),2)
    st.write("Completeness Ratio for the dataset : ",completeness)
    if completeness >=0.80:
        st.success('Looks Good !')
    else:
        st.error('Poor Data Quality due to low completeness ratio : less than 80 perecent !')
        st.text('Completeness is defined as the ratio of non-missing values to total records in dataset.')


# Outlier Check

if st.button("Check for Outliers", key=2):
    # Calculate z-scores
    z_scores = np.abs(stats.zscore(read_data[selected_columns].select_dtypes(include=[np.number]), nan_policy='omit'))
    
    # Define a threshold
    threshold = 3
    
    # Identify outliers
    outlier_positions = np.where(z_scores > threshold)
    outliers = read_data.iloc[outlier_positions[0]]
    
    if not outliers.empty:
        st.warning(f"Found outliers in your dataset. Here are some of them:")
        st.dataframe(outliers.head())  # Show a few outliers
    else:
        st.success("No significant outliers found in the selected columns.")
st.markdown('---')

st.subheader('> Thank you for using the dataset quality checker.')
