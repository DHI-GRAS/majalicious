import os
import glob
import shutil


def _find_filter_granules(src_productdir, startdate, enddate, tile, orbit):
    """
    Returns
    -------
    pandas.DataFrame
        columns date, path
        L1C .SAFE products sorted by date
    """
    pass


def _remove_duplicates(df_granules):
    pass


def _find_outputs(dst_output):
    """
    Returns
    -------
    pandas.DataFrame
        columns date, path
        L2A products sorted by date
    """
    pass


def _get_outputs_forward(df_outputs, date, nprods=8):
    """Finds `nprods` L2A products before `date` to be used in forward mode

    Returns
    -------
    pandas.DataFrame
        columns date, path
        L2A products used for backward processing
    """
    pass


def _get_outputs_backward(df_outputs, date, nprods=8):
    """Finds `nprods` L2A products after `date` to be used in backward mode

    Returns
    -------
    pandas.DataFrame
        columns date, path
        L2A products used for backward processing
    """
    pass


def link_parameter_files(src_gipp, dst_work):
    for src in src_gipp.listdir('*'):
        dst = dst_work / src.name
        src.symlink_to(dst)


def link_dem(path_dem, dst_work):
    for src in path_dem.listdir('*'):
        dst = dst_work / src.name
        src.symlink_to(dst)


def link_config_files(src_userconf, dst_userconf):
    src_userconf.symlink_to(dst_userconf)


num_backward = 8  # number of images to process in backward mode

src_userconf = '/source/input/userconf'
src_dtm = '/source/input/dtm'
src_gipp = '/source/input/gpp'
dst_work = '/destination/work'
dst_output = '/destination/output'
dst_userconf = '/destination/userconf'

maja = '/path/to/maja'
tile = '32UNG'
src_productdir = '/source/products'

startdate = None

df_granules = _find_filter_granules(src_productdir, tile=tile, startdate=startdate)

df_granules = _remove_duplicates(df_granules)


all_dates_input = df_granules['date'].values

products_by_date = {}
outputs_by_date = {}
for d in all_dates_input:
    # keep only the products with the most recent date
    products_by_date[d] = granules_filtered[ind]
    outputs_by_date[d] = "S2?_OPER_SSC_L2VALD_%s____%s.DBL.DIR" % (tile, d)


# find the first image to process

previous_date = None
for d in all_dates_input:
    try:
        nomL2init = glob.glob("%s/%s" % (dst_output, outputs_by_date[d]))[0]
        previous_date = d
    except:
        pass


# print "Most recent processed date :", previous_date

# For each product
nb_dates = len(all_dates_input)


if not(os.path.exists(dst_work)):
    os.makedirs(dst_work)

if not(os.path.exists(dst_userconf)):
    link_config_files(src_userconf, dst_userconf)

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
            os.symlink(products_by_date[date_backward], dst_work / os.path.basename(products_by_date[date_backward]))
        link_parameter_files(src_gipp, dst_work)
        link_dem(src_dtm, dst_work)

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
        os.symlink(products_by_date[previous_date], dst_work / os.path.basename(products_by_date[previous_date]))
        os.symlink(nomL2, dst_work / os.path.basename(nomL2))
        os.symlink(nomL2.replace("DBL.DIR", "HDR"), dst_work / os.path.basename(nomL2).replace("DBL.DIR", "HDR"))
        os.symlink(nomL2.replace("DIR", ""), dst_work / os.path.basename(nomL2).replace("DIR", ""))

        link_parameter_files(src_gipp, dst_work, tile)
        link_dem(src_dtm, dst_work, tile)

        commande = f"{maja} -i {dst_work} -o {dst_output} -m L2NOMINAL -ucs {dst_userconf} --TileId {tile}"
        #os.system(commande)
