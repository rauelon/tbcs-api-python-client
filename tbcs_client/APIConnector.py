import requests
import json
import os
import time

from typing import List

from tbcs_client.APIError import APIError
from tbcs_client.ItemNotFoundError import ItemNotFoundError

""" Class for connecting to a TestBench CS REST-API

The APIConnector class wraps a set of API-calls against the TestBench CS REST-API, that can be used to
create test cases within TestBench CS, start test executions and report test results. This class expects
the path to a JSON-configuration file for initialization (structure is shown in 'empty.tbcs.config.json'
in the root of the GitLab-Repository). If no path is given it defaults to a file with name 'tbcs.config.json'
that must be placed inside your project root.

When provided with valid configuration, you can simply call any of this classes get-, create- and
report-functions from any instance of this class. Redundant steps such as authenticating with the API
are handled internally.
"""


class APIConnector:
    TEST_CASE_TYPE_SIMPLE: str = 'SimpleTestCase'
    TEST_CASE_TYPE_STRUCTURED: str = 'StructuredTestCase'
    TEST_CASE_TYPE_CHECKLIST: str = 'CheckListTestCase'

    TEST_BLOCK_PREPARATION_NAME: str = 'Preparation'
    TEST_BLOCK_NAVIGATION_NAME: str = 'Navigation'
    TEST_BLOCK_TEST_NAME: str = 'Test'
    TEST_BLOCK_RESULTCHECK_NAME: str = 'ResultCheck'
    TEST_BLOCK_CLEANUP_NAME: str = 'CleanUp'

    TEST_BLOCK_PREPARATION_INDEX: int = 0
    TEST_BLOCK_NAVIGATION_INDEX: int = 1
    TEST_BLOCK_TEST_INDEX: int = 2
    TEST_BLOCK_RESULTCHECK_INDEX: int = 3
    TEST_BLOCK_CLEANUP_INDEX: int = 4

    TEST_STEP_STATUS_UNDEFINED: str = 'Undefined'
    TEST_STEP_STATUS_PASSED: str = 'Passed'
    TEST_STEP_STATUS_FAILED: str = 'Failed'

    __base_url: str
    __headers: dict == {}
    __tenant_name: str
    __tenant_id: int = -1
    __username: str
    __password: str
    __user_id: int = -1
    __product_id: str
    __session: requests.sessions
    __persist_timeout: int = 30

    def __init__(self, config_path: str = '../tbcs.config.json'):
        with open(config_path) as config_file:
            config_data: dict = json.load(config_file)
            self.__base_url = f'https://{config_data["server_address"]}'
            self.__tenant_name = config_data['tenant_name']
            self.__product_id = config_data['product_id']
            self.__username = config_data['tenant_user']
            self.__password = config_data['password']
            if not config_data['use_system_proxy']:
                os.environ['no_proxy'] = '*'
                os.environ['NO_PROXY'] = '*'

            self.__session = requests.Session()
            self.__session.verify = config_data['truststore_path'] if not os.name == 'nt' else True

    def create_test_case(
            self,
            test_case_name: str,
            test_case_description: str,
            test_case_type: str,
            external_id: str,
    ) -> str:
        response_create: requests.Response = self.__send_request(
            http_method=self.__session.post,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/specifications/testCases',
            expected_status_code=201,
            data=json.dumps({'name': test_case_name, 'testCaseType': test_case_type})
        )

        test_case_id: str = str(json.loads(response_create.text)['testCaseId'])

        test_case_data: dict = {
            'name': test_case_name,
            'description': {'text': test_case_description},
            'responsibles': [self.__user_id],
            'customFields': [],
            'isAutomated': True,
            'toBeReviewed': False,
            'externalId': {'value': external_id}
        }

        self.__send_request(
            http_method=self.__session.patch,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/specifications/testCases/{test_case_id}',
            expected_status_code=200,
            data=json.dumps(test_case_data)
        )

        for counter in range(self.__persist_timeout):
            try:
                written_data: dict = self.get_test_case_by_id(test_case_id)
                if written_data['automation']['externalId'] == external_id:
                    break
                elif counter == self.__persist_timeout:
                    raise APIError('Persistence of test case data not achieved before timeout.')
                time.sleep(1)
            except APIError as error:
                if counter == self.__persist_timeout:
                    raise error
                time.sleep(1)

        return test_case_id

    def update_test_case_description(
            self,
            test_case_id: str,
            new_description: str
    ) -> None:
        test_case_data: dict = {
            'description': {
                'text': new_description
            }
        }
        self.__send_request(
            http_method=self.__session.patch,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/specifications/testCases/{test_case_id}',
            expected_status_code=200,
            data=json.dumps(test_case_data)
        )

    def add_test_step(
            self,
            test_case_id: str,
            new_test_step: str,
            previous_test_step_id: str = '-1',
            test_block_name: str = TEST_BLOCK_TEST_NAME
    ) -> str:
        test_step_data: dict = {
            'testStepBlock': test_block_name,
            'description': new_test_step
        }
        if not previous_test_step_id == '-1':
            test_step_data['position'] = {
                'relation': 'After',
                'testStepId': previous_test_step_id
            }

        response_create: requests.Response = self.__send_request(
            http_method=self.__session.post,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/specifications/testCases/{test_case_id}/testSteps',
            expected_status_code=201,
            data=json.dumps(test_step_data)
        )

        new_test_step_id: str = str(json.loads(response_create.text)['testStepId'])

        for counter in range(self.__persist_timeout):
            written_data: dict = self.get_test_case_by_id(test_case_id)
            write_completed: bool = False
            for test_step in written_data['testSequence']['testStepBlocks'][APIConnector.get_test_block_index_by_name(test_block_name)]['steps']:
                if str(test_step['id']) == new_test_step_id:
                    write_completed = True
                    break
            if write_completed:
                break
            elif counter == self.__persist_timeout:
                raise APIError('Persistence of test step not achieved before timeout.')
            time.sleep(1)

        return new_test_step_id

    def remove_test_step(
            self,
            test_case_id: str,
            test_step_id: str,
            test_block_name: str = TEST_BLOCK_TEST_NAME,
    ) -> None:
        self.__send_request(
            http_method=self.__session.delete,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/specifications/testCases/{test_case_id}/testSteps/{test_step_id}',
            expected_status_code=200
        )

        for counter in range(self.__persist_timeout):
            written_data: dict = self.get_test_case_by_id(test_case_id)
            write_completed: bool = True
            for test_step in written_data['testSequence']['testStepBlocks'][APIConnector.get_test_block_index_by_name(test_block_name)]['steps']:
                if str(test_step['id']) == test_step_id:
                    write_completed = False
                    break
            if write_completed:
                break
            elif counter == self.__persist_timeout:
                raise APIError('Persistence of test step not achieved before timeout.')
            time.sleep(1)

    def get_test_case_by_external_id(
            self,
            external_id: str
    ) -> dict:
        search_filter: str = f'fieldValue=externalId:equals:{external_id}'
        response: requests.Response = self.__send_request(
            http_method=self.__session.get,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/specifications/testCases?{search_filter}',
            expected_status_code=200
        )

        tests: List[dict] = json.loads(response.text)

        if len(tests) == 0:
            raise ItemNotFoundError(f'No test case found with external ID: {external_id}')

        return self.get_test_case_by_id(str(tests[0]["id"]))

    def get_test_case_by_id(
            self,
            test_case_id: str
    ) -> dict:
        response: requests.Response = self.__send_request(
            http_method=self.__session.get,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/specifications/testCases/{test_case_id}',
            expected_status_code=200
        )

        return json.loads(response.text)

    def start_execution(
            self,
            test_case_id: str
    ) -> str:
        response: requests.Response = self.__send_request(
            http_method=self.__session.post,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/executions/testCases/{test_case_id}',
            expected_status_code=201
        )

        execution_id: str = str(json.loads(response.text)['executionId'])

        for counter in range(self.__persist_timeout):
            try:
                self.get_execution_by_id(test_case_id, execution_id)
                break
            except APIError:
                if counter == self.__persist_timeout:
                    raise APIError('Persistence of execution not achieved before timeout.')
                time.sleep(1)

        return execution_id

    def get_execution_by_id(
            self,
            test_case_id: str,
            execution_id: str
    ) -> dict:
        response: requests.Response = self.__send_request(
            http_method=self.__session.get,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/executions/testCases/{test_case_id}/executions/{execution_id}',
            expected_status_code=200
        )

        return json.loads(response.text)

    def report_step_result(
            self,
            test_case_id: str,
            execution_id: str,
            test_step_id: str,
            result: str
    ) -> None:
        self.__send_request(
            http_method=self.__session.put,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/executions/testCases/{test_case_id}/executions/{execution_id}/testSteps/{test_step_id}/result',
            expected_status_code=200,
            data=f'"{result}"'
        )

    def create_defect(
            self,
            name: str,
            message: str
    ) -> str:
        defect_data: dict = {
            "name": f'{name}',
            "description": f'{message}'
        }

        response: requests.Response = self.__send_request(
            http_method=self.__session.post,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/defects',
            expected_status_code=201,
            data=json.dumps(defect_data)
        )

        return str(json.loads(response.text)['defectId'])

    def assign_defect(
            self,
            test_case_id: str,
            execution_id: str,
            test_step_id: str,
            defect_id: str
    ) -> None:
        self.__send_request(
            http_method=self.__session.post,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/executions/testCases/{test_case_id}/executions/{execution_id}/testSteps/{test_step_id}/defects',
            expected_status_code=201,
            data=f'"{defect_id}"'
        )

    def __send_request(
            self,
            http_method: requests.api,
            endpoint: str,
            expected_status_code: int,
            data: str = ''
    ) -> requests.Response:
        response: requests.Response = http_method(
            url=f'{self.__base_url}{endpoint}',
            data=data,
            headers=self.__headers
        )

        if response.status_code == 401:
            if endpoint == '/api/tenants/login/session':
                raise Exception('Unable to authenticate', response)
            else:
                self.log_in()
                return self.__send_request(http_method, endpoint, expected_status_code, data)
        elif response.status_code == expected_status_code:
            return response
        else:
            raise APIError(f'{endpoint} failed with message {response.text}')

    def log_in(self) -> None:
        self.__headers: dict = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Charset': 'UTF-8'
        }
        auth_data: dict = {
            'force': True,
            'tenantName': self.__tenant_name,
            'login': self.__username,
            'password': self.__password
        }
        response: requests.Response = self.__send_request(
            http_method=self.__session.post,
            endpoint='/api/tenants/login/session',
            expected_status_code=201,
            data=json.dumps(auth_data)
        )
        response_data: dict = json.loads(response.text)
        self.__headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Charset': 'UTF-8',
            'Authorization': f'Bearer {response_data["sessionToken"]}'
        }
        self.__tenant_id = response_data['tenantId']
        self.__user_id = response_data['userId']

    @staticmethod
    def get_test_block_index_by_name(name: str) -> int:
        if name == APIConnector.TEST_BLOCK_PREPARATION_NAME:
            return APIConnector.TEST_BLOCK_PREPARATION_INDEX
        elif name == APIConnector.TEST_BLOCK_NAVIGATION_NAME:
            return APIConnector.TEST_BLOCK_NAVIGATION_INDEX
        elif name == APIConnector.TEST_BLOCK_TEST_NAME:
            return APIConnector.TEST_BLOCK_TEST_INDEX
        elif name == APIConnector.TEST_BLOCK_RESULTCHECK_NAME:
            return APIConnector.TEST_BLOCK_RESULTCHECK_INDEX
        elif name == APIConnector.TEST_BLOCK_CLEANUP_NAME:
            return APIConnector.TEST_BLOCK_CLEANUP_INDEX
        else:
            raise APIError(f'TestBlock {name} does not exist')
