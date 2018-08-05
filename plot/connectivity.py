def plot_matrix(matrix_file, modules, atlas=False, output_file="matrix.png"):
    import os
    import matplotlib.pyplot as plt
    from matplotlib import gridspec as mgs
    from nilearn import plotting
    import pandas as pd
    from matplotlib.colors import ListedColormap
    import matplotlib.cm as cm
    import nibabel as nb
    import PUMI.utils.globals as glb
    import numpy as np
    from nilearn.plotting import plot_img

    # load matrix file
    mat = pd.read_csv(matrix_file, sep="\t")
    mat.set_index('Unnamed: 0', inplace=True)
    regnum = mat.shape[0]

    legend = False
    if atlas:
        legend=True

    subplot = mgs.GridSpec(1, 1)[0]
    wratios = [10, 130, 30]  # this works probably only for the MIST122 atlas
    gs = mgs.GridSpecFromSubplotSpec(1, 2 + int(legend), subplot_spec=subplot,
                                     width_ratios=wratios[:2 + int(legend)],
                                     wspace=0.0)

    ax0 = plt.subplot(gs[0])

    ax0.set_yticks([])
    ax0.set_xticks([])

    mycolors = ListedColormap(cm.get_cmap('Set1').colors[:7][::-1])

    modules = pd.Series(modules).values
    lut = pd.factorize(modules)[0]+1
    lutt = pd.DataFrame({'1': lut})
    ax0.imshow(lutt, interpolation='none', aspect='auto',
               cmap=mycolors, vmin=0, vmax=8)

    ax0.grid(False)
    ax0.spines["left"].set_visible(False)
    ax0.spines["bottom"].set_color('none')
    ax0.spines["bottom"].set_visible(False)

    mycolors = ListedColormap(cm.get_cmap('Set1').colors[:7][::-1])
    ax1 = plt.subplot(gs[1])
    ax1.set_yticks([])
    ax1.set_xticks([])

    plotting.plot_matrix(mat.values, axes=ax1, colorbar=False)

    if legend:
        gslegend = mgs.GridSpecFromSubplotSpec(
            5, 1, subplot_spec=gs[2], wspace=0.0, hspace=0.0)

        background_file = glb._FSLDIR_ + "/data/standard/MNI152_T1_3mm_brain.nii.gz" #TODO: works only for 3mm atlas
        background = nb.load(background_file)
        atlas = nb.load(atlas)

        nslices = background.shape[-1]
        #coords = np.linspace(int(0 * nslices), int(0.99 * nslices), 5).astype(np.uint8)
        coords = [-40, 20, 0, 20, 40] #works in MNI space
        lut2 = lut
        lut2 = np.array([0] + lut2.tolist())

        relabeled=lut2[np.array(atlas.get_data(), dtype=int)]
        atl = nb.Nifti1Image(relabeled, atlas.get_affine())
        for i, c in enumerate(coords):
            ax2 = plt.subplot(gslegend[i])
            plot_img(atl, bg_img=background, axes=ax2, display_mode='z',
                     annotate=False, cut_coords=[c], threshold=0.1, cmap=mycolors,
                     interpolation='nearest', vmin=1, vmax=7)

    if output_file is not None:
        figure = plt.gcf()
        figure.savefig(output_file, bbox_inches='tight')
        plt.close(figure)
        return os.getcwd() + '/' + output_file

    return 0


def plot_conn_hist(matrix_file, modules, atlas=False, output_file="hist.png"):

    from matplotlib import pyplot as plt
    from matplotlib import gridspec as mgs
    import matplotlib.cm as cm
    from matplotlib.colors import ListedColormap
    import PUMI.utils.globals as glb
    import pandas as pd
    import numpy as np
    import nibabel as nb
    from nilearn.plotting import plot_img
    import os
    from nilearn.connectome import sym_matrix_to_vec

    # load matrix file
    mat = pd.read_csv(matrix_file, sep="\t")
    mat.set_index('Unnamed: 0', inplace=True)
    regnum = mat.shape[0]

    mat = mat.values

    histdata=[]
    # create a list of modular connectivities
    for mod in pd.Series(modules).unique():
        idx = np.array(np.where([m == mod for m in modules])).flatten()
        submat = mat[np.ix_(idx, idx)]
        mat[np.ix_(idx, idx)] = None
        histdata.insert(0, np.array(sym_matrix_to_vec(submat)))

    histdata.insert(0, np.array([0])) # temporary hack to make nicer inter-modular colors
    histdata.insert(0, np.array(sym_matrix_to_vec(mat)))

    mycolors = ListedColormap(cm.get_cmap('Set1').colors[:7][::-1])
    modules = pd.Series(modules).values
    lut = pd.factorize(modules)[0] + 1

    legend = False
    if atlas:
        legend = True

    # Define nested GridSpec
    wratios = [100, 20]
    subplot = mgs.GridSpec(1, 1)[0]
    gs = mgs.GridSpecFromSubplotSpec(1, 1 + int(legend), subplot_spec=subplot,
                                     width_ratios=wratios[:2 + int(legend)],
                                     wspace=0.0)

    ax0 = plt.subplot(gs[0])
    # colorbars are very much hardcoded
    # TODO: fix colorbars (make it work for other atlases)
    cols = cm.get_cmap('Set1').colors[:9][::-1]
    plt.hist(histdata, stacked=True, normed=True, color=cols)

    if legend:
        gslegend = mgs.GridSpecFromSubplotSpec(
            5, 1, subplot_spec=gs[1], wspace=0.0, hspace=0.0)

        background_file = glb._FSLDIR_ + "/data/standard/MNI152_T1_3mm_brain.nii.gz" #TODO: works only for 3mm atlas
        background = nb.load(background_file)
        atlas = nb.load(atlas)

        nslices = background.shape[-1]
        #coords = np.linspace(int(0 * nslices), int(0.99 * nslices), 5).astype(np.uint8)
        coords = [-40, 20, 0, 20, 40] #works in MNI space
        lut2 = lut
        lut2 = np.array([0] + lut2.tolist())

        relabeled = lut2[np.array(atlas.get_data(), dtype=int)]
        atl = nb.Nifti1Image(relabeled, atlas.get_affine())
        for i, c in enumerate(coords):
            ax2 = plt.subplot(gslegend[i])
            plot_img(atl, bg_img=background, axes=ax2, display_mode='z',
                     annotate=False, cut_coords=[c], threshold=0.1, cmap=mycolors,
                     interpolation='nearest', vmin=1, vmax=7)

    if output_file is not None:
        figure = plt.gcf()
        figure.savefig(output_file, bbox_inches='tight')
        plt.close(figure)
        return os.getcwd() + '/' + output_file

    return 0


def plot_conn_polar(matrix_file, modules, atlas=False, output_file="hist.png"):

    from matplotlib import pyplot as plt
    from matplotlib import gridspec as mgs
    import matplotlib.cm as cm
    from matplotlib.colors import ListedColormap
    import PUMI.utils.globals as glb
    import pandas as pd
    import numpy as np
    import nibabel as nb
    from nilearn.plotting import plot_img
    import os
    from nilearn.connectome import sym_matrix_to_vec

    # load matrix file
    mat = pd.read_csv(matrix_file, sep="\t")
    mat.set_index('Unnamed: 0', inplace=True)
    regnum = mat.shape[0]

    mat = mat.values

    meandata=[]
    # create a list of modular connectivities
    for mod in pd.Series(modules).unique():
        idx = np.array(np.where([m == mod for m in modules])).flatten()
        submat = mat[np.ix_(idx, idx)]
        mat[np.ix_(idx, idx)] = None
        meandata.append( np.abs(np.array(sym_matrix_to_vec(submat))).mean())

    #meandata.insert(0, np.array([0])) # temporary hack to make nicer inter-modular colors
    intermod = [x for x in sym_matrix_to_vec(mat) if x is not None]
    intermod = np.array(intermod)
    intermod = intermod[~np.isnan(intermod)]

    meandata.insert(0, np.abs(np.array(intermod)).mean())

    mycolors = ListedColormap(cm.get_cmap('Set1').colors[:7][::-1])
    modules = pd.Series(modules).values
    lut = pd.factorize(modules)[0] + 1

    legend = False
    if atlas:
        legend = True

    # Define nested GridSpec
    wratios = [100, 20]
    subplot = mgs.GridSpec(1, 1)[0]
    gs = mgs.GridSpecFromSubplotSpec(1, 1 + int(legend), subplot_spec=subplot,
                                     width_ratios=wratios[:2 + int(legend)],
                                     wspace=0.0)

    ax0 = plt.subplot(gs[0], polar=True)
    # colorbars are very much hardcoded
    # TODO: fix colorbars (make it work for other atlases)
    cols = cm.get_cmap('Set1').colors[:8][::-1]

    polx  = np.linspace(0, 2 * np.pi, len(meandata), endpoint=False)
    ax0.grid(True)
    ax0.set_xticks(polx)
    #ax0.set_theta_zero_location("N")
    #ax0.set_theta_direction(-1)
    ax0.bar(polx, meandata, color=cols)
    labels=pd.Series(modules).unique().tolist() #.append("intermodular")
    labels.insert(0, "intermodular")
    ax0.set_xticklabels(labels)

    if legend:
        gslegend = mgs.GridSpecFromSubplotSpec(
            5, 1, subplot_spec=gs[1], wspace=0.0, hspace=0.0)

        background_file = glb._FSLDIR_ + "/data/standard/MNI152_T1_3mm_brain.nii.gz" #TODO: works only for 3mm atlas
        background = nb.load(background_file)
        atlas = nb.load(atlas)

        nslices = background.shape[-1]
        #coords = np.linspace(int(0 * nslices), int(0.99 * nslices), 5).astype(np.uint8)
        coords = [-40, 20, 0, 20, 40] #works in MNI space
        lut2 = lut
        lut2 = np.array([0] + lut2.tolist())

        relabeled = lut2[np.array(atlas.get_data(), dtype=int)]
        atl = nb.Nifti1Image(relabeled, atlas.get_affine())
        for i, c in enumerate(coords):
            ax2 = plt.subplot(gslegend[i])
            plot_img(atl, bg_img=background, axes=ax2, display_mode='z',
                     annotate=False, cut_coords=[c], threshold=0.1, cmap=mycolors,
                     interpolation='nearest', vmin=1, vmax=7)

    if output_file is not None:
        figure = plt.gcf()
        figure.savefig(output_file, bbox_inches='tight')
        plt.close(figure)
        return os.getcwd() + '/' + output_file

    return 0