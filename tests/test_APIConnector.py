from typing import List
import random
import string
import os
import time

import tbcs_client

testcase_for_validation: dict = {
    'id': 1,
    'name': 'some',
    'externalId': '1',
    'executions': [{
        'id': 1
    }]
}

new_testcase_name: str = 'test_create_testcase'
new_testcase_test_steps: List[str] = ['first step', 'second step', 'third step']
def new_testcase_external_id() -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=24))


def get_test_connector() -> tbcs_client.APIConnector:
    return tbcs_client.APIConnector()


def test_get_testcase():
    testcase: dict = get_test_connector().get_testcase(testcase_for_validation['externalId'])
    assert (testcase['name'] == testcase_for_validation['name'])
    assert (testcase['id'] == testcase_for_validation['id'])


def test_get_testcase_by_id():
    testcase: dict = get_test_connector().get_testcase_by_id(str(testcase_for_validation['id']))
    assert (testcase['name'] == testcase_for_validation['name'])
    assert (testcase['externalId'] == testcase_for_validation['externalId'])


def test_get_execution():
    execution: dict = get_test_connector().get_execution_by_id(testcase_for_validation['externalId'])
    assert (execution['testCase']['name'] == testcase_for_validation['name'])
    assert (execution['id'] == testcase_for_validation['id'])


def test_get_execution_by_id():
    execution: dict = get_test_connector().get_execution_by_id(
        str(testcase_for_validation['id']),
        str(testcase_for_validation['executions'][0]['id'])
    )
    assert (execution['testCase']['name'] == testcase_for_validation['name'])
    assert (execution['externalId'] == testcase_for_validation['externalId'])


def test_create_testcase():
    connector: tbcs_client.APIConnector = get_test_connector()
    external_id: str = new_testcase_external_id()
    testcase_id: str = connector.create_testcase(
        new_testcase_name,
        external_id,
        new_testcase_test_steps
    )
    time.sleep(1)

    testcase: dict = connector.get_testcase_by_id(testcase_id)
    response_steps: List[dict] = testcase['testStepBlocks'][2]['steps']

    assert (testcase['name'] == new_testcase_name)
    assert (testcase['externalId'] == external_id)
    assert (response_steps[0]['description'] == new_testcase_test_steps[0])
    assert (response_steps[1]['description'] == new_testcase_test_steps[1])
    assert (response_steps[2]['description'] == new_testcase_test_steps[2])


def test_start_execution():
    connector: tbcs_client.APIConnector = get_test_connector()
    external_id: str = new_testcase_external_id()
    testcase_id: str = connector.create_testcase(
        new_testcase_name,
        external_id,
        new_testcase_test_steps
    )
    time.sleep(1)

    execution_id: str = connector.start_execution(testcase_id)
    time.sleep(1)

    execution: dict = connector.get_execution_by_id(
        testcase_id,
        execution_id
    )
    assert (execution['testCase']['name'] == new_testcase_name)
    assert (execution['externalId'] == external_id)


def test_report_step_result():
    connector: tbcs_client.APIConnector = get_test_connector()
    testcase_id: str = connector.create_testcase(
        new_testcase_name,
        new_testcase_external_id(),
        new_testcase_test_steps
    )
    time.sleep(1)

    execution_id: str = connector.start_execution(testcase_id)
    time.sleep(1)

    connector.report_step_result(
        testcase_id,
        execution_id,
        '1',
        tbcs_client.APIConnector.test_step_status_passed
    )
    connector.report_step_result(
        testcase_id,
        execution_id,
        '2',
        tbcs_client.APIConnector.test_step_status_failed
    )
    time.sleep(1)

    execution_steps: dict = connector.get_execution_by_id(
        testcase_id,
        execution_id
    )['testStepBlocks'][2]['steps']

    assert (execution_steps[0]['result'] == tbcs_client.APIConnector.test_step_status_passed)
    assert (execution_steps[1]['result'] == tbcs_client.APIConnector.test_step_status_failed)
    assert (execution_steps[2]['result'] == tbcs_client.APIConnector.test_step_status_undefined)


def test_report_testcase_result():
    connector: tbcs_client.APIConnector = get_test_connector()
    testcase_id: str = connector.create_testcase(
        new_testcase_name,
        new_testcase_external_id(),
        new_testcase_test_steps
    )
    time.sleep(1)

    execution_id: str = connector.start_execution(testcase_id)
    time.sleep(1)

    execution: dict = connector.get_execution_by_id(
        testcase_id,
        execution_id
    )
    assert (execution['overallStatus']['status'] == tbcs_client.APIConnector.test_status_inprogress)

    connector.report_testcase_result(
        testcase_id,
        execution_id,
        tbcs_client.APIConnector.test_status_passed
    )
    time.sleep(1)

    execution: dict = connector.get_execution_by_id(
        testcase_id,
        execution_id
    )
    assert (execution['overallStatus']['status'] == tbcs_client.APIConnector.test_status_passed)
