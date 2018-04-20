import os
import re
import glob
import shutil
from collections import OrderedDict


def _find_granules(src_input, tile):
    granules = list(src_input.glob(f'*.SAFE/GRANULE/*L1C*{tile}*'))
    if not granules:
        raise RuntimeError(
            f'No granule files found in {src_input} for tile {tile}')
    return granules


def _maja_date_from_safe_name(safe_name):
    """Get the date that MAJA uses to name its product from a .SAFE name"""
    dateex = re.compile(r'\d{8}T\d{6}')
    if len(safe_name) < 70:
        # new format
        datestr = safe_name.split('_')[2]
    else:
        # old format
        datestr = safe_name.split('_')[5]
    if dateex.match(datestr) is None:
        raise ValueError(f'Unable to get date from {path_safe}')
    return datestr


def _find_filter_granules(src_input, startdate, enddate, tile, orbit):
    """
    Returns
    -------
    OrderedDict
        maps date to path
        L1C .SAFE products sorted by date
    """
    all_graules = _find_granules(src_input, tile=tile)

    pairs = []
    for granule in all_granules:
        safe = granule.parents[1]
        if not safe.name.endswith('.SAFE'):
            raise ValueError(f'Expecting .SAFE, got {safe}')
        date = _maja_date_from_safe_name(safe.name)

        pairs.append((date, safe))

    return OrderedDict(sorted(pairs))


def _remove_date_duplicates(dates_paths):
    dates_sorted = sorted(list(dates_paths))
    for date_and_time in dates_sorted[::-1]:
        date_only = date_and_time[:8]


def _find_outputs(dst_output):
    """
    Returns
    -------
    OrderedDict
        maps date to path
        L2A products sorted by date
    """
    pass


def _get_outputs_forward(df_outputs, date, nprods=8):
    """Finds `nprods` L2A products before `date` to be used in forward mode

    Returns
    -------
    OrderedDict
        columns date, path
        L2A products used for backward processing
    """
    pass


def _get_outputs_backward(df_outputs, date, nprods=8):
    """Finds `nprods` L2A products after `date` to be used in backward mode

    Returns
    -------
    OrderedDict
        columns date, path
        L2A products used for backward processing
    """
    pass


def _link_parameter_files(src_gipp, dst_work):
    for src in src_gipp.glob('*'):
        dst = dst_work / src.name
        src.sym_link_to(dst)


def _link_dem(path_dem, dst_work):
    for src in path_dem.glob('*'):
        dst = dst_work / src.name
        src.sym_link_to(dst)


def _link_config_files(src_userconf, dst_userconf):
    src_userconf.sym_link_to(dst_userconf)


def make_symlinks_forward(date, inputs_by_date, outputs_by_date, dst_work):
    pass


def make_symlinks_backward(date, inputs_by_date, outputs_by_date, dst_work):
    pass


def generate_maja_commands(src_input, dst_output, num_backward=8, **filterkw):
    inputs_by_date = _find_filter_granules(src_input, **filterkw)

    outputs_by_date = _find_outputs(dst_output)

    inputs_to_process = {d: path for d, path in inputs_by_date if d not in outputs_by_date}

    for date, input_path in inputs_to_process.items():
        pass


num_backward = 8  # number of images to process in backward mode

src_userconf = '/source/input/userconf'
src_dtm = '/source/input/dtm'
src_gipp = '/source/input/gpp'
dst_work = '/destination/work'
dst_output = '/destination/output'
dst_userconf = '/destination/userconf'

maja = '/path/to/maja'
tile = '32UNG'
src_input = '/source/products'

startdate = None

df_granules = _find_filter_granules(src_input, tile=tile, startdate=startdate)

df_granules = _remove_date_duplicates(df_granules)


all_dates_input = df_granules['date'].values

inputs_by_date = {}
outputs_by_date = {}
for d in all_dates_input:
    # keep only the products with the most recent date
    inputs_by_date[d] = granules_filtered[ind]
    outputs_by_date[d] = "S2?_OPER_SSC_L2VALD_%s____%s.DBL.DIR" % (tile, d)


# print "Most recent processed date :", previous_date

# For each product
nb_dates = len(all_dates_input)


if not(os.path.exists(dst_work)):
    os.makedirs(dst_work)

if not(os.path.exists(dst_userconf)):
    _link_config_files(src_userconf, dst_userconf)

for i in range(nb_dates):
    d = all_dates_input[i]
    if d <= previous_date:
        continue

    if os.path.exists(dst_work):
        shutil.rmtree(dst_work)
    os.makedirs(dst_work)

    if i == 0:
        # BACKWARD MODE
        nb_prod_backward = min(len(all_dates_input), num_backward)
        for date_backward in all_dates_input[0:nb_prod_backward]:
            # print "#### dates à traiter", date_backward
            os.symlink(inputs_by_date[date_backward], dst_work / os.path.basename(inputs_by_date[date_backward]))
        _link_parameter_files(src_gipp, dst_work)
        _link_dem(src_dtm, dst_work)

        commande = f"{maja} -i {dst_work} -o {dst_output} -m L2BACKWARD -ucs {dst_userconf} --TileId {tile}"
        #os.system(commande)
    else:
        # NOMINAL MODE
        # Search for previous L2 product
        for previous_date in all_dates_input[0:i]:
            nom_courant = "%s/%s" % (dst_output,
                                     outputs_by_date[previous_date])
            try:
                nomL2 = glob.glob(nom_courant)[0]
                # "Previous L2 names, per increasing date :", nomL2
            except:
                # print "pas de L2 pour :", nom_courant
                pass
        # print "previous L2 : ", nomL2
        os.symlink(inputs_by_date[previous_date], dst_work / os.path.basename(inputs_by_date[previous_date]))
        os.symlink(nomL2, dst_work / os.path.basename(nomL2))
        os.symlink(nomL2.replace("DBL.DIR", "HDR"), dst_work / os.path.basename(nomL2).replace("DBL.DIR", "HDR"))
        os.symlink(nomL2.replace("DIR", ""), dst_work / os.path.basename(nomL2).replace("DIR", ""))

        _link_parameter_files(src_gipp, dst_work, tile)
        _link_dem(src_dtm, dst_work, tile)

        commande = f"{maja} -i {dst_work} -o {dst_output} -m L2NOMINAL -ucs {dst_userconf} --TileId {tile}"
        #os.system(commande)
