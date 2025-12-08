"""
Step definitions for Web API feature tests
"""
import pytest
import json
from pytest_bdd import scenarios, given, when, then, parsers

# Load scenarios from feature file
scenarios('../features/web_api.feature')


@given('the Flask application is running')
def flask_app_running(test_client):
    """Verify Flask app is running"""
    assert test_client is not None
    return test_client


@given('the MCP server is connected')
def mcp_connected(mcp_manager):
    """Verify MCP connection"""
    assert mcp_manager is not None
    return mcp_manager


@when(parsers.parse('I make a GET request to "{endpoint}"'))
def make_get_request(test_client, api_context, endpoint):
    """Make GET request to endpoint"""
    response = test_client.get(endpoint)
    api_context['response'] = response
    api_context['endpoint'] = endpoint


@then(parsers.parse('the response status should be {status_code:d}'))
def verify_status_code(api_context, status_code):
    """Verify response status code"""
    assert api_context['response'].status_code == status_code


@then('the response should contain HTML')
def response_contains_html(api_context):
    """Verify response contains HTML"""
    content_type = api_context['response'].headers.get('Content-Type', '')
    assert 'text/html' in content_type


@then(parsers.parse('the page should contain "{text}"'))
def page_contains_text(api_context, text):
    """Verify page contains text"""
    data = api_context['response'].data.decode('utf-8')
    assert text in data


@then('the response should be valid JSON')
def response_is_json(api_context):
    """Verify response is JSON"""
    try:
        json_data = api_context['response'].get_json()
        api_context['json'] = json_data
        assert json_data is not None
    except Exception as e:
        pytest.fail(f"Response is not valid JSON: {e}")


@then(parsers.parse('the JSON should have a "{field}" array'))
def json_has_array(api_context, field):
    """Verify JSON has array field"""
    json_data = api_context['json']
    assert field in json_data
    assert isinstance(json_data[field], list)


@then(parsers.parse('the {field} array should have {count:d} items'))
def array_has_count(api_context, field, count):
    """Verify array item count"""
    json_data = api_context['json']
    assert len(json_data[field]) == count


@then(parsers.parse('each prompt should have "{field1}" and "{field2}"'))
def prompts_have_fields(api_context, field1, field2):
    """Verify each prompt has required fields"""
    prompts = api_context['json']['prompts']
    for prompt in prompts:
        assert field1 in prompt
        assert field2 in prompt


@given('I have a JSON payload with')
def create_json_payload(api_context, datatable):
    """Create JSON payload from data table"""
    payload = {}
    for row in datatable:
        field = row['field']
        value = row['value']
        # Parse JSON strings
        if value.startswith('{') or value.startswith('['):
            try:
                value = json.loads(value)
            except:
                pass
        payload[field] = value
    api_context['payload'] = payload


@when(parsers.parse('I make a POST request to "{endpoint}" with the payload'))
def make_post_request(test_client, api_context, endpoint):
    """Make POST request with payload"""
    payload = api_context.get('payload', {})
    response = test_client.post(
        endpoint,
        data=json.dumps(payload),
        content_type='application/json'
    )
    api_context['response'] = response
    try:
        api_context['json'] = response.get_json()
    except:
        pass


@then(parsers.parse('the JSON should have "{field}" set to {value}'))
def json_field_equals(api_context, field, value):
    """Verify JSON field value"""
    json_data = api_context['json']

    # Convert string value to proper type
    if value.lower() == 'true':
        value = True
    elif value.lower() == 'false':
        value = False
    elif value.isdigit():
        value = int(value)

    assert field in json_data
    assert json_data[field] == value


@then(parsers.parse('the JSON should have an "{field}" field'))
def json_has_field(api_context, field):
    """Verify JSON has field"""
    json_data = api_context['json']
    assert field in json_data


@then('the results should contain multiple rounds')
def results_have_rounds(api_context):
    """Verify results contain rounds"""
    results = api_context['json']['results']
    assert len(results) > 1


@then('the results should contain tool calls')
def results_have_tool_calls(api_context):
    """Verify results contain tool calls"""
    results = api_context['json']['results']
    tool_results = [r for r in results if r.get('type') == 'tools']
    assert len(tool_results) > 0


@then(parsers.parse('the tool_calls should contain "{tool_name}"'))
def tool_calls_contain_tool(api_context, tool_name):
    """Verify tool calls contain specific tool"""
    data = api_context['json']['data']
    tool_calls = data.get('tool_calls', [])
    tool_names = [tc['name'] for tc in tool_calls]
    assert tool_name in tool_names


@given('I have an invalid JSON payload')
def create_invalid_payload(api_context):
    """Create invalid JSON payload"""
    api_context['invalid_payload'] = '{invalid json'


@when(parsers.parse('I make a POST request to "{endpoint}" with the payload'))
def make_post_with_invalid_json(test_client, api_context, endpoint):
    """Make POST request with invalid JSON"""
    if 'invalid_payload' in api_context:
        response = test_client.post(
            endpoint,
            data=api_context['invalid_payload'],
            content_type='application/json'
        )
        api_context['response'] = response


@then('the response should have CORS headers')
def has_cors_headers(api_context):
    """Verify CORS headers present"""
    headers = api_context['response'].headers
    # Check for any CORS-related header
    cors_headers = [h for h in headers.keys() if 'Access-Control' in h]
    assert len(cors_headers) > 0


@then(parsers.parse('the "{header_name}" header should be present'))
def header_present(api_context, header_name):
    """Verify specific header is present"""
    headers = api_context['response'].headers
    assert header_name in headers
