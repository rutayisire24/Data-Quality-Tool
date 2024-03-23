**Key Features**

*Intuitive Upload Easily upload your CSV data.
Customizable Outlier Detection: Select the data element (column) you want to analyze.
Interactive Visualization: Explore potential outliers with a line chart, highlighting outliers and indicating quantiles for context.
Facility-Specific Filtering: Focus your analysis on a single facility using the dropdown filter.
Downloadable Results: Obtain a CSV file containing identified outliers for further review.
Missing Value Handling: Choose from various imputation methods (mean, median, removal, custom value) to address missing data.
How to Use

**Install Dependencies:**
```Bash
pip install streamlit pandas plotly adtk numpy
```


*Download the App:* 
``` Clone this repository or download app.py.
Run the Streamlit App:
Bash
streamlit run app.py
```

Access the App: The app will open in your web browser, typically at http://localhost:8501.
Otherwise this Tool currently hosted at https://rutayisire24-data-quality-tool-localarea-u4ok6l.streamlit.app

**Data Requirements**

Your CSV file should contain the following columns:
periodname (dates)
organisationunitname (facility names)
Data elements that you'd like to analyze

**Example Dataset**

The app will work effectively with HMIS datasets, and you can find sample data or create your own using this structure:

```
periodname,organisationunitname,ANC Visits,Deliveries,IPD Patients
2023-01-01,Facility A,100,50,20
2023-02-01,Facility A,115,45,30
2023-01-01,Facility B,50,10,15
```


**Customization**

Modify the detect_outliers function to fine-tune outlier detection methods.
Adjust the plotting section to experiment with different visualizations.
Within the validate_series function, implement additional data validation checks and imputation strategies.
Contributing

We welcome contributions to improve this app! Feel free to:

Submit bug reports and feature requests as issues.
Fork the repository and create pull requests with your enhancements.
License

This project is licensed under the MIT License. For more information, see the LICENSE file.
