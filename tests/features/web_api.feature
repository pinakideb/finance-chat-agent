Feature: Web API Endpoints
  As a web client
  I want to interact with the Flask API
  So that I can use the application through HTTP requests

  Background:
    Given the Flask application is running
    And the MCP server is connected

  Scenario: Access home page
    When I make a GET request to "/"
    Then the response status should be 200
    And the response should contain HTML
    And the page should contain "Finance MCP Chat Agent"

  Scenario: Get list of prompts via API
    When I make a GET request to "/api/prompts"
    Then the response status should be 200
    And the response should be valid JSON
    And the JSON should have a "prompts" array
    And the prompts array should have 6 items
    And each prompt should have "name" and "description"

  Scenario: Get list of tools via API
    When I make a GET request to "/api/tools"
    Then the response status should be 200
    And the response should be valid JSON
    And the JSON should have a "tools" array
    And the tools array should have 5 items

  Scenario: Execute prompt via API
    Given I have a JSON payload with:
      | field         | value                      |
      | prompt_name   | finance_complete_analysis  |
      | arguments     | {"hierarchy": "FHC"}       |
    When I make a POST request to "/api/execute-prompt" with the payload
    Then the response status should be 200
    And the JSON should have "success" set to true
    And the JSON should have a "results" array
    And the results should contain multiple rounds
    And the results should contain tool calls

  Scenario: Execute prompt without required parameters
    Given I have a JSON payload with:
      | field         | value                      |
      | prompt_name   | finance_complete_analysis  |
      | arguments     | {}                         |
    When I make a POST request to "/api/execute-prompt" with the payload
    Then the response status should be 500
    And the JSON should have "success" set to false
    And the JSON should have an "error" field

  Scenario: Send chat message via API
    Given I have a JSON payload with:
      | field     | value                              |
      | message   | What hierarchies are available?    |
      | history   | []                                 |
    When I make a POST request to "/api/chat" with the payload
    Then the response status should be 200
    And the JSON should have "success" set to true
    And the JSON should have a "data" object
    And the data should have a "response" field
    And the data should have a "tool_calls" array
    And the tool_calls should contain "get_all_hierarchies"

  Scenario: Send chat with conversation history
    Given I have a JSON payload with:
      | field     | value                                                              |
      | message   | Get the formula for FHC                                            |
      | history   | [{"role": "user", "content": "What hierarchies are available?"}]   |
    When I make a POST request to "/api/chat" with the payload
    Then the response status should be 200
    And the JSON should have "success" set to true
    And the tool_calls should contain "get_hpl_formula"

  Scenario: Handle invalid endpoint
    When I make a GET request to "/api/invalid_endpoint"
    Then the response status should be 404

  Scenario: Handle malformed JSON in POST request
    Given I have an invalid JSON payload
    When I make a POST request to "/api/chat" with the payload
    Then the response status should be 400

  Scenario: CORS headers are present
    When I make a GET request to "/api/tools"
    Then the response should have CORS headers
    And the "Access-Control-Allow-Origin" header should be present
