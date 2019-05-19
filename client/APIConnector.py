import requests
import json

class APIConnector:
    _base_url: str
    __headers: dict
    __tenant_name: str
    __tenant_id: int = -1
    __username: str
    __password: str
    __user_id: int = -1
    __product_id: str
    __session: requests.sessions

    def __init__(
            self,
            server_address: str,
            tenant_name: str,
            product_id: str,
            username: str,
            password: str):
        self.__base_url = f'https://{server_address}'
        self.__tenant_name = tenant_name
        self.__product_id = product_id
        self. __username = username
        self.__password = password
        self.__session = requests.Session()

    def create_testcase(
            self,
            testcase_name: str,
            testcase_description: str,
            external_id: str):
        response_create: requests.Response = self.__send_request(
            http_method=self.__session.post,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/specifications/testcases',
            expected_status_code=201,
            data=json.dumps({'name': testcase_name})
        )

        testcase_id: str = str(json.loads(response_create.text)['testCaseId'])

        testcase_data: dict = {
            'name': testcase_name,
            'description': testcase_description,
            'responsibles': [self.__user_id],
            'customFields': [],
            'isAutomated': True,
            'toBeReviewed': False,
            'externalId': {'value': external_id}
        }

        self.__send_request(
            http_method=self.__session.patch,
            endpoint=f'/api/tenants/{self.__tenant_id}/products/{self.__product_id}/specifications/testcases/{testcase_id}',
            expected_status_code=200,
            data=json.dumps(testcase_data)
        )

    def __send_request(
            self,
            http_method: requests.api,
            endpoint: str,
            expected_status_code: int,
            data: str = '') -> requests.Response:
        response: requests.Response = http_method(
            url=f'{self.__base_url}{endpoint}',
            data=data,
            headers=self.__headers
        )

        if response.status_code == 401:
            if endpoint == '/api/tenants/login/session':
                raise Exception('Unable to authenticate', response)
            else:
                self.__log_in(self.__tenant_name, self.__username, self.__password)
                return self.__send_request(http_method, endpoint, expected_status_code, data)
        elif response.status_code == expected_status_code:
            return response
        else:
            # TODO: Error handling (e.g. headers and data)
            raise Exception(f'{endpoint} failed', response.text)

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