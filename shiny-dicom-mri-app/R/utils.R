# Utility functions for the Shiny DICOM MRI app

# Function to validate chronological age input
validate_age <- function(age) {
  if (!is.numeric(age) || age < 0 || age > 120) {
    return(FALSE)
  }
  return(TRUE)
}

# Function to check if a file is a DICOM file
is_dicom_file <- function(file) {
  if (is.null(file)) {
    return(FALSE)
  }
  return(grepl("\\.dcm$", file$name, ignore.case = TRUE))
}

# Function to read DICOM file and return metadata
read_dicom_metadata <- function(file) {
  if (!is_dicom_file(file)) {
    stop("Uploaded file is not a valid DICOM file.")
  }
  # Placeholder for actual DICOM reading logic
  # dicom_data <- readDICOM(file$datapath)
  # return(dicom_data)
  return("DICOM metadata would be returned here.")
}