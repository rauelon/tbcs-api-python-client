from typing import List, Dict
import random
import string

import pytest

import tbcs_client

connector: tbcs_client.APIConnector = tbcs_client.APIConnector()
connector.log_in()

new_test_case_name: str = 'Python APIConnector Test'
new_test_case_description: str = 'Description'
new_test_case_test_steps: List[Dict] = [
    {'description': 'first step', 'id': '-1'},
    {'description': 'second step', 'id': '-1'},
    {'description': 'third step', 'id': '-1'}
    ]
new_test_case_external_id: str = ''.join(random.choices(string.ascii_letters + string.digits, k=24))

new_defect_name: str = 'Python APIConnector Defect'
new_defect_message: str = 'Message'

new_test_case_id: str
new_execution_id: str
new_defect_id: str


@pytest.mark.dependency()
def test_create_test_case_and_get_test_case_by_id():
    global new_test_case_id
    new_test_case_id = connector.create_test_case(
        new_test_case_name,
        new_test_case_description,
        tbcs_client.APIConnector.TEST_CASE_TYPE_STRUCTURED,
        new_test_case_external_id
    )

    test_case: dict = connector.get_test_case_by_id(new_test_case_id)

    assert (test_case['name'] == new_test_case_name)
    assert (test_case['description'] == new_test_case_description)
    assert (test_case['automation']['externalId'] == new_test_case_external_id)


@pytest.mark.dependency(depends=["test_create_test_case_and_get_test_case_by_id"])
def test_get_test_case_by_external_id():
    test_case: dict = connector.get_test_case_by_external_id(new_test_case_external_id)
    assert (str(test_case['id']) == new_test_case_id)


@pytest.mark.dependency(depends=["test_create_test_case_and_get_test_case_by_id"])
def test_update_test_case_description():
    new_description: str = "New"
    connector.update_test_case_description(new_test_case_id, new_description)
    test_case: dict = connector.get_test_case_by_id(new_test_case_id)

    assert (test_case['description'] == new_description)


@pytest.mark.dependency(depends=["test_create_test_case_and_get_test_case_by_id"])
def test_add_test_step():
    new_test_case_test_steps[0]['id'] = connector.add_test_step(new_test_case_id, new_test_case_test_steps[0]['description'])
    new_test_case_test_steps[1]['id'] = connector.add_test_step(new_test_case_id, new_test_case_test_steps[1]['description'])
    new_test_case_test_steps[2]['id'] = connector.add_test_step(new_test_case_id, new_test_case_test_steps[2]['description'], new_test_case_test_steps[0]['id'])

    test_steps: List = connector.get_test_case_by_id(new_test_case_id)['testSequence']['testStepBlocks'][tbcs_client.APIConnector.get_test_block_index_by_name(tbcs_client.APIConnector.TEST_BLOCK_TEST_NAME)]['steps']

    assert (str(test_steps[0]['id']) == new_test_case_test_steps[0]['id'])
    assert (str(test_steps[1]['id']) == new_test_case_test_steps[2]['id'])
    assert (str(test_steps[2]['id']) == new_test_case_test_steps[1]['id'])


@pytest.mark.dependency(depends=["test_add_test_step"])
def test_remove_test_step():
    connector.remove_test_step(new_test_case_id, new_test_case_test_steps[2]['id'])

    test_steps: List = connector.get_test_case_by_id(new_test_case_id)['testSequence']['testStepBlocks'][tbcs_client.APIConnector.get_test_block_index_by_name(tbcs_client.APIConnector.TEST_BLOCK_TEST_NAME)]['steps']

    assert (str(test_steps[0]['id']) == new_test_case_test_steps[0]['id'])
    assert (str(test_steps[1]['id']) == new_test_case_test_steps[1]['id'])


@pytest.mark.dependency(depends=["test_remove_test_step"])
def test_start_execution_and_get_execution_by_id():
    global new_execution_id
    new_execution_id = connector.start_execution(new_test_case_id)

    execution: dict = connector.get_execution_by_id(new_test_case_id, new_execution_id)
    assert (str(execution['testCase']['id']) == new_test_case_id)


@pytest.mark.dependency(depends=["test_start_execution_and_get_execution_by_id"])
def test_report_step_result():
    connector.report_step_result(new_test_case_id, new_execution_id, new_test_case_test_steps[0]['id'], tbcs_client.APIConnector.TEST_STEP_STATUS_PASSED)
    connector.report_step_result(new_test_case_id, new_execution_id, new_test_case_test_steps[1]['id'], tbcs_client.APIConnector.TEST_STEP_STATUS_FAILED)

    execution_steps: dict = connector.get_execution_by_id(new_test_case_id, new_execution_id)['testSequence']['testStepBlocks'][tbcs_client.APIConnector.get_test_block_index_by_name(tbcs_client.APIConnector.TEST_BLOCK_TEST_NAME)]['steps']
    assert (execution_steps[0]['result'] == tbcs_client.APIConnector.TEST_STEP_STATUS_PASSED)
    assert (execution_steps[1]['result'] == tbcs_client.APIConnector.TEST_STEP_STATUS_FAILED)


@pytest.mark.dependency(depends=["test_report_step_result"])
def test_create_and_assign_defect():
    global new_defect_id
    new_defect_id = connector.create_defect(new_defect_name, new_defect_message)
    connector.assign_defect(new_test_case_id, new_execution_id, new_test_case_test_steps[1]['id'], new_defect_id)

    execution_steps: dict = connector.get_execution_by_id(new_test_case_id, new_execution_id)['testSequence']['testStepBlocks'][tbcs_client.APIConnector.get_test_block_index_by_name(tbcs_client.APIConnector.TEST_BLOCK_TEST_NAME)]['steps']
    assert (str(execution_steps[1]['defectIds'][0]) == new_defect_id)
