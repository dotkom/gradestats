from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class Client:
    session = None

    def __init__(self):
        super().__init__()
        self.session = requests.session()

    def init_soup(self, page_text: str):
        return BeautifulSoup(page_text, "html5lib")

    def requests_retry_session(
        retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504), session=None
    ):
        session = session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
