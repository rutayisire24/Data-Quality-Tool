import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from adtk.detector import QuantileAD
import io
import base64

mfl = pd.read_excel('mfl.xlsx')
## Function 

@st.cache_data
def detect_outliers(data, column_name):


    data = data[[column_name, 'organisationunitname']].copy()

    # Placeholder for the results
    outlier_results = []

    for unit in data['organisationunitname'].unique():
        print('processing unit:', unit)

        sample_fac_data = data[data['organisationunitname'] == unit]
        period_names = sample_fac_data.index

        try:
            # Data validation and imputation
            data_test = sample_fac_data.drop('organisationunitname', axis=1)
            data_test = validate_series(data_test)
            quantile_ad = QuantileAD(high=0.999999999, low=0.0000001)
            anomaly_scores = quantile_ad.fit_detect(data_test) 
            # Create results DataFrame
            anomalies = pd.DataFrame(index=period_names)
            anomalies['organisationunitname'] = unit
            anomalies[column_name] = data_test[column_name]  
            anomalies['outlier'] = anomaly_scores != 0
            anomalies['missing'] = data_test[column_name].isna()
            outlier_results.append(anomalies)

        except Exception as e:
            print(f"Error during processing for unit {unit}: {e}. Skipping this unit.")
            continue

    # Concatenate results
    all_outliers = pd.concat(outlier_results, ignore_index=False)
        # New code to aggregate outlier counts per facility
    outlier_counts = all_outliers.groupby('organisationunitname')['outlier'].sum().reset_index()
    outlier_counts.columns = ['Facility', 'Outlier Count']
    outlier_counts.sort_values('Outlier Count', ascending=False, inplace=True)
    
    return all_outliers , outlier_counts

def validate_series(data_test):
    """Validates the data and handles missing values.
    """
    # Other validation checks (ensure data type, etc.)
    #data_test = data_test.fillna(data_test.mean())  # Impute missing values with the mean
    #return data_test

    # Concatenate results
    all_outliers = pd.concat(outlier_results, ignore_index=False)
    all_outliers = pd.merge(all_outliers,mfl , left_on= "organisationunitname", right_on='facility' , how= 'outer')
        # New code to aggregate outlier counts per facility
    outlier_counts = all_outliers.groupby('organisationunitname')['outlier'].sum().reset_index()
    outlier_counts.columns = ['Facility','Outlier Count']
    outlier_counts.sort_values('Outlier Count', ascending=False, inplace=True)
    
    return all_outliers , outlier_counts

def validate_series(data_test):
    """Validates the data and handles missing values.
    """
    # Other validation checks (ensure data type, etc.)
    data_test = data_test.fillna(data_test.median())  # Impute missing values with the mean
    return data_test

# Streamlit app layout
st.title('HMIS - Data Quality App')

with st.expander("How to Use This App"):
    st.write("""
    **Purpose:** This app helps you identify potential outliers and Missing Values  in HMIS data based on statistical analysis. 

    **Steps:**
    1. **Upload CSV File:** Click the "Choose a CSV file" button and select the file. Your data should have a 'periodname' column (as dates) and a 'organisationunitname' column or 
             you can use the Test data in the link.
    2. **Select Data Element:** Choose the column you want to analyze from the dropdown.
    3. **Review Results:** The app will process your data and generate:
       * A line chart visualizing the data points and highlighting potential outliers (red markers).
       * A count of possible outliers for the selected facility.
    4. **Filter by Facility:** Use the facility dropdown to focus on results for a specific facility.
    5. **Download Outliers:**  Click the "Download as CSV" link to save identified outliers.
    """)

def get_file_download_link(file_path):
    """Creates a Streamlit download link for a given file."""
    with open(file_path, 'rb') as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()  # Base64 encoding
    return f'<a href="data:file/csv;base64,{b64}" download="{file_path}">Download {file_path}</a>'

# Section for the download link
file_path = "Test_data.csv"  
st.markdown(get_file_download_link(file_path), unsafe_allow_html=True)
# Selector for which column to analyze
st.subheader("Upload Data to be Accessed")
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    with st.spinner("Processing data..."):
        try:
            data = pd.read_csv(uploaded_file, index_col='periodname', parse_dates=True)
            st.success("CSV file uploaded successfully!")
            st.write('Preview of the Uploaded Data')
            st.write(data.head())
            # ... (The rest of your app code, using the 'data' variable)

        except Exception as e:
            st.error(f"Error uploading CSV file: {e}")

## Select the column to Display 
if uploaded_file is not None:
  columns = data.columns
  last_col_index = len(columns) - 1
  selected_col = st.selectbox("Select a Data element" , options=columns, index=last_col_index) 

  ## run the function on the selected columns 

  outliers_df, outlier_counts = detect_outliers(data.copy() , selected_col)  # Make a copy to avoid modifying the original data
  data = outliers_df.copy()
  data.index = pd.to_datetime(data.index)

  ## try somethings 
  total_facilities = len(data['organisationunitname'].unique())

  # Calculate the number of facilities with at least one outlier
  facilities_with_outliers = outlier_counts[outlier_counts['Outlier Count'] > 0].shape[0]

  # Compute the percentage of facilities with at least one outlier
  percentage_with_outliers = (facilities_with_outliers / total_facilities) * 100
  
# show possible outliers 
  outlier_counts = pd.merge(outlier_counts,mfl , left_on= "Facility", right_on='facility' , how= 'outer')
  outlier_counts = (outlier_counts.drop('facility' , axis = 1)).dropna() 
  st.subheader("Possible Outlier Counts by Facility")
  st.write(outlier_counts)

  # Display the metrics
  # Column layout setup
  cols = st.columns(3)  # Create three columns

  # Metrics in columns
  with cols[0]:
      st.metric(label="Total Facilities Reviewed", value=total_facilities)

  with cols[1]:
      st.metric(label="Facilities with Potential Outliers", value=facilities_with_outliers)

  with cols[2]:
      st.metric(label="%  Potential Outliers", value=f"{percentage_with_outliers:.2f}%")

  # Download CSV section
  st.subheader("Download Results")
  if outliers_df.shape[0] > 0:  # Check if there are outliers to download
      csv = outliers_df.to_csv(index=False)
      b64 = base64.b64encode(csv.encode()).decode()  
      href = f'<a href="data:file/csv;base64,{b64}" download="outliers.csv">Download as CSV</a>'
      st.markdown(href, unsafe_allow_html=True)
  else:
      st.warning("No outliers found to download.")
  st.subheader("Explore the Data")
    # Dropdown to select facility
  facilities_with_outliers = data[data['outlier'] == True]['organisationunitname'].unique()
  selected_facility = st.selectbox('Select a Facility', facilities_with_outliers)

  # Filter data based on selection
  filtered_data = data[data['organisationunitname'] == selected_facility]
  
  missing_counts = filtered_data.groupby('organisationunitname')['missing'].sum().reset_index()
  missing_counts = pd.merge(missing_counts, mfl , left_on= 'organisationunitname', right_on='facility', how= 'outer')
  missing_counts = (missing_counts.drop('facility', axis = 1)).dropna()
  missing_counts.columns = ['Facility', 'Counts of Missing Values', 'District']
  

  st.write( f'Missing Values for {selected_facility} in {selected_col}')
  st.write(missing_counts)
  
  # Count the number of possible outliers for the selected facility
  num_outliers = filtered_data['outlier'].sum()
  # Display the summary at the top as a value box
  st.metric(label="Number of Possible Outliers", value=num_outliers)
  # Plotting with Plotly
      # Plotting with Plotly
  fig = go.Figure()

  # Add line for the data
  fig.add_trace(go.Scatter(x=filtered_data.index, y=filtered_data[selected_col], mode='lines', name='Data'))

  # Add markers for outliers and non-outliers
  outliers = filtered_data['outlier'] == True
  fig.add_trace(go.Scatter(x=filtered_data[outliers].index, y=filtered_data[outliers][selected_col], 
                            mode='markers', marker=dict(color='red'), name='Outlier'))
  fig.add_trace(go.Scatter(x=filtered_data[~outliers].index, y=filtered_data[~outliers][selected_col], 
                            mode='markers', marker=dict(color='blue'), name='Not Outlier'))

  # Calculate quantiles (you can adjust the values as needed)
  q1 = filtered_data[selected_col].quantile(0.01)
  q3 = filtered_data[selected_col].quantile(0.99)

  # Add quantile lines for visual reference
  fig.add_shape(type='line', y0=q1, y1=q1, x0=filtered_data.index.min(), x1=filtered_data.index.max(),
                line=dict(color='yellow', width=2, dash='dash'), name='25th Quantile')
  fig.add_shape(type='line', y0=q3, y1=q3, x0=filtered_data.index.min(), x1=filtered_data.index.max(),
                line=dict(color='cyan', width=2, dash='dash'), name='75th Quantile')

  # Update layout
  fig.update_layout(title=f'Possible Outliers for {selected_facility} in  <br> {selected_col}', 
                    xaxis_title='', yaxis_title='', legend_title='Data Points',
                    showlegend=True)  

 
  # Show plot in Streamlit
  st.plotly_chart(fig) 

   # Short explanation about quantiles
  st.write("**Quantiles:** The yellow and cyan lines represent the 10th and 99th quantiles respectively, helping you see how the data is distributed around the central values.")
