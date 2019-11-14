from typing import List
import json
import random
import string

import tbcs_client

test_case_for_validation: dict = {
    'id': 5,
    'name': 'some',
    'externalId': '1',
    'executions': [{
        'id': 1
    }]
}

new_test_case_name: str = 'test_create_test_case'
new_test_case_test_steps: List[str] = ['first step', 'second step', 'third step']


def new_test_case_external_id() -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=24))


def get_test_connector() -> tbcs_client.APIConnector:
    return tbcs_client.APIConnector()


def test_get_test_case_by_external_id():
    test_case: dict = get_test_connector().get_test_case_by_external_id(test_case_for_validation['externalId'])
    assert (test_case['name'] == test_case_for_validation['name'])
    assert (test_case['id'] == test_case_for_validation['id'])


def test_get_test_case_by_external_id_negative():
    try:
        test_case: dict = get_test_connector().get_test_case_by_external_id('some not existing external ID')
        raise Exception(f'Test case was matched. Data returned: {json.dumps(test_case)}')
    except tbcs_client.ItemNotFoundError:
        pass


def test_get_test_case_by_id():
    test_case: dict = get_test_connector().get_test_case_by_id(str(test_case_for_validation['id']))
    assert (test_case['name'] == test_case_for_validation['name'])
    assert (test_case['externalId'] == test_case_for_validation['externalId'])


def test_get_execution_by_id():
    execution: dict = get_test_connector().get_execution_by_id(
        str(test_case_for_validation['id']),
        str(test_case_for_validation['executions'][0]['id'])
    )
    assert (execution['testCase']['name'] == test_case_for_validation['name'])
    assert (execution['externalId'] == test_case_for_validation['externalId'])


def test_create_test_case():
    connector: tbcs_client.APIConnector = get_test_connector()
    external_id: str = new_test_case_external_id()
    test_case_id: str = connector.create_test_case(
        new_test_case_name,
        external_id,
        new_test_case_test_steps
    )

    test_case: dict = connector.get_test_case_by_id(test_case_id)
    response_steps: List[dict] = test_case['testStepBlocks'][2]['steps']

    assert (test_case['name'] == new_test_case_name)
    assert (test_case['externalId'] == external_id)
    assert (response_steps[0]['description'] == new_test_case_test_steps[0])
    assert (response_steps[1]['description'] == new_test_case_test_steps[1])
    assert (response_steps[2]['description'] == new_test_case_test_steps[2])


def test_start_execution():
    connector: tbcs_client.APIConnector = get_test_connector()
    external_id: str = new_test_case_external_id()
    test_case_id: str = connector.create_test_case(
        new_test_case_name,
        external_id,
        new_test_case_test_steps
    )

    execution_id: str = connector.start_execution(test_case_id)

    execution: dict = connector.get_execution_by_id(
        test_case_id,
        execution_id
    )
    assert (execution['testCase']['name'] == new_test_case_name)
    assert (execution['externalId'] == external_id)


def test_report_step_result():
    connector: tbcs_client.APIConnector = get_test_connector()
    test_case_id: str = connector.create_test_case(
        new_test_case_name,
        new_test_case_external_id(),
        new_test_case_test_steps
    )

    execution_id: str = connector.start_execution(test_case_id)

    connector.report_step_result(
        test_case_id,
        execution_id,
        '1',
        tbcs_client.APIConnector.test_step_status_passed
    )
    connector.report_step_result(
        test_case_id,
        execution_id,
        '2',
        tbcs_client.APIConnector.test_step_status_failed
    )

    execution_steps: dict = connector.get_execution_by_id(
        test_case_id,
        execution_id
    )['testStepBlocks'][2]['steps']

    assert (execution_steps[0]['result'] == tbcs_client.APIConnector.test_step_status_passed)
    assert (execution_steps[1]['result'] == tbcs_client.APIConnector.test_step_status_failed)
    assert (execution_steps[2]['result'] == tbcs_client.APIConnector.test_step_status_undefined)


def test_report_test_case_result():
    connector: tbcs_client.APIConnector = get_test_connector()
    test_case_id: str = connector.create_test_case(
        new_test_case_name,
        new_test_case_external_id(),
        new_test_case_test_steps
    )

    execution_id: str = connector.start_execution(test_case_id)

    execution: dict = connector.get_execution_by_id(
        test_case_id,
        execution_id
    )
    assert (execution['overallStatus']['status'] == tbcs_client.APIConnector.test_status_in_progress)

    connector.report_test_case_result(
        test_case_id,
        execution_id,
        tbcs_client.APIConnector.test_status_passed
    )

    execution: dict = connector.get_execution_by_id(
        test_case_id,
        execution_id
    )
    assert (execution['overallStatus']['status'] == tbcs_client.APIConnector.test_status_passed)
