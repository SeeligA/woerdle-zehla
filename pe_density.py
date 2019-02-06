import argparse

from scripts.parsing import read_from_file
from scripts.utils import new_sample, new_translation, query_yes_no, comp_entry
from scripts.calculation import new_calculation


parser = argparse.ArgumentParser(
    description="Calculate Post-Edit Density and submit entry",
)
parser.add_argument("user", help="Specify name of user.")
parser.add_argument("input", help="Specify filename.")
parser.add_argument("--folder", default="data", help="path/to/file.")
parser.add_argument("--sample_size", type=int, default=50, help="Run sampling on specified no. of segments")

args = parser.parse_args()
print(args)
# Read source file and project information
df, cache = read_from_file(args.input, args.folder)
cache['user'] = args.user
# Create sample object
sample_object, source = new_sample(df, sample_size=args.sample_size)
#
target_list, mt_list, cache = new_translation(df, cache, sample_object, source, args.input)
# Calculate Post-Edit Density, show bad apples and peach perfects, plot results for user review
cache = new_calculation(target_list, mt_list, cache)

if query_yes_no('Do you want to submit your competition entry? '):
    cache = comp_entry(cache)
    print('Thank you for submitting your entry!')
