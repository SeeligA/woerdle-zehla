from bs4 import BeautifulSoup
# import datetime
from html.parser import HTMLParser
# import json
# import matplotlib.pyplot as plt
# import numpy as np
import os.path
import pandas as pd
import re
# import requests
# import sys
# import textwrap
from scripts.utils import cleanup_strings, img_alt

def collect_metadata_xml(filepath):
    '''Collect metadata from filepath:
    Arguments:
    filepath = String specifying the SDLXLIFF input file on F:

    Returns:
    cache -- Dictionary for further referencing and translation calls
    '''
    cache = {}
    # Extract Client name and id
    regex = re.compile('((?<=ab Dez 2010\\\)[^\\\]+)')
    cache['Relation'] = regex.search(filepath)
    # Extract project and PO ids
    regex = re.compile('((?<=03_Projekte\\\)[^\\\]+)')
    cache['Project'] = regex.search(filepath)
    # Extract document name
    regex = re.compile('((?<=\\\)[^\\\]+$)')
    cache['Document'] = regex.search(filepath)
    # Iterate through search results and write values to cache
    for k, v in cache.items():
        if v:
            cache[k] = v.group(0)

    return cache

def collect_metadata_html(soup):
    '''Read header of the bilingual table and parses pertintent project information
    Arguments:
    Soup -- BeautifulSoupObject created from Across HTML export

    Returns:
    cache -- Dictionary for further referencing and translation calls
    '''
    # Parse source and target column header
    trs = soup.find_all('tr')
    tds_m = trs[0].find_all('td')
    meta = tds_m[1].find_all(string=True) + tds_m[3].find_all(string=True)

    # Parse string data from column headers
    cache = {}
    cache['Project'] = meta[1].split(sep=': ')[1]
    cache['Relation'] = meta[2].split(sep=': ')[1]
    cache['Document'] = meta[3].split(sep=': ')[1]
    #TODO : Remove user entry here
    cache['user'] = meta[5].split(sep=': ')[1]
    s_lid = meta[0].split(sep=' ')[0]
    t_lid = meta[4].split(sep=' ')[0]

    # Create lookup dictionary for languages with MT support
    # TODO: Update dictionary where required
    lid_trans = {'Deutsch': 'DE', 'Englisch': 'EN', 'Französisch': 'FR',
                 'Italienisch': 'IT', 'Niederländisch': 'NL', 'Polnisch': 'PL',
                 'Portugiesisch': 'PT', 'Russisch': 'RU', 'Spanisch': 'ES'}

    # Translate string data to ISO-type Language IDs
    cache['s_lid'] = lid_trans.get(s_lid, str("'{}' not supported".format(s_lid)))
    cache['t_lid'] = lid_trans.get(t_lid, str("'{}' not supported".format(t_lid)))

    return cache

def parse_html_strings(soup):
    # Create lists of strings for segment id and source
    seg_id = [element.text for element in soup.find_all('td', attrs={'class': 'inactiveNumbering'})]
    source = [element.text for element in soup.find_all('td', attrs={'class': 'inactiveSource'})]

    # Create list of strings from previous version elements in target
    # previous = collect_versions(soup) TODO: Implement to compare target with previous versions
    # Remove version elements from soup
    [element.replace_with('') for element in soup.find_all('div', attrs={'class': 'atomHistory-box'})]
    # Create list of strings for target
    target = [element.text for element in soup.find_all('td', attrs={'class': 'inactiveTarget'})]
    # Function call to delete additional whitespace and ignore first row
    # TODO: Clean up lines with for loop
    seg_id = cleanup_strings(seg_id[1:])
    source = cleanup_strings(source[1:])
    # previous = cleanup_strings(previous[1:]) TODO: Implement to compare target with previous versions
    target = cleanup_strings(target[1:])
    return seg_id, source, target

def parse_xml_strings(soup):
    '''Read segment strings and segments status information
    Arguments:
    soup -- BeautifulSoup object generated from input

    Returns:
    seg_id -- List containing segment ids
    source -- List containing source strings
    target -- List containing target strings
    status_list -- List containing segment status information
    '''
    seg_id = []
    source = []
    target = []
    status_list = []
    # Find mrk elements with mtype attribute value "seg"
    mrk = soup.find_all('mrk', attrs={'mtype':'seg'})
    for i in mrk:
        for parent in i.parents:
            if parent.name == 'target':
                target.append(''.join(i.strings))
            if parent.name == 'seg-source':
                source.append(''.join(i.strings))

    segs = soup.find_all("sdl:seg")
    for seg in segs:
        seg_id.append(seg.attrs['id'])
        status_list.append(seg.attrs.get('conf', 'Unbearbeitet'))

    return seg_id, source, target, status_list


def collect_string_data(soup, filetype):
    '''Read segment ID, source and target strings

    Arguments:
    soup -- BeautifulSoupObject created from Across HTML export
    filetype -- String specifying supported file type. Takes either 'HTML' or "XML"

    Function has been updated to account for XML-based SDLXLIFF files

    Returns:
    seg_id_se -- Series with segment id data
    text_se -- Series with string data
    stype_se -- Series referencing segment type (source, target, previous)
    status_se -- Series object containing status info
    '''
    if filetype == 'HTML':
        seg_id, source, target = parse_html_strings(soup)
        # function call to extract status data from third column
        status_list = collect_status_data(soup)

    elif filetype == 'XML':
        seg_id, source, target, status_list = parse_xml_strings(soup)

    status_se = pd.Series(status_list)
    status_se.name = 'status'

    # Convert seg_id list to Series
    # TODO: Clean up lines with for loop
    seg_id_se = pd.Series(seg_id + seg_id, name='seg_id')

    # create new lists for segment type values
    stype_source = ['source' for i in range(len(source))]
    stype_target = ['target' for i in range(len(target))]
    # stype_previous = ['previous' for i in range(len(previous))]
    # Convert clean lists to Series
    text_se = pd.Series(source + target, name='text')
    stype_se = pd.Series(stype_source + stype_target, name='stype')

    return seg_id_se, text_se, stype_se, status_se

def collect_status_data(soup):
    '''Select status attribute in each row and write to list
    Arguments
    trs -- Rows in data table

    Loops through the table data elements in each row. Calls img_alt function
    to find first img alt item in each element, which will include status info.
    Uses regex pattern to extract segment status string.

    TODO: Implement list comprehension to write img_alt item.

    Returns
    status_list -- List object containing status info
    '''

    trs = soup.find_all('tr')
    status_list = []
    regex = re.compile('((?<= alt=)[^"]+?\b|(?<= alt=").+?(?=" ))')

    for i in range(len(trs)):
        tds = trs[i].find_all('td')

        for j in range(len(tds)):
            _ = tds[j].find(img_alt)

            if _:
                status_string = str(_)
                status = regex.search(status_string)
                status_list.append(status.group())

    return status_list

def collect_versions(soup):
    '''Check for earlier edits and return first edit
    Arguments:
    soup -- Beautiful soup object representing the nested HTML data structure

    Returns:
    pre_versions -- list with first entry in previous edits
    '''
    # create list from target elements
    target_elements = [element for element in soup.find_all('td', attrs={'class': 'inactiveTarget'})]
    pre_versions = []

    # loop through target elements to lookup versions
    for i in range(len(target_elements)):
        soup = BeautifulSoup(str(target_elements[i]), "lxml")
        versions = [element for element in soup.find_all('div', attrs={'class': 'atomHistory-box'})]
        # store earliest version and lookup string
        soup = BeautifulSoup(str(versions), "lxml")
        if soup.pre is not None:
            pre_versions.append(soup.pre.text)
        else:
            pre_versions.append('')

    return pre_versions

def read_filetype(file):
    '''Check for xml or html declaration'''
    first_line = file.readline()
    if re.match('\\ufeff<\?xml', first_line):
        filetype = 'XML'
    elif re.match('<HTML', first_line):
        filetype = 'HTML'
    else:
        print('Filetype not supported, please use either HTML or SDLXLIFF')
    return filetype

def read_from_file(fp, encoding='utf-8'):

    '''Read file with translation unit data
    Arguments:
    file -- file to be parsed.
            Note: At the moment the parser accepts both sdlxliff and html files (with/without change history)
    folder -- defaults to "data"
    encoding -- defaults to utf-8
    TODO: Check for other encodings,
          idea: Lookup charset from HTML Header / XML declaration and return in cache
    Returns:
    df -- DataFrame object with parsed text, segment type and status information which uses seg_id as index
    cache -- Dictionary with metadata pertaining to the project
    '''

    #file_to_open = os.path.join(folder, file)

    with open(fp, 'r', encoding=encoding) as f:
        filetype = read_filetype(f)
        soup = BeautifulSoup(f, 'lxml')
    # Collect metadata from HTML table's head column
    if filetype == 'HTML':
        # function call to extract metadata from first row of table
        cache = collect_metadata_html(soup)
    # Collect metadata from file path and SDLXLIFF "file" element
    elif filetype == 'XML':
        # Collect project data from file path
        filepath = os.path.abspath(file_to_open)
        cache = collect_metadata_xml(filepath)
        # Collect language IDs from SDLXLIFF "file" element
        with open(file_to_open, 'r', encoding=encoding) as f:
            soup = BeautifulSoup(f, 'lxml')
            cache['s_lid'] = str(soup.file['source-language'].split('-')[0]).upper()
            cache['t_lid'] = str(soup.file['target-language'].split('-')[0]).upper()
    # function call to extract string data from source and target columns
    seg_id, text_se, stype_se, status_se = collect_string_data(soup, filetype)

    for i in range(2):
        # copy values from Series and add them as rows below
        status_se = status_se.append(status_se, ignore_index = True)

    # Merge Series to DataFrame
    columns = ['text', 'stype', 'status']
    data_tuples = list(zip(text_se, stype_se, status_se))
    df = pd.DataFrame(data_tuples, columns = columns, index=seg_id)

    return df, cache
