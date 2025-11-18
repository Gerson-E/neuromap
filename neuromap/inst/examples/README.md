# README for Shiny DICOM MRI App

## Overview
The Shiny DICOM MRI App is designed to facilitate the upload of DICOM MRI images and the input of chronological age for preprocessing in machine learning models. This application serves as a user-friendly interface for researchers and clinicians to interact with MRI data.

## Features
- Upload DICOM MRI files for analysis.
- Input chronological age to accompany the uploaded MRI data.
- Modular design for easy maintenance and scalability.

## Usage Instructions
1. **Installation**: Ensure you have R and the Shiny package installed. You can install the necessary packages using the following command:
   ```R
   install.packages(c("shiny", "shinydashboard", "oro.dicom"))
   ```

2. **Running the App**: To run the application, navigate to the project directory in R and execute:
   ```R
   shiny::runApp("app.R")
   ```

3. **Uploading DICOM Files**: Use the upload button in the app to select and upload your DICOM MRI files.

4. **Inputting Age**: Enter your chronological age in the provided input field.

## Example Data
For testing purposes, you can use sample DICOM MRI files available in the `inst/examples` directory. Ensure that the files are in the correct format for the application to process them effectively.

## Contribution
Contributions to enhance the functionality of the Shiny DICOM MRI App are welcome. Please submit a pull request or open an issue for discussion.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.