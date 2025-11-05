library(shiny)
source("R/modules/upload_module.R")
source("R/modules/age_input_module.R")

ui <- fluidPage(
  titlePanel("DICOM MRI Upload and Age Input"),
  
  sidebarLayout(
    sidebarPanel(
      uploadModuleUI("dicom_upload"),
      ageInputModuleUI("age_input")
    ),
    
    mainPanel(
      textOutput("info")
    )
  )
)

server <- function(input, output, session) {
  dicom_data <- uploadModuleServer("dicom_upload")
  age <- ageInputModuleServer("age_input")
  
  output$info <- renderText({
    req(dicom_data(), age())
    paste("Uploaded DICOM file:", dicom_data()$name, 
          "\nChronological Age:", age())
  })
}

shinyApp(ui, server)