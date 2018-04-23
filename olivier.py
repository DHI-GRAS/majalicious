import re
import uuid
import warnings
from collections import OrderedDict


def _find_granules(src_input, tile):
    granules = list(src_input.glob(f'*.SAFE/GRANULE/*L1C*{tile}*'))
    if not granules:
        raise RuntimeError(
            f'No granule files found in {src_input} for tile {tile}')
    return granules


def _maja_date_from_safe_name(safe_name):
    """Get the date-time that MAJA uses to name its product from a .SAFE name"""
    dateex = re.compile(r'\d{8}T\d{6}')
    if len(safe_name) < 70:
        # new format
        datestr = safe_name.split('_')[2]
    else:
        # old format
        datestr = safe_name.split('_')[5]
    if dateex.match(datestr) is None:
        raise ValueError(f'Unable to get date from {safe_name}')
    return datestr


def _date_from_maja_output(name):
    """Get the date-time string from a MAJA L2A product filename"""
    try:
        return re.search(r'\d{8}T\d{6}', name).group(0)
    except AttributeError:
        raise ValueError(f'Unable to get date string from {name}.')


def _remove_duplicate_date_entries(date_mapping):
    """Remove duplicates in a mapping of date-time strings IN-PLACE, retaining most recent

    Parameters
    ----------
    date_mapping : dict
        mapping date-time string
        of format %Y%m%dT%H%M%S
    """
    unique_dates = []
    for date_and_time in sorted(list(date_mapping), reverse=True):
        date_only = date_and_time[:8]
        if date_only in unique_dates:
            del date_mapping[date_and_time]
        else:
            unique_dates.append(date_only)


def _find_inputs(src_input, tile):
    """Find Sentinel 2 L1C products in src_input for a given tile name

    Parameters
    ----------
    src_input : pathlib.Path
        source directory
    tile : str
        tile name e.g. 32UMG

    Returns
    -------
    OrderedDict
        maps date to path
        L1C .SAFE products sorted by date
    """
    all_granules = _find_granules(src_input, tile=tile)
    pairs = []
    for granule in all_granules:
        safe = granule.parents[1]
        if not safe.name.endswith('.SAFE'):
            raise ValueError(f'Expecting .SAFE, got {safe}')
        date = _maja_date_from_safe_name(safe.name)
        pairs.append((date, safe))
    paths_by_date = OrderedDict(sorted(pairs))
    _remove_duplicate_date_entries(paths_by_date)
    return paths_by_date


def _find_outputs(dst_output, tile):
    """Find MAJA's L2A products for tile in an output directory

    Parameters
    ----------
    dst_output : Path
        destination directory
    tile : str, format \d{2}{[A-Z]{4}}
        Sentinel 2 tile name

    Returns
    -------
    OrderedDict
        maps date to path
        L2A products sorted by date
    """
    fnpattern = f'*{tile}*.DBL.DIR'
    all_paths = dst_output.glob(fnpattern)
    pairs = []
    for path in all_paths:
        date = _date_from_maja_output(path.name)
        pairs.append((date, path))
    paths_by_date = OrderedDict(sorted(pairs))
    _remove_duplicate_date_entries(paths_by_date)
    return paths_by_date


def _get_most_recent_output(date, outputs_by_date):
    """Finds the most recent L2A product before `date` to be used in forward mode

    Parameters
    ----------
    date : str
        date in format %Y%m%d
    outputs_by_date : OrderedDict
        mapping date to path

    Returns
    -------
    dict length 1
        most recent item from outputs_by_date before the given date
    """
    most_recent_date = None
    for output_date, output_path in outputs_by_date.items():
        if output_date >= date:
            break
        if (most_recent_date is None) or (output_date > most_recent_date):
            most_recent_date = output_date
    if most_recent_date is None:
        return None
    else:
        return {most_recent_date: outputs_by_date[most_recent_date]}


def _get_inputs_backward(date, inputs_by_date, num_inputs=8):
    """Get L1C products after a reference date

    Parameters
    ----------
    date : str
        reference date
    inputs_by_date : OrderedDict
        mapping date to path
        assumed to be ordered in ascending order by date
    num_inputs : int
        number of inputs to find

    Returns
    -------
    OrderedDict
        selected items from inputs_by_date
    """
    pairs = []
    for input_date, input_path in inputs_by_date.items():
        if input_date < date:
            continue
        if len(pairs) >= num_inputs:
            break
        pairs.append((input_date, input_path))
    return OrderedDict(pairs)


def _symlink_dir_contents(src_dir, dst_dir):
    """Create symlinks in dst_dir for all files in src_dir"""
    for src in src_dir.glob('*'):
        dst = dst_dir / src.name
        src.sym_link_to(dst)


def _symlink_into_dir(src_file, dst_dir):
    """Create a symlink for src_file in dst_dir"""
    dst_file = dst_dir / src_file.name
    src_file.symlink_to(dst_file)
    return dst_file


def _symlink_l2a(src_dbldir, dst_dir):
    """Create symlinks for a MAJA L2A product, including .HDR file"""
    if not src_dbldir.suffixes == ('.DBL', '.DIR'):
        raise ValueError(f'Expecting a .DBL.DIR file, got {src_dbldir}')
    dbl = src_dbldir.stem
    hdr = dbl.with_suffix('.HDR')
    for path in [src_dbldir, dbl, hdr]:
        if not path.exists():
            raise RuntimeError(f'File not found: {path}')
        _symlink_into_dir(path, dst_dir)


def be_a_symlink_guy(
        src_input, src_userconf, src_dtm, src_gipp,
        dst_work_root, dst_output, tile, maja,
        start_date=None, num_backward=8):
    """Create all necessary symlinks in dst_work and yield MAJA commands to be run sequentially

    Parameters
    ----------
    src_input : pathlib.Path
        directory containing L1C input products (.SAFE)
    src_userconf : pathlib.Path
        directory containing config files
    src_dtm : pathlib.Path
        directory containing DTM files
    src_gipp : pathlib.Path
        directory containing GIPP files
    dst_work_root : pathlib.Path
        root directory where to create work folders
        for products
    dst_output : pathlib.Path
        directory where to save L2A outputs to
    tile : str
        tile name (e.g. 32UNG)
    maja : pathlib.Path
        path to MAJA executable
    start_date : str, optional
        start processing from this date
        format %Y%m%dT%H%M%S
    num_backward : int
        number of products to process when running
        in backward mode

    Yields
    ------
    str
        command to execute MAJA
    """
    inputs_by_date = _find_inputs(src_input, tile)
    outputs_by_date = _find_outputs(dst_output, tile)
    if outputs_by_date:
        inputs_to_process = {d: path for d, path in inputs_by_date if d not in outputs_by_date}
    else:
        inputs_to_process = inputs_by_date

    if start_date is not None:
        inputs_to_process = {d: path for d, path in inputs_to_process if d >= start_date}

    minusp = dict(parents=True, exist_ok=True)
    dst_output.mkdir(**minusp)
    dst_work_root.mkdir(**minusp)

    dst_userconf = dst_work_root / 'userconf'
    if dst_userconf.exists():
        dst_userconf.unlink()
    src_userconf.symlink_to(dst_userconf)

    for date, input_path in inputs_to_process.items():

        new_uuid = str(uuid.uuid4())
        dst_work = dst_work_root / f'work_{date}_{new_uuid}'
        dst_work.mkdir(exist_ok=False)

        _symlink_dir_contents(src_dtm, dst_work)
        _symlink_dir_contents(src_gipp, dst_work)

        output = _get_most_recent_output(date, outputs_by_date)
        if output is None:
            print(f'No recent L2A product for date {date}')
            mode = 'L2BACKWARD'
            inputs_backward = _get_inputs_backward(date, inputs_by_date, num_backward)
            num_backward_found = len(inputs_backward)
            if num_backward_found < num_backward:
                warnings.warn(
                    f'Did not find {num_backward} input products for '
                    f'backward processing but only {num_backward_found}.')
            for input_path in inputs_backward.values():
                _symlink_into_dir(input_path, dst_work)
        else:
            output_date, output_path = next(iter(output.items()))
            print(f'Most recent L2A product date is {output_date}')
            mode = 'L2NOMINAL'
            _symlink_l2a(output_path, dst_work)

        cmd = f'{maja} -i {dst_work} -o {dst_output} -m {mode} -ucs {dst_userconf} --TileId {tile}'
        yield cmd

        # update outputs
        outputs_by_date = _find_outputs(dst_output)


if __name__ == '__main__':
    import pathlib
    import click

    class PathlibPath(click.ParamType):
        name = 'path'

        def convert(self, value, param, ctx):
            if value:
                return pathlib.Path(value)
            else:
                return value

    @click.command()
    @click.option(
        '--src-input', type=PathlibPath(), required=True, help='dir containing L1C .SAFE')
    @click.option('--src-userconf', type=PathlibPath(), required=True, help='userconf dir')
    @click.option('--src-dtm', type=PathlibPath(), required=True, help='DTM dir')
    @click.option('--src-gipp', type=PathlibPath(), required=True, help='GIPP dir')
    @click.option('--dst-work-root', type=PathlibPath(), required=True, help='Work root dir')
    @click.option('--dst-output', type=PathlibPath(), required=True, help='Output directory')
    @click.option('--tile', required=True, help='Tile name (e.g. 32UNG)')
    @click.option('--maja', type=PathlibPath(), required=True, help='Path to maja executable')
    def cli(**kwargs):
        """Create symlinks and run MAJA"""
        import subprocess
        for cmd in be_a_symlink_guy(**kwargs):
            subprocess.run(cmd, check=True)

    cli()
