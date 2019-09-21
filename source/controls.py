import ipywidgets as widgets
from PyQt5 import QtCore
from ipywidgets.widgets.interaction import show_inline_matplotlib_plots

from ipywidgets import Button, Layout, GridspecLayout
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sb
from distutils import util
import pandas as pd
import os

from source.parsing import read_from_file
from source.utils import new_translation, match_target_mt, save_cache
from source.sampling import new_sample
from source.calculation import pe_density
from source.settings import SettingsWindow


class MyControlWidget(widgets.Tab):
    def __init__(self):
        super(MyControlWidget, self).__init__()

        # Load settings
        self.settings = QtCore.QSettings("Lev Corp.", "woerdle-zehla")


        self.input_widget = widgets.GridBox()
        self.source_file_input = None
        self.sample_size_box = None
        self.init_ui()
        # self.out = widgets.Output()

    def init_ui(self):


        self.source_file_input = self.file_selector(placeholder="Enter path to file", desc="Deliverable")
        self.raw_mt_input = self.file_selector(placeholder="Enter path to raw MT file", desc="Raw MT file", disabled=True)


        self.input_widget = self.build_input_widget()
        self.file_toggle = self.build_file_toggle()
        self.textarea = self.build_text_area()
        self.sample_size_box = self.build_sample_size_box()
        self.control_buttons = self.build_button_controls()
        self.plot_button = create_expanded_button('Plot Button', 'danger')

        self.build_settings_accordion()

        self.grid = self.build_grid()

        self.out = widgets.Output(layout={'width': '98.5%', 'border': '2px solid grey', 'overflow_y': 'scroll'})

        self.build_tabs()

        self.toggle_files_button.observe(self.toggle_file_options, names='value')
        self.calculate_button.on_click(self.run_calculation)
        self.plot_button.on_click(self.plot_results)
        self.sample_button.on_click(self.run_sample)


    def run_sample(self, b):
        """Sample segments from input file and write alpha_share to text edit"""
        self.out.clear_output()
        self.df, self.cache = read_from_file(self.source_file_input.value)
        sample_size = self.sample_size_box.value
        self.sample_object, alpha_share = new_sample(self.df, sample_size=sample_size)
        self.textarea.value = "The sample's share of translatable characters is {:.1f}%".format(alpha_share * 100)

    def build_settings_accordion(self):
        """Create selection widgets and add to accordion view."""

        self.accordion = widgets.Accordion([widgets.Checkbox()])
        self.accordion.set_title(0, 'API')
        #for i, j in enumerate(self.selectors.keys()):
        #    self.accordion.set_title(i, j)
        #    self.accordion.set_title(i, j)

    @staticmethod
    def build_text_area():
        return widgets.Textarea(
            layout={'width': '98.5%', 'height': '99.5%', 'border': '2px solid grey'})

    def build_grid(self):
        grid = GridspecLayout(4, 6, height='400px')
        grid[0:1, 0:5] = self.input_widget
        grid[0:1, 5] = self.file_toggle
        grid[1:, 0:5] = self.textarea
        grid[1:3, 5] = self.control_buttons
        grid[3, 5] = self.plot_button
        return grid

    def build_tabs(self):
        """Add accordion widget and query text area to MyFilterWidget instance."""
        self.children = [self.grid, self.accordion]
        self.set_title(0, "Grid")
        self.set_title(1, "Settings")

    def build_button_controls(self):

        self.labelled_sample_size_box = self.label_sample_size_box()
        self.sample_button = create_expanded_button('Sample', 'warning')
        self.calculate_button = create_expanded_button('Calculate', 'warning')

        return widgets.GridBox([self.labelled_sample_size_box, self.sample_button, self.calculate_button],
                               layout=widgets.Layout(grid_template_columns="repeat(1, 99.5%)"))

    def build_input_widget(self):

        return widgets.GridBox([self.source_file_input, self.raw_mt_input],
                               layout=widgets.Layout(grid_template_columns="repeat(1, 99.5%)"))

    @staticmethod
    def file_selector(placeholder, desc, disabled=False):
        return widgets.Text(value=None,
                            placeholder=placeholder,
                            description=desc,
                            layout=Layout(width='100%', height='30px'),
                            disabled=disabled
                            )

    def build_file_toggle(self):
        self.toggle_files_button = self.ignore_history()
        self.toggle_files_label = widgets.HTML('File Selection')
        self.toggle_files_label.layout.margin = '0 0 0 0px'
        self.toggle_files_label.layout.justify_content = 'center'
        return widgets.VBox([self.toggle_files_label, self.toggle_files_button])

    @staticmethod
    def ignore_history():
        return widgets.ToggleButtons(
            options=['Source & Target', 'Source, Target & MT'],
            disabled=False,
            button_style='',  # 'success', 'info', 'warning', 'danger' or ''
            tooltips=['For translation', 'Use existing translations'],
            layout=Layout(width='98.5%', height='98.5%')
        )

    def toggle_file_options(self, change):
        toggle_dict = {"Source & Target": [True, False, False, "<font color='black'>Sample Size</font>"],
                       "Source, Target & MT": [False, True, True, "<font color='grey'>Sample Size</font>"]
                       }

        attr_list = [(self.raw_mt_input, 'disabled'), (self.sample_button, 'disabled'),
                     (self.sample_size_box, 'disabled'), (self.sample_size_label, 'value')]

        for i, j in enumerate(attr_list):
            setattr(j[0], j[1], toggle_dict[change['new']][i])

    @staticmethod
    def build_sample_size_box():
        return widgets.BoundedIntText(value=50, min=1, max=125, step=1, disabled=False,
                                      layout=Layout(width='98.5%', height='30px'))

    def label_sample_size_box(self):
        self.sample_size_label = widgets.HTML('Sample Size', layout=self.toggle_files_label.layout)
        # sample_size_label.layout.margin = '0 0 0 40px'
        return widgets.VBox([self.sample_size_label, self.sample_size_box])

    def plot_results(self, b):

        self.out.clear_output()
        show_inline_matplotlib_plots()

        with self.out:
            plot(self.cache)

    def run_calculation(self, b):
        """Calculate post-edit density results and create separate outputs.

        By enabling/ignoring version information, you tell the function to either:
            a) create a new dataframe from the input file
            b) populate the dataframe with translations called via the MT provider API
        The function then calculates post-edit density scores from the dataframe and stores the data in the cache.
        Cache information is then passed to different outputs:
            - the Output line edit
            - Optional: A json file saved manually or via the autosave function set in settings.
        """

        if self.toggle_files_button.value == 'Source, Target & MT':

            if os.path.exists(self.raw_mt_input.value):
                raw_mt = self.raw_mt_input.value
            else:
                raw_mt = True

            self.df, self.cache = read_from_file(self.source_file_input.value, raw_mt=raw_mt)
            #  TODO: Check if the filter index is still necessary when matching string indices in match_target_mt below.
            filter_index = self.df.query('status == "mt"').index
            self.df = self.df.loc[filter_index]

            # Create boolean filter with all repetitions except for first occurrences set to True
            filter_index = self.df.query('stype == "source"').duplicated('text')
            self.df = self.df[-filter_index]

        else:
            self.df = new_translation(self.df, self.cache, self.sample_object)

        df_mt = match_target_mt(self.df)

        self.cache = pe_density(df_mt, self.cache)
        #w.actionSave_as.setEnabled(True)
        self.textarea.value = 'Your Post-Edit Density score is {:.3f}\n'.format(self.cache['ped'])
        self.statistics()

        self.autosave()

    def autosave(self):
        if util.strtobool(self.settings.value("autosave", "")):
            self.save_as(auto=True)

    def print_details(self, apples_or_peaches):
        """Helper function for printing PED details"""

        count = 0
        for k, v in apples_or_peaches.items():

            self.textarea.value += 'PED = {:.3f}\n'.format(v['score'])
            self.textarea.value += 'MT Output  : ' + v['mt'] + '\n'
            self.textarea.value += 'Target Übs : ' + v['target'] + '\n'

            count += 1
            if count == 10:
                break

    def save_as(self, auto=False):

        file_format = 'ped{:.3f}_{}___{}.json'.format(self.cache['ped'], self.cache['Relation'], self.cache['Project'])

        if auto:
            fp = os.path.join(self.settings.value("autosave_folder", ""), file_format)
        #else:
        #    fp = QFileDialog.getSaveFileName(filter='JSON-Datei (*.json)', directory=file_format)[0]

        try:
            save_cache(fp, self.cache)

        except OSError:
            with self.out:
                print("Warning", "Not a valid path for saving!")

    def statistics(self, ba_limit=0.4, pp_limit=0.05):
        """Run additional statistics on Levenshtein distance results

        Arguments:
            cache -- containing a dictionary with Levenshtein results on a string level
            ba_limit -- as lower limit for the bad_apples classification
            pp_limit -- as upper limit for the peach perfect classification

        Prints detailed results for review purposes
            bad_apples -- dictionary for benchmarking strings with high pe efforts (Bad Apples)
            peach_perfect -- dictionary for benchmarking strings with minimal pe efforts (Peach Perfects)

        Returns:
            None
        """
        # TODO: Add BA and PP limits to app settings
        bad_apples = {k: v for k, v in self.cache['ped_details'].items() if v['score'] >= ba_limit}
        peach_perfect = {k: v for k, v in self.cache['ped_details'].items() if v['score'] <= pp_limit}

        if len(bad_apples) > 0:
            self.textarea.value += str(f'\n---Zu den Bad Apples (PED >= {ba_limit}) gehören folgende Strings---\n')
            self.print_details(bad_apples)

        else:
            self.textarea.value += str(f'\n---Super! Es gibt keine Bad Apples (PED <= {ba_limit})\n')

        if len(peach_perfect) > 0:
            self.textarea.value += str(f'\n---Zu den Peach Perfects (PED <= {pp_limit}) gehören folgende Strings---\n')
            self.print_details(peach_perfect)

        else:
            self.textarea.value += str(f'---Es gibt leider keine Peach Perfects (PED <= {pp_limit})---\n')


def create_expanded_button(description, button_style):
    return Button(description=description,
                  button_style=button_style,
                  layout=Layout(height='auto', width='auto'))


def plot(cache, cat_column=None, kde=False, save=False, color=None, ped=None, linewidth=5, fontsize=20):
    """Plot PED score data as histogram.

    Arguments:
        df -- DataFrame; containing ped analysis data.
              Columns = ["Project", "Relation", "Document", "s_lid", "t_lid", "score", "source", "target", "mt"]
        cat_column -- String; categorical variable for displaying
                      differential distributions (e.g. "t_lid", "s_lid", "Relation")
        kde -- Boolean; controls kernel density estimation and ticks on y axis
        save -- String specifying path to save file
        color -- String specifying the line color ("r", "b", "g", etc.)
    """
    df = pd.DataFrame.from_dict(data={k: v['score'] for k, v in cache['ped_details'].items()},
                                orient='index', columns=['score'])

    if len(df) == 0:
        return print("Not enough data.")

    step = 0.05
    bin_edges = np.arange(0.00, df['score'].max() + step, step)
    # Create grid to accommodate subplots
    sb.set(font_scale=2, style="white")
    g = sb.FacetGrid(data=df, hue=cat_column, height=10, xlim=(0, 1), palette="husl")

    g.map(sb.distplot, "score", bins=bin_edges, kde=kde, color=color,
          kde_kws={"alpha": 1, "lw": linewidth, "label": cat_column},
          hist_kws={"alpha": 1, "histtype": "step", "linewidth": linewidth})

    # Get labels from distplot
    if kde:
        locs, labels = plt.yticks()
        # Replace density under the curve labels with proportion per bin
        # Density values depend on bin sizes which is less intuitive
        labels = [round(step * label.get_position()[1], 2) for label in labels]
        plt.yticks(locs, labels)

        g.set_ylabels("Bin share ({} seg. total)".format(len(df)), fontsize=fontsize)
    else:
        g.set_ylabels("# of segments ({} seg. total)".format(len(df)), fontsize=fontsize)

    # Note that the aggregated score does not account for different segment length

    g.set_xlabels('Post-edit density (Agg. score: {:.3f})'.format(round(cache['ped'], 3)), fontsize=fontsize)
    g.fig.suptitle("Distribution of PED segment scores", fontsize=fontsize)
    g.add_legend(fontsize=fontsize)

    if save:
        g.savefig(save, pad_inches=0.1)
    show_inline_matplotlib_plots()
