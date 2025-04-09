import argparse
import os

from dotenv import load_dotenv

from rmpd import logger, fetch_rmpd

HTML_DUMP_FILE = 'rmpd.html'
JSON_DUMP_FILE = 'rmpd.json'


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
            dump_html = HTML_DUMP_FILE if args.dump else None
            dump_json = JSON_DUMP_FILE if args.dump else None
        else:
            raise ValueError("Missing CLI args; falling back to env")
    except Exception as e:
        logger.info(f"Falling back to environment variables: {e}")
        load_dotenv('.env')

        rmpd = os.getenv('RMPD')
        truck = os.getenv('TRUCK')
        locator = os.getenv('LOCATOR')
        dump_html = os.getenv('HTML_DUMP_FILE') if os.getenv('HTML_DUMP_FILE') else HTML_DUMP_FILE
        dump_json = os.getenv('JSON_DUMP_FILE') if os.getenv('JSON_DUMP_FILE') else JSON_DUMP_FILE
        logger.info("Request data: RMPD=%s TRUCK=%s LOCATOR=%s", rmpd, truck, locator)
        if not all([rmpd, truck, locator]):
            parser.error("Missing required values from both CLI and environment.")

    try:
        fetch_rmpd(rmpd, truck, locator, dump_html, dump_json)
    except Exception as e:
        parser.error(str(e))


if __name__ == '__main__':
    main()
