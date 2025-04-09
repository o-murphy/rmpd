import json
import logging
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO,
                    filemode="a",
                    format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# URL = "https://test.puesc.gov.pl/en/uslugi/przewoz-towarow-objety-monitorowaniem/rmpd-406?systemName=SENT&formName=1000951"
URL = "https://puesc.gov.pl/en/uslugi/przewoz-towarow-objety-monitorowaniem/rmpd-406?systemName=SENT&formName=1000951"

QUERY_PARAMS = {
    'p_p_id': 'Sent_Rmpd406Portlet',
    'p_p_lifecycle': 2,
    'p_p_state': 'normal',
    'p_p_mode': 'view',
    'p_p_resource_id': '/rmpd-406/verify-rmpd-number-and-truck',
    'p_p_cacheability': 'cacheLevelPage',
}

CONFIG_ID = 'pl_gov_mf_sent_Sent.rmpd406PortletConfig'
DATA_PHRASE_ATTR = "data-phrase-id"
DATA_PHRASE_IDS_BASIC_INFO = [
    'rmpdTraderName',
    'rmpdTraderIdentityType',
    'rmpdTraderIdentityNumber',
]
DATA_PHRASE_IDS_STATUS = [
    'rmpdRmpdStatus2',
]
DATA_PHRASE_IDS_LAST_POS = [
    'rmpdLatitude',
    'rmpdLongitude',
]
DATA_PHRASE_IDS = [
    'rmpdNumber',
    # 'rmpdCurrentDateTime',
    'rmpdCrationDate',
    'rmpdGeoLocatorNumber',
]

POP_CONFIG_FIELDS = [
    'poiBlueImgSrc',
    'polandMapImgSrc',
    'language',
]

def _extract_nested(element):
    nested_text = element.find(text=True)
    if nested_text.has_attr(DATA_PHRASE_ATTR):
        return None
    if nested_text:
        return nested_text.strip()
    return _extract_nested(nested_text)

def _extract_data_by_phrase_id(soup, data_phrase_ids):
    result = {}

    for phrase_id in data_phrase_ids:
        # Find the element that has the given data-phrase-id
        element = soup.find(attrs={DATA_PHRASE_ATTR: phrase_id})

        if element:
            # Try to extract the text from the current element (span in this case)
            text = element.get_text(strip=True) if element.get_text(strip=True) else None

            # If no text found in the element itself, find sibling elements that might contain the relevant text
            if not text:
                siblings = element.find_all_next(text=True)  # Find all the following text nodes
                for sibling in siblings:
                    # Check if the sibling contains actual address-like data
                    if sibling.strip():
                        text = sibling.strip()
                        break

            # If the text is still missing, look for it inside nested tags (like <p>, <b>)
            if not text:
                text = _extract_nested(element)

            # Remove any &nbsp; characters and replace them with regular spaces (or remove entirely)
            if text:
                text = text.replace('\xa0', ' ')  # Replace non-breaking spaces with a regular space

            # If no text found, mark as not found
            result[phrase_id] = text if text else None
        else:
            result[phrase_id] = None

    return result


def _extract_address(soup):

    # Special case for address where it's spread across multiple <p> elements
    address_element = soup.find(attrs={"data-phrase-id": "rmpdAdress"})
    if address_element:
        address_parts = []
        # Collect all <p> elements following the address element (they are siblings)
        # address_p_tags = address_element.find_all_next('p', text=True)
        address_p_tags = address_element.find_all_next('p')
        for p_tag in address_p_tags:
            if p_tag.has_attr(DATA_PHRASE_ATTR):
                break
            if p_tag.text:
                address_parts.append(p_tag.get_text(strip=True).replace('\xa0', ' '))

        return ' '.join(address_parts).strip()
    return None


def _extract_json_from_script(soup: BeautifulSoup, script_identifier: str) -> dict:
    """
    Extracts JSON data from a <script> tag in the HTML document.

    Args:
        soup (BeautifulSoup): The parsed HTML document.
        script_identifier (str): The unique identifier of the script's content.

    Returns:
        dict: The extracted JSON data as a Python dictionary.
    """
    # Find the <script> tag containing the JSON-like content
    script_tag = soup.find('script', text=lambda t: script_identifier in t)

    if script_tag:
        # Extract the content of the <script> tag
        script_content = script_tag.string

        # Clean the JSON string by removing the assignment part, replacing single quotes with double quotes,
        # and ensuring that keys are also enclosed in double quotes
        json_str = script_content.split('= ', 1)[1].strip().rstrip(';').replace("'", '"')

        # Add quotes around unquoted keys (i.e., replace unquoted keys with quoted keys)
        json_str = re.sub(r'(\w+):', r'"\1":', json_str)

        # Decode escape sequences like \x3a to ":" and \x2e to "."
        json_str = json_str.encode().decode('unicode_escape')

        # Convert the cleaned JSON string into a Python dictionary
        return json.loads(json_str)
    else:
        raise ValueError(f"Script tag with identifier '{script_identifier}' not found.")


def parse_response(html):
    soup = BeautifulSoup(html, 'html.parser')
    if alert := soup.select_one('div.alert.alert-danger'):
        if strong := alert.find('strong'):
            error_text = ''
            # Get all content after <strong>
            for elem in strong.next_siblings:
                if hasattr(elem, 'get_text'):  # if it's a tag
                    error_text += elem.get_text()
                elif isinstance(elem, str):  # if it's a string
                    error_text += elem

            raise Exception("🛑 Alert message: %s" % error_text.strip())

    try:
        config = _extract_json_from_script(soup, CONFIG_ID)
        [config.pop(k) for k in POP_CONFIG_FIELDS]
    except Exception as e:
        config = None

    report = soup.select_one("div.rmpd-xslt")

    report_data = {
        **_extract_data_by_phrase_id(report, DATA_PHRASE_IDS),
        'rmpdStatus': _extract_data_by_phrase_id(report, DATA_PHRASE_IDS_STATUS),
        'rmpdAdress': _extract_address(soup),
        'rmpdGoodsCarrierInfo': {
            'rmpdBasicInfo': _extract_data_by_phrase_id(report, DATA_PHRASE_IDS_BASIC_INFO),
            'rmpdLastGPSPosition': _extract_data_by_phrase_id(report, DATA_PHRASE_IDS_LAST_POS),
        }
    } if report else None
    return {
        "config": config,
        "report": report_data,
    }


def _fetch_data(rmpd, truck_number, geoLocatorNumber, filename=None):
    timestamp_ms = int(datetime.now().timestamp() * 1000)

    form_data = {
        '_Sent_Rmpd406Portlet_formDate': timestamp_ms,
        '_Sent_Rmpd406Portlet_rmpdNumber': rmpd,
        '_Sent_Rmpd406Portlet_truckNumber': truck_number,
        '_Sent_Rmpd406Portlet_geoLocatorNumber': geoLocatorNumber,
        # 'p_auth': 'ubHpc3RC',
    }

    request = requests.post(URL, params=QUERY_PARAMS, data=form_data)
    if request.status_code == 200:
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(request.text)
        return request.text
    else:
        raise Exception('Something went wrong', request.status_code)


def fetch_rmpd(rmpd, truck, locator, dump_html=None, dump_json=None):
    html = _fetch_data(rmpd, truck, locator)
    if dump_html:
        with open(dump_html, 'w', encoding='utf-8') as f:
            f.write(html)

    rmpd_result = parse_response(html)
    if dump_json:
        with open(dump_json, 'w', encoding='utf-8') as f:
            f.write(json.dumps(rmpd_result, indent=4))
