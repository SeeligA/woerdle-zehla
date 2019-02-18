# from bs4 import BeautifulSoup
# import datetime
# from html.parser import HTMLParser
# import json
import matplotlib.pyplot as plt
import numpy as np
# import os.path
import pandas as pd
# import re
# import requests
# import sys
import textwrap


def levenshtein(s1, s2):
    '''Calculate Levenshtein distance based on string1 and string2
    Arguments:
    s1 and s2 as str() where s1 corresponds to the target segment and s2 to the mt segment

    returns Levenshtein distance as int()
    Source: Wikibooks
    '''
    if len(s1) < len(s2):
        return levenshtein(s2, s1)

    # len(s1) >= len(s2)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1 # j+1 instead of j since previous_row and current_row are one character longer
            deletions = current_row[j] + 1       # than s2
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def new_calculation(target_list, mt_list, cache):
    # Calculating post-edit density scores
    #cache = {'today': {'user': 'user_test'}} # for testing purposes only
    cache = pe_density(target_list, mt_list, cache)

    print('Your Post-Edit Density score is {:.3f}\n'.format(cache['ped']))
    # TODO: make ba_limit and pp_limit customizable
    statistics(cache, target_list, mt_list, verbose = True)
    plot_ped(cache)

    return cache



def pe_density(s1, s2, cache):
    '''Calculate post edit density for two lists of strings
    Arguments:
    s1, s2 as ordered lists with strings

    Returns
    tuple containing Post-Edit density results on document level (as int()) and string level (as dict())
    updated cache with ped result
    '''

    lev_count = float()
    char_count = int()
    ped_details = {}

    # Run through lists and calculate Levenshtein distance and max length for each pair of strings
    for i in range(len(s1)):
        if len(s1[i]) == len(s2[i]):
            max_char = len(s1[i])
        else:
            max_char = max(len(s1[i]), len(s2[i]))

        lev = levenshtein(s1[i], s2[i])

        char_count += max_char
        lev_count += lev

        ped_details[i] = lev/max_char

    ped = lev_count/char_count
    cache['ped'] = ped
    cache['ped_details'] = ped_details

    return cache


def statistics(cache, target_list, mt_list, ba_limit = 0.4, pp_limit = 0.05, verbose = False):
    '''Run additional statistics on Levenshtein distance results
    Arguments:
    cache -- containing a dictionary with Levenshtein results on a string level
    ba_limit -- as lower limit for the bad_apples classification
    pp_limit -- as upper limit for the peach perfect classification

    Prints detailed results for review purposes

    Returns:
    bad_apples -- dictionary for benchmarking strings with high pe efforts (Bad Apples)
    peach_perfect -- dictionary for benchmarking strings with minimal pe efforts (Peach Perfects)
    '''

    bad_apples = {k: v for k, v in cache['ped_details'].items() if v >= ba_limit}
    peach_perfect = {k: v for k, v in cache['ped_details'].items() if v <= pp_limit}

    if verbose:

        if len(bad_apples) > 0:

            print('---Zu den Bad Apples (PED >= {}) gehören folgende Strings---\n'.format(ba_limit))

            print_details(bad_apples, target_list, mt_list)

        else:
            print('---Super! Es gibt keine Bad Apples (PED <= {})\n'.format(ba_limit))


        if len(peach_perfect) > 0:
            print('---Zu den Peach Perfects (PED <= {}) gehören folgende Strings---\n'.format(pp_limit))

            print_details(peach_perfect, target_list, mt_list)

        else:
            print('---Es gibt leider keine Peach Perfects (PED <= {})\n'.format(pp_limit))

    return bad_apples, peach_perfect

def plot_ped(cache):
    '''Plot post-edit density results to help understand the distribution of the object

    Arguments:
    cache -- dictionary with seg_id as key and post-edit distance as value

    returns:
    Nothing
    '''
    df = pd.DataFrame.from_dict(data=cache['ped_details'], orient='index', columns=['ped'])
    bin_edges = np.arange(0, df['ped'].max()+0.05, 0.05)
    plt.hist(data=df, x = df['ped'], bins=bin_edges, color='#ffa500');
    plt.xlabel('Post-edit density (Agg. score: {:.3f})'.format(cache['ped']))
    plt.ylabel('Number of segments ({} seg. total)'.format(len(cache['ped_details'])));
    plt.savefig('out/{}_ped_{:.3f}_{}.png'.format(cache['user'], cache['ped'], cache['Project'], dpi=300))
    return None

def print_details(apples_or_peaches, target_list, mt_list):
    wrapper = textwrap.TextWrapper(subsequent_indent=' '*13)
    count = 0
    for i, j in apples_or_peaches.items():

        string1 = mt_list[i]
        string2 = target_list[i]

        print('PED = {:.3f}'.format(j))
        print('MT Output  :', wrapper.fill(text=string1))
        print('Target Übs :', wrapper.fill(text=string2), '\n')
        count += 1
        if count == 10:
            break
