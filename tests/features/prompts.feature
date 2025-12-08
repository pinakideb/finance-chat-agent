Feature: MCP Prompts Management
  As a user
  I want to use predefined MCP prompts
  So that I can execute guided financial analysis workflows

  Background:
    Given the MCP connection is established
    And prompts are loaded

  Scenario: List available prompts
    When I request the list of prompts
    Then I should receive 6 prompts
    And the prompts should include "finance_step1"
    And the prompts should include "finance_complete_analysis"

  Scenario: Get prompt details
    When I request details for prompt "finance_step1"
    Then the prompt should have a name "finance_step1"
    And the prompt should have a description
    And the prompt should have 0 required arguments

  Scenario: Get prompt with arguments
    When I request details for prompt "finance_complete_analysis"
    Then the prompt should have a name "finance_complete_analysis"
    And the prompt should require argument "hierarchy"

  Scenario: Execute simple prompt
    Given I select the prompt "finance_step1"
    When I execute the prompt
    Then the prompt should execute successfully
    And I should receive prompt messages
    And the messages should contain "hierarchy"

  Scenario: Execute prompt with parameters
    Given I select the prompt "finance_complete_analysis"
    And I set the parameter "hierarchy" to "FHC"
    When I execute the prompt
    Then the prompt should execute successfully
    And I should receive 4 workflow steps
    And the workflow should call tools
    And the workflow should produce results

  Scenario: Execute complete workflow
    Given I select the prompt "finance_complete_analysis"
    And I set the parameter "hierarchy" to "FHC"
    When I execute the complete workflow
    Then the workflow should complete in 3 rounds
    And I should see "get_hpl_formula" was called
    And I should see "get_all_accounts" was called
    And I should see "calculate_hypothetical_pnl" was called
    And the final result should contain "Hypothetical P&L"
    And the final result should contain "$165,000"

  Scenario: Handle missing required parameters
    Given I select the prompt "finance_complete_analysis"
    When I execute the prompt without parameters
    Then the execution should fail
    And I should receive an error about missing "hierarchy" parameter

  Scenario Outline: Execute different workflow steps
    Given I select the prompt "<prompt_name>"
    And I set the parameter "hierarchy" to "<hierarchy>"
    When I execute the prompt
    Then the prompt should execute successfully
    And the result should contain "<expected_content>"

    Examples:
      | prompt_name     | hierarchy | expected_content  |
      | finance_step2   | FHC       | formula           |
      | finance_step3   | FHC       | account           |
