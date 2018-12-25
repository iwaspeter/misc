#!/usr/bin/env python

import socket
import requests
from requests import Response
import sys
import rados
import rbd
import re
import time
import os

class APIRequest(object):

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

        # Establish defaults for the API connection
        self.http_methods = ['get', 'put',  'delete']
        self.data = None

    def _get_response(self):
        return self.data

    def __getattr__(self, name):
        if name in self.http_methods:
            self.kwargs['timeout'] = 2
            request_method = getattr(requests, name)
            try:
                self.data = request_method(*self.args, **self.kwargs)
            #except requests.ConnectionError:
            except:
                msg = ("Unable to connect to api endpoint @ "
                       "{}".format(self.args[0]))
                self.data = Response()
                self.data.status_code = 502
                self.data._content = '{{"message": "{}" }}'.format(msg)
                return self._get_response
            #except:
            #    raise GatewayAPIError("Unknown error connecting to "
            #                          "{}".format(self.args[0]))
            else:
                # since the attribute is a callable, we must return with
                # a callable
                return self._get_response
        raise AttributeError()

    response = property(_get_response,
                        doc="get http response output")


def response_message(response, logger=None):
    """
    Attempts to retrieve the "message" value from a JSON-encoded response
    message. If the JSON fails to parse, the response will be returned
    as-is.
    :param response: (requests.Response) response
    :param logger: optional logger
    :return: (str) response message
    """
    try:
        return response.json()['message']
    except:
        if logger:
            logger.debug("Failed API request: {} {}\n{}".format(response.request.method,
                                                                response.request.url,
                                                                response.text))
        return "{} {}".format(response.status_code, response.reason)

def call_api(gw, endpoint, element, http_method, api_vars):
    if element == '':
        api_endpoint = ("{}://{}:{}/api/"
                        "{}".format('http',
                                       gw,
                                       '5001',
                                       endpoint,
                                       ))
    else:
        api_endpoint = ("{}://{}:{}/api/"
                        "{}/{}".format('http',
                                       gw,
                                       '5001',
                                       endpoint,
                                       element
                                       ))

    api = APIRequest(api_endpoint, data=api_vars)
    api_method = getattr(api, http_method)
    api_method()

    if api.response.status_code == 200:
        #updated.append(gw)
        continue
    else:
        try:
            fail_msg = api.response.json()['message']
        except:
            fail_msg = 'error on gateway'
        return fail_msg, api.response.status_code

    return api.response.text, 200

