# from bs4 import BeautifulSoup
import datetime
# from html.parser import HTMLParser
# import json
# import matplotlib.pyplot as plt
# import numpy as np
# import os.path
import pandas as pd
# import re
# import requests
import sys
# import textwrap
from scripts.api import call_api, collect_trans_parameters
from scripts.sampling import append_sample_translations, optimize_sample_object, prepare_sample_object


def cleanup_strings(string_list):
    '''Remove additional whitespace'''
    clean = [w.replace('\n', '') for w in string_list]
    return clean

def comp_entry(cache):
    # Add date as key for indexing entries
    d = datetime.datetime.today().replace(microsecond=0)
    cache = {str(d): cache}
    entry = pd.DataFrame.from_dict(cache, orient='index')
    with open('entry.csv', 'a') as f:
        entry.to_csv(f, header=False, sep=';')

    return cache

def img_alt(tag):
    '''Filter for 1st img element with alt text after table data tag'''
    return tag.has_attr('alt') and tag.parent.name=='td'

def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    Source = https://stackoverflow.com/questions/3041986/apt-command-line-interface-like-yes-no-input
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


def new_sample(df, sample_size=50):

    # Create sample object
    filtered_items = prepare_sample_object(df, sample_size)
    sample_object, source, alpha_share = optimize_sample_object(filtered_items, sample_size)
    print("The sample's share of translatable characters is {:.1f}%".format(alpha_share * 100))
    x = query_yes_no('Use this sample? ')
    while x == 0:
        sample_object, source, alpha_share = optimize_sample_object(filtered_items, sample_size)
        x = print("The sample's share of translatable characters is of {:.1f}%".format(alpha_share * 100))
        x = query_yes_no('Use this sample? ')

    return sample_object, source

def match_target_mt(df):
    '''Lookup target strings and corresponding MT strings and write to 2 separate lists
    Arguments:
    df -- DataFrame from input module, referencing seg_id, text, and type

    Returns
    target_list, mt_list -- two aligned lists containing target strings and mt strings
    '''

    #Note for testing: Include assert statement to make sure that lists are aligned (e.g. count/sum over seg_id)
    is_target = df['stype']=='target'
    is_mt = df['stype']=='MT'

    mt_list = list(df[is_mt]['text'].values)
    target_list = []
    idx = df[is_mt].index

    #loop over MT strings, find first instance and check for corresponding seg_ids in target strings.
    # TODO: Check alternative approach with df.query, which includes index in function namespace
    for i in range(len(idx)):
        target_list.append(df[is_target].loc[idx[i]]['text'])

    return target_list, mt_list

def new_translation(df, cache, sample_object, source, file):
    # generate parameters dictionary from input data
    parameters = collect_trans_parameters(source=source, target_lang=cache['t_lid'], source_lang=cache['s_lid'])
    # call API
    target_mt = call_api(parameters)
    # Update DataFrame with translations as new rows
    df = append_sample_translations(df, sample_object, target_mt)
    # Optional: Save output to file for testing on other modules
    # TODO: Make output more accessible to users
    df.to_csv('after_trans_{}.csv'.format(file))
    print('\nYour data has been written to you current working directory.\n')
    # Matching target strings and MT strings based on index numbers
    target_list, mt_list = match_target_mt(df)

    return target_list, mt_list, cache
