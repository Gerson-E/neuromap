library(testthat)

# Test for the upload module
test_that("uploadModuleUI returns a valid UI", {
  ui <- uploadModuleUI("test_upload")
  expect_s3_class(ui, "shiny.tag")
})

test_that("uploadModuleServer handles file upload", {
  # Mock server function
  server <- function(input, output, session) {
    uploadModuleServer("test_upload")
  }
  
  # Create a mock Shiny app
  shiny::shinyApp(ui = uploadModuleUI("test_upload"), server = server)
  
  # Simulate file upload
  session$setInputs(test_upload = list(files = list(name = "test.dcm", type = "application/dicom", size = 12345)))
  
  # Check if the file is uploaded correctly
  expect_true(!is.null(input$test_upload))
})

# Test for the age input module
test_that("ageInputModuleUI returns a valid UI", {
  ui <- ageInputModuleUI("test_age")
  expect_s3_class(ui, "shiny.tag")
})

test_that("ageInputModuleServer captures age input", {
  # Mock server function
  server <- function(input, output, session) {
    ageInputModuleServer("test_age")
  }
  
  # Create a mock Shiny app
  shiny::shinyApp(ui = ageInputModuleUI("test_age"), server = server)
  
  # Simulate age input
  session$setInputs(test_age = 30)
  
  # Check if the age is captured correctly
  expect_equal(input$test_age, 30)
})