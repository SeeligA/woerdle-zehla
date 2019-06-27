import json

from source.api import Error414
from source.api import call_api, collect_trans_parameters
from source.sampling import append_sample_translations

# Set the size of your request batches.
# Reduce if your average segment size is larger; increase if segments are smaller in size.
# TODO: Check how multi-byte characters affects request sizes
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
    """Lookup target strings and corresponding MT strings and write to 3 separate lists

    Arguments:
        df -- DataFrame from input module, referencing seg_id, text, and type

    Returns:
        source_list, target_list, mt_list -- aligned lists of strings sharing index numbers
    """

    # Create boolean filters from segment type data
    is_target = df['stype'] == 'target'
    is_source = df['stype'] == 'source'
    is_mt = (df['stype'] == 'MT') & (df['text'] != '')

    # Apply filter to create index for valid MT segments
    idx = df[is_mt].index

    # Select text items matching MT index
    source_list = df[is_source].ix[idx, 'text']
    target_list = df[is_target].ix[idx, 'text']
    mt_list = df[is_mt]['text']

    return source_list, target_list, mt_list


def new_translation(df, cache, sample_object):
    """
    Helper function managing API calls to generate MT output from source strings

    Arguments:
        df -- Source object DataFrame with columns 'seg_id', 'text', 'stype', 'status'
        cache -- Dictionary of metadata for indexing purposes and translation calls
        sample_object -- DataFrame view of source object
        source -- List of strings selected for translations

    Return:
         source_list -- List of source strings
         target_list -- List of target strings
         mt_list -- List of MT output strings
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
