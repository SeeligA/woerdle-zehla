

def levenshtein(s1, s2):
    """Calculate Levenshtein distance based on string1 and string2

    Arguments:
        s1 and s2 as str() where s1 corresponds to the target segment and s2 to the mt segment

    Returns:
        Levenshtein distance as int()

    Source: Wikibooks
    """
    if len(s1) < len(s2):
        return levenshtein(s2, s1)

    # len(s1) >= len(s2)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[
                             j + 1] + 1  # j+1 instead of j since previous_row and current_row are one character longer
            deletions = current_row[j] + 1  # than s2
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def pe_density(df, cache):
    """Calculate post edit density for MT strings.

    Arguments:
        df -- DataFrame table containing string data in "source", "target" and "mt" columns

        The function applies the Levenshtein algorithm to each row and stores the output and corresponding ped data in
        three new columns. The aggregated score as well as string and individual score data is the added to the cache.

    Returns:
        cache -- Updated dictionary containing ped score data
    """

    # Write the maximum length for each target-mt pair to a new column. We need this value to avoid dividing by zero.
    df["max_char"] = df.apply(lambda x: max(len(x.target), len(x.mt)), axis=1)
    # Calculate Levenshtein distance for each target-mt pair.
    df["lev"] = df.apply(lambda x: levenshtein(x.target, x.mt), axis=1)
    # Normalize Levenshtein distance by maximum segment length.
    df['score'] = df['lev'].copy().div(df['max_char'])

    ped_details = df[['score', 'source', 'target', 'mt']].to_dict('index')
    ped = df['lev'].sum() / df['max_char'].sum()
    cache['ped'] = ped
    cache['ped_details'] = ped_details

    return cache
