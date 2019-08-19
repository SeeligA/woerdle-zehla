import json
import pandas as pd

from source.api import Error414
from source.api import call_api, collect_trans_parameters
from source.sampling import append_sample_translations

# Set the size of your request batches.
# Reduce if your average segment size is larger; increase if segments are smaller in size.
# TODO: Check how multi-byte characters affect request sizes
MAX_REQUEST_SIZE = 50
# Set the increment at which request sizes are automatically reduced if deemed too long by the API.
# Smaller increments can mean more (unsuccessful) requests until a valid size has been reached.
# Larger increments can mean more requests due to smaller batch sizes.
REDUCE_REQUEST_SIZE_STEP = 10


def cleanup_strings(string_list):
    """Remove additional whitespace"""
    return [w.replace('\n', '') for w in string_list]


def img_alt(tag):
    """Filter for 1st img element with alt text after table data tag"""
    return tag.has_attr('alt') and tag.parent.name == 'td'


def match_target_mt(df):
    """Create new table with corresponding source, target and MT data in separate columns

    Arguments:
        df -- DataFrame from input module, referencing seg_id, text, and type

    Returns:
        df_mt -- Dataframe with source, target and MT data aligned on index numbers
    """

    # Create boolean filters from segment type data
    target_idx = df[df['stype'] == 'target'].index
    mt_idx = df[(df['stype'] == 'mt') & (df['text'] != '')].index
    # Create new index so that only index numbers are included
    # that exist in both target_idx and mt_idx
    intersect = mt_idx.intersection(target_idx)
    df = df.loc[intersect, ['text', 'stype']]

    strings = {stype: df[df['stype'] == stype].loc[:, 'text'] for stype in ['source', 'target', 'mt']}

    df_mt = pd.DataFrame(strings)

    return df_mt


def new_translation(df, cache, sample_object):
    """
    Helper function managing API calls to generate MT output from source strings

    Arguments:
        df -- Source object DataFrame with columns 'seg_id', 'text', 'stype', 'status'
        cache -- Dictionary of metadata for indexing purposes and translation calls
        sample_object -- DataFrame view of source object
        source -- List of strings selected for translations

    Return:
        df --
    """
    # Setting text parameter limit according to DeepL API recommendations
    # This is to prevent URI too long (414) errors

    source = sample_object['text']
    limit = MAX_REQUEST_SIZE
    base = limit
    target_mt = list()
    t_lid, s_lid = cache['t_lid'], cache['s_lid']

    while limit >= REDUCE_REQUEST_SIZE_STEP:
        try:
            if max(len(source), limit) - base <= 0:
                batch = source[base-limit:len(source)]
                parameters = collect_trans_parameters(source=batch, target_lang=t_lid, source_lang=s_lid)
                target_mt += call_api(parameters)
                break

            else:
                batch = source[base-limit:base]
                parameters = collect_trans_parameters(source=batch, target_lang=t_lid, source_lang=s_lid)
                target_mt += call_api(parameters)
                base += limit

        except Error414:
            # If URI is too long, reset variables and send requests for smaller batches
            limit -= REDUCE_REQUEST_SIZE_STEP
            base = limit
            target_mt = list()

    # Update DataFrame with translations as new rows
    df = append_sample_translations(df, sample_object, target_mt)

    return df


def save_cache(fp, cache):
    """Store cache for reference purposes."""
    with open(fp, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False)


def range_positive(start, stop, step):
    while start < stop:
        yield start
        start += step
