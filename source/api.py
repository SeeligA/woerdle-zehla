import json
import os.path

import requests


def call_api(parameters, method='post'):
    """
    Call API and store response in translation variable

    Arguments:
        parameters -- dictionary containing api parameters as key-value pairs
        method -- string specifying the method called in the request function.
                  Accepts the following values: "post" (default), 'get'
                  Get method IS considered less secure, because data is sent as part of the URL!
    #  TODO: Managing requests by splitting up requests considered too long

    Returns:
        target -- list of strings from translation output
    """

    # POST request, preferred method
    if method == 'post':
        translation = post_translation(parameters)
    # GET request, deprecated method
    elif method == 'get':
        translation = get_translation(parameters)

    # Output successful response or notify user that the request has failed
    target = []

    if translation is not None:
        # Parse output from json response: target values are stored under the 'text' key
        for i in range(len(translation['translations'])):
            target.append(translation['translations'][i]['text'])

    else:
        target[0] = '[!] Request Failed!'

    return target


def collect_trans_parameters(source,
                             target_lang,
                             file='API_key.txt',
                             source_lang=0,
                             tag_handling=None,
                             non_splitting_tags=None,
                             ignore_tags=None,
                             split_sentences='0',  # make sure to use dtype string. Else the for loop
                             preserve_formatting=0  # will default split_sentence parameter to "1"
                             ):
    """
    Check for required and optional parameters and write to list

    Arguments: (see API documentation: https://www.deepl.com/api.html)
        file -- required, local file containing API key.
        source -- list of source strings. Used as input for the 'text' parameter
        target_lang -- required string, eg. 'EN', 'DE', 'FR'
        source_lang -- optional string, eg. 'EN', 'DE', 'FR'
        tag_handling -- optional, comma separated string, currently accepts only xml
        non_splitting_tags -- optional, comma-separated list of XML tags which never split sentence
        ignore_tags -- optional, comma-separated list of XML tags whose content is never translated
        split_sentences -- optional, accepts '0' and '1' (default)
        preserve_formatting -- optional, accepts '1' and '0' (default)

    Returns:
    Parameters -- dictionary with key-value pairs
    """

    # collect authentication key string from file
    fp = os.path.join("data", file)
    with open(fp, 'r') as f:
        auth_key = f.readline()

    # populate list with parameter values
    parameters = {'auth_key': auth_key, 'text': source, 'target_lang': target_lang, 'source_lang': source_lang,
                  'tag_handling': tag_handling, 'non_splitting_tags': non_splitting_tags, 'ignore_tags': ignore_tags,
                  'split_sentences': split_sentences, 'preserve_formatting': preserve_formatting}

    return parameters


def get_translation(parameters):
    """
    Send request via API and collect response

    Arguments:
        Parameters -- dictionary referencing required and optional parameters

    Returns:
        API response in nested dict format with detected source language and translation as text.
        Error code in case the request failed
    """

    url = 'https://api.deepl.com/v2/translate'
    params = parameters

    response = requests.get(url, params=params)

    if response.status_code == 200:
        return json.loads(response.content.decode('utf-8'))
    else:
        return None


def post_translation(parameters):
    """
    Send request via API and collect response

    Arguments:
        Parameters -- dictionary referencing required and optional parameters

    Returns:
        API response in nested dict format with detected source language and translation as text.
        Error code in case the request failed
    """

    url = 'https://api.deepl.com/v2/translate'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    response = requests.post(url, params=parameters, headers=headers)
    if response.status_code == 200:
        return json.loads(response.content.decode('utf-8'))
    else:
        return None
