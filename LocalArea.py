import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from adtk.detector import QuantileAD
import io 
import base64
from io import BytesIO
import xlsxwriter
from datetime import datetime, timedelta
import numpy as np 

st.set_page_config(layout= "wide", page_title="HMIS Data Quality Tool", page_icon= 'logo.png')

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

def calculate_outlier_magnitude(row, column_name, data):
    """Finds the nearest non-outliers before and after, then determines the maximum difference."""
    if not row['outlier']:
        return 0

    data_subset = data[column_name]
    index = row.name

    nearest_below = data_subset[data_subset.index < index][~data_subset.index.isin(data_subset[data_subset['outlier']].index)].idxmax()
    nearest_above = data_subset[data_subset.index > index][~data_subset.index.isin(data_subset[data_subset['outlier']].index)].idxmin()

    diff_below = abs(row[column_name] - data_subset.loc[nearest_below]) if nearest_below else np.inf
    diff_above = abs(row[column_name] - data_subset.loc[nearest_above]) if nearest_above else np.inf

    return max(diff_below, diff_above)
    
def validate_series(data_test):
    """Validates the data and handles missing values."""
    data_test = data_test.fillna(data_test.median())  
    return data_test

def filter_data_by_condition(data, column1, column2, condition):
    """Filters data based on a comparison condition."""
    if condition == 'lower':
        return data[data[column1] > data[column2]]
    elif condition == 'higher':
        return data[data[column1] < data[column2]]
    elif condition == 'equal':
        return data[data[column1] == data[column2]]
    else:
        return pd.DataFrame() 

def delete_columns(data, columns_to_delete):
    """Deletes specified columns from a DataFrame if they exist."""
    for col in columns_to_delete:
        if col in data:
            del data[col]
    return data

def convert_week_period_to_date(periodname):
    """
    Converts a period name in the format 'Wn YYYY' (e.g., 'W1 2023') to 
    the start date of that week.

    Args:
        periodname (str): The period name to convert.

    Returns:
        datetime.date: The start date of the week.
    """
    week_num, year = periodname.split(' ')
    year = int(year)
    first_day_of_year = datetime(year, 1, 1)
    start_of_week = first_day_of_year - timedelta(days=first_day_of_year.isoweekday() - 1)  
    return start_of_week + timedelta(days=7 * (int(week_num[1:]) - 1))

# Streamlit app layout
#st.title('HMIS - Data Quality App')
# Color palette example
primaryColor = "#004777"  # Blue
secondaryColor = "#EAF2F8"  # Light gray
accentColor = "#2E86C1"  # Light blue

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
    **Purpose:** This app helps to ease Data Quality Checks in HMIS data based on statistical analysis. 

    **Steps:**
    1. **Upload File downloaded from DHIS2:** Click the "Choose file" button and select the file. Your data should have a 'periodname' column (as dates) and a 'organisationunitname' column or 
             you can use the Test data in the link.
    2. **Select Data Element:** Choose the column/element you want to analyze from the dropdown.
    3. **Review Results:** The app will process your data and generate:
       * A line chart visualizing the data points and highlighting potential outliers (red markers).
       * A count of possible outliers for the selected facility.
    4. **Filter by Facility:** Use the facility dropdown to focus on results for a specific facility.
    5. **Download Outliers:**  Click the "Download as CSV" link to save identified outliers.
    6. **LogicalTest:** Set relationships between selected elements and cross check which elements violate the Rule
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

def cconvert_week_period_to_date(period):
    year_week = period.split('W')
    return f"{year_week[0]}-W{int(year_week[1])}-1"

def convert_quarter_period_to_date(period):
    year_quarter = period.split('Q')
    quarter_start_month = (int(year_quarter[1]) - 1) * 3 + 1
    return f"{year_quarter[0]}-{quarter_start_month:02d}-01"

def parse_index(data):

    if isinstance(data.index, pd.Index) and data.index.str.contains('W').any():
        # Handle week format
        data.index = data.index.map(convert_week_period_to_date)
    elif isinstance(data.index, pd.Index) and data.index.str.contains('Q').any():
        # Handle quarter format
        data.index = data.index.map(convert_quarter_period_to_date)
    else:
        for fmt in ['%B %Y', '%b-%y']:
            try:
                data.index = pd.to_datetime(data.index, format=fmt)
                break
            except ValueError:
                pass 
        else:
            raise ValueError ("Could not parse date format in index. Supported formats: %B %Y, %b %Y")
    return data

# Section for the download link
file_path = "Test_data.csv"  
st.markdown(get_file_download_link(file_path), unsafe_allow_html=True)
# Selector for which column to analyze 
st.subheader("Upload Data to be Accessed")
uploaded_file = st.file_uploader("Choose file ( weekly , Monthly ,  Quarterly, Annualy)", type=['csv', 'xls', 'xlsx'])

if uploaded_file is not None:
    with st.spinner("Processing data..."):
        try:
            file_extension = uploaded_file.name.split('.')[-1].lower()
            
            if file_extension == 'csv':
                data = pd.read_csv(uploaded_file, index_col='periodname', parse_dates=False)
                columns_to_delete = ['periodid','periodcode','perioddescription','organisationunitid','organisationunitcode','organisationunitdescription','test']
                data = delete_columns(data, columns_to_delete)
            elif file_extension in  ["xls",'xlsx']:
                data = pd.read_excel(uploaded_file, index_col='periodname',skiprows=1, parse_dates=False, engine='openpyxl' if file_extension == 'xlsx' else 'xlrd')
            else:
                st.error("Unsupported file format. Please upload a CSV or Excel file.")
                raise ValueError

            data = parse_index(data)
            original = data

            # Apply column deletion

            st.success("Data uploaded successfully!")
            st.write('Preview of the Uploaded Data')
            st.dataframe(data.head(),use_container_width=True)

            # ... (The rest of your app code, using the 'data' variable)

        except Exception as e:
            st.error(f"Error uploading file: {e}") 

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
                min_value = 0.75, max_value = 0.99,value = 0.97 , step= 0.0001 )
  
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
  st.subheader("Download the Possible Outliers")

  download_format = st.radio(" ", ['CSV', 'Excel'], index=0, horizontal= True)

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
  
  st.header("Logical Checks")
   # User selections
  

  column1 = st.selectbox("Select the first element", columns, last_col_index)
  column2 = st.selectbox("Select the second element", columns, last_col_index - 2)
  relationship = st.selectbox(f'Choose the Relationship between  {column1} and {column2}', ['higher', 'lower', 'equal'])
  
  # Filter and display outliers based on user selections
  filtered_data = filter_data_by_condition(original, column1, column2, relationship)
  filtered_data['year']  = filtered_data.index.year
  filtered_data = filtered_data[filtered_data['year'] == 2024]
  filtered_data = filtered_data[['organisationunitname',column1, column2]]

  if filtered_data.empty:
        st.warning("No records found that violate the specified relationship.")
  else:
        st.subheader("Records Violating the Expected Relationship n 2024")
        st.dataframe(filtered_data, use_container_width=True)
    # Download CSV section

  if filtered_data.shape[0] > 0:  # Check if there are outliers to download
    if download_format == 'CSV':
        csv = filtered_data.to_csv(index=True)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="Rule_violaters.csv">Download as CSV</a>'

    elif download_format == 'Excel':
        def to_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=True, sheet_name='Sheet1')
            processed_data = output.getvalue()
            return processed_data

        df_xlsx = to_excel(filtered_data)
        b64 = base64.b64encode(df_xlsx).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="rule_violators.xlsx">Download as Excel</a>'
    
    with st.expander('Download the Results'):
        download_format = st.radio(" ", ['CSV', 'Excel'], index=0, horizontal= True, key= 'rules')

        st.markdown(href, unsafe_allow_html=True)

  else:
      st.warning("No Records to Download.")

 
  
  
  
  with st.expander("Contact the Biostatician"):
        biostat = pd.read_excel('Biostats contacts.xlsx')
        biostat = biostat.iloc[:, :5]
        st.dataframe(biostat, use_container_width=True)