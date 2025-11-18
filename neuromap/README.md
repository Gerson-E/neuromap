# Shiny DICOM MRI App

This Shiny application allows users to upload DICOM MRI images and input their chronological age. It serves as a preliminary step for preprocessing data for machine learning models.

## Features

- **DICOM File Upload**: Users can upload MRI images in DICOM format.
- **Age Input**: Users can input their chronological age, which may be used for analysis or preprocessing.
- **Modular Design**: The application is built using a modular approach, making it easy to maintain and extend.

## Installation

To run this application, you need to have R and the Shiny package installed. You can install the required packages using the following commands:

```R
install.packages("shiny")
```

## Usage

1. Clone the repository or download the ZIP file.
2. Open the `app.R` file in RStudio or your preferred R environment.
3. Run the application by executing the following command in the R console:

```R
shiny::runApp("path/to/shiny-dicom-mri-app")
```

4. Once the application is running, you can upload your DICOM MRI file and input your chronological age.

## Contributing

Contributions are welcome! If you have suggestions for improvements or new features, please open an issue or submit a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.