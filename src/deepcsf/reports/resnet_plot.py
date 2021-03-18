"""
Plotting the output of CSF tests.
"""

import numpy as np
import glob
from matplotlib import pyplot as plt
from scipy import stats

from . import animal_csfs


def _area_name_from_path(file_name):
    for area_ind in range(5):
        area_name = 'area%d' % area_ind
        if area_name in file_name:
            return area_name
    return None


def _load_network_results(path, chns=None):
    net_results = dict()
    for chns_dir in sorted(glob.glob(path + '/*/')):
        chn_name = chns_dir.split('/')[-2]
        if chns is not None and chn_name not in chns:
            continue
        chn_res = []
        for file_path in sorted(glob.glob(chns_dir + '*.csv')):
            file_name = file_path.split('/')[-1]
            # finding the appropriate name
            area_name = _area_name_from_path(file_name)
            chn_res.append([np.loadtxt(file_path, delimiter=','), area_name])
        # if results were read add it to dictionary
        if len(chn_res) > 0:
            net_results[chn_name] = chn_res
    return net_results


def _extract_sensitivity(result_mat):
    unique_waves = np.unique(result_mat[:, 1])
    csf_inds = []
    for wave in unique_waves:
        lowest_contrast = result_mat[result_mat[:, 1] == wave][-1]
        csf_inds.append(1 / lowest_contrast[0])
    return csf_inds


def wave2sf(wave, target_size):
    base_sf = ((target_size / 2) / np.pi)
    return [((1 / e) * base_sf) for e in wave]


def uniform_sfs(xvals, yvals, target_size):
    max_xval = (target_size / 2)
    base_sf = max_xval / np.pi
    new_xs = [base_sf / e for e in np.arange(1, max_xval + 0.5, 0.5)]
    new_ys = np.interp(new_xs, xvals, yvals)
    return new_xs, new_ys


def _extract_data(result_mat, target_size):
    keys = ['contrast', 'wave', 'angle', 'phase', 'side']
    unique_params = dict()
    unique_params['wave'] = np.unique(result_mat[:, 1])
    # networks see the entire image, this assuming similar to fovea of 2 deg
    # to convert it to one degree, divided by 2
    unique_params['sf'] = np.array(
        wave2sf(unique_params['wave'], target_size)
    ) / 2
    accuracies = dict()
    contrasts_waves = dict()

    var_keys = ['angle', 'phase', 'side']

    sensitivities = dict()
    sensitivities['all'] = _extract_sensitivity(result_mat)
    data_summary = {
        'unique_params': unique_params, 'accuracies': accuracies,
        'contrasts_waves': contrasts_waves, 'sensitivities': sensitivities
    }
    # interpolating to all points
    int_xvals, int_yvals = uniform_sfs(
        unique_params['wave'], sensitivities['all'], target_size
    )
    unique_params['sf_int'] = np.array(wave2sf(int_xvals, target_size)) / 2
    sensitivities['all_int'] = int_yvals

    return data_summary


def _extract_network_summary(net_results, target_size):
    net_summary = dict()
    for chn_name, chn_data in net_results.items():
        net_summary[chn_name] = []
        num_tests = len(chn_data)
        for i in range(num_tests):
            test_summary = _extract_data(chn_data[i][0], target_size)
            net_summary[chn_name].append([test_summary, chn_data[i][1]])
    return net_summary


def _chn_plot_params(chn_name):
    label = chn_name
    kwargs = {}
    if chn_name in ['lum']:
        colour = 'gray'
        kwargs = {'color': colour, 'marker': 'x', 'linestyle': '-'}
    elif chn_name == 'rg':
        colour = 'green'
        label = 'rg   '
        kwargs = {
            'color': colour, 'marker': '1', 'linestyle': '-',
            'markerfacecolor': 'white', 'markeredgecolor': 'r'
        }
    elif chn_name == 'yb':
        colour = 'blue'
        label = 'yb   '
        kwargs = {
            'color': colour, 'marker': '2', 'linestyle': '-',
            'markerfacecolor': 'white', 'markeredgecolor': 'y'
        }
    return label, kwargs


def _plot_chn_csf(chn_summary, chn_name, figsize=(22, 4), log_axis=False,
                  normalise=True, model_name=None, old_fig=None):
    if old_fig is None:
        fig = plt.figure(figsize=figsize)
    else:
        fig = old_fig

    num_tests = len(chn_summary)
    for i in range(num_tests):
        # getting the x and y values
        org_yvals = np.array(chn_summary[i][0]['sensitivities']['all'])
        org_freqs = np.array(chn_summary[i][0]['unique_params']['sf'])

        if old_fig:
            ax = fig.axes[i]
        else:
            ax = fig.add_subplot(1, num_tests, i + 1)
        ax.set_title(chn_summary[i][1])

        label, chn_params = _chn_plot_params(chn_name)

        if normalise:
            org_yvals /= org_yvals.max()

        # first plot the human CSF
        if model_name is not None:
            hcsf = np.array([animal_csfs.csf(f, model_name) for f in org_freqs])
            hcsf /= hcsf.max()
            hcsf *= np.max(org_yvals)
            ax.plot(org_freqs, hcsf, '--', color='black', label='human')

            # use interpolation for corelation
            int_freqs = np.array(chn_summary[i][0]['unique_params']['sf_int'])
            hcsf = np.array([animal_csfs.csf(f, model_name) for f in int_freqs])
            hcsf /= hcsf.max()

            int_yvals = np.array(chn_summary[i][0]['sensitivities']['all_int'])
            int_yvals /= int_yvals.max()
            p_corr, r_corr = stats.pearsonr(int_yvals, hcsf)
            euc_dis = np.linalg.norm(hcsf - int_yvals)
            suffix_label = ' [r=%.2f | d=%.2f]' % (p_corr, euc_dis)
        else:
            suffix_label = ''
        chn_label = '%s%s' % (label, suffix_label)
        ax.plot(org_freqs, org_yvals, label=chn_label, **chn_params)

        ax.set_xlabel('Spatial Frequency (Cycle/Image)')
        ax.set_ylabel('Sensitivity (1/Contrast)')
        if log_axis:
            ax.set_xscale('log')
        ax.legend()
    return fig


def plot_csf_areas(path, target_size, chns=None, **kwargs):
    net_results = _load_network_results(path, chns=chns)
    net_summary = _extract_network_summary(net_results, target_size)
    net_csf_fig = None
    for chn_key, chn_val in net_summary.items():
        if net_csf_fig is not None:
            kwargs['old_fig'] = net_csf_fig
            kwargs['model_name'] = None
        net_csf_fig = _plot_chn_csf(chn_val, chn_key, **kwargs)
    return net_csf_fig