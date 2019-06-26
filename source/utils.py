import json

from source.api import call_api, collect_trans_parameters
from source.sampling import append_sample_translations, optimize_sample_object, prepare_sample_object
from source.api import Error414


def cleanup_strings(string_list):
    """Remove additional whitespace"""
    clean = [w.replace('\n', '') for w in string_list]
    return clean


def img_alt(tag):
    """Filter for 1st img element with alt text after table data tag"""
    return tag.has_attr('alt') and tag.parent.name == 'td'


def new_sample(df, sample_size=50):
    # Create sample object
    filtered_items = prepare_sample_object(df, sample_size)
    sample_object, source, alpha_share = optimize_sample_object(filtered_items, sample_size)

    return sample_object, source, alpha_share


def match_target_mt(df):
    """Lookup target strings and corresponding MT strings and write to 2 separate lists

    Arguments:
        df -- DataFrame from input module, referencing seg_id, text, and type

    Returns:
        target_list, mt_list -- two aligned lists containing target strings and mt strings
    """

    # Note for testing: Include assert statement to make sure that lists are aligned (e.g. count/sum over seg_id)
    is_target = df['stype'] == 'target'
    is_mt = (df['stype'] == 'MT') & (df['text'] != '')

    mt_list = list(df[is_mt]['text'].values)
    target_list = []
    idx = df[is_mt].index

    # loop over MT strings, find first instance and check for corresponding seg_ids in target strings.
    # TODO: Check alternative approach with df.query, which includes index in function namespace
    for i in range(len(idx)):
        target_list.append(df[is_target].loc[idx[i]]['text'])

    return target_list, mt_list


def new_translation(df, cache, sample_object, source):
    """
    Helper function managing API calls to generate MT output from source strings

    Arguments:
        df -- Source object DataFrame with columns 'seg_id', 'text', 'stype', 'status'
        cache -- Dictionary of metadata for indexing purposes and translation calls
        sample_object -- DataFrame view of source object
        source -- List of strings selected for translations

    Return:
         target_list -- List of target strings
         mt_list -- List of MT output strings
    """
    # Setting text parameter limit according to DeepL API recommendations
    # This is to prevent URI too long (414) errors

    limit = 50
    base = limit
    target_mt = list()

    while limit >= 10:
        try:
            if max(len(source), limit) - base <= 0:
                batch = source[base-limit:len(source)]
                parameters = collect_trans_parameters(source=batch,
                                                      target_lang=cache['t_lid'],
                                                      source_lang=cache['s_lid'])
                target_mt += call_api(parameters)
                break

            else:
                batch = source[base-limit:base]
                parameters = collect_trans_parameters(source=batch,
                                                      target_lang=cache['t_lid'],
                                                      source_lang=cache['s_lid'])
                target_mt += call_api(parameters)
                base += limit

        except Error414:
            # If URI is too long, reset variables and send requests for smaller batches
            limit -= 10
            base = limit
            target_mt = list()

    # Update DataFrame with translations as new rows
    df = append_sample_translations(df, sample_object, target_mt)
    # Matching target strings and MT strings based on index numbers
    target_list, mt_list = match_target_mt(df)

    return target_list, mt_list


def save_cache(fp, cache):
    """Store cache for reference purposes."""
    print(fp)
    with open(fp, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False)
