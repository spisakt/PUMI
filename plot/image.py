def plot_fmri_qc(func, atlaslabels, confounds, output_file=None):
    # ADAPTED from niworkflows
    import seaborn as sns
    import numpy as np
    from seaborn import color_palette
    from matplotlib import gridspec as mgs
    import matplotlib.pyplot as plt
    import pandas as pd
    import os

    def plot_carpet(img, atlaslabels, detrend=True, nskip=0, size=(950, 800),
                    subplot=None, title=None, output_file=None, legend=False,
                    lut=None):
        """
        Adapted from: https://github.com/poldracklab/niworkflows

        Plot an image representation of voxel intensities across time also know
        as the "carpet plot" or "Power plot". See Jonathan Power Neuroimage
        2017 Jul 1; 154:150-158.
        Parameters
        ----------
            img : Niimg-like object
                See http://nilearn.github.io/manipulating_images/input_output.html
                4D input image
            atlaslabels: ndarray
                A 3D array of integer labels from an atlas, resampled into ``img`` space.
            detrend : boolean, optional
                Detrend and standardize the data prior to plotting.
            nskip : int
                Number of volumes at the beginning of the scan marked as nonsteady state.
            long_cutoff : int
                Number of TRs to consider img too long (and decimate the time direction
                to save memory)
            axes : matplotlib axes, optional
                The axes used to display the plot. If None, the complete
                figure is used.
            title : string, optional
                The title displayed on the figure.
            output_file : string, or None, optional
                The name of an image file to export the plot to. Valid extensions
                are .png, .pdf, .svg. If output_file is not None, the plot
                is saved to a file, and the display is closed.
            legend : bool
                Whether to render the average functional series with ``atlaslabels`` as
                overlay.
        """
        import numpy as np
        import nibabel as nb

        import matplotlib.pyplot as plt
        from matplotlib import gridspec as mgs
        import matplotlib.cm as cm
        from matplotlib.colors import ListedColormap

        from nilearn.plotting import plot_img
        from nilearn.signal import clean
        from nilearn._utils import check_niimg_4d
        from nilearn._utils.niimg import _safe_get_data

        # actually load data
        img = nb.load(img)
        atlaslabels = nb.load(atlaslabels).get_data()

        img_nii = check_niimg_4d(img, dtype='auto')
        func_data = _safe_get_data(img_nii, ensure_finite=True)

        minimum = np.min(func_data)
        maximum = np.max(func_data)
        myrange = maximum - minimum

        # Define TR and number of frames
        tr = img_nii.header.get_zooms()[-1]
        ntsteps = func_data.shape[-1]

        data = func_data[atlaslabels > 0].reshape(-1, ntsteps)
        seg = atlaslabels[atlaslabels > 0].reshape(-1)

        # Map segmentation
        if lut is None:
            lut = np.zeros((256,), dtype='int')
            #lut[1:11] = 1
            #lut[255] = 2
            #lut[30:99] = 3
            #lut[100:201] = 4

            lut[1] = 1
            lut[2] = 2
            lut[3] = 3
            lut[4] = 4
            lut[5] = 5
            lut[6] = 6
            lut[7] = 7

        # Apply lookup table
        newsegm = lut[seg.astype(int)]

        p_dec = 1 + data.shape[0] // size[0]
        if p_dec:
            data = data[::p_dec, :]
            newsegm = newsegm[::p_dec]

        t_dec = 1 + data.shape[1] // size[1]
        if t_dec:
            data = data[:, ::t_dec]

        # Detrend data
        v = (None, None)
        if detrend:
            data = clean(data.T, t_r=tr).T
            v = (-2, 2)

        # Order following segmentation labels
        order = np.argsort(newsegm)[::-1]

        # If subplot is not defined
        if subplot is None:
            subplot = mgs.GridSpec(1, 1)[0]

        # Define nested GridSpec
        wratios = [1, 100, 20]
        gs = mgs.GridSpecFromSubplotSpec(1, 2 + int(legend), subplot_spec=subplot,
                                         width_ratios=wratios[:2 + int(legend)],
                                         wspace=0.0)

        mycolors = ListedColormap(cm.get_cmap('tab10').colors[:4][::-1])

        # Segmentation colorbar
        ax0 = plt.subplot(gs[0])
        ax0.set_yticks([])
        ax0.set_xticks([])
        ax0.imshow(newsegm[order, np.newaxis], interpolation='none', aspect='auto',
                   cmap=mycolors, vmin=1, vmax=4)
        ax0.grid(False)
        ax0.spines["left"].set_visible(False)
        ax0.spines["bottom"].set_color('none')
        ax0.spines["bottom"].set_visible(False)

        # Carpet plot
        ax1 = plt.subplot(gs[1])
        ax1.imshow(data[order, ...], interpolation='nearest', aspect='auto', cmap='gray',
                   vmin=v[0], vmax=v[1])

        ax1.grid(False)
        ax1.set_yticks([])
        ax1.set_yticklabels([])

        ax1.annotate(
            'intensity range: ' + str(myrange), xy=(0.0, 1.02), xytext=(0, 0), xycoords='axes fraction',
            textcoords='offset points', va='center', ha='left',
            color='r', size=6,
            bbox={'boxstyle': 'round', 'fc': 'w', 'ec': 'none',
                  'color': 'none', 'lw': 0, 'alpha': 0.0})

        # Set 10 frame markers in X axis
        interval = max((int(data.shape[-1] + 1) // 10, int(data.shape[-1] + 1) // 5, 1))
        xticks = list(range(0, data.shape[-1])[::interval])
        ax1.set_xticks(xticks)
        ax1.set_xlabel('time (s)')
        labels = tr * (np.array(xticks)) * t_dec
        ax1.set_xticklabels(['%.02f' % t for t in labels.tolist()], fontsize=5)

        # Remove and redefine spines
        for side in ["top", "right"]:
            # Toggle the spine objects
            ax0.spines[side].set_color('none')
            ax0.spines[side].set_visible(False)
            ax1.spines[side].set_color('none')
            ax1.spines[side].set_visible(False)

        ax1.yaxis.set_ticks_position('left')
        ax1.xaxis.set_ticks_position('bottom')
        ax1.spines["bottom"].set_visible(False)
        ax1.spines["left"].set_color('none')
        ax1.spines["left"].set_visible(False)

        if legend:
            gslegend = mgs.GridSpecFromSubplotSpec(
                5, 1, subplot_spec=gs[2], wspace=0.0, hspace=0.0)
            epiavg = func_data.mean(3)
            epinii = nb.Nifti1Image(epiavg, img_nii.affine, img_nii.header)
            segnii = nb.Nifti1Image(lut[atlaslabels.astype(int)], epinii.affine, epinii.header)
            segnii.set_data_dtype('uint8')

            nslices = epiavg.shape[-1]
            coords = np.linspace(int(0.10 * nslices), int(0.95 * nslices), 5).astype(np.uint8)
            for i, c in enumerate(coords.tolist()):
                ax2 = plt.subplot(gslegend[i])
                plot_img(segnii, bg_img=epinii, axes=ax2, display_mode='z',
                         annotate=False, cut_coords=[c], threshold=0.1, cmap=mycolors,
                         interpolation='nearest')

        if output_file is not None:
            figure = plt.gcf()
            figure.savefig(output_file, bbox_inches='tight')
            plt.close(figure)
            figure = None
            return output_file

        return [ax0, ax1], gs

    def confoundplot(tseries, gs_ts, gs_dist=None, name=None,
                     units=None, tr=None, hide_x=True, color='b', nskip=0,
                     cutoff=None, ylims=None):

        import numpy as np
        from matplotlib import gridspec as mgs
        import matplotlib.pyplot as plt
        import seaborn as sns

        # Define TR and number of frames
        notr = False
        if tr is None:
            notr = True
            tr = 1.
        ntsteps = len(tseries)
        tseries = np.array(tseries)

        # Define nested GridSpec
        gs = mgs.GridSpecFromSubplotSpec(1, 2, subplot_spec=gs_ts,
                                         width_ratios=[1, 100], wspace=0.0)

        ax_ts = plt.subplot(gs[1])
        ax_ts.grid(False)

        # Set 10 frame markers in X axis
        interval = max((ntsteps // 10, ntsteps // 5, 1))
        xticks = list(range(0, ntsteps)[::interval])
        ax_ts.set_xticks(xticks)

        if not hide_x:
            if notr:
                ax_ts.set_xlabel('time (frame #)')
            else:
                ax_ts.set_xlabel('time (s)')
                labels = tr * np.array(xticks)
                ax_ts.set_xticklabels(['%.02f' % t for t in labels.tolist()])
        else:
            ax_ts.set_xticklabels([])

        if name is not None:
            if units is not None:
                name += ' [%s]' % units

            ax_ts.annotate(
                name, xy=(0.0, 0.7), xytext=(0, 0), xycoords='axes fraction',
                textcoords='offset points', va='center', ha='left',
                color=color, size=8,
                bbox={'boxstyle': 'round', 'fc': 'w', 'ec': 'none',
                      'color': 'none', 'lw': 0, 'alpha': 0.8})

        for side in ["top", "right"]:
            ax_ts.spines[side].set_color('none')
            ax_ts.spines[side].set_visible(False)

        if not hide_x:
            ax_ts.spines["bottom"].set_position(('outward', 20))
            ax_ts.xaxis.set_ticks_position('bottom')
        else:
            ax_ts.spines["bottom"].set_color('none')
            ax_ts.spines["bottom"].set_visible(False)

        # ax_ts.spines["left"].set_position(('outward', 30))
        ax_ts.spines["left"].set_color('none')
        ax_ts.spines["left"].set_visible(False)
        # ax_ts.yaxis.set_ticks_position('left')

        # Calculate Y limits
        def_ylims = [tseries[~np.isnan(tseries)].min() - 0.1 * abs(tseries[~np.isnan(tseries)].min()),
                     1.1 * tseries[~np.isnan(tseries)].max()]
        if ylims is not None:
            if ylims[0] is not None:
                def_ylims[0] = min([def_ylims[0], ylims[0]])
            if ylims[1] is not None:
                def_ylims[1] = max([def_ylims[1], ylims[1]])

        # Add space for plot title and mean/SD annotation
        def_ylims[0] -= 0.1 * (def_ylims[1] - def_ylims[0])

        ax_ts.set_ylim(def_ylims)
        yticks = sorted(def_ylims)
        #ax_ts.set_yticks([])
        #ax_ts.set_yticklabels([])
        ax_ts.set_yticks(yticks)
        ax_ts.set_yticklabels(['%.02f' % y for y in yticks], fontsize=5)

        # Annotate stats
        maxv = tseries[~np.isnan(tseries)].max()
        mean = tseries[~np.isnan(tseries)].mean()
        stdv = tseries[~np.isnan(tseries)].std()
        p95 = np.percentile(tseries[~np.isnan(tseries)], 95.0)

        stats_label = (r'max: {max:.3f}{units} $\bullet$ mean: {mean:.3f}{units} '
                       r'$\bullet$ $\sigma$: {sigma:.3f}').format(
            max=maxv, mean=mean, units=units or '', sigma=stdv)
        ax_ts.annotate(
            stats_label, xy=(0.98, 0.7), xycoords='axes fraction',
            xytext=(0, 0), textcoords='offset points',
            va='center', ha='right', color=color, size=4,
            bbox={'boxstyle': 'round', 'fc': 'w', 'ec': 'none', 'color': 'none',
                  'lw': 0, 'alpha': 0.8}
        )

        # Annotate percentile 95
        ax_ts.plot((0, ntsteps - 1), [p95] * 2, linewidth=.1, color='lightgray')
        ax_ts.annotate(
            '%.2f' % p95, xy=(0, p95), xytext=(-1, 0),
            textcoords='offset points', va='center', ha='right',
            color='lightgray', size=3)

        if cutoff is None:
            cutoff = []

        for i, thr in enumerate(cutoff):
            ax_ts.plot((0, ntsteps - 1), [thr] * 2,
                       linewidth=.2, color='dimgray')

            ax_ts.annotate(
                '%.2f' % thr, xy=(0, thr), xytext=(-1, 0),
                textcoords='offset points', va='center', ha='right',
                color='dimgray', size=3)

        ax_ts.plot(tseries, color=color, linewidth=.8)
        ax_ts.set_xlim((0, ntsteps - 1))

        if gs_dist is not None:
            ax_dist = plt.subplot(gs_dist)
            sns.displot(tseries, vertical=True, ax=ax_dist)
            ax_dist.set_xlabel('Timesteps')
            ax_dist.set_ylim(ax_ts.get_ylim())
            ax_dist.set_yticklabels([])

            return [ax_ts, ax_dist], gs
        return ax_ts, gs

    def calculate_DVARS(rest):
        """
        Adapted form C-PAC

        mask is calculated based on 10% rule

        Method to calculate DVARS as per
        power's method

        Parameters
        ----------
        rest : string (nifti file)
            path to motion correct functional data


        Returns
        -------
        DVARS list
        """

        import numpy as np
        import nibabel as nib

        rest_data = nib.load(rest).get_data().astype(np.float32)
        #maximum = rest_data.max()
        mask_data = rest_data[:, :, :, 0]
        #mask_data[mask_data ] = 0  # 10% threshold fro DVARS!!! # should be already masked...

        # square of relative intensity value for each voxel across
        # every timepoint
        data = np.square(np.diff(rest_data, axis=3))
        # applying mask, getting the data in the brain only
        data = data[mask_data > 0]
        # square root and mean across all timepoints inside mask
        DVARS = np.sqrt(np.mean(data, axis=0))
        return DVARS

    sns.set_style("whitegrid")
    sns.set_context("paper", font_scale=1)

    figure = plt.gcf()

    data = pd.read_csv(confounds, sep=r'[\t\s]+', index_col=False)

    dvars = calculate_DVARS(func)

    confounds = {}
    confounds['DVARS'] = {
                'values': dvars
            }

    for name in data.columns.ravel():
        confounds[name] = {
                'values': data[[name]].values.ravel().tolist()
            }


    nconfounds = len(confounds)
    nrows = 1 + nconfounds

    # Create grid
    grid = mgs.GridSpec(nrows, 1, wspace=0.0, hspace=0.05,
                        height_ratios=[1] * (nrows - 1) + [5])

    grid_id = 0

    palette = color_palette("husl", nconfounds)

    for i, (name, kwargs) in enumerate(confounds.items()):
        tseries = kwargs.pop('values')
        confoundplot(
            tseries, grid[grid_id], color=palette[i], **kwargs)
        grid_id += 1

    plot_carpet(func, atlaslabels, subplot=grid[-1], detrend=True)

    if output_file is not None:
        figure = plt.gcf()
        figure.savefig(output_file, bbox_inches='tight', dpi=500)
        plt.close(figure)
        figure = None
        return os.getcwd() + '/' + output_file

    return figure