# age_input_module.R

ageInputModuleUI <- function(id) {
  ns <- NS(id)
  tagList(
    h3("Input Your Chronological Age"),
    numericInput(ns("age"), "Age (in years):", value = NULL, min = 0, step = 1),
    helpText("Please enter your age as a whole number.")
  )
}

ageInputModuleServer <- function(id) {
  moduleServer(id, function(input, output, session) {
    return(reactive({
      input$age
    }))
  })
}