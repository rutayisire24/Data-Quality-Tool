import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from adtk.detector import QuantileAD
import io 
import base64
from io import BytesIO
import xlsxwriter

mfl = pd.read_excel('mfl.xlsx')
 

## Function 
@st.cache_data
def detect_outliers(data, column_name, upper):
    data = data[[column_name, 'organisationunitname']].copy()

    # Placeholder for the results
    outlier_results = []

    for unit in data['organisationunitname'].unique():

        sample_fac_data = data[data['organisationunitname'] == unit]
        period_names = sample_fac_data.index

        try:
            data_test = sample_fac_data.drop('organisationunitname', axis=1)
            data_test = validate_series(data_test)
            quantile_ad = QuantileAD(high = upper , low= 0.0001)
            anomaly_scores = quantile_ad.fit_detect(data_test)
            anomalies = pd.DataFrame(index=period_names)
            anomalies['organisationunitname'] = unit
            anomalies[column_name] = data_test[column_name]  
            anomalies['outlier'] = anomaly_scores != 0
            anomalies['missing'] = data_test[column_name].isna()
            outlier_results.append(anomalies)

        except Exception as e:
            print(f"Error during processing for unit {unit}: {e}. Skipping this unit.")
            continue

    all_outliers = pd.concat(outlier_results, ignore_index=False)
    recent_outliers =  all_outliers[all_outliers['outlier'] == True]
    recent_outliers['year']  = recent_outliers.index.year
    recent_outliers = recent_outliers[recent_outliers['year'] == 2024]
    # Aggregate outlier counts and standard deviation per facility
    outlier_summary = recent_outliers.groupby('organisationunitname')['outlier'].agg(['sum']).reset_index()
    outlier_summary.columns = ['Facility', 'Outlier Count']
    outlier_summary.sort_values('Outlier Count', ascending=False, inplace=True)

    return all_outliers, outlier_summary,recent_outliers


def validate_series(data_test):
    """Validates the data and handles missing values."""
    data_test = data_test.fillna(data_test.median())  
    return data_test

def delete_columns(data, columns_to_delete):
    """Deletes specified columns from a DataFrame if they exist."""
    for col in columns_to_delete:
        if col in data:
            del data[col]
    return data

# Streamlit app layout
#st.title('HMIS - Data Quality App')
# Color palette example
primaryColor = "#336699"  # Blue
secondaryColor = "#E0E8EF"  # Light gray
accentColor = "#99C2FF"  # Light blue

map_logo_path = 'logo.png'
st.image(map_logo_path, width=100)

st.markdown("""
<style>
    body {  /* Style the entire app background */
        background-color: ${secondaryColor};
    }
    .app-title {  /*  Class to style the main title */
        font-size: 48px;
        font-weight: bold;
        color: ${primaryColor};    
        text-align: center;
    }
    .section-header {  /*  Style section headers */
        font-size: 28px;
        font-weight: bold;
        color: ${primaryColor};
        padding-bottom: 10px;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
    }
    /* Style buttons here using similar principles */
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='app-title'>HMIS - Data Quality App</h1>", unsafe_allow_html=True) 



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
def filter_missing_values(data):

  # Filter rows with missing values
  filtered_df = data[data.isna().any(axis=1)]

  return filtered_df

def get_file_download_link(file_path):
    """Creates a Streamlit download link for a given file."""
    with open(file_path, 'rb') as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()  # Base64 encoding
    return f'<a href="data:file/csv;base64,{b64}" download="{file_path}">Download {file_path}</a>'

def drop_all_false_rows(df):  
    return df[df.any(axis=1)]

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

            columns_to_delete = ['periodid','periodcode','perioddescription','organisationunitid','organisationunitcode','organisationunitdescription','test']
            
            # Apply column deletion
            data = delete_columns(data, columns_to_delete)

            st.success("Data uploaded successfully!")
            st.write('Preview of the Uploaded Data')
            st.dataframe(data.head(),use_container_width=True)

            # ... (The rest of your app code, using the 'data' variable)

        except Exception as e:
            st.error(f"Error uploading CSV file: {e}") 

## Select the column to Display 
if uploaded_file is not None:
  columns = data.columns
  last_col_index = len(columns) - 1

  ## run the function on the selected columns 
  ## Missing values 
  # Calculate missing value percentages

# Display results in Streamlit
  st.subheader("Missing Value Analysis")

  def filter_missing_values(data):

  # Filter rows with missing values
    data['year']  = data.index.year
    data = data[data['year'] == 2024]
    filtered_df = data[data.isna().any(axis=1)]
    filtered_df = filtered_df.drop('year', axis = 1)

    return filtered_df
  
  filtered_df_missing = filter_missing_values(data)
  
  st.dataframe(filtered_df_missing, use_container_width= True)

  # Calculations for display
  total_records = data.count().sum()  # Count across all columns
  missing_records = filtered_df_missing.isnull().sum().sum() 
  missing_percentage = (missing_records / total_records) * 100
  
  st.write("The records with missing values are ", missing_records, " of the ", total_records, 
         "representing a percentage of ", f"{missing_percentage:.2f}%")
  # Download link

  if filtered_df_missing.shape[0] > 0: 
    def to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=True, sheet_name='Sheet1')
        processed_data = output.getvalue()
        return processed_data

    df_xlsx = to_excel(filtered_df_missing)
    b64 = base64.b64encode(df_xlsx).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="filtered_data.xlsx">Download Missing values as Excel</a>'
    st.markdown(href, unsafe_allow_html=True)
  



  selected_col = st.selectbox("Select a Data element" , options=columns, index=last_col_index) 

  with st.expander("Change the Upper Threshold for Outlier Detection"):
      upper = st.slider('Select Upper Cut off ( Default 90th Quantile)',
                min_value = 0.75, max_value = 0.99,value = 0.90 , step= 0.0001 )
  
  ## Outliers
  outliers_df, outlier_summary , recent_outliers = detect_outliers(data.copy() , selected_col, upper)  # Make a copy to avoid modifying the original data
  data = outliers_df.copy()
  data.index = pd.to_datetime(data.index)

  ## try somethings 
  total_facilities = len(data['organisationunitname'].unique())

  # Calculate the number of facilities with at least one outlier
  facilities_with_outliers = outlier_summary[outlier_summary['Outlier Count'] > 0].shape[0]

  # Compute the percentage of facilities with at least one outlier
  percentage_with_outliers = (facilities_with_outliers / total_facilities) * 100
  

# show possible outliers 

  outlier_counts = pd.merge(outlier_summary,mfl , left_on= "Facility", right_on='facility' , how= 'outer')
  outlier_counts = (outlier_counts.drop('facility' , axis = 1)).dropna() 
  
  
  
  st.subheader("Possible Outlier Counts by Facility")
      
    # Column layout setup
  cols = st.columns(3)  # Create three columns

  # Metrics in columns
  with cols[0]:
      st.metric(label="Total Facilities Reviewed", value=total_facilities)

  with cols[1]:
      st.metric(label="Facilities with Potential Outliers", value=facilities_with_outliers)

  with cols[2]:
      st.metric(label="%  Potential Outliers", value=f"{percentage_with_outliers:.2f}%")

  #st.write(outlier_counts)
  # Display summary table
  st.subheader("Possible Outliers  Analysis")
  st.dataframe(outlier_summary, use_container_width= True)
  st.info("Only possible outliers in the current year are displayed")
  # Display the metrics

  # Download CSV section
  st.subheader("Download Results")

  download_format = st.radio("Choose download format:", ['CSV', 'Excel'], index=0)

  if recent_outliers.shape[0] > 0:  # Check if there are outliers to download
    if download_format == 'CSV':
        csv = recent_outliers.to_csv(index=True)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="outliers.csv">Download as CSV</a>'

    elif download_format == 'Excel':
        def to_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=True, sheet_name='Sheet1')
            processed_data = output.getvalue()
            return processed_data

        df_xlsx = to_excel(recent_outliers)
        b64 = base64.b64encode(df_xlsx).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="outliers.xlsx">Download as Excel</a>'
    st.markdown(href, unsafe_allow_html=True)
  else:
      st.warning("No outliers found to download.")

      
  st.subheader("Explore the Data for the Flagged Facilities for 2024")
    # Dropdown to select facility
  facilities_with_outliers = recent_outliers['organisationunitname'].unique()
  selected_facility = st.selectbox('Select a Facility', facilities_with_outliers)

  # Filter data based on selection
  filtered_data = data[data['organisationunitname'] == selected_facility]
  
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

  with st.expander("Contact the Biostatician"):
        biostat = pd.read_excel('Biostats contacts.xlsx')
        biostat = biostat.iloc[:, :5]
        st.dataframe(biostat, use_container_width=True)