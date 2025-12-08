# BDD Test Suite

Comprehensive Behavior-Driven Development (BDD) tests for the Finance MCP Chat Agent.

## Overview

This test suite uses pytest-bdd to write tests in Gherkin syntax that are readable by both technical and non-technical stakeholders. The tests cover:

- MCP server integration
- Prompt management and execution
- Chat interface functionality
- Web API endpoints
- Tool calling and result processing

## Test Structure

```
tests/
├── features/               # Gherkin feature files
│   ├── mcp_integration.feature
│   ├── prompts.feature
│   ├── chat.feature
│   └── web_api.feature
├── step_defs/             # Step implementations
│   ├── test_mcp_integration_steps.py
│   └── test_web_api_steps.py
├── fixtures/              # Test data and helpers
├── conftest.py            # Pytest configuration and fixtures
└── README.md              # This file
```

## Prerequisites

1. **Install test dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Ensure MCP server is running**:
   - The finance MCP server must be accessible at the configured path
   - Check `.mcp.json` for server configuration

3. **Set environment variables**:
   - Copy `.env.example` to `.env`
   - Add your `ANTHROPIC_API_KEY`

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Feature

```bash
# Run MCP integration tests
pytest tests/features/mcp_integration.feature

# Run prompt tests
pytest tests/features/prompts.feature

# Run chat tests
pytest tests/features/chat.feature

# Run API tests
pytest tests/features/web_api.feature
```

### Run Specific Scenario

```bash
pytest tests/features/mcp_integration.feature -k "Successfully connect to MCP server"
```

### Run with Markers

```bash
# Run only integration tests
pytest -m integration

# Run only API tests
pytest -m api

# Skip slow tests
pytest -m "not slow"
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```

### Verbose Output

```bash
# Detailed output
pytest -v

# Even more detailed
pytest -vv

# Show print statements
pytest -s
```

## Test Features

### MCP Integration (`mcp_integration.feature`)

Tests the Model Context Protocol server integration:

- **Connection establishment**: Verify MCP server connection
- **Tool listing**: Get available tools from MCP server
- **Tool execution**: Call tools with and without arguments
- **Error handling**: Handle invalid tool names and failures

**Example scenarios**:
```gherkin
Scenario: Successfully connect to MCP server
  When I initialize the MCP connection
  Then the connection should be established
  And I should see available tools loaded
```

### Prompts Management (`prompts.feature`)

Tests MCP prompt functionality:

- **Prompt listing**: Get all available prompts
- **Prompt details**: Get prompt metadata and requirements
- **Prompt execution**: Execute prompts with parameters
- **Workflow execution**: Multi-step workflow completion
- **Parameter validation**: Handle missing required parameters

**Example scenarios**:
```gherkin
Scenario: Execute complete workflow
  Given I select the prompt "finance_complete_analysis"
  And I set the parameter "hierarchy" to "FHC"
  When I execute the complete workflow
  Then the workflow should complete in 3 rounds
```

### Chat Interface (`chat.feature`)

Tests conversational AI capabilities:

- **Simple messages**: Send and receive chat messages
- **Tool calling**: Automatic tool invocation based on queries
- **Multi-turn conversations**: Maintain context across messages
- **History management**: Use conversation history
- **Question variety**: Handle different types of financial questions

**Example scenarios**:
```gherkin
Scenario: Request HPL calculation
  When I send the message "Calculate hypothetical P&L for account ACCT-001"
  Then the tool "calculate_hypothetical_pnl" should be called
  And the response should contain "165000"
```

### Web API (`web_api.feature`)

Tests Flask REST API endpoints:

- **Homepage**: Serve web UI
- **GET endpoints**: List prompts and tools
- **POST endpoints**: Execute prompts and chat
- **Error responses**: Handle malformed requests
- **CORS headers**: Verify cross-origin support

**Example scenarios**:
```gherkin
Scenario: Get list of prompts via API
  When I make a GET request to "/api/prompts"
  Then the response status should be 200
  And the JSON should have a "prompts" array
```

## Writing New Tests

### 1. Create Feature File

Create a new `.feature` file in `tests/features/`:

```gherkin
Feature: New Feature Name
  As a user
  I want to do something
  So that I can achieve a goal

  Scenario: Test scenario name
    Given a precondition
    When I perform an action
    Then I should see a result
```

### 2. Implement Step Definitions

Create corresponding steps in `tests/step_defs/`:

```python
from pytest_bdd import scenarios, given, when, then

scenarios('../features/new_feature.feature')

@given('a precondition')
def precondition():
    # Setup code
    pass

@when('I perform an action')
def perform_action(context):
    # Action code
    context['result'] = do_something()

@then('I should see a result')
def verify_result(context):
    assert context['result'] is not None
```

### 3. Use Fixtures

Leverage existing fixtures from `conftest.py`:

```python
@when('I use MCP manager')
def use_manager(mcp_manager, context):
    context['tools'] = await mcp_manager.list_tools()
```

## Test Markers

Use markers to categorize tests:

```python
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.api
def test_something():
    pass
```

## Debugging Tests

### Print Debug Info

```bash
# Show print statements
pytest -s

# Show detailed traceback
pytest --tb=long
```

### Run Single Test

```bash
# Run specific test function
pytest tests/step_defs/test_mcp_integration_steps.py::test_connect

# Run with Python debugger
pytest --pdb
```

### Check Test Collection

```bash
# List all tests without running
pytest --collect-only
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Best Practices

1. **Keep scenarios focused**: One scenario should test one behavior
2. **Use descriptive names**: Scenario names should be clear and specific
3. **Avoid implementation details**: Write from user perspective
4. **Reuse steps**: Share common steps across features
5. **Use backgrounds**: Extract common setup to Background sections
6. **Test edge cases**: Include error scenarios and boundary conditions
7. **Mock external dependencies**: Use fixtures for external services
8. **Keep tests fast**: Mock slow operations when possible

## Troubleshooting

### MCP Server Connection Fails

```
Error: Could not connect to MCP server
```

**Solution**: Ensure the MCP server is running and the path in `mcp_integration.py` is correct.

### Missing Fixtures

```
Error: fixture 'mcp_manager' not found
```

**Solution**: Check that `conftest.py` is in the tests directory and properly configured.

### Import Errors

```
ImportError: No module named 'app'
```

**Solution**: Ensure the parent directory is in Python path (handled by `conftest.py`).

### Async Issues

```
Error: Event loop is closed
```

**Solution**: Use the `event_loop` fixture and `run_async` helper from `conftest.py`.

## Test Coverage

Current coverage targets:

- **Overall**: >80%
- **Critical paths**: >95%
- **API endpoints**: 100%
- **Error handling**: >90%

View coverage report:
```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

## Contributing

When adding new features:

1. Write feature file first (BDD approach)
2. Implement step definitions
3. Ensure tests pass
4. Update this documentation
5. Submit pull request with tests

## Resources

- [pytest-bdd documentation](https://pytest-bdd.readthedocs.io/)
- [Gherkin syntax reference](https://cucumber.io/docs/gherkin/reference/)
- [pytest documentation](https://docs.pytest.org/)
- [BDD best practices](https://cucumber.io/docs/bdd/)
