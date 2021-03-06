import datetime
import requests
import xml.etree.ElementTree as ET
import logging
import os
import sys


class DpsHelper:
    """
    Functions used for DPS API interfacing
    """
    def __init__(self, api_header):
        self._api_header = api_header
        self._location = os.path.dirname(os.path.abspath(__file__))
        self._logger = logging.getLogger(__name__)

    def _skit(self, lines, kwargs):
        res = {}
        for k in kwargs:
            if k not in lines:
                res[k] = kwargs[k]

        return res

    def submit_job(self, request_url, **kwargs):
        xml_file = os.path.join(self._location, 'execute.xml')
        input_xml = os.path.join(self._location, 'execute_inputs.xml')

        # ==================================
        # Part 1: Parse Required Arguments
        # ==================================
        fields = ["identifier", "algo_id", "version", "inputs"]

        input_names = self._skit(fields, kwargs)

        if not 'username' in kwargs:
            input_names['username'] = 'username'

        params = {}
        for f in fields:
            try:
                params[f] = kwargs[f]
            except:
                params[f] = ''

        inputs = {}
        for f in input_names:
            try:
                inputs[f] = kwargs[f]
            except:
                inputs[f] = ''

        logging.debug('fields are')
        logging.debug(fields)

        logging.debug('params are')
        logging.debug(params)

        logging.debug('inputs are')
        logging.debug(inputs)

        params['timestamp'] = str(datetime.datetime.today())
        if 'username' in params.keys() and inputs['username'] == '':
            inputs['username'] = 'anonymous'

        # ==================================
        # Part 2: Build & Send Request
        # ==================================

        other = ''
        with open(input_xml) as xml:
            ins_xml = xml.read()

        # -------------------------------
        # Insert XML for algorithm inputs
        # -------------------------------
        for key in input_names:
            other += ins_xml.format(name=key).format(value=input_names[key])
            other += '\n'

        # print(other)
        params['other_inputs'] = other

        with open(xml_file) as xml:
            req_xml = xml.read()

        req_xml = req_xml.format(**params)

        logging.debug('request is')
        logging.debug(req_xml)

        # -------------------------------
        # Send Request
        # -------------------------------
        try:
            r = requests.post(
                url=request_url,
                data=req_xml,
                headers=self._api_header
            )
            logging.debug('status code ' + str(r.status_code))
            logging.debug('response text\n' + r.text)

            # ==================================
            # Part 3: Check & Parse Response
            # ==================================
            # malformed request will still give 200
            if r.status_code == 200:
                try:
                    # parse out JobID from response
                    rt = ET.fromstring(r.text)

                    # if bad request, show provided parameters
                    if 'Exception' in r.text:
                        result = 'Exception: {}\n'.format(rt[0].attrib['exceptionCode'])
                        result += 'Bad Request\nThe provided parameters were:\n'
                        for f in fields:
                            result += '\t{}: {}\n'.format(f, params[f])
                        result += '\n'
                        self.finish({"status_code": 400, "result": result})

                    else:
                        job_id = rt[0].text

                        if job_id is not None:
                            return {"status": "success", "http_status_code": r.status_code, "job_id": job_id}
                except:
                    return {"status": "failed", "http_status_code": r.status_code, "job_id": ""}
            else:
                return {"status": "failed", "http_status_code": r.status_code, "job_id": ""}
        except:
            return {"status": "failed", "http_status_code": r.status_code, "job_id": ""}

