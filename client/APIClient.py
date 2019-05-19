import requests
import json
import os
import urllib3

from robot.api import logger

class ITBConnector:
    ROBOT_LIBRARY_SCOPE = 'TEST SUITE'
    ROBOT_LIBRARY_VERSION = '0.1'
    ROBOT_LISTENER_API_VERSION = 2

    __is_itb_test_case: bool = False

    automation_roles: [str] = ('TestManager', 'TestAnalyst', 'Tester')
    test_status_calculated: str = 'Calculated'
    test_status_failed: str = 'Failed'
    test_status_inprogress: str = 'InProgress'
    test_status_passed: str = 'Passed'
    test_step_status_undefined: str = 'Undefined'
    test_step_status_passed: str = 'Passed'
    test_step_status_failed: str = 'Failed'

    __test_id: str
    __test_name: str
    __test_steps: [dict] = []
    __mark_for_review: bool
    __overwrite: bool
    __test_description: str

    def __init__(self):
        # TODO: Make sure these settings are not needed here
        os.environ['no_proxy'] = '*'
        os.environ['NO_PROXY'] = '*'
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.ROBOT_LIBRARY_LISTENER = self

    def __send_request(self, http_method: requests.api, endpoint: str, expected_status_code: int,
                       data: str = '') -> requests.Response:
        logger.console(f'Sending {http_method.__name__.upper()} request to {self.__base_url}{endpoint} with {data}')

        response: requests.Response = http_method(
            url=f'{self.__base_url}{endpoint}',
            data=data,
            headers=self.__headers
        )

        if response.status_code == 401:
            if endpoint == '/tenants/login/session':
                raise Exception('Unable to Authenticate', response)
            else:
                self.__headers = {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'Charset': 'UTF-8'
                }
                self.__log_in(self.__tenant_name, self.__username, self.__password)
                return self.__send_request(http_method, endpoint, expected_status_code, data)
        elif response.status_code == expected_status_code:
            return response
        else:
            # TODO: Error handling (e.g. headers and data)
            raise Exception(f'{endpoint} failed', response.text)

    def __log_in(self):
        auth_data: dict = {
            'force': True,
            'tenantName': self.__tenant_name,
            'login': self.__username,
            'password': self.__password
        }
        response: requests.Response = self.__send_request(
            http_method=self.__session.post,
            endpoint='/tenants/login/session',
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
        if not self.__user_has_required_roles():
            raise Exception('The user does not have any of the roles required to use the automation api: ',
                            json.dumps(self.automation_roles))

    def __log_out(self):
        # TODO: Probably no longer required
        self.__send_request(
            http_method=self.__session.delete,
            endpoint=f'/tenants/{self.__tenant_id}/login/session',
            expected_status_code=204
        )
        self.__headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Charset': 'UTF-8'
        }
        self.__tenant_id = -1
        self.__user_id = -1
        self.__session.close()

    def __user_has_required_roles(self) -> bool:
        response: requests.Response = self.__send_request(
            http_method=self.__session.get,
            endpoint=f'/tenants/{self.__tenant_id}/products/{self.__product_id}/users/{self.__user_id}/roles',
            expected_status_code=200
        )
        assigned_roles: [str] = json.loads(response.text)['productRoles']
        if any(role in assigned_roles for role in self.automation_roles):
            return True
        else:
            return False

    def start_execution(self, test_id: int, test_name: str, product_id: int, mark_for_review: bool = False,
                        overwrite: bool = True, config_path: str = '../config.json',
                        test_description: str = 'None') -> dict:
        # TODO: Maybe change default for overwrite to False
        self.__is_itb_test_case = True
        test_config: dict = json.loads(open(config_path, 'r').read())
        self.__base_url = f'https://{test_config["server_address"]}/api'
        self.__tenant_name = test_config['tenant_name']
        self.__username = test_config['username']
        self.__password = test_config['password']
        self.__product_id = str(product_id)
        self.__test_id = str(test_id)
        self.__test_name = test_name
        self.__mark_for_review = mark_for_review
        self.__overwrite = overwrite
        self.__test_description = test_description

        self.__session = requests.Session()
        self.__session.verify = False  # TODO: Make sure certificate is checked correctly

    def report_test_result(self, status: str):
        self.__log_in()

        # TODO: json.dumps truncates arrays with len < 2 to simple strings -> find some solution to prevent that with teststeps
        test_steps: [str] = []
        for test_step in self.__test_steps:
            test_steps.append(test_step['keyword'])

        execution_data: dict = {
            "externalId": str(self.__test_id),
            "name": self.__test_name,
            "description": {
                "text": self.__test_description
            },
            "testSteps": test_steps,
            "overwrite": self.__overwrite,
            "markForReview": self.__mark_for_review
        }
        response: requests.Response = self.__send_request(
            http_method=self.__session.post,
            endpoint=f'/tenants/{self.__tenant_id}/products/{self.__product_id}/automation/testCase',
            expected_status_code=201,
            data=json.dumps(execution_data)
        )
        response_data = json.loads(response.text)
        self.__test_id = response_data['testCaseId']

        for index in range(0, len(test_steps)):
            self.update_test_step_status(response_data['testSteps'][index]['id'],
                                         self.__test_steps[index]['status'])

        self.__send_request(
            http_method=self.__session.patch,
            endpoint=f'/tenants/{self.__tenant_id}/products/{self.__product_id}/automation/testCase',
            expected_status_code=200,
            data=json.dumps({"executionStatus": status})
        )

    def update_test_step_status(self, test_step_id: int, status: str):
        self.__send_request(
            http_method=self.__session.put,
            endpoint=f'/tenants/{self.__tenant_id}/products/{self.__product_id}/automation/testCase/testSteps/{str(test_step_id)}/result',
            expected_status_code=200,
            data=f'"{status}"'
        )

    def _end_test(self, name: str, attributes: dict):
        try:
            if self.__is_itb_test_case:
                self.report_test_result(
                    self.test_step_status_passed if attributes['status'] == 'PASS' else self.test_step_status_failed
                )
        except Exception as error:
            logger.console('Test failed ' + str(error))
            if self.__is_itb_test_case:
                self.__send_request(
                    http_method=self.__session.patch,
                    endpoint=f'/tenants/{self.__tenant_id}/products/{self.__product_id}/automation/testCase',
                    expected_status_code=200,
                    data=json.dumps({"executionStatus": "Failed"})
                )
        # TODO: Find better way to mark test for report
        self.__is_itb_test_case = False

    def _end_keyword(self, name: str, attributes: dict):
        if not attributes['kwname'] == 'Start Execution':
            params: str = (' <> ' + json.dumps(attributes['args'])) if len(attributes['args']) > 0 else ''
            self.__test_steps.append({
                "keyword": attributes['kwname'] + params,
                "status": self.test_step_status_passed if attributes['status'] == 'PASS' else self.test_step_status_failed
            })

    def add_numbers(self, a: int, b: int, result: int):
        c: int = a + b
        if c == result:
            pass
        else:
            raise Exception(f'Result was incorrect. Expected {result} but got {c}.')

    def multiply_numbers(self, a: int, b: int, result: int):
        c: int = a * b
        if c == result:
            pass
        else:
            raise Exception(f'Result was incorrect. Expected {result} but got {c}.')
