Feature: MCP Server Integration
  As a developer
  I want to connect to the MCP server
  So that I can use finance tools and prompts

  Background:
    Given the MCP server is available
    And the application is initialized

  Scenario: Successfully connect to MCP server
    When I initialize the MCP connection
    Then the connection should be established
    And I should see available tools loaded
    And the tools list should contain "get_hpl_formula"
    And the tools list should contain "calculate_hypothetical_pnl"

  Scenario: List available MCP tools
    Given the MCP connection is established
    When I request the list of tools
    Then I should receive 5 tools
    And each tool should have a name and description

  Scenario: Call MCP tool successfully
    Given the MCP connection is established
    When I call the tool "get_all_hierarchies" with no arguments
    Then the tool should execute successfully
    And I should receive the result "FHC"

  Scenario: Call MCP tool with arguments
    Given the MCP connection is established
    When I call the tool "get_hpl_formula" with argument "hierarchy" set to "FHC"
    Then the tool should execute successfully
    And the result should contain "Hypothetical P&L"
    And the result should contain "Trading P&L"

  Scenario: Handle invalid tool name
    Given the MCP connection is established
    When I call the tool "invalid_tool_name" with no arguments
    Then the tool call should fail
    And I should receive an error message
