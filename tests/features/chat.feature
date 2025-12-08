Feature: Chat Interface
  As a user
  I want to chat with the AI assistant
  So that I can ask questions and get financial analysis

  Background:
    Given the MCP connection is established
    And the LLM is initialized
    And tools are bound to the LLM

  Scenario: Send simple chat message
    Given I have no chat history
    When I send the message "Hello"
    Then I should receive a response
    And the response should be a greeting
    And no tools should be called

  Scenario: Ask about available hierarchies
    Given I have no chat history
    When I send the message "What hierarchies are available?"
    Then I should receive a response
    And the tool "get_all_hierarchies" should be called
    And the response should mention "FHC"

  Scenario: Request HPL calculation
    Given I have no chat history
    When I send the message "Calculate hypothetical P&L for account ACCT-001 using FHC hierarchy"
    Then I should receive a response
    And the tool "calculate_hypothetical_pnl" should be called
    And the tool call arguments should include "account_number" set to "ACCT-001"
    And the tool call arguments should include "hierarchy" set to "FHC"
    And the response should contain "165000" or "$165,000"

  Scenario: Multi-turn conversation
    Given I have no chat history
    When I send the message "What hierarchies are available?"
    And I receive a response mentioning "FHC"
    And I send the message "Get the formula for FHC"
    Then I should receive a response
    And the tool "get_hpl_formula" should be called
    And the response should contain "Trading P&L"

  Scenario: Chat with conversation history
    Given I have a chat history with 2 messages
    When I send the message "What was my previous question?"
    Then I should receive a response
    And the response should reference the conversation history

  Scenario: Handle unclear questions
    Given I have no chat history
    When I send the message "Tell me about it"
    Then I should receive a response
    And the response should ask for clarification

  Scenario Outline: Ask various financial questions
    Given I have no chat history
    When I send the message "<question>"
    Then I should receive a response
    And the tool "<expected_tool>" should be called
    And the response should contain "<expected_content>"

    Examples:
      | question                          | expected_tool              | expected_content |
      | List all accounts                 | get_all_accounts           | ACCT-001         |
      | What's the formula for FHC?       | get_hpl_formula            | formula          |
      | Show P&L for ACCT-001             | get_account_pnl            | P&L              |
