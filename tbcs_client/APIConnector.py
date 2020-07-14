import requests
import json
import os
import time

import tbcs_client

from typing import List

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
    test_step_status_undefined: str = 'Undefined'
    test_step_status_passed: str = 'Passed'
    test_step_status_failed: str = 'Failed'
    test_status_calculated: str = 'Calculated'
    test_status_failed: str = 'Failed'
    test_status_in_progress: str = 'InProgress'
    test_status_passed: str = 'Passed'
    test_case_type_simple: str = 'SimpleTestCase'
    test_case_type_structured: str = 'StructuredTestCase'
    test_case_type_checklist: str = 'CheckListTestCase'

    __base_url: str
    __headers: dict
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
            self.__log_in()

    def create_test_case(
            self,
            test_case_name: str,
            test_case_description: str,
            test_case_type: str,
            external_id: str,
            test_steps: List[str],
            test_setup: List[str],
            test_teardown: List[str]
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
                    raise tbcs_client.APIError('Persistence of test case data not achieved before timeout.')
                time.sleep(1)
            except tbcs_client.APIError as error:
                if counter == self.__persist_timeout:
                    raise error
                time.sleep(1)


        for test_step in test_setup:
            self.add_test_step(test_case_id, test_step, 0)
        for test_step in test_steps:
            self.add_test_step(test_case_id, test_step, 2)
        for test_step in test_teardown:
            self.add_test_step(test_case_id, test_step, 4)

        

        return test_case_id

    #TODO: Think about defining a update_test_case method and explicitly using the power of 'HTTP-patch' by maybe using a dictionary {key:value, key2:value2,...} as input arguments and when such a structure will be necessary
    def update_test_case_description(
            self,
            test_case_id: str,
            test_case_description: str
    ):
        test_case_data: dict = {
            'description': {
                'text': test_case_description
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
            test_step: str,
            test_step_block: int,
            test_block: List = ['Preparation', 'Navigation', 'Test', 'ResultCheck', 'CleanUp'],
            previous_test_step_id: str = '-1'
    ) -> str:
        test_step_data: dict = {
            'testStepBlock': test_block[test_step_block],
            'description': test_step
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

        test_step_id: str = str(json.loads(response_create.text)['testStepId'])
        for counter in range(self.__persist_timeout):
            written_data: dict = self.get_test_case_by_id(test_case_id)
            write_completed: bool = False
            for test_step in written_data['testSequence']['testStepBlocks'][test_step_block]['steps']:
                if str(test_step['id']) == test_step_id:
                    write_completed = True
                    break
            if write_completed:
                break
            elif counter == self.__persist_timeout:
                raise tbcs_client.APIError('Persistence of test step not achieved before timeout.')
            time.sleep(1)

        return test_step_id

    def remove_test_step(
            self,
            test_case_id: str,
            test_step_id: str,
            test_step_block: int,
            test_block: List[str] = ['Preparation', 'Navigation', 'Test', 'ResultCheck', 'CleanUp'] #noch an Anfang schieben und dann mit self. aufrufen.
    ):
        self.__send_request(
            http_method=self.__session.delete,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/specifications/testCases/{test_case_id}/testSteps/{test_step_id}',
            expected_status_code=200
        )

        for counter in range(self.__persist_timeout):
            written_data: dict = self.get_test_case_by_id(test_case_id)
            write_completed: bool = True
            for test_step in written_data['testSequence']['testStepBlocks'][test_step_block]['steps']:
                if str(test_step['id']) == test_step_id:
                    write_completed = False
                    break
            if write_completed:
                break
            elif counter == self.__persist_timeout:
                raise tbcs_client.APIError('Persistence of test step not achieved before timeout.')
            time.sleep(1)

    def get_test_case_by_external_id(
            self,
            external_id: str
    ) -> dict:
        filter: str = f'fieldValue=externalId:equals:{external_id}'
        response: requests.Response = self.__send_request(
            http_method=self.__session.get,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/specifications/testCases?{filter}',
            expected_status_code=200
        )

        tests: List[dict] = json.loads(response.text)

        if len(tests) == 0:
            raise tbcs_client.ItemNotFoundError(f'No test case found with external ID: {external_id}')

        response = self.__send_request(
            http_method=self.__session.get,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/specifications/testCases/{str(tests[0]["id"])}',
            expected_status_code=200
        )
        return json.loads(response.text)

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
                written_data: dict = self.get_execution_by_id(test_case_id, execution_id)
                break
            except:
                if counter == self.__persist_timeout:
                    raise tbcs_client.APIError('Persistence of execution not achieved before timeout.')
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
            test_case_id,
            execution_id,
            test_step_id,
            result
    ):
        self.__send_request(
            http_method=self.__session.put,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/executions/testCases/{test_case_id}/executions/{execution_id}/testSteps/{test_step_id}/result',
            expected_status_code=200,
            data=f'"{result}"'
        )

    def create_defect(
            self,
            test_case_name,
            test_step_name,
            message
    ) -> dict:

        defect_data: dict = {
            "name": f"{test_case_name}: {test_step_name}",
            "description": f"Automated Defect. Robot Framework logs '{message}'"
        }

        response: requests.Response = self.__send_request(
            http_method=self.__session.post,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/defects',
            expected_status_code=201,
            data=json.dumps(defect_data)
        )

        return json.loads(response.text)

    def assign_defect(
            self,
            test_case_id,
            execution_id,
            test_step_id,
            defect_id
    ):
        self.__send_request(
            http_method=self.__session.post,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/executions/testCases/{test_case_id}/executions/{execution_id}/testSteps/{test_step_id}/defects',
            expected_status_code=201,
            data=f'"{defect_id}"'
        )

    def update_execution_status(
            self,
            test_case_id,
            execution_id,
            status
    ):
        self.__send_request(
            http_method=self.__session.put,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/executions/testCases/{test_case_id}/executions/{execution_id}/status',
            expected_status_code=200,
            data=f'"{status}"'
        )

    def report_test_case_result(
            self,
            test_case_id,
            execution_id,
            result
    ):
        result_data: dict = {
            'executionStatus': result
        }
        self.__send_request(
            http_method=self.__session.patch,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/executions/testCases/{test_case_id}/executions/{execution_id}',
            expected_status_code=200,
            data=json.dumps(result_data)
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
                self.__log_in()
                return self.__send_request(http_method, endpoint, expected_status_code, data)
        elif response.status_code == expected_status_code:
            return response
        else:
            raise tbcs_client.APIError(f'{endpoint} failed with message {response.text}')

    def __log_in(self):
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
