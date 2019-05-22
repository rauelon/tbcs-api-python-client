from typing import List
import random
import string
import os

import tbcs_client


def get_test_connector() -> tbcs_client.APIConnector:
    os.environ['no_proxy'] = '*'
    os.environ['NO_PROXY'] = '*'
    return tbcs_client.APIConnector(
        'localhost.testbench.com',
        'rfimbus',
        '1',
        'first',
        'first123'
    )


def test_get_testcase_by_id():
    testcase: dict = get_test_connector().get_testcase_by_id('1')
    assert(testcase['name'] == 'some')
    assert(testcase['externalId'] == '1')


def test_create_testcase():
    testcase_name: str = 'test_create_testcase'
    testcase_external_id: str = ''.join(random.choices(string.ascii_letters + string.digits, k=24))
    testcase_test_steps: List[str] = ['first step', 'second step', 'third step']

    connector: tbcs_client.APIConnector = get_test_connector()
    testcase_id: str = connector.create_testcase(
        testcase_name,
        testcase_external_id,
        testcase_test_steps
    )

    testcase: dict = connector.get_testcase_by_id(testcase_id)
    response_steps: List[dict] = testcase['testStepBlocks'][2]['steps']

    assert(testcase['name'] == testcase_name)
    assert(testcase['externalId'] == testcase_external_id)
    assert(response_steps[0]['description'] == testcase_test_steps[0])
    assert(response_steps[1]['description'] == testcase_test_steps[1])
    assert(response_steps[2]['description'] == testcase_test_steps[2])
