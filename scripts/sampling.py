# from bs4 import BeautifulSoup
# import datetime
# from html.parser import HTMLParser
# import json
# import matplotlib.pyplot as plt
# import numpy as np
# import os.path
import pandas as pd
import re
# import requests
# import sys
# import textwrap

def prepare_sample_object(df, sample_size = 15):
    '''
    Filter project data for valid segments
    Arguments:
    df -- Source object DataFrame with columns 'seg_id', 'text', 'stype', 'status'
    sample_size -- integer used to define maximum of items in sample object

    Returns:
    filtered_items -- DataFrame object for filtering out rows with
                      a) non-source,
                      b) non-translated
                      c) repeated segments
    '''

    # Use query logic to filter for valid source segments
    # Checks for segment type first. Then checks for different valid status
    my_filter = df.query('stype == "source" & (status == "Korrigiert" | status == "Übersetzt" | status == "Übersetzt (Aus zweisprachigem Dokument eingefügt)" | status == "Bearbeitet (Aus zweisprachigem Dokument eingefügt)")')
    # Eliminate repetitions
    filtered_items = my_filter.drop_duplicates('text')
    # Adapt sample size, use the lesser of all the sample segments available
    # or a multiple of the sample_size
    if 0 < filtered_items.shape[0]:
        # TODO: Review this bit and
        sample_size = min(filtered_items.shape[0], sample_size*5)

        return filtered_items

    else:
        print('Not enough items for sampling!')
        return None  # TODO: Check if raising an exception would be more appropriate


def optimize_sample_object(filtered_items, sample_size):
    '''
    Sample source strings multiple times to reduce proportion of non-translatables
    Arguments:
    filtered_items --
    sample_size --

    With this functions we avoid sampling nontranslatable text which would skew the final result.

    Returns:
    sample_object -- DataFrame object containing
    source -- list of source strings used for translation
    max_alpha -- no. letters in proportion to the full string
    '''
    # Create object for storing sample objects, source texts and ratios
    sample_objects_dict = {}
    source_dict = {}
    alpha_share = []
    sample_size = min(filtered_items.shape[0], sample_size)
    # Set count and specify no. of iterations
    count = 0
    while count < 7:

        sample_object = filtered_items.sample(sample_size)
        # Write items in sample object to list
        source = sample_object['text'].tolist()

        sample_objects_dict[count] = sample_object
        source_dict[count] = source

        length = 0
        alpha = 0

        for i in range(len(source)):
            length += len(source[i])
            alpha += len(re.findall('[^\W\d]', source[i]))

        alpha_share.append(alpha/length)
        count += 1

    max_alpha = max(alpha_share)
    sample_object = sample_objects_dict[alpha_share.index(max_alpha)]
    source = source_dict[alpha_share.index(max_alpha)]
    return sample_object, source, max_alpha


def append_sample_translations(df, sample_object, translations):
    '''
    Update source object with translations
    Arguments:
    df -- Source object DataFrame with columns 'seg_id', 'text', 'stype', 'status'
    sample_object -- DataFrame view of source object with the following filters:
                     stype == "source"
                     status == "Übersetzt"
    translations -- list with translated string

    Returns:
    df -- Source object with translated strings being added at the end and marked as 'MT'
    '''
    # TODO: Check if another status marker might be more appropriate than 'MT'
    for i in range(sample_object.shape[0]):
        sample_object['text'].values[i] = translations[i]
        sample_object['stype'].values[i] = 'MT'
    df = df.append(sample_object, ignore_index=False)

    return df
