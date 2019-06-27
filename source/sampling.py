import re

# Set maximum number of iterations to create a sample object
MAX_SAMPLING = 7


def new_sample(df, sample_size):
    """Create sample object.
    Arguments:
        df -- Source object DataFrame with columns 'seg_id', 'text', 'stype', 'status'
        sample_size -- int() specifying the number of segments in a sample
    """
    filtered_items = prepare_sample_object(df)

    return optimize_sample_object(filtered_items, sample_size)


def prepare_sample_object(df):
    """
    Filter project data for valid segments

    Arguments:
    df -- Source object DataFrame with columns 'seg_id', 'text', 'stype', 'status'
    sample_size -- integer used to define maximum of items in sample object

    Returns:
    filtered_items -- DataFrame object for filtering out rows with
                      a) non-source,
                      b) non-translated
                      c) repeated segments
    """

    # Use query logic to filter for valid source segments
    # Checks for segment type first. Then checks for different valid status
    my_filter = df.query(
        'stype == "source" & (status == "ApprovedTranslation" | \
        status == "ApprovedSignOff" | \
        status == "Translated" | \
        status == "Korrigiert" | \
        status == "Korrigiert (Maschinell übersetzt)" | \
        status == "Übersetzt" | \
        status == "Übersetzt (Aus zweisprachigem Dokument eingefügt)" | \
        status == "Bearbeitet (Aus zweisprachigem Dokument eingefügt)")')

    # Eliminate repetitions
    filtered_items = my_filter.drop_duplicates('text')
    # Adapt sample size, use the lesser of all the sample segments available
    # or a multiple of the sample_size
    if filtered_items.shape[0] != 0:
        return filtered_items

    else:
        print('Not enough items for sampling!')
        raise Exception


def optimize_sample_object(filtered_items, sample_size):
    """
    Sample source strings multiple times to reduce proportion of non-translatables

    Arguments:
        filtered_items -- DataFrame object for filtering out rows with
                          a) non-source,
                          b) non-translated
                          c) repeated segments
        sample_size -- int() specifying the number of segments in a sample

    With this function we avoid sampling non-translatable text which would skew the final result.

    Returns:
        sample_object -- DataFrame object containing seg_id, text, stype and status information
        max_alpha -- no. letters in proportion to the full string
    """
    # Create object for storing sample objects, source texts and ratios
    sample_objects_dict = {}
    alpha_share = []
    sample_size = min(filtered_items.shape[0], sample_size)
    # Set count and specify no. of iterations
    count = 0
    while count < MAX_SAMPLING:

        # Create dataframe sample from valid segments
        sample_object = filtered_items.sample(sample_size)
        # Store sample in dict for later reuse
        sample_objects_dict[count] = sample_object

        length = 0
        alpha = 0
        # Find translatable characters in sample object
        for i in range(len(sample_object)):
            length += len(sample_object['text'][i])
            alpha += len(re.findall('[^\W\d]', sample_object['text'][i]))

        alpha_share.append(alpha / length)
        count += 1

    max_alpha = max(alpha_share)
    # Pick sample with maximum number of translatable characters from dict
    sample_object = sample_objects_dict[alpha_share.index(max_alpha)]

    return sample_object, max_alpha


def append_sample_translations(df, sample_object, translations):
    """
    Update source object with translations

    Arguments:
        df -- Source object DataFrame with columns 'seg_id', 'text', 'stype', 'status'
        sample_object -- DataFrame view of source object with the following filters:
                         stype == "source"
                         status == "Übersetzt"
        translations -- list with translated string

    Returns:
        df -- Source object with translated strings being added at the end and marked as 'MT'
    """

    for i in range(sample_object.shape[0]):
        sample_object['text'].values[i] = translations[i]
        sample_object['stype'].values[i] = 'MT'
    df = df.append(sample_object, ignore_index=False)

    return df
