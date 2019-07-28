import re
from collections import defaultdict
import itertools
import logging

import pandas as pd
import numpy as np
from bs4 import BeautifulSoup

from source.utils import cleanup_strings, img_alt


def collect_metadata_xml(filepath):
    """Collect metadata from filepath

    Arguments:
        filepath = String specifying the SDLXLIFF input file on F:

    Returns:
        cache -- Dictionary for further referencing and translation calls
    """
    cache = {}

    # Extract Client name and id. The regex acounts for both Windows and Unix-style paths
    regex = re.compile('((?<=ab Dez 2010(\\\|/))[^\\\/]+)')
    cache['Relation'] = regex.search(filepath)
    # Extract project and PO ids
    regex = re.compile('((?<=03_Projekte(\\\|/))[^\\\/]+)')
    cache['Project'] = regex.search(filepath)
    # Extract document name
    regex = re.compile('((?<=(\\\|/))[^\\\|/]+$)')
    cache['Document'] = regex.search(filepath)
    # Iterate through search results and write values to cache
    for k, v in cache.items():
        if v:
            cache[k] = v.group(0)

    return cache


def clean_data(meta_list):
    """Clean meta data from any invalid file path characters."""
    p = re.compile('[<>;?"*|/]')
    return [p.sub('_', string) for string in meta_list]


def collect_metadata_html(soup):
    """Read header of the bilingual table and parses pertinent project information

    Arguments:
        Soup -- BeautifulSoupObject created from Across HTML export

    Returns:
        cache -- Dictionary for further referencing and translation calls
    """
    # Parse source and target column header

    try:
        tds_m = soup.find_all('div')

        meta = tds_m[0].get_text().split("\n")
        meta = clean_data(meta)

        # Parse string data from column headers
        p = re.compile(r'(^.+?) \((.+?)\)$')
        result = p.match(meta[3])

        cache = dict()
        cache['Project'] = result[1]
        cache['Relation'] = result[2].split(', ')[1]
        cache['Document'] = soup.find('div', attrs={'class': 'docTitleDocumentName'}).get_text()

        p = re.compile(r'(?:^.+?: )(.+?) \(.+?\) (?:nach|to) (.+?) \(.+?\)$')
        result = p.match(meta[5])
        s_lid = result[1]
        t_lid = result[2]

    # Handle exception for Across exports created pre v7.0
    except IndexError:
        cache, s_lid, t_lid = collect_metadata_html_v6_3(soup)

    # Create lookup dictionary for languages with MT support
    # TODO: Update dictionary where required
    lid_trans = {'Deutsch': 'DE', 'Englisch': 'EN', 'Französisch': 'FR',
                 'Italienisch': 'IT', 'Niederländisch': 'NL', 'Polnisch': 'PL',
                 'Portugiesisch': 'PT', 'Russisch': 'RU', 'Spanisch': 'ES'}

    cache['s_lid'] = lid_trans.get(s_lid, str("'{}' not supported".format(s_lid)))
    cache['t_lid'] = lid_trans.get(t_lid, str("'{}' not supported".format(t_lid)))

    return cache


def collect_metadata_html_v6_3(soup):
    """Read header of the bilingual table and parses pertinent project information

    Arguments:
        Soup -- BeautifulSoupObject created from Across HTML export

    Returns:
        cache -- Dictionary for further referencing and translation calls
    """
    # Parse source and target column header
    trs = soup.find_all('tr')
    tds_m = trs[0].find_all('td')
    meta = tds_m[1].find_all(string=True) + tds_m[3].find_all(string=True)

    meta = clean_data(meta)

    # Parse string data from column headers
    cache = dict()
    cache['Project'] = meta[1].split(sep=': ')[1]
    cache['Relation'] = meta[2].split(sep=': ')[1]
    cache['Document'] = meta[3].split(sep=': ')[1]

    s_lid = meta[0].split(sep=' ')[0]
    t_lid = meta[4].split(sep=' ')[0]

    return cache, s_lid, t_lid


def parse_html_versions_v6_3(soup):
    """Parse first entry from version history as MT output

    Arguments:
        soup -- BeautifulSoup object generated from input

    Returns:
         target_mt -- List of strings from version history
    """
    target_mt = []
    for element in soup.find_all('td', attrs={'class': 'inactiveTarget'})[1:]:
        versions = [box.span.text for box in element.find_all('div', attrs={'class': 'atomHistory-box'})]

        # Add last version from table data and ignore any other versions
        if len(versions) > 0:
            target_mt.append(versions[-1])
        else:
            target_mt.append('')

    return target_mt


def parse_html_versions(soup):
    """Parse first entry from version history as MT output

    Arguments:
        soup -- BeautifulSoup object generated from input

    Returns:
         target_mt -- List of strings from version history
    """
    target_mt = []

    try:
        for element in soup.find_all('td', attrs={'class': 'inactiveTarget'}):

            box = element.find('div', attrs={'class': 'atomHistory-box'})

            if box.span:
                versions = box.span.text

            # Add last version from table data and ignore any other versions
            if len(versions) > 0:
                target_mt.append(versions)
            else:
                target_mt.append('')

    except AttributeError:
        logging.info("Detected v6.3 HTML")
        target_mt = parse_html_versions_v6_3(soup)

    return target_mt


def parse_html_strings(soup, text):
    # Create lists of strings for segment id and source

    seg_id = [element.text for element in soup.find_all('td', attrs={'class': 'inactiveNumbering'})]
    text['source'] = [element.text for element in soup.find_all('td', attrs={'class': 'inactiveSource'})]

    # Create list of strings from previous version elements in target
    # TODO: Implement to compare target with previous versions
    # Remove version elements from soup
    [element.replace_with('') for element in soup.find_all('div', attrs={'class': 'atomHistory-box'})]
    # Create list of strings for target
    targets = list()
    for element in soup.find_all('td', attrs={'class': 'inactiveTarget'}):
        targets.append(element.find('pre', attrs={'class': 'atom'}).text)

    text['target'] = targets
    # Function call to delete additional whitespace and ignore first row
    # TODO: Clean up lines with for loop
    # Account for the fact that v7.0 segments start in the first table row
    if seg_id[1] != "\xa0":
        seg_id = cleanup_strings(seg_id)
        text['source'] = cleanup_strings(text['source'])
        text['target'] = cleanup_strings(text['target'])

    else:
        seg_id = cleanup_strings(seg_id[1:])
        text['source'] = cleanup_strings(text['source'][1:])
        text['target'] = cleanup_strings(text['target'][1:])

    return seg_id, text


def parse_xml_strings(soup, text):
    """Read segment strings and segments status information.

    Arguments:
        soup -- BeautifulSoup object generated from input

    Returns:
        seg_id -- List containing segment ids
        source -- List containing source strings
        target -- List containing target strings
        status_list -- List containing segment status information
    """
    seg_id = []

    status_list = []
    # Find mrk elements with mtype attribute value "seg"
    mrk = soup.find_all('mrk', attrs={'mtype': 'seg'})
    for i in mrk:
        for parent in i.parents:
            if parent.name == 'target':
                text['target'].append(''.join(i.strings))
            if parent.name == 'seg-source':
                text['source'].append(''.join(i.strings))

    segs = soup.find_all('sdl:seg')
    for seg in segs:
        seg_id.append(seg.attrs['id'])
        status_list.append(seg.attrs.get('conf', 'Unbearbeitet'))

    return seg_id, text, status_list


def collect_string_data(soup, filetype, mt_soup=None):
    """Read segment ID, source and target strings.

    Arguments:
        soup -- BeautifulSoupObject created from Across HTML export
        filetype -- String specifying supported file type. Takes either 'HTML' or "XML"

    Function has been updated to account for XML-based SDLXLIFF files

    Returns:
        seg_id_se -- Series with segment id data
        text_se -- Series with string data
        stype_se -- Series referencing segment type (source, target, previous)
        status_se -- Series object containing status info
    """
    text = defaultdict(list)

    if filetype == 'HTML':
        seg_id, text = parse_html_strings(soup, text)
        # function call to extract status data from third column
        status_list = collect_status_data(soup)

    elif filetype == 'XML':
        seg_id, text, status_list = parse_xml_strings(soup, text)

    else:
        return None

    if mt_soup:
        # Add MT version strings to text dictionary
        text['MT'] = parse_html_versions(mt_soup)

    # Concatenate status
    status_se = pd.Series(status_list * len(text))
    status_se.name = 'status'

    # Convert seg_id list to Series
    seg_id_se = pd.Series(seg_id * len(text), name='seg_id')

    # Convert text dictionary values to Series
    text_se = pd.Series(itertools.chain.from_iterable(text.values()), name='text')

    # Create segment type column from dictionary keys
    stype = (np.repeat(k, len(v)) for k, v in text.items())
    stype_se = pd.Series(itertools.chain.from_iterable(stype), name='stype')

    return seg_id_se, text_se, stype_se, status_se


def collect_status_data(soup):
    """Select status attribute in each row and write to list
    Arguments
        trs -- Rows in data table

    Loops through the table data elements in each row. Calls img_alt function
    to find first img alt item in each element, which will include status info.
    Uses regex pattern to extract segment status string.

    TODO: Implement list comprehension to write img_alt item.

    Returns:
        status_list -- List object containing status info
    """

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


def read_filetype(file):
    """Check for xml or html declaration"""
    first_line = file.readline()
    if re.match('\\ufeff<\?xml', first_line):
        return 'XML'
    elif re.match('<HTML', first_line):
        return 'HTML'
    else:
        print('Filetype not supported, please use either HTML or SDLXLIFF')
        return None


def read_from_file(fp, encoding='utf-8', versions=False):
    """Read file with translation unit data

    Arguments:
        fp -- path to file to be parsed. At the moment the parser accepts both sdlxliff and
              html files (with/without change history)
        encoding -- defaults to utf-8
    TODO: Check for other encodings,
          idea: Lookup charset from HTML Header / XML declaration and return in cache
    Returns:
        df -- DataFrame object with parsed text, segment type and status information which uses seg_id as index
        cache -- Dictionary with metadata pertaining to the project
    """

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
        cache = collect_metadata_xml(fp)
        # Collect language IDs from SDLXLIFF "file" element
        # TODO: Move this bit to collect_metadata_xml method without making new soup
        with open(fp, 'r', encoding=encoding) as f:
            soup = BeautifulSoup(f, 'lxml')
            cache['s_lid'] = str(soup.file['source-language'].split('-')[0]).upper()
            cache['t_lid'] = str(soup.file['target-language'].split('-')[0]).upper()
    else:
        return None

    # function call to extract string data from source and target columns
    if versions:
        # Make new soup
        with open(fp, 'r', encoding=encoding) as f:
            filetype = read_filetype(f)
            mt_soup = BeautifulSoup(f, 'lxml')
        seg_id, text_se, stype_se, status_se = collect_string_data(soup, filetype, mt_soup=mt_soup)

    else:
        seg_id, text_se, stype_se, status_se = collect_string_data(soup, filetype)

    # Merge Series to DataFrame
    df = pd.concat([text_se, stype_se, status_se], axis=1)
    df.index = seg_id

    return df, cache
