import argparse
import logging
import os
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO,
                    filemode="a",
                    format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

URL = "https://test.puesc.gov.pl/en/uslugi/przewoz-towarow-objety-monitorowaniem/rmpd-406?systemName=SENT&formName=1000951"

DUMP_FILE = 'rmpd.html'


def get_data(rmpd, truck_number, geoLocatorNumber, filename=None):
    timestamp_ms = int(datetime.now().timestamp() * 1000)

    query_params = {
        'p_p_id': 'Sent_Rmpd406Portlet',
        'p_p_lifecycle': 2,
        'p_p_state': 'normal',
        'p_p_mode': 'view',
        'p_p_resource_id': '/rmpd-406/verify-rmpd-number-and-truck',
        'p_p_cacheability': 'cacheLevelPage',
    }

    form_data = {
        '_Sent_Rmpd406Portlet_formDate': timestamp_ms,  # 1744218281169,
        '_Sent_Rmpd406Portlet_rmpdNumber': rmpd,
        '_Sent_Rmpd406Portlet_truckNumber': truck_number,
        '_Sent_Rmpd406Portlet_geoLocatorNumber': geoLocatorNumber,
        # 'p_auth': 'ubHpc3RC',
    }

    request = requests.post(URL, params=query_params, data=form_data)
    if request.status_code == 200:
        if filename:
            with open(filename, 'w') as f:
                f.write(request.text)
        return request.text
    else:
        raise Exception('Something went wrong', request.status_code)


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


def main():
    parser = argparse.ArgumentParser('RMPD', exit_on_error=False)
    parser.add_argument('rmpd', help='RMPD number', nargs='?')
    parser.add_argument('truck', help='Truck number', nargs='?')
    parser.add_argument('locator', help='GeoLocator number', nargs='?')
    parser.add_argument('--dump', help='Save html to file', action='store_true')

    try:
        args = parser.parse_args()
        # If all 3 args are present, we use them
        if args.rmpd and args.truck and args.locator:
            rmpd = args.rmpd
            truck = args.truck
            locator = args.locator
            dump_file = DUMP_FILE if args.dump else DUMP_FILE
        else:
            raise ValueError("Missing CLI args; falling back to env")
    except Exception as e:
        logger.info(f"Falling back to environment variables: {e}")
        load_dotenv('.env')

        rmpd = os.getenv('RMPD')
        truck = os.getenv('TRUCK')
        locator = os.getenv('LOCATOR')
        dump_file = DUMP_FILE if os.getenv('DUMP_FILE') else DUMP_FILE
        logger.info("Request data: RMPD=%s TRUCK=%s LOCATOR=%s", rmpd, truck, locator)
        if not all([rmpd, truck, locator]):
            parser.error("Missing required values from both CLI and environment.")

    try:
        html = get_data(rmpd, truck, locator, dump_file)
        parse_response(html)
    except Exception as e:
        parser.error(str(e))


if __name__ == '__main__':
    main()
