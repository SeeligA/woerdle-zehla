import re
from collections import defaultdict, OrderedDict
import itertools
import logging
import os.path

import pandas as pd
import numpy as np
from bs4 import BeautifulSoup

from PyQt5.QtWidgets import QFileDialog

from source.utils import cleanup_strings, img_alt


def collect_metadata_xml(fp):
    """Collect metadata from file path.

    Arguments:
        filepath = String specifying the SDLXLIFF input file on F:

    Returns:
        cache -- Dictionary for further referencing and translation calls
    """
    cache = {}

    # Extract Client name and id. The regex acounts for both Windows and Unix-style paths
    regex = re.compile('((?<=ab Dez 2010(\\\|/))[^\\\/]+)')
    cache['Relation'] = regex.search(fp)
    # Extract project and PO ids
    regex = re.compile('((?<=03_Projekte(\\\|/))[^\\\/]+)')
    cache['Project'] = regex.search(fp)
    # Extract document name
    regex = re.compile('((?<=(\\\|/))[^\\\|/]+$)')
    cache['Document'] = regex.search(fp)
    # Iterate through search results and write values to cache
    for k, v in cache.items():
        if v:
            cache[k] = v.group(0)

    return cache


def clean_data(meta_list):
    """
    Remove invalid file path characters from meta data.
    Arguments:
        meta_list -- List of meta data strings
        Comma was excluded from character list for parsing purposes

    Returns:
        List of clean meta data strings
    """
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


def parse_html_strings(soup):
    # Create lists of strings for segment id and source
    text_dict = defaultdict(list)

    seg_id_list = [element.text for element in soup.find_all('td', attrs={'class': 'inactiveNumbering'})]
    text_dict['source'] = [element.text for element in soup.find_all('td', attrs={'class': 'inactiveSource'})]

    # Create list of strings from previous version elements in target
    # TODO: Implement to compare target with previous versions
    # Remove version elements from soup
    [element.replace_with('') for element in soup.find_all('div', attrs={'class': 'atomHistory-box'})]
    # Create list of strings for target
    targets = list()
    for element in soup.find_all('td', attrs={'class': 'inactiveTarget'}):

        try:
            targets.append(element.find('pre', attrs={'class': 'atom'}).text)
        except AttributeError:
            targets.append('')

    text_dict['target'] = targets
    # Function call to delete additional whitespace and ignore first row
    # TODO: Clean up lines with for loop
    # Account for the fact that v7.0 segments start in the first table row
    if seg_id_list[1] != "\xa0":
        seg_id_list = cleanup_strings(seg_id_list)
        text_dict['source'] = cleanup_strings(text_dict['source'])
        text_dict['target'] = cleanup_strings(text_dict['target'])

    else:
        seg_id_list = cleanup_strings(seg_id_list[1:])
        text_dict['source'] = cleanup_strings(text_dict['source'][1:])
        text_dict['target'] = cleanup_strings(text_dict['target'][1:])

    return seg_id_list, text_dict


def parse_xml_strings(soup, versions=False):
    """Read segment strings and segments status information.

    Arguments:
        soup -- BeautifulSoup object generated from input

    Returns:
        seg_id_list -- List containing segment ids
        text -- Dictionary containing two lists with source and target strings
        status_list -- List containing segment status information
    """
    seg_id_list = list()
    text = defaultdict(list)
    status_list = list()
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
        seg_id_list.append(seg.attrs['id'])

        if versions:
            status_list.append(seg.attrs.get('origin', 'Unknown'))
        else:
            status_list.append(seg.attrs.get('conf', 'Unbearbeitet'))

    return seg_id_list, text, status_list


def collect_string_data(soup, filetype, mt_soup=None):
    """Read segment ID, source and target strings.

    Arguments:
        soup -- BeautifulSoupObject created from Across HTML export
        filetype -- String specifying supported file type. Takes either 'HTML' or "XML"
        mt_soup -- Optional soup object identical with the original soup for parsing an MT file

    Returns:
        df -- Cleaned DataFrame object containing Segment IDs as index, and strings, status infos and segment type info
              as columns.
    """
    seg_id = defaultdict(list)
    status = defaultdict(list)

    if filetype == 'HTML':
        seg_id['source'], text = parse_html_strings(soup)
        # function call to extract status data from third column
        status['source'] = collect_status_data(soup)

        if mt_soup:

            # Change status information for lookup purposes and write as new list to dict
            status['mt'] = ['mt' if x == 'Bearbeitet (Maschinell übersetzt)'
                            or x == 'Bearbeitet (Maschinell übersetzt und manuell bearbeitet)'
                            or x == 'Korrigiert (Maschinell übersetzt)'
                            or x == 'Korrigiert (Maschinell übersetzt und manuell bearbeitet)'
                            or x == 'Übersetzt (Maschinell übersetzt)'
                            or x == 'Übersetzt (Maschinell übersetzt und manuell bearbeitet)'
                            else x for x in status['source']]

            seg_id['mt'] = seg_id['source']
            # Add MT version strings to text dictionary
            text['mt'] = parse_html_versions(mt_soup)

    elif filetype == 'XML':
        # Parse segment information in file and add to dictionaries.
        seg_id['source'], text, status['source'] = parse_xml_strings(soup)

        if mt_soup:
            # Now parse information in MT file.
            # We add the "versions" flag, because this operations is identical to parsing the original file.
            # The only difference is that we are only interested in the segments with origin "mt".
            seg_id['mt'], mt_text, mt_origin_list = parse_xml_strings(mt_soup, versions=True)
            status['mt'] = mt_origin_list
            text['mt'] = mt_text['target']

    # Create target keys and populate with source values.
    status['target'] = status['source']
    seg_id['target'] = seg_id['source']
    #  TODO: Add keys in the same order or create DataFrame from keys and not from iterable
    seg_id = OrderedDict(sorted(seg_id.items(), key=lambda t: t[0]))
    text = OrderedDict(sorted(text.items(), key=lambda t: t[0]))
    status = OrderedDict(sorted(status.items(), key=lambda t: t[0]))

    return create_dataframe(seg_id, text, status)


def create_dataframe(seg_id, text, status):
    """
    Create DataFrame object from dictionary with parsed strings.

    Arguments:
        seg_id -- Dictionary mapping segment IDs to segment types (source, target, MT [optional])
        text -- Dictionary mapping text strings to segment types (source, target, MT [optional])
        status -- Dictionary mapping status info to segment types (source, target, MT [optional])

    Returns:
        df -- Cleaned DataFrame object containing Segment IDs as index, and strings, status infos and segment type info
              as columns.
    """

    # Convert dictionary values to Series'
    seg_id_se = pd.Series(itertools.chain.from_iterable(seg_id.values()), name='seg_id')
    text_se = pd.Series(itertools.chain.from_iterable(text.values()), name='text')
    status_se = pd.Series(itertools.chain.from_iterable(status.values()), name='status')

    # Populate segment type Series from status keys
    stype = (np.repeat(k, len(v)) for k, v in status.items())
    stype_se = pd.Series(itertools.chain.from_iterable(stype), name='stype')

    # Merge Series to DataFrame
    df = pd.concat([text_se, stype_se, status_se], axis=1)
    df.index = seg_id_se

    # Filter for index items that contain only digits.
    # This is to ignore split segment which use alphanumerics as IDs. (Studio XML only)
    split_filter = df.index.str.isdigit()
    df = df[split_filter]

    return df


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
    """Check for xml or html declaration."""
    first_line = file.readline()
    if re.match('\\ufeff<\?xml', first_line):
        return 'XML'
    elif re.match('<HTML', first_line):
        return 'HTML'
    else:
        print('Filetype not supported, please use either HTML or SDLXLIFF')
        return None


def read_from_file(fp, encoding='utf-8', raw_mt=False):
    """Read file with translation unit data.

    Arguments:
        fp -- path to file to be parsed. At the moment the parser accepts both sdlxliff and
              html files (with/without change history)
        encoding -- defaults to utf-8
        raw_mt -- Flag to control the source of the MT output. Either a Boolean or a valid file path
                    If True, MT strings will be parsed from the version history (HTML) or a separate file (XML).
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
    if raw_mt:
        # Prompt for path to SDLXLIFF containing MT output
        if filetype == 'XML':
            # Updata file path with file path to raw MT file
            if raw_mt == bool():
                fp = QFileDialog.getOpenFileName(caption="Select file with MT segments",
                                                 filter='SDLXLIFF-Datei ({})'.format(os.path.basename(fp)))[0]
            else:
                fp = raw_mt
        # Make new soup
        with open(fp, 'r', encoding=encoding) as f:
            mt_soup = BeautifulSoup(f, 'lxml')
        df = collect_string_data(soup, filetype, mt_soup=mt_soup)

    else:
        df = collect_string_data(soup, filetype)

    return df, cache
